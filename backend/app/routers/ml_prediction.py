"""FastAPI routes for the trained ML flood-rainfall predictor."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import require_permission
from app.ml_predictor import flood_predictor
from app.security.rbac import PERM_ML_PREDICT

router = APIRouter(prefix="/ml/flood", tags=["Machine Learning Prediction"])


class FloodPredictionRequest(BaseModel):
    prcp_mm: float = Field(..., ge=0.0, le=500.0)
    tmax_c: float = Field(..., ge=-90.0, le=70.0)
    tmin_c: float = Field(..., ge=-90.0, le=70.0)
    snow_mm: float = Field(0.0, ge=0.0, le=2000.0)
    prcp_lag1_mm: float = Field(..., ge=0.0, le=500.0)
    prcp_rolling_3d_mean_mm: float = Field(..., ge=0.0, le=500.0)
    prcp_rolling_7d_mean_mm: float = Field(..., ge=0.0, le=500.0)
    prcp_rolling_14d_mean_mm: float = Field(..., ge=0.0, le=500.0)


@router.post("/predict", summary="Predict next-day rainfall flood-risk class")
async def predict_flood_risk(
    payload: FloodPredictionRequest,
    _: Any = Depends(require_permission(PERM_ML_PREDICT)),
):
    try:
        return flood_predictor.predict(payload.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
