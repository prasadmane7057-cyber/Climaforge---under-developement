"""ML-only flood rainfall-risk prediction service."""

from pathlib import Path
from typing import Dict, List, Optional

import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "flood_rf.joblib"


class FloodPredictor:
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = model_path
        self.pipeline = None
        self.feature_columns: List[str] = []
        self.model_version: Optional[str] = None
        self.load_error: Optional[str] = None
        self.thresholds = {"LOW": 1.0, "MEDIUM": 1.0, "HIGH": 1.0, "CRITICAL": 1.0}
        self.load()

    def load(self) -> None:
        if not self.model_path.exists():
            self.load_error = f"Model not found at {self.model_path}. Train it with backend/ml/train_flood_model.py."
            return
        try:
            artifact = joblib.load(self.model_path)
            self.pipeline = artifact["pipeline"]
            self.feature_columns = artifact["feature_columns"]
            self.model_version = artifact["model_version"]
            self.thresholds = artifact.get("thresholds", {label: 1.0 for label in ("LOW", "MEDIUM", "HIGH", "CRITICAL")})
            self.load_error = None
        except Exception as exc:
            self.pipeline = None
            self.load_error = f"Could not load trained model: {exc}"

    def predict(self, features: Dict[str, float]) -> Dict:
        if self.pipeline is None:
            raise RuntimeError(self.load_error or "Flood model is not available")
        frame = pd.DataFrame([{name: features[name] for name in self.feature_columns}])
        predicted_class = str(self.pipeline.predict(frame)[0])
        probabilities = self.pipeline.predict_proba(frame)[0]
        probability_by_class = {
            str(class_name): float(probability)
            for class_name, probability in zip(self.pipeline.classes_, probabilities)
        }
        adjusted_class = max(
            probability_by_class,
            key=lambda label: probability_by_class[label] / self.thresholds.get(label, 1.0),
        )
        if self.thresholds != {"LOW": 1.0, "MEDIUM": 1.0, "HIGH": 1.0, "CRITICAL": 1.0}:
            predicted_class = adjusted_class
        return {
            "predicted_risk_class": predicted_class,
            "confidence": float(probability_by_class[predicted_class]),
            "class_probabilities": probability_by_class,
            "model_version": self.model_version,
        }


flood_predictor = FloodPredictor()
