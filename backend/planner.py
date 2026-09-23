"""Weather-aware task planner — a deterministic, explainable heuristic. Never calls an LLM.

Scoring (per task, per forecast hour):
    penalty  = W[rain sens] × RAIN_MAX_PENALTY × rain_probability
             + W[wind sens] × WIND_MAX_PENALTY × wind_severity         (0 at WIND_CALM_KMH → 1 at WIND_STOP_KMH)
             + W[vis sens]  × VIS_MAX_PENALTY  × visibility_severity   (0 at VIS_GOOD_M → 1 at VIS_POOR_M)
    effective duration = base duration × (1 + penalty), integrated hour by hour across the task's window.
    Rain enters as a probability, so 40% rain costs half as much as 80% (probabilistic scoring,
    deterministic execution).

Sequencing (list scheduling, one lane per machine, operators may not overlap):
    1. Done / active tasks are locked in place. Manager start-time overrides are pinned.
    2. At each decision point the default is the next task in the manager's original order.
    3. For every candidate:   advantage = weather delay if postponed to the end of the lane
                                        − (weather delay + waiting) if started now
       A different task is pulled forward only if its advantage beats the default's by at least
       REORDER_THRESHOLD_MIN. So sensitive work claims good windows and tolerant work drifts into
       poor ones, but the manager's order is kept whenever the forecast gives no real reason to change.
    4. Dependencies, earliest start, latest finish (as a large cost) and shift bounds are respected;
       whatever cannot be satisfied is returned as a warning, never silently dropped.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from planner_explain import build_summary, explain_task
from weather import hhmm, hour_at, to_min, window_weather

# ============================ CONFIG — every planner coefficient lives here ============================
SENSITIVITY_LEVELS = ("low", "medium", "high")
SENSITIVITY_FACTORS = ("rain", "wind", "visibility")
SENSITIVITY_WEIGHT = {"low": 0.1, "medium": 0.5, "high": 1.0}
RAIN_MAX_PENALTY = 0.60       # HIGH rain sensitivity at 100% rain -> task runs 60% longer
WIND_MAX_PENALTY = 0.50
WIND_CALM_KMH = 20.0
WIND_STOP_KMH = 50.0
VIS_MAX_PENALTY = 0.40
VIS_GOOD_M = 2000.0
VIS_POOR_M = 300.0
REORDER_THRESHOLD_MIN = 5.0   # min extra weather delay avoided before the manager's order is changed
DEADLINE_MISS_COST_MIN = 1000.0
DEFAULT_PRIORITY = 50
UNASSIGNED = "UNASSIGNED"
# =======================================================================================================

DEFAULT_SENSITIVITY: dict[str, dict[str, str]] = {
    "grading": {"rain": "high", "wind": "low", "visibility": "medium"},
    "trenching": {"rain": "medium", "wind": "low", "visibility": "medium"},
    "stockpile": {"rain": "low", "wind": "low", "visibility": "low"},
    "load_truck": {"rain": "medium", "wind": "low", "visibility": "medium"},
}
SENSITIVITY_PRESETS = {**DEFAULT_SENSITIVITY, "slope_travel": {"rain": "high", "wind": "high", "visibility": "high"}}

CONSTANTS = {
    "SENSITIVITY_WEIGHT": SENSITIVITY_WEIGHT, "RAIN_MAX_PENALTY": RAIN_MAX_PENALTY,
    "WIND_MAX_PENALTY": WIND_MAX_PENALTY, "WIND_CALM_KMH": WIND_CALM_KMH, "WIND_STOP_KMH": WIND_STOP_KMH,
    "VIS_MAX_PENALTY": VIS_MAX_PENALTY, "VIS_GOOD_M": VIS_GOOD_M, "VIS_POOR_M": VIS_POOR_M,
    "REORDER_THRESHOLD_MIN": REORDER_THRESHOLD_MIN,
}

DurationFn = Callable[[dict], tuple[float, str]]


# ---------------------------------------------------------------- sensitivity -------------
def default_sensitivity(task_type: str) -> dict[str, str]:
    return dict(DEFAULT_SENSITIVITY.get(task_type, {"rain": "medium", "wind": "medium", "visibility": "medium"}))


def validate_sensitivity(profile) -> dict[str, str]:
    if not isinstance(profile, dict):
        raise ValueError("weather_sensitivity must be an object with rain, wind and visibility levels")
    extra = set(profile) - set(SENSITIVITY_FACTORS)
    if extra:
        raise ValueError(f"unknown weather_sensitivity factor(s): {', '.join(sorted(extra))}")
    out = {}
    for f in SENSITIVITY_FACTORS:
        v = profile.get(f)
        if v not in SENSITIVITY_LEVELS:
            raise ValueError(f"weather_sensitivity.{f} must be one of low|medium|high (got {v!r})")
        out[f] = v
    return out


# ---------------------------------------------------------------- scoring -----------------
def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def hour_penalty(hour: dict, profile: dict[str, str]) -> dict[str, float]:
    """Fractional slowdown per factor for one forecast hour."""
    wind_sev = _clamp01((hour["wind_kmh"] - WIND_CALM_KMH) / (WIND_STOP_KMH - WIND_CALM_KMH))
    vis_sev = _clamp01((VIS_GOOD_M - hour["visibility_m"]) / (VIS_GOOD_M - VIS_POOR_M))
    return {
        "rain": SENSITIVITY_WEIGHT[profile["rain"]] * RAIN_MAX_PENALTY * hour["rain_probability"] / 100.0,
        "wind": SENSITIVITY_WEIGHT[profile["wind"]] * WIND_MAX_PENALTY * wind_sev,
        "visibility": SENSITIVITY_WEIGHT[profile["visibility"]] * VIS_MAX_PENALTY * vis_sev,
    }


def run_task(base_min: float, start: float, hours: list[dict], profile: dict[str, str]) -> tuple[float, dict]:
    """Integrate a task through the forecast. Returns (end minute, weather delay per factor in minutes)."""
    t, left = float(start), float(base_min)
    delay = {f: 0.0 for f in SENSITIVITY_FACTORS}
    while left > 1e-9:
        pen = hour_penalty(hour_at(hours, t), profile)
        p = sum(pen.values())
        slot_end = (t // 60 + 1) * 60
        rate = 1.0 / (1.0 + p)
        dt = min(slot_end - t, left / rate)
        left -= dt * rate
        if p > 0:
            for f in delay:
                delay[f] += dt * (pen[f] / (1.0 + p))
        t += dt
    return t, delay


# ---------------------------------------------------------------- scheduling --------------
def lane_of(task: dict) -> str:
    return task.get("assigned_machine") or UNASSIGNED


def build_schedule(tasks: list[dict], hours: list[dict], shift_start: int, shift_end: int,
                   durations: dict[str, tuple[float, str]], *, reorder: bool,
                   overrides: dict | None = None, locked: list[dict] | None = None) -> list[dict]:
    """`tasks` must be in the manager's original order. Returns entries sorted by start time."""
    overrides = overrides or {}
    order = {t["id"]: i for i, t in enumerate(tasks)}
    by_id = {t["id"]: t for t in tasks}
    lane_free: dict[str, float] = defaultdict(lambda: float(shift_start))
    lane_count: dict[str, int] = defaultdict(int)
    busy: dict[tuple, list[tuple[float, float]]] = defaultdict(list)
    finish: dict[str, float] = {}
    entries: list[dict] = []

    def res_keys(t):
        ks = [("machine", lane_of(t))] if t.get("assigned_machine") else []
        return ks + ([("operator", t["assigned_operator"])] if t.get("assigned_operator") else [])

    def fit(t, ready):
        start = ready
        for _ in range(len(tasks) * 2 + 2):
            end, fd = run_task(durations[t["id"]][0], start, hours, t["weather_sensitivity"])
            clash = [e for k in res_keys(t) for s, e in busy[k] if s < end - 1e-6 and e > start + 1e-6]
            if not clash:
                break
            start = max(clash)
        return start, end, fd

    def place(t, start, end, fd, *, advance=True, **flags):
        for k in res_keys(t):
            busy[k].append((start, end))
        if advance:
            lane_free[lane_of(t)] = max(lane_free[lane_of(t)], end)
            lane_count[lane_of(t)] += 1
        finish[t["id"]] = end
        entries.append(_entry(t, start, end, fd, durations[t["id"]], hours, **flags))

    # 1. done / active tasks never move
    for lk in locked or []:
        t = by_id.get(lk["task_id"])
        if not t:
            continue
        if lk.get("start") is not None and lk.get("end") is not None:
            s, e = float(lk["start"]), float(lk["end"])
            fd = run_task(durations[t["id"]][0], s, hours, t["weather_sensitivity"])[1]
        else:
            s, e, fd = fit(t, lane_free[lane_of(t)])
        place(t, s, e, fd, locked=True, live_status=lk.get("status"))

    # 2. manager-pinned start times (placed as-is; clashes are reported as conflicts, not moved)
    if reorder:
        for t in tasks:
            ov = overrides.get(t["id"]) or {}
            if t["id"] not in finish and ov.get("start"):
                s = float(to_min(ov["start"]))
                e, fd = run_task(durations[t["id"]][0], s, hours, t["weather_sensitivity"])
                place(t, s, e, fd, advance=False, override=ov)

    # 3. greedy list scheduling for everything else
    remaining = [t for t in tasks if t["id"] not in finish]
    while remaining:
        eligible = [t for t in remaining if all(d in finish for d in t.get("depends_on") or [])] or remaining[:1]
        ready = {t["id"]: max([float(shift_start), float(to_min(t.get("earliest_start") or hhmm(shift_start))),
                               lane_free[lane_of(t)]] + [finish[d] for d in t.get("depends_on") or [] if d in finish])
                 for t in eligible}
        first = min(eligible, key=lambda t: (ready[t["id"]], order[t["id"]]))
        lane = lane_of(first)
        decision = ready[first["id"]]
        cands = [t for t in eligible if lane_of(t) == lane]
        pos = lane_count[lane] + 1
        forced = next((t for t in cands if reorder and (overrides.get(t["id"]) or {}).get("position") == pos), None)
        if forced:
            s, e, fd = fit(forced, ready[forced["id"]])
            pick, flags = forced, {"override": overrides[forced["id"]]}
        else:
            lane_total = sum(durations[c["id"]][0] for c in cands)
            scored = []
            for c in cands:
                base = durations[c["id"]][0]
                s, e, fd = fit(c, ready[c["id"]])
                latest = to_min(c.get("latest_finish") or hhmm(shift_end))
                now_cost = (s - decision) + (e - s - base) + (DEADLINE_MISS_COST_MIN if e > latest else 0)
                ls, le, _ = fit(c, max(ready[c["id"]], decision + lane_total - base))
                late_cost = (le - ls - base) + (DEADLINE_MISS_COST_MIN if le > latest else 0)
                scored.append({"t": c, "s": s, "e": e, "fd": fd, "adv": late_cost - now_cost})
            default = scored[0]
            best = min(scored, key=lambda x: (-round(x["adv"], 1), -int(x["t"].get("priority", DEFAULT_PRIORITY)),
                                              order[x["t"]["id"]]))
            choice = best if reorder and best["adv"] - default["adv"] >= REORDER_THRESHOLD_MIN else default
            pick, s, e, fd, flags = choice["t"], choice["s"], choice["e"], choice["fd"], {}
        place(pick, s, e, fd, **flags)
        remaining.remove(pick)

    entries.sort(key=lambda x: (x["start_min"], x["machine"] or "", order[x["task_id"]]))
    for i, x in enumerate(entries, 1):
        x["position"] = i
    _warn(entries, by_id, finish, shift_end)
    return entries


