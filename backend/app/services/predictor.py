from __future__ import annotations

import numpy as np

from app.config import settings
from app.services.features import FeatureVector, to_matrix
from app.services.trainer import load_model


def redundant_probability(f: FeatureVector) -> float:
    model = load_model(settings.ml_model_path)
    X = np.array(to_matrix(f), dtype=np.float64)
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        if proba.shape[0] >= 2:
            return float(proba[1])
        return float(proba[0])
    p = float(model.predict(X)[0])
    return p


def risk_score(ml_redundant_proba: float, max_similarity: float) -> float:
    combined = 0.45 * ml_redundant_proba + 0.35 * max_similarity + 0.2 * (ml_redundant_proba * max_similarity)
    return float(max(0.0, min(100.0, round(combined * 100.0, 2))))
