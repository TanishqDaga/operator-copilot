"""Task ETA: RandomForestRegressor on task history. The ± band is the real held-out MAE."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from simulator import ROOT, TASK_TYPES, TERRAIN_F, WEATHERS

MODEL_PATH = ROOT / "models" / "eta.joblib"
TEST_SIZE = 0.2

NUMERIC = ["tonnes", "distance_m", "operator_experience_yrs", "recent_cycle_s"]
CATEGORICAL = {"task_type": list(TASK_TYPES), "terrain": list(TERRAIN_F), "weather": WEATHERS}


def encode(rows: pd.DataFrame) -> np.ndarray:
    cols = [rows[c].astype(float).to_numpy() for c in NUMERIC]
    for c, cats in CATEGORICAL.items():
        for v in cats:
            cols.append((rows[c] == v).astype(float).to_numpy())
    return np.column_stack(cols)


def feature_names() -> list[str]:
    return NUMERIC + [f"{c}={v}" for c, cats in CATEGORICAL.items() for v in cats]


class EtaModel:
    def __init__(self):
        self.model: RandomForestRegressor | None = None
        self.metrics: dict = {}

    def train(self, hist: pd.DataFrame):
        X, y = encode(hist), hist["duration_min"].to_numpy()
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_SIZE, random_state=42)
        model = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1)
        model.fit(Xtr, ytr)
        mae = float(mean_absolute_error(yte, model.predict(Xte)))
        imp = sorted(zip(feature_names(), model.feature_importances_), key=lambda t: -t[1])
        self.model = model
        self.metrics = {
            "mae_min": round(mae, 1), "n_train": int(len(ytr)), "n_test": int(len(yte)),
            "test_size": TEST_SIZE,
            "top_features": [{"name": n, "importance": round(float(v), 3)} for n, v in imp[:5]],
        }
        joblib.dump({"model": model, "metrics": self.metrics}, MODEL_PATH)

    def load_or_train(self, hist: pd.DataFrame):
        if MODEL_PATH.exists():
            d = joblib.load(MODEL_PATH)
            self.model, self.metrics = d["model"], d["metrics"]
        else:
            MODEL_PATH.parent.mkdir(exist_ok=True)
            self.train(hist)

    @property
    def err_min(self) -> float:
        return self.metrics["mae_min"]

    def predict(self, task_type: str, tonnes: float, distance_m: float, experience_yrs: float,
                terrain: str, weather: str, recent_cycle_s: float) -> float:
        if tonnes <= 0:
            return 0.0
        row = pd.DataFrame([{
            "task_type": task_type, "tonnes": tonnes, "distance_m": distance_m,
            "operator_experience_yrs": experience_yrs, "terrain": terrain, "weather": weather,
            "recent_cycle_s": recent_cycle_s,
        }])
        return float(self.model.predict(encode(row))[0])
