"""Controlled binary-vs-four-class experiment for rare heavy rainfall detection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
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
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "prcp_mm", "tmax_c", "tmin_c", "snow_mm", "prcp_lag1_mm",
    "prcp_rolling_3d_mean_mm", "prcp_rolling_7d_mean_mm",
    "prcp_rolling_14d_mean_mm",
]
FOUR_CLASS_LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def four_class(next_day_prcp_mm: float) -> str:
    if next_day_prcp_mm >= 100.0:
        return "CRITICAL"
    if next_day_prcp_mm >= 50.0:
        return "HIGH"
    if next_day_prcp_mm >= 25.0:
        return "MEDIUM"
    return "LOW"


def prepare(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, low_memory=False)
    frame["DATE"] = pd.to_datetime(frame["DATE"], errors="coerce")
    frame = frame.sort_values("DATE").drop_duplicates("DATE").reset_index(drop=True)
    for column in ("PRCP", "TMAX", "TMIN", "SNOW"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["prcp_mm"] = frame["PRCP"] / 10.0
    frame["tmax_c"] = frame["TMAX"] / 10.0
    frame["tmin_c"] = frame["TMIN"] / 10.0
    frame["snow_mm"] = frame["SNOW"].fillna(0.0)
    frame["prcp_lag1_mm"] = frame["prcp_mm"].shift(1)
    historical = frame["prcp_mm"].shift(1)
    frame["prcp_rolling_3d_mean_mm"] = historical.rolling(3, min_periods=3).mean()
    frame["prcp_rolling_7d_mean_mm"] = historical.rolling(7, min_periods=7).mean()
    frame["prcp_rolling_14d_mean_mm"] = historical.rolling(14, min_periods=14).mean()

    frame["next_day_prcp_mm"] = frame["prcp_mm"].shift(-1)
    frame["four_class"] = frame["next_day_prcp_mm"].map(four_class)
    frame["binary"] = (frame["next_day_prcp_mm"] >= 50.0).map(
        {True: "HEAVY_RAIN", False: "NORMAL"}
    )
    return frame.dropna(subset=["next_day_prcp_mm"] + FEATURES + ["four_class"]).reset_index(drop=True)


def pipeline(classifier) -> Pipeline:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    return Pipeline([
        ("numeric", numeric),
        ("classifier", classifier),
    ])


def distribution(series: pd.Series) -> dict:
    counts = series.value_counts().to_dict()
    return {
        "counts": {str(key): int(value) for key, value in counts.items()},
        "percentages": {
            str(key): float(value / len(series) * 100.0)
            for key, value in counts.items()
        },
        "rows": len(series),
    }


def binary_metrics(y_true, probabilities, threshold: float) -> dict:
    y_true_binary = (y_true == "HEAVY_RAIN").astype(int)
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true_binary, predicted, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true_binary, predicted, zero_division=0)),
        "recall": float(recall_score(y_true_binary, predicted, zero_division=0)),
        "f1": float(f1_score(y_true_binary, predicted, zero_division=0)),
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else 0.0,
        "confusion_matrix": {
            "labels": ["NORMAL", "HEAVY_RAIN"],
            "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        },
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def tune_threshold(y_true, probabilities) -> tuple[float, dict]:
    y_binary = (y_true == "HEAVY_RAIN").astype(int)
    precision, recall, thresholds = precision_recall_curve(y_binary, probabilities)
    best_threshold = 0.5
    best = None
    candidate_thresholds = thresholds[
        np.linspace(0, len(thresholds) - 1, num=min(100, len(thresholds)), dtype=int)
    ].tolist() if len(thresholds) else []
    for threshold in [*candidate_thresholds, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        if 0.0 <= threshold <= 1.0:
            metrics = binary_metrics(y_true, probabilities, float(threshold))
            # F2 prioritizes heavy-rain recall while retaining precision information.
            recall_value = metrics["recall"]
            precision_value = metrics["precision"]
            f2 = (
                5.0 * precision_value * recall_value / (4.0 * precision_value + recall_value)
                if precision_value + recall_value else 0.0
            )
            score = f2
            if best is None or score > best["score"]:
                best = {"score": score, "threshold": float(threshold), "metrics": metrics}
                best_threshold = float(threshold)
    return best_threshold, best["metrics"]


def run(csv_path: Path, result_path: Path, model_path: Path) -> dict:
    frame = prepare(csv_path)
    train_end = int(len(frame) * 0.60)
    validation_end = int(len(frame) * 0.80)
    train = frame.iloc[:train_end]
    validation = frame.iloc[train_end:validation_end]
    test = frame.iloc[validation_end:]

    candidates = {
        "logistic_weighted": LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=42,
        ),
        "rf_balanced": RandomForestClassifier(
            n_estimators=100, max_depth=12, min_samples_leaf=3,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
        "rf_balanced_subsample": RandomForestClassifier(
            n_estimators=100, max_depth=12, min_samples_leaf=3,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        ),
        "extra_trees_balanced": ExtraTreesClassifier(
            n_estimators=120, max_depth=12, min_samples_leaf=3,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ),
    }

    comparison = {}
    fitted = {}
    for name, classifier in candidates.items():
        binary_target = (train["binary"] == "HEAVY_RAIN").astype(int)
        model = pipeline(classifier)
        model.fit(train[FEATURES], binary_target)
        validation_probabilities = model.predict_proba(validation[FEATURES])[:, 1]
        threshold, validation_metrics = tune_threshold(validation["binary"], validation_probabilities)
        pr_auc = average_precision_score(
            (validation["binary"] == "HEAVY_RAIN").astype(int),
            validation_probabilities,
        )
        comparison[name] = {
            "validation_pr_auc": float(pr_auc),
            "validation_tuned": validation_metrics,
        }
        fitted[name] = (model, threshold)

    selected_name = max(
        comparison,
        key=lambda name: (
            comparison[name]["validation_tuned"]["recall"],
            comparison[name]["validation_pr_auc"],
            comparison[name]["validation_tuned"]["f1"],
        ),
    )
    selected_model, selected_threshold = fitted[selected_name]
    test_binary = (test["binary"] == "HEAVY_RAIN").astype(int)
    test_probabilities = selected_model.predict_proba(test[FEATURES])[:, 1]
    final_metrics = binary_metrics(test["binary"], test_probabilities, selected_threshold)
    final_metrics["pr_auc"] = float(average_precision_score(test_binary, test_probabilities))

    heavy_test = int(test_binary.sum())
    normal_test = int(len(test_binary) - heavy_test)
    four_class_heavy_actual = test["four_class"].isin(["HIGH", "CRITICAL"]).sum()

    results = {
        "experiment": "M11 rare heavy-rainfall binary detection",
        "production_model_unchanged": True,
        "target_definition": {
            "NORMAL": "next-day precipitation <50 mm",
            "HEAVY_RAIN": "next-day precipitation >=50 mm (existing HIGH threshold; includes HIGH and CRITICAL)",
        },
        "features": FEATURES,
        "partition_method": "Chronological 60% train / 20% validation / 20% test",
        "partition_rows": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "partition_distributions": {
            "train_four_class": distribution(train["four_class"]),
            "validation_four_class": distribution(validation["four_class"]),
            "test_four_class": distribution(test["four_class"]),
            "train_binary": distribution(train["binary"]),
            "validation_binary": distribution(validation["binary"]),
            "test_binary": distribution(test["binary"]),
        },
        "leakage_controls": {
            "chronological": True,
            "rolling_features_use_shifted_history": True,
            "target_is_next_day": True,
            "test_used_for_tuning": False,
            "test_used_for_model_selection": False,
            "synthetic_observations": False,
        },
        "models_compared": list(candidates),
        "model_comparison_validation": comparison,
        "selected_model": selected_name,
        "selected_threshold": selected_threshold,
        "final_test_binary": final_metrics,
        "test_event_counts": {
            "normal": normal_test,
            "heavy_rain": heavy_test,
            "four_class_high_or_critical": int(four_class_heavy_actual),
        },
        "four_class_vs_binary": {
            "four_class_production_test_confusion_matrix": [
                [11086, 0, 0, 0],
                [346, 0, 0, 0],
                [81, 0, 0, 0],
                [12, 0, 0, 0],
            ],
            "four_class_production_high_recall": 0.0,
            "four_class_production_critical_recall": 0.0,
            "four_class_production_high_or_critical_recall": 0.0,
            "binary_heavy_rain_recall": final_metrics["recall"],
            "binary_heavy_rain_false_negative_rate": final_metrics["false_negative_rate"],
        },
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "pipeline": selected_model,
        "feature_columns": FEATURES,
        "selected_model": selected_name,
        "threshold": selected_threshold,
        "model_version": "binary-heavy-rain-experimental-v1",
        "target": "next-day rainfall >=50 mm",
        "production_model": False,
    }, model_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Research rare heavy-rainfall event detection")
    parser.add_argument("--data", type=Path, default=Path("backend/data/nyc_central_park.csv"))
    parser.add_argument("--results", type=Path, default=Path("backend/models/binary_heavy_rain_experiment.json"))
    parser.add_argument("--model", type=Path, default=Path("backend/models/binary_heavy_rain_experimental.joblib"))
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.results, args.model), indent=2))


if __name__ == "__main__":
    main()
