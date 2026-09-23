"""Synthetic data for CAT Operator Copilot.

Two jobs:
  1. generate_history()  -> data/telemetry_history.csv (per-sample machine telemetry, used by the
                            anomaly model + operator baselines) and data/task_history.csv (completed
                            task segments, used by the ETA model). Everything is SYNTHETIC.
  2. LiveSim            -> tick-by-tick live telemetry for the current shift, driven by the same
                            generative assumptions as the history so the models see consistent data.
"""
from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ---------------------------------------------------------------- config -----------------
MACHINE_ID = "CAT320-042"
FUEL_TANK_L = 345.0          # tank size used to convert L/h burn into fuel_pct
START_FUEL_PCT = 78.0        # tank level at shift start
DATA_SOURCE = "synthetic"    # no real dataset provided -> every number derives from synthetic data

OPERATORS = {
    # idle_median: typical length (min) of this operator's idle stretches in the synthetic history
    "OP-101": {"name": "R. Alvarez", "experience_yrs": 12, "idle_median": 3.0, "skill": 0.96},
    "OP-102": {"name": "K. Osei", "experience_yrs": 2, "idle_median": 5.5, "skill": 1.06},
    "OP-103": {"name": "M. Lindqvist", "experience_yrs": 8, "idle_median": 3.5, "skill": 1.00},
    "OP-104": {"name": "D. Tanaka", "experience_yrs": 6, "idle_median": 4.0, "skill": 1.00},
    "OP-105": {"name": "S. Brennan", "experience_yrs": 4, "idle_median": 4.5, "skill": 1.03},
    "OP-106": {"name": "P. Nair", "experience_yrs": 15, "idle_median": 2.5, "skill": 0.94},
}

TASK_TYPES = {
    # base_cycle: seconds per dig-swing-dump cycle for a 0-experience-adjusted operator on firm ground
    "load_truck": {"base_cycle": 38.0, "bucket_t": 7.2, "delay": 0.12, "label": "Truck loading"},
    "trenching": {"base_cycle": 46.0, "bucket_t": 5.4, "delay": 0.06, "label": "Trenching"},
    "stockpile": {"base_cycle": 34.0, "bucket_t": 7.8, "delay": 0.05, "label": "Stockpile rehandle"},
    "grading": {"base_cycle": 50.0, "bucket_t": 4.2, "delay": 0.08, "label": "Grading / cleanup"},
}
TERRAIN_F = {"firm": 1.00, "soft": 1.12, "rocky": 1.25}
TRAM_M_PER_MIN = {"firm": 55.0, "soft": 40.0, "rocky": 35.0}
WEATHER_CYCLE_F = {"clear": 1.00, "rain": 1.15, "heat": 1.05}
WEATHER_DELAY = {"clear": 0.00, "rain": 0.14, "heat": 0.05}  # stoppages, slip, hydration breaks
WEATHER_HYD = {"clear": 0.0, "rain": -2.0, "heat": 7.0}
WEATHERS = ["clear", "rain", "heat"]

HYD_WORK_C = 63.0
HYD_IDLE_C = 57.0
IDLE_RPM = 820.0
WORK_RPM = 1480.0
IDLE_FUEL_LPH = 4.2
TRAM_EVERY_N_CYCLES = 3


def exp_factor(yrs: float) -> float:
    """Cycle-time multiplier from operator experience (more years -> faster, floors at 12 yrs)."""
    return 1.22 - 0.025 * min(yrs, 12)


def cycle_mean(task_type: str, terrain: str, weather: str, operator_id: str) -> float:
    op = OPERATORS[operator_id]
    return (TASK_TYPES[task_type]["base_cycle"] * TERRAIN_F[terrain] * WEATHER_CYCLE_F[weather]
            * exp_factor(op["experience_yrs"]) * op["skill"])


def work_fuel_lph(rpm: float, rng) -> float:
    return 0.0125 * rpm + rng.normal(0, 1.1)