def _entry(t: dict, start: float, end: float, fd: dict, dur: tuple[float, str], hours: list[dict], *,
           locked: bool = False, live_status: str | None = None, override: dict | None = None) -> dict:
    base, src = dur
    return {
        "task_id": t["id"], "name": t["name"], "task_type": t["task_type"], "location": t.get("location"),
        "machine": t.get("assigned_machine"), "operator": t.get("assigned_operator"),
        "start": hhmm(start), "end": hhmm(end), "start_min": round(start, 2), "end_min": round(end, 2),
        "base_min": round(base, 1), "duration_source": src, "effective_min": round(end - start, 1),
        "delay_min": round(sum(fd.values()), 1), "factor_delay": {k: round(v, 1) for k, v in fd.items()},
        "weather_sensitivity": dict(t["weather_sensitivity"]), "weather": window_weather(hours, start, end),
        "locked": locked, "live_status": live_status, "override": override, "warnings": [],
    }


def _warn(entries: list[dict], by_id: dict, finish: dict, shift_end: int):
    for x in entries:
        t = by_id[x["task_id"]]
        if not t.get("assigned_operator"):
            x["warnings"].append("No operator assigned")
        if not t.get("assigned_machine"):
            x["warnings"].append("No machine assigned")
        if x["end_min"] > shift_end + 0.5:
            x["warnings"].append(f"Finishes {x['end']}, after shift end {hhmm(shift_end)}")
        if t.get("earliest_start") and x["start_min"] < to_min(t["earliest_start"]) - 0.5:
            x["warnings"].append(f"Starts before earliest start {t['earliest_start']}")
        if t.get("latest_finish") and x["end_min"] > to_min(t["latest_finish"]) + 0.5:
            x["warnings"].append(f"Misses latest finish {t['latest_finish']}")
        for d in t.get("depends_on") or []:
            if d not in finish:
                x["warnings"].append(f"Depends on {d}, which is not in the plan")
            elif finish[d] > x["start_min"] + 0.5:
                x["warnings"].append(f"Starts before dependency {d} finishes")


