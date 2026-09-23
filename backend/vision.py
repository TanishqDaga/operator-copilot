"""Webcam person detection -> uncalibrated distance proxy + approach speed.

The browser captures webcam frames and POSTs them here; YOLOv8n (pretrained, class 0 = person,
no training) finds people. The tallest box height relative to the frame is turned into a distance
*proxy* with K / h. K was chosen by eye — this is NOT a calibrated range measurement.
"""
from __future__ import annotations

import base64
import threading
import time

import numpy as np

from simulator import ROOT

# ================= CONFIG =================
K = 1.6                  # distance_proxy = K / h, h = tallest person box height / frame height (by eye)
MIN_CONF = 0.4           # ignore weaker person detections
STALE_S = 1.5            # a reading older than this is ignored by the safety engine
EMA_ALPHA = 0.5          # smoothing on the distance proxy before differentiating
MAX_APPROACH_MS = 3.0    # clamp approach speed to a running person
# ==========================================

try:  # optional dependency — the slider fallback works without it
    import cv2
    from ultralytics import YOLO
    AVAILABLE = True
    IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    AVAILABLE = False
    IMPORT_ERROR = str(exc)


class Vision:
    def __init__(self):
        self.available = AVAILABLE
        self.error = IMPORT_ERROR
        self._model = None
        self._lock = threading.Lock()
        self.latest: dict | None = None
        self._prev_d: float | None = None
        self._prev_h: float | None = None
        self._prev_t: float | None = None

    def _load(self):
        if self._model is None:
            weights = ROOT / "models" / "yolov8n.pt"   # pretrained COCO weights, fetched on first use
            weights.parent.mkdir(exist_ok=True)
            self._model = YOLO(str(weights))
        return self._model

    def warmup(self):
        """Load weights and run one dummy inference so the first camera frame is not slow."""
        if self.available:
            with self._lock:
                self._load()(np.zeros((480, 640, 3), np.uint8), classes=[0], verbose=False)

    def reset(self):
        self.latest = None
        self._prev_d = self._prev_h = self._prev_t = None

    def process(self, data_url: str) -> dict:
        if not self.available:
            return {"ok": False, "error": f"Vision unavailable: {self.error}"}
        raw = base64.b64decode(data_url.split(",", 1)[-1])
        frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return {"ok": False, "error": "Could not decode frame"}
        fh, fw = frame.shape[:2]
        with self._lock:
            t0 = time.time()
            r = self._load()(frame, classes=[0], verbose=False)[0]
            infer_ms = (time.time() - t0) * 1000
        boxes = []
        for b in r.boxes:
            conf = float(b.conf[0])
            if conf < MIN_CONF:
                continue
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
            boxes.append({"x": x1 / fw, "y": y1 / fh, "w": (x2 - x1) / fw, "h": (y2 - y1) / fh, "conf": round(conf, 2)})
        now = time.time()
        out = {"ok": True, "t": now, "detected": bool(boxes), "boxes": boxes, "infer_ms": round(infer_ms),
               "distance_m": None, "approach_ms": 0.0, "h_ratio": None, "h_rate": 0.0}
        if boxes:
            h = max(b["h"] for b in boxes)
            d_raw = K / max(h, 1e-3)
            d = d_raw if self._prev_d is None else EMA_ALPHA * d_raw + (1 - EMA_ALPHA) * self._prev_d
            if self._prev_d is not None and self._prev_t is not None and now > self._prev_t:
                dt = now - self._prev_t
                out["approach_ms"] = round(float(np.clip((self._prev_d - d) / dt, -MAX_APPROACH_MS, MAX_APPROACH_MS)), 2)
                out["h_rate"] = round((h - (self._prev_h or h)) / dt, 3)   # box growing = approaching
            out.update({"distance_m": round(d, 2), "h_ratio": round(h, 3)})
            self._prev_d, self._prev_h, self._prev_t = d, h, now
        else:
            self._prev_d = self._prev_h = self._prev_t = None
        self.latest = out
        return out

    def reading(self) -> dict | None:
        """Latest fresh reading for the safety engine, or None if stale."""
        if self.latest and time.time() - self.latest["t"] <= STALE_S:
            return self.latest
        return None
