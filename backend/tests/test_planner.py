"""Planner tests: pure algorithm + the service that binds it to the live shift (fake engine, temp JSON)."""
from __future__ import annotations

import json
import threading

import pytest

from planner import (WeatherAwarePlanner, build_schedule, detect_conflicts, hour_penalty, run_task,
                     validate_sensitivity)
from planning_service import PlanningService
from planning_store import SEED_PATH, PlanningError, PlanningStore, normalize_task
from roles import User
from simulator import LiveSim
from weather import generate_forecast

MGR = User("MGR-01", "manager", "Test manager")
RAIN = generate_forecast("rain_window")
RAIN_START = next(w for w in RAIN["windows"] if w["kind"] == "rain")["start_min"]


def seed_tasks() -> list[dict]:
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))["tasks"]
    return [{"id": t["id"], "original_order": i, **normalize_task(t)} for i, t in enumerate(raw, 1)]


def manual(t):
    return float(t["estimated_duration_min"]), "manager_estimate"


def plan(tasks=None, forecast=RAIN, **kw):
    return WeatherAwarePlanner(forecast, "09:00", "19:00", manual).plan(tasks or seed_tasks(), **kw)


def by_id(entries):
    return {x["task_id"]: x for x in entries}


# ---------------------------------------------------------------- fake engine for service tests
class FakeEta:
    def predict(self, **kw):
        return 30.0


class FakeEngine:
    def __init__(self):
        self.lock = threading.RLock()
        self.sim = None
        self.shift = {"active": False}
        self.events: list[dict] = []
        self.state: dict = {}
        self.eta = FakeEta()

    def cycle_baseline(self, op, task, weather):
        return 40.0

    def _log(self, kind, level, title, detail=None, **data):
        ev = {"id": len(self.events) + 1, "kind": kind, "level": level, "title": title, "detail": detail, **data}
        self.events.append(ev)
        return ev

    def start(self, operator_id, svc):
        self.sim = LiveSim(operator_id, svc.execution_tasks(operator_id), seed=1)
        self.shift = {"active": True}


@pytest.fixture
def svc(tmp_path):
    return PlanningService(FakeEngine(), "OP-104", PlanningStore(tmp_path / "planning.json"))


# ---------------------------------------------------------------- 1. rain-sensitive task moves before rain
def test_rain_sensitive_task_moves_before_rain():
    res = plan()
    o, r = by_id(res["original_schedule"]), by_id(res["recommended_schedule"])
    assert o["T4"]["start_min"] >= RAIN_START - 60          # originally runs into the rain
    assert r["T4"]["end_min"] <= RAIN_START                 # recommended entirely before it
    assert r["T4"]["position"] < o["T4"]["position"]
    rec = res["recommendations"]["T4"]
    assert rec["label"] == "Moved earlier — rain sensitive"
    assert "HIGH rain sensitivity" in rec["reason"] and "85%" in rec["reason"]
    assert rec["priority_type"] == "SCHEDULE_RECOMMENDATION"


# ---------------------------------------------------------------- 2. rain-tolerant task can go into rain
def test_rain_tolerant_task_scheduled_during_rain():
    res = plan()
    r = by_id(res["recommended_schedule"])
    assert r["T3"]["start_min"] >= RAIN_START and r["T3"]["weather"]["max_rain"] >= 50
    assert res["recommendations"]["T3"]["label"] == "Moved later — weather tolerant"
    assert "LOW rain sensitivity" in res["recommendations"]["T3"]["reason"]


# ---------------------------------------------------------------- 3. probability scales the penalty
def test_high_rain_probability_penalises_more_than_low():
    high = {"rain": "high", "wind": "low", "visibility": "low"}
    hour = {"rain_probability": 0, "wind_kmh": 10, "visibility_m": 10000}
    p80 = hour_penalty({**hour, "rain_probability": 80}, high)["rain"]
    p40 = hour_penalty({**hour, "rain_probability": 40}, high)["rain"]
    assert p80 > p40 > 0 and p80 == pytest.approx(2 * p40)
    # and the task-level sensitivity scales it too
    low = {**high, "rain": "low"}
    assert hour_penalty({**hour, "rain_probability": 80}, low)["rain"] < p80
    hours80 = [{"start_min": 540, **hour, "rain_probability": 80}]
    hours40 = [{"start_min": 540, **hour, "rain_probability": 40}]
    assert run_task(60, 540, hours80, high)[0] > run_task(60, 540, hours40, high)[0] > 600


