"""M14 experimental meteorological feature enhancement for heavy rainfall."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


STATIONS = [
    "USW00094728",
    "USW00012839",
    "USW00024233",
    "USW00023174",
    "USW00012960",
]
BASE_FEATURES = [
    "prcp_mm", "prcp_lag1_mm", "prcp_rolling_3d_mean_mm",
    "prcp_rolling_7d_mean_mm", "prcp_rolling_14d_mean_mm",
    "latitude", "longitude", "elevation_m",
]
TEMPERATURE_FEATURES = ["tmax_c", "tmin_c"]
ATMOSPHERIC_FEATURES = [
    "awnd_ms", "wsf2_ms", "wsf5_ms", "wdf2_deg", "wdf5_deg",
    "rhav_pct", "rhmn_pct", "rhmx_pct", "aslp_hpa", "astp_hpa",
]
SEASONAL_FEATURES = ["day_of_year_sin", "day_of_year_cos", "month_sin", "month_cos"]


def merge_meteorological_features(expanded_path: Path, output_path: Path) -> pd.DataFrame:
    expanded = pd.read_csv(expanded_path, low_memory=False)
    expanded["observation_date"] = pd.to_datetime(expanded["observation_date"], errors="coerce")
    frames = []
    source_stats = {}

    for station_id in STATIONS:
        if station_id == "USW00094728":
            source_path = Path("backend/data/nyc_central_park.csv")
        else:
            source_path = Path("backend/data/noaa_expanded/raw") / f"{station_id}.csv"
        raw = pd.read_csv(source_path, low_memory=False)
        raw["DATE"] = pd.to_datetime(raw["DATE"], errors="coerce")
        keep = ["DATE", *[column for column in [
            "TMAX", "TMIN", "TAVG", "AWND", "WSF2", "WSF5", "WDF2", "WDF5",
            "RHAV", "RHMN", "RHMX", "ASLP", "ASTP",
        ] if column in raw.columns]]
        station = raw[keep].rename(columns={"DATE": "observation_date"}).copy()

        for column in station.columns:
            if column != "observation_date":
                station[column] = pd.to_numeric(station[column], errors="coerce")

        station["station_id"] = station_id
        station["tmax_c"] = station["TMAX"] / 10.0 if "TMAX" in station else np.nan
        station["tmin_c"] = station["TMIN"] / 10.0 if "TMIN" in station else np.nan
        station["tavg_c"] = station["TAVG"] / 10.0 if "TAVG" in station else np.nan
        station["awnd_ms"] = station["AWND"] / 10.0 if "AWND" in station else np.nan
        station["wsf2_ms"] = station["WSF2"] / 10.0 if "WSF2" in station else np.nan
        station["wsf5_ms"] = station["WSF5"] / 10.0 if "WSF5" in station else np.nan
        station["wdf2_deg"] = station["WDF2"] if "WDF2" in station else np.nan
        station["wdf5_deg"] = station["WDF5"] if "WDF5" in station else np.nan
        station["rhav_pct"] = station["RHAV"] / 10.0 if "RHAV" in station else np.nan
        station["rhmn_pct"] = station["RHMN"] / 10.0 if "RHMN" in station else np.nan
        station["rhmx_pct"] = station["RHMX"] / 10.0 if "RHMX" in station else np.nan
        station["aslp_hpa"] = station["ASLP"] / 10.0 if "ASLP" in station else np.nan
        station["astp_hpa"] = station["ASTP"] / 10.0 if "ASTP" in station else np.nan
        station_columns = [
            "observation_date", "station_id", "tmax_c", "tmin_c", "tavg_c",
            "awnd_ms", "wsf2_ms", "wsf5_ms", "wdf2_deg", "wdf5_deg",
            "rhav_pct", "rhmn_pct", "rhmx_pct", "aslp_hpa", "astp_hpa",
        ]
        station = station[station_columns]
        source_stats[station_id] = {
            column: {
                "available_values": int(station[column].notna().sum()),
                "missing_values": int(station[column].isna().sum()),
                "coverage_pct": round(float(station[column].notna().mean() * 100.0), 4),
            }
            for column in station_columns
            if column not in ("observation_date", "station_id")
        }
        frames.append(station)

    meteorological = pd.concat(frames, ignore_index=True)
    merged = expanded.merge(
        meteorological,
        on=["station_id", "observation_date"],
        how="left",
        validate="one_to_one",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return merged, source_stats


def prepare_model_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame[frame["station_id"].isin(STATIONS)].copy()
    frame = frame.sort_values(["station_id", "observation_date"]).reset_index(drop=True)
    frame["prcp_mm"] = pd.to_numeric(frame["prcp_mm"], errors="coerce")

    for station_id, station in frame.groupby("station_id", sort=False):
        indices = station.index
        frame.loc[indices, "prcp_lag1_mm"] = station["prcp_mm"].shift(1)
        for days in (3, 7, 14):
            historical = station["prcp_mm"].shift(1)
            frame.loc[indices, f"prcp_rolling_{days}d_mean_mm"] = (
                historical.rolling(days, min_periods=1).mean()
            )

    frame["next_day_prcp_mm"] = frame.groupby("station_id", sort=False)["prcp_mm"].shift(-1)
    next_dates = frame.groupby("station_id", sort=False)["observation_date"].shift(-1)
    consecutive = next_dates.eq(frame["observation_date"] + pd.Timedelta(days=1))
    frame["target"] = np.nan
    valid_target = frame["next_day_prcp_mm"].notna() & consecutive & frame["prcp_mm"].notna()
    frame.loc[valid_target, "target"] = (
        frame.loc[valid_target, "next_day_prcp_mm"] >= 50.0
    ).astype(int)
    frame = frame.dropna(subset=["target"]).copy()

    day = frame["observation_date"].dt.day_of_year
    frame["day_of_year_sin"] = np.sin(2 * np.pi * day / 365.25)
    frame["day_of_year_cos"] = np.cos(2 * np.pi * day / 365.25)
    month = frame["observation_date"].dt.month
    frame["month_sin"] = np.sin(2 * np.pi * month / 12.0)
    frame["month_cos"] = np.cos(2 * np.pi * month / 12.0)
    return frame.reset_index(drop=True)


def make_pipeline(features: list[str], model_name: str) -> Pipeline:
    if model_name == "hist_gradient":
        numeric = SimpleImputer(strategy="median")
        return Pipeline([
            ("preprocessor", ColumnTransformer(
                [("numeric", numeric, features)],
                remainder="drop",
            )),
            ("classifier", HistGradientBoostingClassifier(
                learning_rate=0.08, max_iter=100, max_leaf_nodes=31,
                class_weight="balanced", random_state=42,
            )),
        ])

    numeric_features = [feature for feature in features if feature != "station_id"]
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    transformers = [("numeric", numeric, numeric_features)]
    if "station_id" in features:
        transformers.append(("station", categorical, ["station_id"]))
    return Pipeline([
        ("preprocessor", ColumnTransformer(transformers, remainder="drop")),
        ("classifier", LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42, solver="liblinear",
        )),
    ])


def tune_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, dict]:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    candidates = thresholds[
        np.linspace(0, len(thresholds) - 1, num=min(120, len(thresholds)), dtype=int)
    ].tolist() if len(thresholds) else []
    candidates.extend([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    candidates = sorted(set(round(float(value), 6) for value in candidates if 0 <= value <= 1))

    best = None
    for threshold in candidates:
        metrics = evaluate_binary(y_true, probabilities, threshold)
        score = (metrics["f2"], metrics["pr_auc"], metrics["f1"])
        if best is None or score > best["score"]:
            best = {"score": score, "metrics": metrics, "threshold": threshold}
    return float(best["threshold"]), best["metrics"]


def evaluate_binary(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    precision = precision_score(y_true, predicted, zero_division=0)
    recall = recall_score(y_true, predicted, zero_division=0)
    f1 = f1_score(y_true, predicted, zero_division=0)
    f2 = 5 * precision * recall / (4 * precision + recall) if precision + recall else 0.0
    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "f2": float(f2),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else 0.0,
        "confusion_matrix": {
            "labels": ["NORMAL", "HEAVY_RAIN"],
            "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        },
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "heavy_rain_events": int(y_true.sum()),
        "normal_events": int((1 - y_true).sum()),
    }


def per_station(frame: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> dict:
    return {
        station: evaluate_binary(
            frame.loc[mask, "target"].to_numpy(dtype=int),
            probabilities[mask],
            threshold,
        )
        for station, mask in (
            (station, frame["station_id"].to_numpy() == station)
            for station in sorted(frame["station_id"].unique())
        )
    }


def distribution(frame: pd.DataFrame) -> dict:
    return {
        "rows": len(frame),
        "heavy_rain_events": int(frame["target"].sum()),
        "normal_events": int((1 - frame["target"]).sum()),
        "by_station": {
            station: {
                "rows": len(station_frame),
                "heavy_rain_events": int(station_frame["target"].sum()),
            }
            for station, station_frame in frame.groupby("station_id")
        },
    }


def run_feature_experiment(frame: pd.DataFrame, features: list[str], experiment_name: str,
                           output_dir: Path, held_out_station: str | None = None) -> dict:
    if held_out_station:
        available = frame[frame["station_id"] != held_out_station].copy()
        test = frame[frame["station_id"] == held_out_station].copy()
        dates = np.sort(available["observation_date"].unique())
        train_end = dates[int(len(dates) * 0.80) - 1]
        train = available[available["observation_date"] <= train_end].copy()
        validation = available[available["observation_date"] > train_end].copy()
    else:
        dates = np.sort(frame["observation_date"].unique())
        train_end = dates[int(len(dates) * 0.60) - 1]
        validation_end = dates[int(len(dates) * 0.80) - 1]
        train = frame[frame["observation_date"] <= train_end].copy()
        validation = frame[
            (frame["observation_date"] > train_end)
            & (frame["observation_date"] <= validation_end)
        ].copy()
        test = frame[frame["observation_date"] > validation_end].copy()

    comparison = {}
    fitted = {}
    for model_name in ("logistic", "hist_gradient"):
        model_features = features if model_name == "logistic" else [
            feature for feature in features if feature != "station_id"
        ]
        model = make_pipeline(model_features, model_name)
        model.fit(train[model_features], train["target"])
        probabilities = model.predict_proba(validation[model_features])[:, 1]
        threshold, validation_metrics = tune_threshold(
            validation["target"].to_numpy(dtype=int), probabilities
        )
        comparison[model_name] = {"validation": validation_metrics}
        fitted[model_name] = (model, threshold, model_features)

    selected_name = max(
        comparison,
        key=lambda name: (
            comparison[name]["validation"]["f2"],
            comparison[name]["validation"]["pr_auc"],
            comparison[name]["validation"]["f1"],
        ),
    )
    model, threshold, model_features = fitted[selected_name]
    test_probabilities = model.predict_proba(test[model_features])[:, 1]
    test_metrics = evaluate_binary(
        test["target"].to_numpy(dtype=int), test_probabilities, threshold
    )
    test_metrics["per_station"] = per_station(test, test_probabilities, threshold)

    safe_name = experiment_name.replace(" ", "_")
    artifact_name = (
        f"m14_{safe_name}_heldout_{held_out_station}.joblib"
        if held_out_station else f"m14_{safe_name}_chronological.joblib"
    )
    joblib.dump(model, output_dir / artifact_name)

    return {
        "features": features,
        "partition_distributions": {
            "train": distribution(train),
            "validation": distribution(validation),
            "test": distribution(test),
        },
        "model_comparison_validation": comparison,
        "selected_model": selected_name,
        "selected_threshold": threshold,
        "test": test_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="M14 predictive feature enhancement research")
    parser.add_argument("--expanded", type=Path, default=Path("backend/data/noaa_expanded_rainfall.csv"))
    parser.add_argument("--feature-dataset", type=Path, default=Path("backend/data/m14_predictive_features.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("backend/models"))
    args = parser.parse_args()

    frame, source_stats = merge_meteorological_features(args.expanded, args.feature_dataset)
    frame = prepare_model_frame(frame)

    feature_sets = {
        "precipitation_only": ["station_id", *BASE_FEATURES],
        "precipitation_temperature": ["station_id", *BASE_FEATURES, *TEMPERATURE_FEATURES],
        "precipitation_atmospheric": ["station_id", *BASE_FEATURES, *ATMOSPHERIC_FEATURES],
        "precipitation_seasonal": ["station_id", *BASE_FEATURES, *SEASONAL_FEATURES],
    }

    chronological = {}
    held_out = {}
    for name, features in feature_sets.items():
        chronological[name] = run_feature_experiment(
            frame, features, name, args.output_dir, held_out_station=None
        )
        held_out[name] = {
            station: run_feature_experiment(
                frame, features, name, args.output_dir, held_out_station=station
            )
            for station in STATIONS
        }

    missing_stats = {}
    for column in ["prcp_mm", *TEMPERATURE_FEATURES, *ATMOSPHERIC_FEATURES, *SEASONAL_FEATURES]:
        missing_stats[column] = {
            "missing_values": int(frame[column].isna().sum()),
            "coverage_pct": round(float(frame[column].notna().mean() * 100.0), 4),
        }

    report = {
        "experiment": "M14 predictive feature enhancement",
        "production_model_changed": False,
        "target": {
            "NORMAL": "next-day precipitation below 50 mm",
            "HEAVY_RAIN": "next-day precipitation at least 50 mm",
        },
        "data_sources": {
            "base": "NOAA NCEI GHCN-Daily station CSV files",
            "meteorological_elements": [
                "TMAX/TMIN/TAVG", "AWND", "WSF2/WSF5", "WDF2/WDF5",
                "RHAV/RHMN/RHMX", "ASLP/ASTP",
            ],
            "unit_limits": [
                "TMAX/TMIN/TAVG tenths of degrees Celsius divided by 10",
                "AWND and WSF tenths of metres per second divided by 10",
                "RH values divided by 10 when sourced as tenths of percent",
                "ASLP/ASTP tenths of hectopascals divided by 10",
                "Missing values remain missing; no target-driven interpolation used",
            ],
        },
        "feature_dataset": str(args.feature_dataset),
        "valid_model_rows": len(frame),
        "source_missing_statistics_by_station": source_stats,
        "model_missing_statistics": missing_stats,
        "methodology": {
            "chronological": "Unique-date 60/20/20 split matching M13 methodology",
            "station_held_out": "Each station omitted completely; remaining stations use an 80/20 chronological validation split",
            "threshold_tuning": "Validation-only F2-first threshold selection",
            "rolling_features": "Station-local shifted precipitation only; no station boundary or future target leakage",
            "same_day_weather": "Temperature, wind, humidity and pressure are observations on the prediction date; next-day precipitation is never used as an input",
            "m13_comparison": "backend/models/multi_station_heavy_rain_experiment.json",
        },
        "chronological": chronological,
        "station_held_out": held_out,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "m14_predictive_feature_experiment.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "feature_dataset": str(args.feature_dataset),
        "report": str(report_path),
        "chronological": {
            name: {
                "selected_model": result["selected_model"],
                "precision": result["test"]["precision"],
                "recall": result["test"]["recall"],
                "f1": result["test"]["f1"],
                "pr_auc": result["test"]["pr_auc"],
                "false_positive_rate": result["test"]["false_positive_rate"],
                "false_negative_rate": result["test"]["false_negative_rate"],
            }
            for name, result in chronological.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
