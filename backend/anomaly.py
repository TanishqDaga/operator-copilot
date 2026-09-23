"""Anomaly detection: IsolationForest on normal historical telemetry + the operator's own baseline.

The model says *that* something is unusual and *which* feature is furthest from this operator's
normal — it never knows *why*. Causes are always returned as possibilities, not facts.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from simulator import ROOT

MODEL_PATH = ROOT / "models" / "anomaly.joblib"

# ================= CONFIG =================
FEATURES = ["idle_min", "rpm", "cycle_s", "hyd_temp", "fuel_rate_lph", "payload_t"]
SCORE_QUANTILE = 0.05      # flag when a sample is less typical than 95 % of historical normal samples
PERSIST_TICKS = 3          # consecutive anomalous ticks to raise a flag (and normal ticks to clear it)
STATES = ["working", "idle"]  # one IsolationForest per machine state (idle telemetry is a different regime)
# ==========================================

FEATURE_META = {
    "idle_min": {"type": "excess_idle", "label": "Idle duration", "unit": "min"},
    "rpm": {"type": "rpm_abnormal", "label": "Engine speed", "unit": "rpm"},
    "cycle_s": {"type": "slow_cycle", "label": "Cycle time", "unit": "s"},
    "hyd_temp": {"type": "hyd_overheat", "label": "Hydraulic oil temp", "unit": "°C"},
    "fuel_rate_lph": {"type": "high_fuel_burn", "label": "Fuel burn rate", "unit": "L/h"},
    "payload_t": {"type": "payload_abnormal", "label": "Bucket payload", "unit": "t"},
}

POSSIBLE_CAUSES = {
    "excess_idle": ["Material or haul truck not available", "Obstruction or blocked work face",
                    "Operator delay (radio call, break, paperwork)"],
    "slow_cycle": ["Harder digging conditions (rock, wet material)", "Truck spotting / positioning delays",
                   "Operator fatigue or unfamiliar task"],
    "hyd_overheat": ["High ambient temperature", "Cooler fins blocked by dust",
                     "Sustained heavy digging at high load"],
    "hyd_cold": ["Machine recently idle — oil not yet at working temperature", "Cold ambient conditions",
                 "Temperature sensor fault"],
    "high_fuel_burn": ["Working at high engine speed for the load", "Heavy material or hard digging",
                       "Air filter or injector wear"],
    "rpm_abnormal": ["Engine speed dial set outside the normal band", "Auto-idle disabled",
                     "Engine governor issue"],
    "payload_abnormal": ["Bucket under- or over-filled", "Material density changed",
                         "Payload scale needs calibration"],
}


class AnomalyDetector:
    def __init__(self):
        self.models: dict = {}
        self.thresholds: dict = {}
        self.baselines: dict = {}
        self.meta: dict = {}
        self._streak = 0
        self._clear_streak = 0
        self._flag = False

    # ---- training -----------------------------------------------------------------------
    def train(self, tele: pd.DataFrame):
        for st in STATES:
            X = tele.loc[tele.state == st, FEATURES].to_numpy()
            model = IsolationForest(n_estimators=300, random_state=42).fit(X)
            self.models[st] = model
            self.thresholds[st] = float(np.quantile(model.score_samples(X), SCORE_QUANTILE))
        self.baselines = {}
        for (op, state), g in tele.groupby(["operator_id", "state"]):
            self.baselines.setdefault(op, {})[state] = {
                f: {"median": float(g[f].median()), "q25": float(g[f].quantile(0.25)),
                    "q75": float(g[f].quantile(0.75)), "n": int(len(g))}
                for f in FEATURES
            }
        idle = tele[tele.state == "idle"]
        self.meta = {
            "n_train": {st: int((tele.state == st).sum()) for st in STATES},
            "score_quantile": SCORE_QUANTILE,
            "persist_ticks": PERSIST_TICKS,
            "idle_burn_lph": round(float(idle.fuel_rate_lph.mean()), 2),
            "idle_burn_n": int(len(idle)),
        }
        joblib.dump({"models": self.models, "thresholds": self.thresholds, "baselines": self.baselines,
                     "meta": self.meta}, MODEL_PATH)

    def load_or_train(self, tele: pd.DataFrame):
        if MODEL_PATH.exists():
            d = joblib.load(MODEL_PATH)
            self.models, self.thresholds = d["models"], d["thresholds"]
            self.baselines, self.meta = d["baselines"], d["meta"]
        else:
            MODEL_PATH.parent.mkdir(exist_ok=True)
            self.train(tele)

    def reset(self):
        self._streak = self._clear_streak = 0
        self._flag = False

    def baseline(self, operator_id: str, idle: bool, feature: str) -> dict:
        return self.baselines[operator_id]["idle" if idle else "working"][feature]

    # ---- inference ----------------------------------------------------------------------
    def evaluate(self, feats: dict, operator_id: str, idle: bool) -> dict:
        state = "idle" if idle else "working"
        if getattr(self, "_state", state) != state:   # regime change: never carry a flag across states
            self.reset()
        self._state = state
        x = np.array([[feats[f] for f in FEATURES]])
        score = float(self.models[state].score_samples(x)[0])
        threshold = self.thresholds[state]
        raw = score < threshold
        self._streak = self._streak + 1 if raw else 0
        self._clear_streak = 0 if raw else self._clear_streak + 1
        if self._streak >= PERSIST_TICKS:
            self._flag = True
        elif self._clear_streak >= PERSIST_TICKS:
            self._flag = False
        flag = self._flag

        # which feature is furthest from this operator's own normal (robust z-score)
        best, best_z = None, 0.0
        for f in FEATURES:
            b = self.baselines[operator_id][state][f]
            spread = max((b["q75"] - b["q25"]) / 1.349, 1e-6)
            z = abs(feats[f] - b["median"]) / spread
            if z > best_z:
                best, best_z = f, z
        out = {"flag": flag, "type": None, "current": None, "baseline": None, "score": round(score, 3),
               "threshold": round(threshold, 3), "model_state": state}
        if flag and best:
            m = FEATURE_META[best]
            b = self.baselines[operator_id][state][best]
            atype = m["type"]
            if best == "hyd_temp" and feats[best] < b["median"]:
                atype = "hyd_cold"
            out.update({
                "type": atype, "feature": best, "label": m["label"], "unit": m["unit"],
                "current": round(float(feats[best]), 1), "baseline": round(b["median"], 1),
                "baseline_q25": round(b["q25"], 1), "baseline_q75": round(b["q75"], 1),
                "baseline_n": b["n"], "robust_z": round(best_z, 1),
                "possible_causes": POSSIBLE_CAUSES[atype],
            })
        return out
