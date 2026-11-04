"""M13 multi-station binary heavy-rainfall research experiment."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
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
RAW_NUMERIC_FEATURES = [
    "prcp_mm",
    "latitude",
    "longitude",
    "elevation_m",
]
NUMERIC_FEATURES = [
    "prcp_mm",
    "prcp_lag1_mm",
    "prcp_rolling_3d_mean_mm",
    "prcp_rolling_7d_mean_mm",
    "prcp_rolling_14d_mean_mm",
    "latitude",
    "longitude",
    "elevation_m",
]
FEATURES = ["station_id", *NUMERIC_FEATURES]


def prepare_frame(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, low_memory=False)
    required = {
        "station_id", "observation_date", "prcp_mm", "prcp_missing",
        "latitude", "longitude", "elevation_m",
    }
    missing_columns = required.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Expanded dataset missing columns: {sorted(missing_columns)}")

    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    for column in RAW_NUMERIC_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["station_id"] = frame["station_id"].astype(str)
    frame = frame[frame["station_id"].isin(STATIONS)].copy()
    frame = frame.dropna(subset=["observation_date", "station_id"])
    frame = frame.sort_values(["station_id", "observation_date"]).drop_duplicates(
        ["station_id", "observation_date"]
    )
    frame = frame.reset_index(drop=True)

    frame["prcp_lag1_mm"] = frame.groupby("station_id", sort=False)["prcp_mm"].shift(1)
    for days in (3, 7, 14):
        historical = frame.groupby("station_id", sort=False)["prcp_mm"].shift(1)
        rolling_values = []
        for _, station_frame in frame.groupby("station_id", sort=False):
            station_historical = station_frame["prcp_mm"].shift(1)
            rolling_values.append(
                station_historical.rolling(days, min_periods=1).mean()
            )
        frame[f"prcp_rolling_{days}d_mean_mm"] = pd.concat(rolling_values).sort_index()

    frame["next_day_prcp_mm"] = frame.groupby("station_id", sort=False)["prcp_mm"].shift(-1)
    next_dates = frame.groupby("station_id", sort=False)["observation_date"].shift(-1)
    consecutive = next_dates.eq(frame["observation_date"] + pd.Timedelta(days=1))
    frame["binary_target"] = np.where(
        frame["next_day_prcp_mm"].ge(50.0), "HEAVY_RAIN", "NORMAL"
    )
    invalid_target = frame["next_day_prcp_mm"].isna() | ~consecutive
    frame.loc[invalid_target, "binary_target"] = np.nan

    frame = frame.dropna(subset=["binary_target"]).copy()
    frame["binary_target_int"] = (frame["binary_target"] == "HEAVY_RAIN").astype(int)
    return frame.reset_index(drop=True)


def make_pipeline(classifier, hist_gradient: bool = False) -> Pipeline:
    if hist_gradient:
        numeric = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
        ])
        preprocessor = ColumnTransformer([
            ("numeric", numeric, NUMERIC_FEATURES),
        ], remainder="drop")
        return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])

    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("station", categorical, ["station_id"]),
    ])
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])


def candidates() -> dict[str, object]:
    return {
        "logistic_weighted": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42, solver="liblinear",
        ),
        "rf_balanced_subsample": RandomForestClassifier(
            n_estimators=100, max_depth=14, min_samples_leaf=3,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        ),
        "extra_trees_balanced": ExtraTreesClassifier(
            n_estimators=100, max_depth=14, min_samples_leaf=3,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
        "hist_gradient_weighted": HistGradientBoostingClassifier(
            learning_rate=0.08, max_iter=100, max_leaf_nodes=31,
            class_weight="balanced", random_state=42,
        ),
    }


def tune_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, dict]:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    candidates = thresholds[
        np.linspace(0, len(thresholds) - 1, num=min(120, len(thresholds)), dtype=int)
    ].tolist() if len(thresholds) else []
    candidates.extend([0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80])
    candidates = sorted(set(round(float(value), 6) for value in candidates if 0 <= value <= 1))

    best = None
    for threshold in candidates:
        metrics = binary_metrics(y_true, probabilities, threshold)
        score = (
            metrics["f2"],
            metrics["pr_auc"],
            metrics["f1"],
        )
        if best is None or score > best["score"]:
            best = {"score": score, "threshold": threshold, "metrics": metrics}
    return float(best["threshold"]), best["metrics"]


def binary_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    precision = precision_score(y_true, predicted, zero_division=0)
    recall = recall_score(y_true, predicted, zero_division=0)
    f1 = f1_score(y_true, predicted, zero_division=0)
    pr_auc = average_precision_score(y_true, probabilities)
    f2 = 5 * precision * recall / (4 * precision + recall) if precision + recall else 0.0
    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "f2": float(f2),
        "pr_auc": float(pr_auc),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else 0.0,
        "confusion_matrix": {
            "labels": ["NORMAL", "HEAVY_RAIN"],
            "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        },
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "heavy_rain_events": int((y_true == 1).sum()),
        "normal_events": int((y_true == 0).sum()),
    }


def per_station_metrics(frame: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> dict:
    result = {}
    for station_id in sorted(frame["station_id"].unique()):
        mask = frame["station_id"].to_numpy() == station_id
        result[station_id] = binary_metrics(
            frame["binary_target_int"].to_numpy()[mask],
            probabilities[mask],
            threshold,
        )
    return result


def distribution(frame: pd.DataFrame) -> dict:
    counts = frame["binary_target"].value_counts().to_dict()
    return {
        "rows": len(frame),
        "heavy_rain_events": int((frame["binary_target_int"] == 1).sum()),
        "normal_events": int((frame["binary_target_int"] == 0).sum()),
        "counts": {str(key): int(value) for key, value in counts.items()},
        "by_station": {
            station: {
                "rows": int(len(station_frame)),
                "heavy_rain_events": int(station_frame["binary_target_int"].sum()),
            }
            for station, station_frame in frame.groupby("station_id")
        },
    }


def chronological_experiment(frame: pd.DataFrame, output_dir: Path) -> dict:
    dates = np.sort(frame["observation_date"].unique())
    train_end_date = dates[int(len(dates) * 0.60) - 1]
    validation_end_date = dates[int(len(dates) * 0.80) - 1]

    train = frame[frame["observation_date"] <= train_end_date].copy()
    validation = frame[
        (frame["observation_date"] > train_end_date)
        & (frame["observation_date"] <= validation_end_date)
    ].copy()
    test = frame[frame["observation_date"] > validation_end_date].copy()

    comparison = {}
    fitted = {}
    for name, classifier in candidates().items():
        is_hist_gradient = name == "hist_gradient_weighted"
        model = make_pipeline(classifier, hist_gradient=is_hist_gradient)
        model.fit(train[FEATURES], train["binary_target_int"])
        probabilities = model.predict_proba(validation[FEATURES])[:, 1]
        threshold, validation_metrics = tune_threshold(
            validation["binary_target_int"].to_numpy(), probabilities
        )
        comparison[name] = {
            "validation": validation_metrics,
        }
        fitted[name] = (model, threshold)

    selected_name = max(
        comparison,
        key=lambda name: (
            comparison[name]["validation"]["f2"],
            comparison[name]["validation"]["pr_auc"],
            comparison[name]["validation"]["f1"],
        ),
    )
    selected_model, selected_threshold = fitted[selected_name]
    test_probabilities = selected_model.predict_proba(test[FEATURES])[:, 1]
    test_metrics = binary_metrics(
        test["binary_target_int"].to_numpy(),
        test_probabilities,
        selected_threshold,
    )
    test_metrics["per_station"] = per_station_metrics(
        test, test_probabilities, selected_threshold
    )

    joblib.dump(selected_model, output_dir / "multi_station_heavy_rain_experimental.joblib")
    with_model_threshold = {
        "model_name": selected_name,
        "threshold": selected_threshold,
        "threshold_source": "validation_only",
    }
    (output_dir / "multi_station_heavy_rain_threshold.json").write_text(
        json.dumps(with_model_threshold, indent=2), encoding="utf-8"
    )
    return {
        "method": "unique-date chronological 60/20/20 split; all stations included on each date",
        "date_boundaries": {
            "train_end": str(pd.Timestamp(train_end_date).date()),
            "validation_end": str(pd.Timestamp(validation_end_date).date()),
            "test_start": str((pd.Timestamp(validation_end_date) + pd.Timedelta(days=1)).date()),
        },
        "partition_distributions": {
            "train": distribution(train),
            "validation": distribution(validation),
            "test": distribution(test),
        },
        "model_comparison_validation": comparison,
        "selected_model": selected_name,
        "selected_threshold": selected_threshold,
        "test": test_metrics,
    }


def station_holdout_experiment(frame: pd.DataFrame, output_dir: Path) -> dict:
    results = {}
    for held_out in STATIONS:
        train_validation = frame[frame["station_id"] != held_out].copy()
        test = frame[frame["station_id"] == held_out].copy()

        dates = np.sort(train_validation["observation_date"].unique())
        train_end_date = dates[int(len(dates) * 0.80) - 1]
        train = train_validation[
            train_validation["observation_date"] <= train_end_date
        ].copy()
        validation = train_validation[
            train_validation["observation_date"] > train_end_date
        ].copy()

        comparison = {}
        fitted = {}
        for name, classifier in candidates().items():
            is_hist_gradient = name == "hist_gradient_weighted"
            model = make_pipeline(classifier, hist_gradient=is_hist_gradient)
            model.fit(train[FEATURES], train["binary_target_int"])
            probabilities = model.predict_proba(validation[FEATURES])[:, 1]
            threshold, validation_metrics = tune_threshold(
                validation["binary_target_int"].to_numpy(), probabilities
            )
            comparison[name] = {"validation": validation_metrics}
            fitted[name] = (model, threshold)

        selected_name = max(
            comparison,
            key=lambda name: (
                comparison[name]["validation"]["f2"],
                comparison[name]["validation"]["pr_auc"],
                comparison[name]["validation"]["f1"],
            ),
        )
        selected_model, selected_threshold = fitted[selected_name]
        test_probabilities = selected_model.predict_proba(test[FEATURES])[:, 1]
        test_metrics = binary_metrics(
            test["binary_target_int"].to_numpy(),
            test_probabilities,
            selected_threshold,
        )
        joblib.dump(
            selected_model,
            output_dir / f"multi_station_heldout_{held_out}.joblib",
        )
        results[held_out] = {
            "held_out_station": held_out,
            "train_validation_distribution": distribution(train_validation),
            "train": distribution(train),
            "validation": distribution(validation),
            "test_held_out": distribution(test),
            "model_comparison_validation": comparison,
            "selected_model": selected_name,
            "selected_threshold": selected_threshold,
            "test": test_metrics,
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="M13 multi-station heavy rainfall experiment")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("backend/data/noaa_expanded_rainfall.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/models"),
    )
    args = parser.parse_args()

    frame = prepare_frame(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "experiment": "M13 multi-station heavy rainfall research",
        "production_model_changed": False,
        "binary_target": {
            "NORMAL": "next-day rainfall below 50 mm",
            "HEAVY_RAIN": "next-day rainfall at or above 50 mm",
        },
        "stations": STATIONS,
        "model_features": FEATURES,
        "feature_engineering": {
            "sorting": "station_id, then observation_date",
            "historical_lag": "prcp_lag1_mm is precipitation shifted one observation within each station",
            "rolling_windows": "3/7/14-day precipitation means use prcp shifted by one observation, independently per station",
            "station_id_crossing": "prevented by groupby station_id",
            "target": "next observation only when it is exactly one calendar day later; invalid consecutive-date target rows excluded",
            "missing_prcp": "missing target observations excluded; missing feature values are median-imputed by the ML pipeline; missing values are never converted to zero",
            "geographic_features": "station_id, latitude, longitude, elevation_m",
        },
        "dataset": {
            "valid_model_rows": len(frame),
            "heavy_rain_events": int(frame["binary_target_int"].sum()),
            "normal_events": int((1 - frame["binary_target_int"]).sum()),
            "date_start": str(frame["observation_date"].min().date()),
            "date_end": str(frame["observation_date"].max().date()),
        },
        "m11_comparison_reference": "backend/models/binary_heavy_rain_experiment.json",
        "chronological": chronological_experiment(frame, args.output_dir),
        "station_held_out": station_holdout_experiment(frame, args.output_dir),
    }

    report_path = args.output_dir / "multi_station_heavy_rain_experiment.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "report": str(report_path),
        "chronological_selected_model": report["chronological"]["selected_model"],
        "chronological_test": report["chronological"]["test"],
        "station_held_out_summary": {
            station: {
                "selected_model": details["selected_model"],
                "precision": details["test"]["precision"],
                "recall": details["test"]["recall"],
                "f1": details["test"]["f1"],
                "pr_auc": details["test"]["pr_auc"],
                "false_negative_rate": details["test"]["false_negative_rate"],
            }
            for station, details in report["station_held_out"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
