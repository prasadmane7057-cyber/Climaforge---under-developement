"""Download and normalize NOAA GHCN-Daily stations for M12 rainfall research."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

BASE_URL = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access"
STATIONS = {
    "USW00094728": {"role": "original", "region": "Northeast US"},
    "USW00012839": {"role": "candidate", "region": "Miami / Southeast US"},
    "USW00024233": {"role": "candidate", "region": "Seattle / Pacific Northwest US"},
    "USW00094846": {"role": "candidate", "region": "Chicago / Great Lakes US"},
    "USW00023174": {"role": "candidate", "region": "Los Angeles / Southwest US"},
    "USW00012960": {"role": "candidate", "region": "Houston / Gulf Coast US"},
}


def download_station(station_id: str, raw_path: Path) -> None:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{station_id}.csv"
    with urlopen(url, timeout=180) as response, raw_path.open("wb") as output:
        output.write(response.read())


def normalize_station(station_id: str, raw_path: Path, role: str, region: str) -> pd.DataFrame:
    frame = pd.read_csv(raw_path, low_memory=False)
    required = {"DATE", "LATITUDE", "LONGITUDE", "ELEVATION", "NAME", "PRCP"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{station_id} missing columns: {sorted(missing)}")

    frame["DATE"] = pd.to_datetime(frame["DATE"], errors="coerce")
    prcp_tenths = pd.to_numeric(frame["PRCP"], errors="coerce")
    normalized = pd.DataFrame({
        "station_id": station_id,
        "station_name": frame["NAME"],
        "latitude": pd.to_numeric(frame["LATITUDE"], errors="coerce"),
        "longitude": pd.to_numeric(frame["LONGITUDE"], errors="coerce"),
        "elevation_m": pd.to_numeric(frame["ELEVATION"], errors="coerce"),
        "observation_date": frame["DATE"],
        "prcp_mm": prcp_tenths / 10.0,
        "prcp_missing": prcp_tenths.isna(),
        "prcp_attributes": frame.get("PRCP_ATTRIBUTES", ""),
        "source_url": f"{BASE_URL}/{station_id}.csv",
        "region": region,
        "source_role": role,
    })
    normalized = normalized.dropna(subset=["observation_date"])
    normalized = normalized.sort_values(["observation_date", "station_id"])
    normalized = normalized.drop_duplicates(["station_id", "observation_date"], keep="first")
    return normalized.reset_index(drop=True)


def station_audit(frame: pd.DataFrame) -> dict:
    station_id = str(frame["station_id"].iloc[0])
    valid_prcp = frame["prcp_mm"].notna()
    current = frame["prcp_mm"].dropna()
    next_day = frame["prcp_mm"].shift(-1).dropna()
    date_count = frame["observation_date"].nunique()
    expected_dates = pd.date_range(frame["observation_date"].min(), frame["observation_date"].max(), freq="D")
    completeness = float(valid_prcp.mean() * 100.0)
    record_years = (
        frame["observation_date"].max() - frame["observation_date"].min()
    ).days / 365.2425

    return {
        "station_id": station_id,
        "station_name": str(frame["station_name"].iloc[0]),
        "region": str(frame["region"].iloc[0]),
        "latitude": float(frame["latitude"].iloc[0]),
        "longitude": float(frame["longitude"].iloc[0]),
        "date_start": str(frame["observation_date"].min().date()),
        "date_end": str(frame["observation_date"].max().date()),
        "record_years": round(record_years, 2),
        "observation_rows": len(frame),
        "unique_observation_dates": date_count,
        "missing_prcp_rows": int(frame["prcp_missing"].sum()),
        "prcp_completeness_pct": round(completeness, 4),
        "date_gap_count": max(0, len(expected_dates) - date_count),
        "observed_heavy_ge50": int((current >= 50.0).sum()),
        "observed_critical_ge100": int((current >= 100.0).sum()),
        "next_day_heavy_ge50": int((next_day >= 50.0).sum()),
        "next_day_critical_ge100": int((next_day >= 100.0).sum()),
        "max_prcp_mm": float(current.max()) if len(current) else None,
    }


def split_audit(frame: pd.DataFrame) -> dict:
    ordered = frame.sort_values(["observation_date", "station_id"]).reset_index(drop=True)
    train_end = int(len(ordered) * 0.60)
    validation_end = int(len(ordered) * 0.80)
    partitions = {
        "train": ordered.iloc[:train_end],
        "validation": ordered.iloc[train_end:validation_end],
        "test": ordered.iloc[validation_end:],
    }
    result = {}
    for name, part in partitions.items():
        valid = part["prcp_mm"].dropna()
        result[name] = {
            "rows": len(part),
            "date_start": str(part["observation_date"].min().date()),
            "date_end": str(part["observation_date"].max().date()),
            "stations": int(part["station_id"].nunique()),
            "missing_prcp": int(part["prcp_missing"].sum()),
            "heavy_ge50": int((valid >= 50.0).sum()),
            "critical_ge100": int((valid >= 100.0).sum()),
        }
    result["station_holdout"] = {
        "strategy": "Each station is tested after training/validation on all remaining stations; final station-held-out aggregate is not a pooled probability estimate.",
        "splits": {
            station_id: {
                "train_rows": int((ordered["station_id"] != station_id).sum()),
                "test_rows": int((ordered["station_id"] == station_id).sum()),
                "test_heavy_ge50": int((
                    ordered.loc[ordered["station_id"] == station_id, "prcp_mm"] >= 50.0
                ).sum()),
                "test_missing_prcp": int(ordered.loc[
                    ordered["station_id"] == station_id, "prcp_missing"
                ].sum()),
            }
            for station_id in sorted(ordered["station_id"].unique())
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and normalize NOAA GHCN-Daily stations for M12")
    parser.add_argument("--original", type=Path, default=Path("backend/data/nyc_central_park.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("backend/data/noaa_expanded"))
    parser.add_argument("--expanded", type=Path, default=Path("backend/data/noaa_expanded_rainfall.csv"))
    parser.add_argument("--report", type=Path, default=Path("backend/models/noaa_expansion_report.json"))
    args = parser.parse_args()

    raw_dir = args.output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    station_reports = []
    downloads = {}

    for station_id, station_meta in STATIONS.items():
        raw_path = raw_dir / f"{station_id}.csv"
        if station_id == "USW00094728":
            if not args.original.exists():
                raise FileNotFoundError(f"Original Central Park dataset not found: {args.original}")
            raw_path = args.original
        elif not raw_path.exists():
            download_station(station_id, raw_path)
            downloads[station_id] = True
        else:
            downloads[station_id] = False

        station = normalize_station(
            station_id, raw_path, station_meta["role"], station_meta["region"]
        )
        frames.append(station)
        station_reports.append(station_audit(station))

    expanded = pd.concat(frames, ignore_index=True)
    expanded = expanded.sort_values(["observation_date", "station_id"]).reset_index(drop=True)
    args.expanded.parent.mkdir(parents=True, exist_ok=True)
    expanded.to_csv(args.expanded, index=False)

    quality = []
    selected = []
    for audit in station_reports:
        passed = (
            audit["record_years"] >= 50.0
            and audit["prcp_completeness_pct"] >= 95.0
            and audit["observation_rows"] >= 18250
        )
        audit["quality_passed"] = passed
        if passed:
            selected.append(audit["station_id"])
        quality.append(audit)

    heavy = expanded["prcp_mm"].dropna()
    report = {
        "dataset": str(args.expanded),
        "source": "NOAA NCEI GHCN-Daily station CSV files",
        "source_base_url": BASE_URL,
        "downloaded_this_run": downloads,
        "preserved_original_dataset": str(args.original),
        "units": {
            "prcp_mm": "PRCP tenths of mm divided by 10; missing remains null",
            "latitude": "decimal degrees",
            "longitude": "decimal degrees",
            "elevation_m": "meters",
        },
        "missing_value_policy": "Missing PRCP values remain NaN and are marked by prcp_missing=true; they are never converted to zero.",
        "stations": quality,
        "quality_thresholds": {
            "record_years": 50,
            "prcp_completeness_pct": 95,
            "observation_rows": 18250,
        },
        "stations_passing_quality": selected,
        "total_observations": len(expanded),
        "unique_station_date_pairs": int(expanded[["station_id", "observation_date"]].drop_duplicates().shape[0]),
        "missing_prcp_observations": int(expanded["prcp_missing"].sum()),
        "missing_prcp_pct": round(float(expanded["prcp_missing"].mean() * 100.0), 4),
        "heavy_ge50_observations": int((heavy >= 50.0).sum()),
        "critical_ge100_observations": int((heavy >= 100.0).sum()),
        "max_prcp_mm": float(heavy.max()),
        "chronological_and_station_holdout": split_audit(expanded),
        "production_model_changed": False,
        "binary_experimental_model_changed": False,
        "quality_summary": (
            "Suitable for controlled data-quality experiments only. "
            "No production retraining or deployment was performed."
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