# ---------------------------------------------------------------- 4. manager override preserved
def test_manager_override_is_preserved():
    res = plan(overrides={"T4": {"start": "14:00", "recommended_start": "09:00"}})
    r = by_id(res["recommended_schedule"])
    assert r["T4"]["start"] == "14:00"
    rec = res["recommendations"]["T4"]
    assert rec["source"] == "manager_override" and rec["label"] == "Manager override"
    assert "Planner recommendation was 09:00" in rec["reason"]
    # nothing else is squeezed into the pinned window on the same machine
    others = [x for x in res["recommended_schedule"] if x["task_id"] != "T4"]
    assert not any(x["start_min"] < r["T4"]["end_min"] and x["end_min"] > r["T4"]["start_min"] for x in others)
    # a position override is kept too, even against the weather
    res = plan(overrides={"T3": {"position": 1}})
    assert res["recommended_schedule"][0]["task_id"] == "T3"


def test_override_survives_regeneration(svc):
    svc.recommend(MGR)
    svc.override("T4", MGR, start="14:00")
    svc.recommend(MGR)
    r = by_id(svc.store.data["recommendation"]["recommended_schedule"])
    assert r["T4"]["start"] == "14:00" and r["T4"]["override"]["start"] == "14:00"


# ---------------------------------------------------------------- 5. done/current task never reordered
def test_completed_and_current_tasks_are_not_reordered():
    locked = [{"task_id": "T1", "status": "done", "start": 540, "end": 663},
              {"task_id": "T2", "status": "active", "start": 663, "end": 793}]
    res = plan(locked=locked)
    r = by_id(res["recommended_schedule"])
    assert (r["T1"]["start_min"], r["T1"]["end_min"]) == (540, 663) and r["T1"]["locked"]
    assert (r["T2"]["start_min"], r["T2"]["end_min"]) == (663, 793) and r["T2"]["locked"]
    assert all(x["start_min"] >= 793 for x in res["recommended_schedule"] if not x["locked"])
    assert res["recommendations"]["T2"]["source"] == "locked"


def test_live_sim_reorders_only_pending(svc):
    svc.recommend(MGR)
    svc.publish(MGR)
    eng = svc.engine
    eng.start("OP-104", svc)
    sim = eng.sim
    sim.task_finished[sim.tasks[0]["id"]] = sim.now()      # first task done, second active
    sim.task_idx = 1
    sim.moved_t[sim.tasks[1]["id"]] = 42.0
    done, active = sim.tasks[0]["id"], sim.tasks[1]["id"]
    with pytest.raises(PlanningError) as e:
        svc.override(active, MGR, move="down")
    assert e.value.status == 409
    pending = [t["id"] for t in sim.tasks[2:]]
    svc.override(pending[-1], MGR, move="up")
    svc.publish(MGR)
    assert [t["id"] for t in sim.tasks[:2]] == [done, active] and sim.task_idx == 1
    assert sim.moved_t[active] == 42.0 and done in sim.task_finished
    assert sorted(t["id"] for t in sim.tasks[2:]) == sorted(pending)
    assert [t["id"] for t in sim.tasks[2:]] != pending
    # started tasks keep the explanation they were first published with
    pub = {e["task_id"]: e for e in svc.store.published["tasks"]}
    assert pub[done]["locked"] and pub[done]["recommendation"]["source"] == "planner"
    assert pub[done]["recommendation"]["operator_note"]


# ---------------------------------------------------------------- 6. operator sees only own tasks
def test_operator_only_receives_assigned_tasks(svc):
    svc.store.assign("T3", "OP-101", "CAT320-051")
    svc.store.assign("T5", "OP-101", "CAT320-051")
    svc.recommend(MGR)
    svc.publish(MGR)
    mine = svc.operator_schedule("OP-101")
    assert {t["task_id"] for t in mine["tasks"]} == {"T3", "T5"}
    other = svc.operator_schedule("OP-104")
    assert {t["task_id"] for t in other["tasks"]} == {"T1", "T2", "T4"}
    assert svc.operator_schedule("OP-102")["tasks"] == []
    assert [t["id"] for t in svc.execution_tasks("OP-101")] == [t["task_id"] for t in mine["tasks"]]


# ---------------------------------------------------------------- 7. time saved
def test_estimated_time_saved_is_calculated_correctly():
    res = plan()
    sm = res["summary"]
    o = sum(x["effective_min"] for x in res["original_schedule"])
    r = sum(x["effective_min"] for x in res["recommended_schedule"])
    assert sm["estimated_time_saved_min"] == round(o - r) > 0
    # effective = base + weather delay, so the saving is exactly the weather delay avoided
    delay_o = sum(x["delay_min"] for x in res["original_schedule"])
    delay_r = sum(x["delay_min"] for x in res["recommended_schedule"])
    assert o - r == pytest.approx(delay_o - delay_r, abs=0.6)
    # clear day: nothing to gain, nothing moves
    clear = plan(forecast=generate_forecast("clear"))
    assert clear["summary"]["estimated_time_saved_min"] == 0 and clear["summary"]["tasks_moved"] == 0


