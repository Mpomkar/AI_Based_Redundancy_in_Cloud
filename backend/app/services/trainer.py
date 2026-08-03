"""Train default redundancy model (logistic regression on synthetic labels)."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _synthetic_dataset(seed: int = 42, n: int = 4000):
    rng = np.random.default_rng(seed)
    X = np.zeros((n, 3), dtype=np.float64)
    y = np.zeros(n, dtype=np.int32)
    for i in range(n):
        sim = float(rng.random())
        size_r = float(rng.random())
        neighbors = int(rng.integers(0, 6))
        X[i, 0] = sim
        X[i, 1] = size_r
        X[i, 2] = min(1.0, neighbors / 5.0)
        redundant = (sim >= 0.88) or (sim >= 0.72 and size_r >= 0.9) or (sim >= 0.65 and neighbors >= 3)
        y[i] = 1 if redundant else 0
    return X, y


def ensure_model(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    X, y = _synthetic_dataset()
    clf = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "lr",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    clf.fit(X, y)
    joblib.dump(clf, path)


def load_model(path: Path):
    ensure_model(path)
    return joblib.load(path)
