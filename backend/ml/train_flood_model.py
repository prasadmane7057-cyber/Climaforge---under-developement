"""Compare and train CLIMAFORGE Random Forest rainfall-risk classifiers."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from urllib.request import urlopen

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_URL = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/USW00094728.csv"
LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
FEATURES = [
    "prcp_mm", "tmax_c", "tmin_c", "snow_mm", "prcp_lag1_mm",
    "prcp_rolling_3d_mean_mm", "prcp_rolling_7d_mean_mm",
    "prcp_rolling_14d_mean_mm",
]


def risk_class(next_day_prcp_mm: float) -> str:
    if next_day_prcp_mm >= 100.0:
        return "CRITICAL"
    if next_day_prcp_mm >= 50.0:
        return "HIGH"
    if next_day_prcp_mm >= 25.0:
        return "MEDIUM"
    return "LOW"


def download_dataset(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(DATA_URL, timeout=120) as response, destination.open("wb") as output:
        output.write(response.read())


def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, low_memory=False)
    required = {"DATE", "PRCP", "TMAX", "TMIN", "SNOW"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    frame["DATE"] = pd.to_datetime(frame["DATE"], errors="coerce")
    frame = frame.sort_values("DATE").drop_duplicates("DATE").reset_index(drop=True)
    for column in ("PRCP", "TMAX", "TMIN", "SNOW"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["prcp_mm"] = frame["PRCP"] / 10.0
    frame["tmax_c"] = frame["TMAX"] / 10.0
    frame["tmin_c"] = frame["TMIN"] / 10.0
    frame["snow_mm"] = frame["SNOW"].fillna(0.0)
    frame["prcp_lag1_mm"] = frame["prcp_mm"].shift(1)

    # Historical features end at the observation before each prediction row.
    # prcp_mm itself is the current observed day, while target is the following day.
    historical_prcp = frame["prcp_mm"].shift(1)
    frame["prcp_rolling_3d_mean_mm"] = historical_prcp.rolling(3, min_periods=3).mean()
    frame["prcp_rolling_7d_mean_mm"] = historical_prcp.rolling(7, min_periods=7).mean()
    frame["prcp_rolling_14d_mean_mm"] = historical_prcp.rolling(14, min_periods=14).mean()
    frame["target"] = frame["prcp_mm"].shift(-1).map(risk_class)
    return frame.dropna(subset=["target"] + FEATURES).reset_index(drop=True)


def make_pipeline(classifier) -> Pipeline:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    preprocessor = ColumnTransformer([("numeric", numeric, FEATURES)])
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])


def evaluate(y_true, y_pred) -> dict:
    report = classification_report(
        y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0
    )
    priority_labels = ["MEDIUM", "HIGH", "CRITICAL"]
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="weighted", zero_division=0)),
        "priority_recall_mean": float(sum(report[label]["recall"] for label in priority_labels) / 3),
        "per_class": {label: report[label] for label in LABELS},
        "confusion_matrix": {
            "labels": LABELS,
            "matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        },
    }


def threshold_predictions(pipeline: Pipeline, frame: pd.DataFrame, thresholds: dict) -> list[str]:
    probabilities = pipeline.predict_proba(frame[FEATURES])
    classes = list(pipeline.classes_)
    adjusted = []
    for row in probabilities:
        class_scores = {
            label: float(row[index] / thresholds[label])
            for index, label in enumerate(classes)
        }
        adjusted.append(max(LABELS, key=lambda label: class_scores.get(label, -1.0)))
    return adjusted


def tune_thresholds(pipeline: Pipeline, validation: pd.DataFrame) -> tuple[dict, dict]:
    rng = random.Random(42)
    best_thresholds = {label: 1.0 for label in LABELS}
    best_score = -1.0
    best_metrics = None
    probability_candidates = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80]

    for _ in range(120):
        thresholds = {
            label: (rng.choice(probability_candidates) if label != "LOW" else 1.0)
            for label in LABELS
        }
        predictions = threshold_predictions(pipeline, validation, thresholds)
        metrics = evaluate(validation["target"], predictions)
        priority_score = metrics["priority_recall_mean"]
        score = priority_score + 0.10 * metrics["weighted_f1"]
        if score > best_score:
            best_score = score
            best_thresholds = thresholds
            best_metrics = metrics
    return best_thresholds, best_metrics or {}


def precision_recall_analysis(pipeline: Pipeline, frame: pd.DataFrame) -> dict:
    probabilities = pipeline.predict_proba(frame[FEATURES])
    classes = list(pipeline.classes_)
    result = {}
    for label in LABELS:
        index = classes.index(label)
        binary = (frame["target"] == label).astype(int)
        precision, recall, threshold = precision_recall_curve(binary, probabilities[:, index])
        result[label] = {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": threshold.tolist(),
        }
    return result


def train(csv_path: Path, model_path: Path, metrics_path: Path, baseline_path: Path) -> dict:
    frame = load_and_prepare(csv_path)
    train_end = int(len(frame) * 0.60)
    validation_end = int(len(frame) * 0.80)
    train_frame = frame.iloc[:train_end]
    validation_frame = frame.iloc[train_end:validation_end]
    test_frame = frame.iloc[validation_end:]

    candidates = {
        "rf_baseline": RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=2,
            class_weight=None, random_state=42, n_jobs=-1,
        ),
        "rf_balanced": RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
        "rf_balanced_subsample": RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=2,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        ),
        "extra_trees_balanced": ExtraTreesClassifier(
            n_estimators=250, max_depth=None, min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
    }

    fitted = {}
    model_comparison = {}
    for name, classifier in candidates.items():
        pipeline = make_pipeline(classifier)
        pipeline.fit(train_frame[FEATURES], train_frame["target"])
        fitted[name] = pipeline

        validation_predictions = pipeline.predict(validation_frame[FEATURES])
        model_comparison[name] = {
            "validation_default": evaluate(validation_frame["target"], validation_predictions),
        }

    # Thresholds are selected only from validation probabilities, never test data.
    baseline_model = fitted["rf_baseline"]
    baseline_validation = baseline_model.predict(validation_frame[FEATURES])
    baseline_metrics = evaluate(validation_frame["target"], baseline_validation)
    for name, pipeline in fitted.items():
        thresholds, threshold_metrics = tune_thresholds(pipeline, validation_frame)
        model_comparison[name]["threshold_tuning"] = {
            "thresholds": thresholds,
            "validation_tuned": threshold_metrics,
        }

    eligible_names = []
    for name in fitted:
        candidate_metrics = model_comparison[name]["threshold_tuning"]["validation_tuned"]
        high_recall = candidate_metrics["per_class"]["HIGH"]["recall"]
        critical_recall = candidate_metrics["per_class"]["CRITICAL"]["recall"]
        if high_recall >= 0.05 and critical_recall >= 0.05:
            eligible_names.append(name)

    if eligible_names:
        selected_name = max(
            eligible_names,
            key=lambda name: (
                model_comparison[name]["threshold_tuning"]["validation_tuned"]["priority_recall_mean"],
                model_comparison[name]["threshold_tuning"]["validation_tuned"]["weighted_f1"],
            ),
        )
    else:
        selected_name = "rf_baseline"
    if selected_name == "rf_baseline":
        selected = baseline_model
        selected_thresholds = {label: 1.0 for label in LABELS}
    else:
        selected = fitted[selected_name]
        selected_thresholds = model_comparison[selected_name]["threshold_tuning"]["thresholds"]
    selected_predictions = threshold_predictions(selected, test_frame, selected_thresholds)
    test_metrics = evaluate(test_frame["target"], selected_predictions)

    baseline_test_predictions = baseline_model.predict(test_frame[FEATURES])
    baseline_test_metrics = evaluate(test_frame["target"], baseline_test_predictions)

    model_version = "rf-ghcnd-central-park-v2"
    if selected_name != "rf_baseline":
        model_version = "rf-ghcnd-central-park-m10-v1"
    else:
        model_version = "rf-ghcnd-central-park-baseline-v1"

    artifact = {
        "pipeline": selected,
        "feature_columns": FEATURES,
        "model_version": model_version,
        "thresholds": selected_thresholds,
        "selected_model_name": selected_name,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    joblib.dump({
        "pipeline": baseline_model,
        "feature_columns": FEATURES,
        "model_version": "rf-ghcnd-central-park-baseline-v1",
        "thresholds": {label: 1.0 for label in LABELS},
        "selected_model_name": "rf_baseline",
    }, baseline_path)

    metrics = {
        "model_version": model_version,
        "dataset": str(csv_path),
        "source": DATA_URL,
        "feature_columns": FEATURES,
        "class_labels": LABELS,
        "target_definition": {
            "LOW": "<25 mm next-day precipitation",
            "MEDIUM": "25-49.999 mm next-day precipitation",
            "HIGH": "50-99.999 mm next-day precipitation",
            "CRITICAL": ">=100 mm next-day precipitation",
        },
        "leakage_controls": {
            "chronological_order": True,
            "target": "prcp_mm shifted forward by one calendar observation (next day)",
            "rolling_features": "Historical precipitation shifted by one row before 3/7/14-day rolling means",
            "current_prcp_mm": "Observed on the prediction day; not the next-day target",
            "test_data_not_used": True,
        },
        "partition_method": "Chronological 60% train / 20% validation / 20% test; rows: "
                           f"{len(train_frame)} / {len(validation_frame)} / {len(test_frame)}",
        "train_rows": len(train_frame),
        "validation_rows": len(validation_frame),
        "test_rows": len(test_frame),
        "baseline_validation": baseline_metrics,
        "baseline_test": baseline_test_metrics,
        "selected_model": selected_name,
        "selected_thresholds": selected_thresholds,
        "model_comparison_validation": model_comparison,
        "final_test": test_metrics,
        "precision_recall_validation": precision_recall_analysis(selected, validation_frame),
        "confusion_matrix": test_metrics["confusion_matrix"],
        "per_class_evaluation": test_metrics["per_class"],
        "training_configuration": {
            "random_state": 42,
            "n_jobs": -1,
            "models": list(candidates),
            "threshold_selection": "Validation-only randomized search over class probability thresholds; objective is priority recall mean plus 10% weighted F1",
        },
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and compare CLIMAFORGE rainfall-risk classifiers")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--data", type=Path, default=Path("backend/data/nyc_central_park.csv"))
    parser.add_argument("--model", type=Path, default=Path("backend/models/flood_rf.joblib"))
    parser.add_argument("--baseline", type=Path, default=Path("backend/models/flood_rf_baseline.joblib"))
    parser.add_argument("--metrics", type=Path, default=Path("backend/models/flood_rf_metrics.json"))
    parser.add_argument("--comparison", type=Path, default=Path("backend/models/flood_rf_comparison.json"))
    args = parser.parse_args()
    if args.download or not args.data.exists():
        print(f"Downloading NOAA GHCN-Daily data from {DATA_URL}")
        download_dataset(args.data)
    metrics = train(args.data, args.model, args.metrics, args.baseline)
    args.comparison.write_text(json.dumps({
        "model_comparison_validation": metrics["model_comparison_validation"],
        "baseline_test": metrics["baseline_test"],
        "selected_model": metrics["selected_model"],
        "selected_thresholds": metrics["selected_thresholds"],
        "final_test": metrics["final_test"],
    }, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
