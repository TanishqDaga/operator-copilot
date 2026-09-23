"""Planner persistence (data/planning.json) and task validation. JSON only — no database.

planning.json is seeded from data/tasks.json on first run (or on "Reset demo plan") and is the
manager-edited source of truth afterwards:
    {"tasks": [...], "forecast_scenario": ..., "forecast": {...}, "overrides": {...},
     "recommendation": {...} | null, "published_schedule": {...} | null, "history": [...]}
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from planner import SENSITIVITY_PRESETS, default_sensitivity, validate_sensitivity
from simulator import DATA, MACHINE_ID, OPERATORS, TASK_TYPES, TERRAIN_F
from weather import DEFAULT_SCENARIO, SCENARIOS, SHIFT_END, SHIFT_START, generate_forecast, to_min

PLANNING_PATH = DATA / "planning.json"
SEED_PATH = DATA / "tasks.json"
HISTORY_KEEP = 20

# Small synthetic fleet. Only MACHINE_ID is driven by the live simulator.
MACHINES = [
    {"id": MACHINE_ID, "model": "CAT 320", "note": "Live-simulated machine"},
    {"id": "CAT320-051", "model": "CAT 320", "note": "Synthetic fleet entry"},
    {"id": "CAT336-017", "model": "CAT 336", "note": "Synthetic fleet entry"},
]
MACHINE_IDS = {m["id"] for m in MACHINES}

EDITABLE = ("name", "description", "location", "task_type", "tonnes", "distance_m", "terrain",
            "estimated_duration_min", "weather_sensitivity", "priority", "assigned_operator",
            "assigned_machine", "earliest_start", "latest_finish", "depends_on")


class PlanningError(Exception):
    def __init__(self, message: str, status: int = 400, detail: dict | None = None):
        super().__init__(message)
        self.status = status
        self.detail = detail


def _num(v, field: str, lo: float, hi: float, allow_none: bool = False):
    if v is None or v == "":
        if allow_none:
            return None
        raise PlanningError(f"{field} is required")
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise PlanningError(f"{field} must be a number") from None
    if not lo <= x <= hi:
        raise PlanningError(f"{field} must be between {lo:g} and {hi:g}")
    return int(x) if x.is_integer() else round(x, 1)


def _time(v, field: str, s0: int, s1: int) -> str:
    try:
        m = to_min(v)
    except (ValueError, AttributeError):
        raise PlanningError(f"{field} must be a time like 09:30") from None
    if not s0 <= m <= s1:
        raise PlanningError(f"{field} {v} is outside the shift ({SHIFT_START}–{SHIFT_END})")
    return f"{m // 60:02d}:{m % 60:02d}"


def normalize_task(payload: dict, *, base: dict | None = None, shift: dict | None = None) -> dict:
    """Merge editable fields over `base` and validate everything. Raises PlanningError."""
    shift = shift or {"start": SHIFT_START, "end": SHIFT_END}
    s0, s1 = to_min(shift["start"]), to_min(shift["end"])
    t = dict(base or {})
    for k in EDITABLE:
        if k in payload:
            t[k] = payload[k]
    name = str(t.get("name") or "").strip()
    if not name:
        raise PlanningError("name is required")
    t["name"] = name[:80]
    t["description"] = str(t.get("description") or "").strip()[:400]
    t["location"] = str(t.get("location") or "").strip()[:80] or "—"
    if t.get("task_type") not in TASK_TYPES:
        raise PlanningError(f"task_type must be one of {', '.join(TASK_TYPES)}")
    if t.get("terrain") not in TERRAIN_F:
        raise PlanningError(f"terrain must be one of {', '.join(TERRAIN_F)}")
    t["tonnes"] = _num(t.get("tonnes"), "tonnes", 1, 5000)
    t["distance_m"] = _num(t.get("distance_m", 0), "distance_m", 0, 5000)
    t["estimated_duration_min"] = _num(t.get("estimated_duration_min"), "estimated_duration_min", 5, 720, True)
    t["priority"] = int(_num(t.get("priority", 50), "priority", 0, 100))
    try:
        t["weather_sensitivity"] = validate_sensitivity(t.get("weather_sensitivity") or default_sensitivity(t["task_type"]))
    except ValueError as e:
        raise PlanningError(str(e)) from None
    op, mc = t.get("assigned_operator") or None, t.get("assigned_machine") or None
    if op is not None and op not in OPERATORS:
        raise PlanningError(f"Unknown operator {op}")
    if mc is not None and mc not in MACHINE_IDS:
        raise PlanningError(f"Unknown machine {mc}")
    t["assigned_operator"], t["assigned_machine"] = op, mc
    t["earliest_start"] = _time(t.get("earliest_start") or shift["start"], "earliest_start", s0, s1)
    t["latest_finish"] = _time(t.get("latest_finish") or shift["end"], "latest_finish", s0, s1)
    if to_min(t["earliest_start"]) >= to_min(t["latest_finish"]):
        raise PlanningError("earliest_start must be before latest_finish")
    deps = t.get("depends_on") or []
    if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
        raise PlanningError("depends_on must be a list of task ids")
    t["depends_on"] = sorted(set(deps))
    return t


class PlanningStore:
    def __init__(self, path: Path = PLANNING_PATH, seed_path: Path = SEED_PATH):
        self.path, self.seed_path = Path(path), Path(seed_path)
        self.data = self._load()

    # ------------------------------------------------------------------ persistence
    def _seed(self) -> dict:
        raw = json.loads(self.seed_path.read_text(encoding="utf-8"))
        shift = {"name": "Day shift", "start": SHIFT_START, "end": SHIFT_END}
        tasks = [{"id": t["id"], "original_order": i, **normalize_task(t, shift=shift)}
                 for i, t in enumerate(raw["tasks"], 1)]
        return {"version": 1, "plan_name": raw.get("shift_plan", "Day shift"), "shift": shift,
                "forecast_scenario": DEFAULT_SCENARIO, "forecast": generate_forecast(DEFAULT_SCENARIO),
                "tasks": tasks, "tasks_version": 1, "overrides": {}, "recommendation": None,
                "plan_status": "draft", "published_schedule": None, "history": []}

    def _load(self) -> dict:
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(d.get("tasks"), list) and d.get("version") == 1:
                    return d
            except (OSError, ValueError):
                pass
        d = self._seed()
        self._write(d)
        return d

    def _write(self, d: dict):
        try:
            self.path.parent.mkdir(exist_ok=True)
            self.path.write_text(json.dumps(d, indent=1, default=str), encoding="utf-8")
        except OSError:
            pass

    def save(self):
        self._write(self.data)

    def reset(self):
        self.data = self._seed()
        self.save()

    # ------------------------------------------------------------------ accessors
    @property
    def shift(self) -> dict:
        return self.data["shift"]

    @property
    def tasks(self) -> list[dict]:
        return sorted(self.data["tasks"], key=lambda t: t["original_order"])

    @property
    def forecast(self) -> dict:
        return self.data["forecast"]

    @property
    def overrides(self) -> dict:
        return self.data["overrides"]

    @property
    def published(self) -> dict | None:
        return self.data["published_schedule"]

    def get(self, task_id: str) -> dict:
        t = next((x for x in self.data["tasks"] if x["id"] == task_id), None)
        if not t:
            raise PlanningError(f"Unknown task {task_id}", 404)
        return t

    def _touch(self):
        self.data["tasks_version"] += 1
        if self.data["recommendation"]:
            self.data["plan_status"] = "draft"

    def _check_deps(self, tasks: list[dict]):
        ids = {t["id"] for t in tasks}
        graph = {t["id"]: t.get("depends_on") or [] for t in tasks}
        for tid, deps in graph.items():
            for d in deps:
                if d == tid:
                    raise PlanningError(f"{tid} cannot depend on itself")
                if d not in ids:
                    raise PlanningError(f"{tid} depends on unknown task {d}")
        seen, stack = set(), set()

        def visit(n):
            if n in stack:
                raise PlanningError(f"Circular dependency involving {n}")
            if n in seen:
                return
            stack.add(n)
            for d in graph[n]:
                visit(d)
            stack.discard(n)
            seen.add(n)
        for n in graph:
            visit(n)

    # ------------------------------------------------------------------ task CRUD
    def create(self, payload: dict) -> dict:
        nums = [int(m.group(1)) for t in self.data["tasks"] if (m := re.fullmatch(r"T(\d+)", t["id"]))]
        t = normalize_task(payload, shift=self.shift)
        t = {"id": f"T{max(nums, default=0) + 1}",
             "original_order": max((x["original_order"] for x in self.data["tasks"]), default=0) + 1, **t}
        self._check_deps(self.data["tasks"] + [t])
        self.data["tasks"].append(t)
        self._touch()
        self.save()
        return t

    def update(self, task_id: str, payload: dict) -> dict:
        cur = self.get(task_id)
        t = normalize_task(payload, base=cur, shift=self.shift)
        self._check_deps([t if x["id"] == task_id else x for x in self.data["tasks"]])
        cur.clear()
        cur.update(t)
        self._touch()
        self.save()
        return cur

    def delete(self, task_id: str) -> dict:
        t = self.get(task_id)
        users = [x["id"] for x in self.data["tasks"] if task_id in (x.get("depends_on") or [])]
        if users:
            raise PlanningError(f"{', '.join(users)} depend{'s' if len(users) == 1 else ''} on {task_id} — "
                                f"remove the dependency first", 409)
        self.data["tasks"].remove(t)
        self.data["overrides"].pop(task_id, None)
        self._touch()
        self.save()
        return t

    def assign(self, task_id: str, operator_id: str | None, machine_id: str | None) -> dict:
        return self.update(task_id, {"assigned_operator": operator_id, "assigned_machine": machine_id})

    # ------------------------------------------------------------------ forecast / plan state
    def set_scenario(self, scenario: str) -> dict:
        if scenario not in SCENARIOS:
            raise PlanningError(f"Unknown forecast scenario {scenario} (use one of {', '.join(SCENARIOS)})")
        self.data["forecast_scenario"] = scenario
        self.data["forecast"] = generate_forecast(scenario, self.shift["start"], self.shift["end"])
        if self.data["recommendation"]:
            self.data["plan_status"] = "draft"
        self.save()
        return self.data["forecast"]

    def set_override(self, task_id: str, override: dict | None):
        if override is None:
            self.data["overrides"].pop(task_id, None)
        else:
            self.data["overrides"][task_id] = override
        self.save()

    def set_recommendation(self, rec: dict, status: str):
        self.data["recommendation"] = {**rec, "tasks_version": self.data["tasks_version"],
                                       "generated_at": datetime.now().isoformat(timespec="seconds")}
        self.data["plan_status"] = status
        self.save()

    def stale_reason(self) -> str | None:
        rec = self.data["recommendation"]
        if not rec:
            return "No recommendation generated yet"
        if rec["tasks_version"] != self.data["tasks_version"]:
            return "Tasks changed since the recommendation was generated"
        if rec["forecast_id"] != self.forecast["forecast_id"]:
            return "Forecast changed since the recommendation was generated"
        return None

    def next_schedule_id(self) -> str:
        return f"SCH-{self.data.get('publish_count', 0) + 1:04d}"

    def publish(self, record: dict):
        prev = self.data["published_schedule"]
        if prev:
            self.data["history"] = ([{**prev, "status": "superseded", "tasks": None}] + self.data["history"])[:HISTORY_KEEP]
        self.data["published_schedule"] = record
        self.data["publish_count"] = self.data.get("publish_count", 0) + 1
        self.data["plan_status"] = "published"
        self.save()

    def presets(self) -> dict:
        return SENSITIVITY_PRESETS
