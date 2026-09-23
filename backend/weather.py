"""Synthetic hourly shift forecast for the weather-aware planner. SYNTHETIC — no weather API.

Two different weather concepts live in this app and must not be confused:
  CURRENT weather   LiveSim.weather (clear | rain | heat) — what the machine experiences now. Drives the
                    ETA model, the simulator and the safety rules. Changed only from the Simulate panel.
  FORECAST weather  this module — what is expected later in the shift. Drives planning only.

The forecast is deterministic: a scenario name always yields the same hours (jitter comes from a fixed
seed), so refreshing the page never changes the plan.
"""
from __future__ import annotations

import hashlib
import json
import zlib

import numpy as np

# ================= CONFIG =================
SHIFT_START = "09:00"
SHIFT_END = "19:00"
FORECAST_SEED = 4207
DEFAULT_SCENARIO = "rain_window"
RAIN_WINDOW_PCT = 50        # rain probability at/above this marks a rain window
WIND_WINDOW_KMH = 35        # wind at/above this marks a wind window
LOW_VIS_M = 1000            # visibility below this marks a low-visibility window
# ==========================================

# Per-hour keyframes from SHIFT_START: (condition, rain %, wind km/h, visibility m)
SCENARIOS: dict[str, dict] = {
    "rain_window": {"label": "Rain window", "hours": [
        ("clear", 5, 10, 10000), ("clear", 10, 12, 10000), ("cloudy", 20, 14, 8000), ("cloudy", 30, 16, 6000),
        ("rain", 55, 20, 2500), ("rain", 70, 22, 1500), ("rain", 80, 24, 1200), ("rain", 85, 26, 1100),
        ("rain", 75, 22, 1300), ("cloudy", 35, 16, 5000)]},
    "clear": {"label": "Clear day", "hours": [
        ("clear", 5, 8, 10000), ("clear", 5, 10, 10000), ("clear", 5, 12, 10000), ("clear", 10, 14, 10000),
        ("clear", 10, 15, 10000), ("cloudy", 15, 14, 9000), ("cloudy", 15, 12, 9000), ("clear", 10, 10, 10000),
        ("clear", 5, 8, 10000), ("clear", 5, 8, 10000)]},
    "wind_visibility": {"label": "Wind / low visibility", "hours": [
        ("low_visibility", 10, 6, 500), ("low_visibility", 10, 8, 800), ("clear", 5, 14, 6000),
        ("clear", 5, 22, 9000), ("wind", 10, 42, 3000), ("wind", 10, 48, 2000), ("wind", 15, 45, 2500),
        ("cloudy", 15, 30, 7000), ("clear", 10, 18, 9000), ("clear", 5, 12, 10000)]},
    "mixed": {"label": "Mixed", "hours": [
        ("low_visibility", 15, 6, 700), ("cloudy", 20, 10, 3000), ("clear", 10, 12, 9000), ("cloudy", 25, 16, 7000),
        ("cloudy", 40, 20, 5000), ("rain", 60, 24, 2000), ("rain", 65, 28, 1800), ("cloudy", 35, 36, 5000),
        ("wind", 20, 40, 6000), ("cloudy", 15, 22, 8000)]},
}


def to_min(hhmm: str) -> int:
    """'09:30' -> 570. Raises ValueError on bad input."""
    h, m = str(hhmm).strip().split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 24 and 0 <= m < 60) or (h == 24 and m):
        raise ValueError(f"invalid time {hhmm!r}")
    return h * 60 + m


def hhmm(minutes: float) -> str:
    m = int(round(minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def generate_forecast(scenario: str = DEFAULT_SCENARIO, shift_start: str = SHIFT_START,
                      shift_end: str = SHIFT_END) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown forecast scenario {scenario!r} (use one of {', '.join(SCENARIOS)})")
    s0, s1 = to_min(shift_start), to_min(shift_end)
    n = max(1, -(-(s1 - s0) // 60))
    keys = SCENARIOS[scenario]["hours"]
    rng = np.random.default_rng(FORECAST_SEED + zlib.crc32(scenario.encode()))
    hours = []
    for i in range(n):
        cond, rain, wind, vis = keys[min(i, len(keys) - 1)]
        start = s0 + 60 * i
        hours.append({
            "time": hhmm(start), "end": hhmm(min(start + 60, s1)), "start_min": start,
            "condition": cond, "rain_probability": int(rain),
            "wind_kmh": int(max(0, wind + int(rng.integers(-2, 3)))),
            "visibility_m": int(round(vis * (1 + float(rng.uniform(-0.05, 0.05))) / 50) * 50),
        })
    fid = hashlib.sha1(json.dumps(hours, sort_keys=True).encode()).hexdigest()[:8]
    windows = detect_windows(hours)
    return {"forecast_id": f"FC-{scenario}-{fid}", "scenario": scenario, "label": SCENARIOS[scenario]["label"],
            "synthetic": True, "shift_start": shift_start, "shift_end": shift_end, "hours": hours,
            "windows": windows, "summary": summarize(windows)}


def detect_windows(hours: list[dict]) -> list[dict]:
    """Merge consecutive hours that cross a hazard threshold into windows."""
    tests = {
        "rain": (lambda h: h["rain_probability"] >= RAIN_WINDOW_PCT, "rain_probability", max, "%"),
        "wind": (lambda h: h["wind_kmh"] >= WIND_WINDOW_KMH, "wind_kmh", max, " km/h"),
        "low_visibility": (lambda h: h["visibility_m"] < LOW_VIS_M, "visibility_m", min, " m"),
    }
    out = []
    for kind, (hit, field, pick, unit) in tests.items():
        run: list[dict] = []
        for h in hours + [None]:
            if h is not None and hit(h):
                run.append(h)
                continue
            if run:
                peak = pick(run, key=lambda x: x[field])
                out.append({"kind": kind, "start": run[0]["time"], "end": run[-1]["end"],
                            "start_min": run[0]["start_min"], "end_min": to_min(run[-1]["end"]),
                            "peak": peak[field], "peak_at": peak["time"], "unit": unit.strip()})
                run = []
    return sorted(out, key=lambda w: w["start_min"])


def summarize(windows: list[dict]) -> str:
    if not windows:
        return "No significant weather expected during the shift."
    names = {"rain": "Rain", "wind": "Strong wind", "low_visibility": "Low visibility"}
    parts = []
    for w in windows:
        peak = f"{w['peak']}%" if w["kind"] == "rain" else f"{w['peak']} {w['unit']}"
        parts.append(f"{names[w['kind']]} expected {w['start']}–{w['end']} (peak {peak} at {w['peak_at']})")
    return "; ".join(parts) + "."


def hour_at(hours: list[dict], minute: float) -> dict:
    """Forecast hour covering `minute`; clamps to the first/last hour outside the forecast range."""
    for h in hours:
        if h["start_min"] <= minute < h["start_min"] + 60:
            return h
    return hours[0] if minute < hours[0]["start_min"] else hours[-1]


def window_weather(hours: list[dict], start: float, end: float) -> dict:
    """Worst-case forecast values over [start, end)."""
    hs = [h for h in hours if h["start_min"] < end and h["start_min"] + 60 > start] or [hour_at(hours, start)]
    wettest = max(hs, key=lambda h: h["rain_probability"])
    return {"max_rain": wettest["rain_probability"], "peak_rain_at": wettest["time"],
            "min_rain": min(h["rain_probability"] for h in hs),
            "max_wind": max(h["wind_kmh"] for h in hs), "min_visibility": min(h["visibility_m"] for h in hs),
            "conditions": sorted({h["condition"] for h in hs})}