# ---------------------------------------------------------------- history ----------------
def generate_history(seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    tele_rows, task_rows = [], []
    day0 = datetime(2026, 7, 1)
    for op_id, op in OPERATORS.items():
        for shift in range(45):
            date = (day0 + timedelta(days=shift)).strftime("%Y-%m-%d")
            weather = rng.choice(WEATHERS, p=[0.65, 0.2, 0.15])
            task_type = rng.choice(list(TASK_TYPES))
            terrain = rng.choice(list(TERRAIN_F), p=[0.55, 0.3, 0.15])
            tt = TASK_TYPES[task_type]
            mean_c = cycle_mean(task_type, terrain, weather, op_id)
            last_cycle, last_payload = mean_c, tt["bucket_t"]
            for _ in range(42):  # working samples
                cyc = mean_c * rng.normal(1, 0.06)
                rpm = rng.normal(WORK_RPM, 60)
                pay = tt["bucket_t"] * rng.normal(1, 0.07)
                last_cycle, last_payload = cyc, pay
                tele_rows.append({
                    "date": date, "machine_id": MACHINE_ID, "operator_id": op_id, "weather": weather,
                    "task_type": task_type, "terrain": terrain, "state": "working", "rpm": rpm,
                    "fuel_rate_lph": work_fuel_lph(rpm, rng),
                    "hyd_temp": HYD_WORK_C + WEATHER_HYD[weather] + rng.normal(0, 2.0),
                    "speed_kmh": rng.uniform(2.4, 3.8) if rng.random() < 0.12 else 0.0,
                    "idle_min": 0.0, "payload_t": pay, "cycle_s": cyc,
                })
            for _ in range(rng.integers(10, 18)):  # completed idle episodes (sampled at episode end)
                idle = float(np.clip(rng.lognormal(np.log(op["idle_median"]), 0.35), 0.5, None))
                tele_rows.append({
                    "date": date, "machine_id": MACHINE_ID, "operator_id": op_id, "weather": weather,
                    "task_type": task_type, "terrain": terrain, "state": "idle", "rpm": rng.normal(IDLE_RPM, 30),
                    "fuel_rate_lph": rng.normal(IDLE_FUEL_LPH, 0.35),
                    "hyd_temp": HYD_IDLE_C + WEATHER_HYD[weather] + rng.normal(0, 2.0),
                    "speed_kmh": 0.0, "idle_min": idle, "payload_t": last_payload, "cycle_s": last_cycle,
                })
            for _ in range(10):  # task segments for the ETA model
                tonnes = rng.uniform(20, 420)
                distance = rng.uniform(0, 160)
                recent = mean_c * rng.normal(1, 0.05)          # what the machine observed recently
                true_cycle = recent * rng.normal(1, 0.05)       # what the rest of the task actually took
                n_cycles = tonnes / (tt["bucket_t"] * rng.normal(1, 0.06))
                delay = tt["delay"] + WEATHER_DELAY[weather] + rng.exponential(0.03)
                minutes = (n_cycles * true_cycle / 60 * (1 + delay)
                           + distance / TRAM_M_PER_MIN[terrain] + rng.normal(0, 1.2))
                task_rows.append({
                    "date": date, "operator_id": op_id, "task_type": task_type, "tonnes": tonnes,
                    "distance_m": distance, "operator_experience_yrs": op["experience_yrs"],
                    "terrain": terrain, "weather": weather, "recent_cycle_s": recent,
                    "duration_min": max(minutes, 1.0),
                })
    tele = pd.DataFrame(tele_rows).round(3)
    tele.insert(0, "synthetic", 1)
    tasks = pd.DataFrame(task_rows).round(3)
    tasks.insert(0, "synthetic", 1)
    return tele, tasks


def ensure_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    DATA.mkdir(exist_ok=True)
    tp, kp = DATA / "telemetry_history.csv", DATA / "task_history.csv"
    if not tp.exists() or not kp.exists():
        tele, tasks = generate_history()
        tele.to_csv(tp, index=False)
        tasks.to_csv(kp, index=False)
    return pd.read_csv(tp), pd.read_csv(kp)


def load_tasks() -> list[dict]:
    return json.loads((DATA / "tasks.json").read_text(encoding="utf-8"))["tasks"]


# ---------------------------------------------------------------- live sim ---------------
PHASES = [("dig", 0.32, False), ("swing_loaded", 0.2, True), ("dump", 0.14, False), ("swing_return", 0.2, True),
          ("position", 0.14, False)]


class LiveSim:
    """One simulated excavator for one shift. Advanced by tick(dt) roughly once per real second.

    The sim clock runs at real time. trigger_idle(v) fast-forwards the clock by v minutes while the
    machine sits idle, so a long idle episode can be demonstrated without waiting.
    """

    def __init__(self, operator_id: str, tasks: list[dict], seed: int | None = None):
        self.rng = np.random.default_rng(seed)
        self.operator_id = operator_id
        self.tasks = tasks
        self.task_idx = 0
        self.moved_t = {t["id"]: 0.0 for t in tasks}
        self.task_started = {}
        self.task_finished = {}
        self.clock_offset = 0.0
        self.weather = "clear"
        self.seatbelt = True
        self.idle = False
        self.idle_since: datetime | None = None
        self.idle_log: list[dict] = []
        self.fuel_pct = START_FUEL_PCT
        self.hyd_temp = HYD_WORK_C - 8.0
        self.rpm = IDLE_RPM
        self.fuel_rate = IDLE_FUEL_LPH
        self.speed = 0.0
        self.swing = False
        self.phase = "dig"
        self.phase_i = 0
        self.phase_t = 0.0
        self.cycle_target = 40.0
        self.cycle_t = 0.0
        self.cycles_done = 0
        self.cycle_log: list[dict] = []
        self.tram_left = 0.0
        self.tram_requested = False
        self.payload = 0.0
        self.last_cycle_s: float | None = None
        self.recent_cycles: deque = deque(maxlen=5)
        self.finished = False
        self.pace = 1.0              # demo control: cycle-time multiplier (1.0 = this operator's normal pace)
        # time accounting for the operator productivity view (seconds; fast-forwarded idle included)
        self.time_s = {"working": 0.0, "travel": 0.0, "idle": 0.0}
        self.task_time_s: dict[str, dict[str, float]] = {}
        self.idle_task: str | None = None
        self.idle_progress: float | None = None
        t = self.current_task
        if t:
            self.task_started[t["id"]] = self.now()
        self._new_cycle()

    # --- clock -------------------------------------------------------------------------
    def now(self) -> datetime:
        return datetime.now() + timedelta(seconds=self.clock_offset)

    @property
    def current_task(self) -> dict | None:
        return self.tasks[self.task_idx] if self.task_idx < len(self.tasks) else None

    def seed_recent_cycles(self, values: list[float]):
        for v in values:
            self.recent_cycles.append(float(v))

    @property
    def recent_cycle_s(self) -> float:
        return float(np.mean(self.recent_cycles)) if self.recent_cycles else self.cycle_target

    @property
    def idle_min(self) -> float:
        if not self.idle or not self.idle_since:
            return 0.0
        return (self.now() - self.idle_since).total_seconds() / 60.0

    # --- controls ----------------------------------------------------------------------
    def start_idle(self, minutes: float):
        """Machine goes idle; the clock fast-forwards `minutes` so the idle stretch has already run."""
        if not self.idle:
            self.idle = True
            self.idle_since = self.now()
            self.idle_task = self.current_task["id"] if self.current_task else None
            self.idle_progress = (self.moved_t[self.idle_task] / self.current_task["tonnes"]) if self.idle_task else None
        skip = max(float(minutes), 0.0)
        self.clock_offset += skip * 60.0
        self._account("idle", skip * 60.0, self.idle_task)
        self.fuel_pct -= IDLE_FUEL_LPH * (skip / 60.0) / FUEL_TANK_L * 100.0
        self.hyd_temp = HYD_IDLE_C + WEATHER_HYD[self.weather]

    def end_idle(self) -> float:
        if not self.idle:
            return 0.0
        dur = self.idle_min
        self.idle_log.append({"start": self.idle_since.strftime("%H:%M:%S"), "minutes": round(dur, 1),
                              "task_id": self.idle_task, "progress": self.idle_progress})
        self.idle = False
        self.idle_since = None
        self._new_cycle()
        return dur

    def request_tram(self):
        self.tram_requested = True

    def reorder_pending(self, order: list[dict]):
        """Replace the not-yet-started tail with `order` (minus anything already done/active).
        Done and active tasks, task_idx, moved_t, task_started and task_finished are left untouched.
        Mutates self.tasks in place so the Engine's reference to the same list stays valid."""
        keep = self.tasks[: self.task_idx + (1 if self.current_task else 0)]
        kept = {t["id"] for t in keep}
        tail = [t for t in order if t["id"] not in kept]
        was_finished = self.finished
        self.tasks[:] = keep + tail
        for t in tail:
            self.moved_t.setdefault(t["id"], 0.0)
        if was_finished and self.current_task:
            self.finished = False
            self.task_started[self.current_task["id"]] = self.now()
            self._new_cycle()

    # --- internals ---------------------------------------------------------------------
    def _new_cycle(self):
        t = self.current_task
        if not t:
            return
        self.cycle_target = cycle_mean(t["task_type"], t["terrain"], self.weather, self.operator_id) \
            * self.rng.normal(1, 0.06) * self.pace
        self.cycle_t = 0.0
        self.phase_i, self.phase_t = 0, 0.0
        self.phase = PHASES[0][0]

    def _complete_cycle(self):
        t = self.current_task
        pay = TASK_TYPES[t["task_type"]]["bucket_t"] * self.rng.normal(1, 0.07)
        self.payload = pay
        self.last_cycle_s = self.cycle_target
        self.recent_cycles.append(self.cycle_target)
        self.cycles_done += 1
        self.cycle_log.append({"task_id": t["id"], "cycle_s": self.cycle_target, "payload_t": pay,
                               "weather": self.weather})
        self.moved_t[t["id"]] += pay
        if self.moved_t[t["id"]] >= t["tonnes"]:
            self.moved_t[t["id"]] = float(t["tonnes"])
            self.task_finished[t["id"]] = self.now()
            self.task_idx += 1
            if self.current_task:
                self.task_started[self.current_task["id"]] = self.now()
            else:
                self.finished = True
        if self.cycles_done % TRAM_EVERY_N_CYCLES == 0 or self.tram_requested:
            self.tram_left = float(self.rng.uniform(5, 8))
            self.tram_requested = False
        self._new_cycle()

    def _account(self, bucket: str, seconds: float, task_id: str | None):
        self.time_s[bucket] += seconds
        if task_id:
            self.task_time_s.setdefault(task_id, {"working": 0.0, "travel": 0.0, "idle": 0.0})[bucket] += seconds

    def tick(self, dt: float) -> dict:
        events = {}
        tid = self.current_task["id"] if self.current_task else None
        if self.finished:
            self.idle = False
        if self.idle or self.finished:
            self.rpm = self.rng.normal(IDLE_RPM, 30)
            self.fuel_rate = self.rng.normal(IDLE_FUEL_LPH, 0.35)
            self.speed, self.swing = 0.0, False
            self.phase = "idle"
            hyd_target = HYD_IDLE_C + WEATHER_HYD[self.weather]
        else:
            self.rpm = self.rng.normal(WORK_RPM, 60)
            self.fuel_rate = work_fuel_lph(self.rpm, self.rng)
            hyd_target = HYD_WORK_C + WEATHER_HYD[self.weather]
            if self.tram_requested and self.tram_left <= 0:
                self.tram_left = float(self.rng.uniform(5, 8))
                self.tram_requested = False
            if self.tram_left > 0:
                self.phase = "tram"
                self.speed = float(self.rng.uniform(2.6, 3.8))
                self.swing = False
                self.tram_left -= dt
            else:
                self.speed = 0.0
                self.cycle_t += dt
                self.phase_t += dt
                name, frac, swing = PHASES[self.phase_i]
                if self.phase_t >= frac * self.cycle_target and self.phase_i < len(PHASES) - 1:
                    self.phase_i += 1
                    self.phase_t = 0.0
                    name, frac, swing = PHASES[self.phase_i]
                self.phase, self.swing = name, swing
                if self.cycle_t >= self.cycle_target:
                    before = self.task_idx
                    self._complete_cycle()
                    events["cycle"] = True
                    if self.task_idx != before:
                        events["task_done"] = self.tasks[before]["id"]
        self.hyd_temp += (hyd_target - self.hyd_temp) * 0.03 + self.rng.normal(0, 0.05)
        self.fuel_pct -= self.fuel_rate * dt / 3600.0 / FUEL_TANK_L * 100.0
        bucket = "idle" if (self.idle or self.finished) else "travel" if self.phase == "tram" else "working"
        self._account(bucket, dt, None if self.finished else tid)
        return events

    def features(self) -> dict:
        """Current feature vector in the same shape as telemetry_history.csv."""
        return {
            "idle_min": self.idle_min,
            "rpm": self.rpm,
            "cycle_s": self.last_cycle_s or self.recent_cycle_s,
            "hyd_temp": self.hyd_temp,
            "fuel_rate_lph": self.fuel_rate,
            "payload_t": self.payload or TASK_TYPES[(self.current_task or self.tasks[-1])["task_type"]]["bucket_t"],
        }


if __name__ == "__main__":
    tele, tasks = generate_history()
    DATA.mkdir(exist_ok=True)
    tele.to_csv(DATA / "telemetry_history.csv", index=False)
    tasks.to_csv(DATA / "task_history.csv", index=False)
    print(f"telemetry_history.csv: {len(tele)} rows | task_history.csv: {len(tasks)} rows (synthetic)")