def detect_conflicts(entries: list[dict]) -> list[dict]:
    """Same operator or same machine booked on overlapping windows."""
    out = []
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if not (a["start_min"] < b["end_min"] - 0.5 and b["start_min"] < a["end_min"] - 0.5):
                continue
            for kind in ("operator", "machine"):
                if a[kind] and a[kind] == b[kind]:
                    out.append({"type": f"{kind}_overlap", kind: a[kind], "tasks": [a["task_id"], b["task_id"]],
                                "message": f"{a[kind]} is booked on {a['task_id']} ({a['start']}–{a['end']}) and "
                                           f"{b['task_id']} ({b['start']}–{b['end']}) at the same time"})
    return out


# ---------------------------------------------------------------- facade ------------------
class WeatherAwarePlanner:
    """Inputs: tasks (original order), forecast, shift bounds, duration estimator, overrides, locked tasks.
    Outputs: original vs recommended schedule, per-task recommendation with reason, summary."""

    def __init__(self, forecast: dict, shift_start: str, shift_end: str, duration_fn: DurationFn):
        self.forecast = forecast
        self.hours = forecast["hours"]
        self.s0, self.s1 = to_min(shift_start), to_min(shift_end)
        self.duration_fn = duration_fn

    def plan(self, tasks: list[dict], overrides: dict | None = None, locked: list[dict] | None = None) -> dict:
        tasks = sorted(tasks, key=lambda t: t.get("original_order", 0))
        durations = {t["id"]: self.duration_fn(t) for t in tasks}
        orig = build_schedule(tasks, self.hours, self.s0, self.s1, durations, reorder=False, locked=locked)
        rec = build_schedule(tasks, self.hours, self.s0, self.s1, durations, reorder=True,
                             overrides=overrides, locked=locked)
        o_by, r_by = {x["task_id"]: x for x in orig}, {x["task_id"]: x for x in rec}
        recs = {t["id"]: explain_task(t, o_by[t["id"]], r_by[t["id"]], o_by, r_by, self.hours) for t in tasks}
        for x in rec:
            x["recommendation"] = recs[x["task_id"]]
        conflicts = detect_conflicts(rec)
        summary = build_summary(self.forecast, orig, rec, recs, conflicts, self.s1)
        return {"forecast_id": self.forecast["forecast_id"], "original_schedule": orig,
                "recommended_schedule": rec, "recommendations": recs, "conflicts": conflicts, "summary": summary}