# ---------------------------------------------------------------- 8. deterministic forecast + plan
def test_forecast_is_deterministic():
    a, b = generate_forecast("rain_window"), generate_forecast("rain_window")
    assert a == b and a["forecast_id"] == b["forecast_id"]
    assert [h["rain_probability"] for h in a["hours"]] == [5, 10, 20, 30, 55, 70, 80, 85, 75, 35]
    assert generate_forecast("clear")["forecast_id"] != a["forecast_id"]
    assert plan()["summary"]["recommended_order"] == plan()["summary"]["recommended_order"]


# ---------------------------------------------------------------- 9. invalid sensitivity rejected
@pytest.mark.parametrize("profile", [
    {"rain": "extreme", "wind": "low", "visibility": "low"},
    {"rain": "high", "wind": "low"},
    {"rain": "high", "wind": "low", "visibility": "low", "snow": "high"},
    True,
])
def test_invalid_sensitivity_profile_rejected(profile, svc):
    with pytest.raises(ValueError):
        validate_sensitivity(profile)
    with pytest.raises(PlanningError):
        svc.create_task({"name": "Bad", "task_type": "grading", "terrain": "firm", "tonnes": 50,
                         "weather_sensitivity": profile}, MGR)


# ---------------------------------------------------------------- 10. conflicting assignment detected
def test_conflicting_operator_assignment_detected(svc):
    tasks = seed_tasks()
    tasks[1]["assigned_machine"] = "CAT336-017"            # T2 on another machine, same operator OP-104
    ov = {"T1": {"start": "10:00"}, "T2": {"start": "10:30"}}
    entries = build_schedule(tasks, RAIN["hours"], 540, 1140, {t["id"]: manual(t) for t in tasks},
                             reorder=True, overrides=ov)
    conflicts = detect_conflicts(entries)
    assert any(c["type"] == "operator_overlap" and c["operator"] == "OP-104" and set(c["tasks"]) == {"T1", "T2"}
               for c in conflicts)
    # publishing such a plan is refused
    svc.store.assign("T2", "OP-104", "CAT336-017")
    svc.override("T1", MGR, start="10:00")
    svc.override("T2", MGR, start="10:30")
    with pytest.raises(PlanningError) as e:
        svc.publish(MGR)
    assert e.value.status == 409 and "OP-104" in str(e.value)


# ---------------------------------------------------------------- service guards
def test_publish_requires_assignments_and_fresh_plan(svc):
    with pytest.raises(PlanningError, match="No recommendation"):
        svc.publish(MGR)
    svc.store.assign("T5", None, None)
    svc.recommend(MGR)
    with pytest.raises(PlanningError, match="operator and a machine"):
        svc.publish(MGR)
    svc.store.assign("T5", "OP-104", "CAT320-042")
    with pytest.raises(PlanningError, match="Tasks changed"):
        svc.publish(MGR)
    svc.recommend(MGR)
    svc.publish(MGR)
    assert svc.store.published["schedule_id"] == "SCH-0001"
    assert any(e["title"] == "Daily schedule published" for e in svc.engine.events)


def test_schedule_outside_shift_rejected(svc):
    with pytest.raises(PlanningError, match="outside the shift"):
        svc.update_task("T1", {"earliest_start": "06:00"}, MGR)
    svc.recommend(MGR)
    with pytest.raises(PlanningError, match="outside the shift"):
        svc.override("T1", MGR, start="20:00")


def test_delete_published_task_removed_from_schedule(svc):
    svc.recommend(MGR)
    svc.publish(MGR)
    svc.delete_task("T5", MGR)
    assert "T5" not in [e["task_id"] for e in svc.store.published["tasks"]]
    assert svc.store.published["modified_after_publish"]


def test_safety_outranks_schedule_recommendation():
    import priority
    rec = {"label": "Moved earlier — rain sensitive"}
    calm = priority.resolve({"safety": {"level": "SAFE"}}, rec)
    assert calm["top"]["type"] == "SCHEDULE_RECOMMENDATION" and not calm["schedule_suppressed"]
    crit = priority.resolve({"safety": {"level": "CRITICAL", "details": ["Person 2 m away"]}}, rec)
    assert crit["schedule_suppressed"] and crit["message"] == "Safety issue takes priority over schedule recommendation."
    assert crit["top"]["priority"] == 100 > crit["items"][-1]["priority"]


def test_seed_default_plan_reorders_visibly():
    res = plan()
    assert res["summary"]["original_order"] == ["T1", "T2", "T3", "T4", "T5"]
    assert res["summary"]["recommended_order"][0] == "T4"
    assert res["summary"]["tasks_moved"] >= 3 and res["summary"]["fits_shift"]
    # every automatically moved task carries a concrete, numeric reason
    for k, v in res["recommendations"].items():
        if v["moved"] != "unchanged":
            assert "→" in v["reason"] or "window" in v["reason"]
            assert "AI" not in v["reason"]
