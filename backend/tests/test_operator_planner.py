"""Operator Task Planner tests — execution guidance on top of a published schedule (pure contexts)."""
from __future__ import annotations

import copy
import json

import pytest

from operator_metrics import live_productivity, shift_summary
from operator_planner import OperatorProductivityPlanner
from operator_service import published_inputs
from planner import WeatherAwarePlanner
from planning_store import SEED_PATH, normalize_task
from schedule_clock import ScheduleClock
from weather import generate_forecast, to_min

FC = generate_forecast("rain_window")
EXPECTED = {"T4": 25.0, "T1": 30.0, "T2": 30.0, "T3": 20.0, "T5": 20.0}    # live reference minutes
PLANNER = OperatorProductivityPlanner()


def published(assign: dict | None = None) -> list[dict]:
    """A published schedule exactly as the manager planner produces it (T4 → T1 → T2 → T3 → T5)."""
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))["tasks"]
    tasks = [{"id": t["id"], "original_order": i, **normalize_task(t)} for i, t in enumerate(raw, 1)]
    for tid, op in (assign or {}).items():
        next(t for t in tasks if t["id"] == tid)["assigned_operator"] = op
    res = WeatherAwarePlanner(FC, "09:00", "19:00", lambda t: (float(t["estimated_duration_min"]), "manager_estimate")).plan(tasks)
    by_id = {t["id"]: t for t in tasks}
    return [{**e, "task": by_id[e["task_id"]]} for e in res["recommended_schedule"]]


PUB = published()


def ctx(live=None, operator="OP-104", pub=PUB, publish=True, **kw):
    tasks, _ = published_inputs(pub, operator, lambda snap: EXPECTED[snap["id"]])
    return {"operator": {"id": operator, "name": "D. Tanaka"},
            "published": {"schedule_id": "SCH-0001", "created_at": "x", "manager_name": "J. Okafor"} if publish else None,
            "tasks": tasks if publish else [], "live_expected": {k: v for k, v in EXPECTED.items()},
            "forecast": {"hours": FC["hours"], "windows": FC["windows"], "summary": FC["summary"], "label": FC["label"],
                         "forecast_id": FC["forecast_id"]},
            "shift": {"start": "09:00", "end": "19:00"}, "live": live, "other_operator": None, **kw}


def live(active="T4", done=(), elapsed=10.0, eta=15.0, cycles=6, **over):
    ids = ["T4", "T1", "T2", "T3", "T5"]
    status = {i: "done" if i in done else "active" if i == active else "pending" for i in ids}
    clock = ScheduleClock(ctx()["tasks"], EXPECTED, to_min("09:00"))
    started = {i: clock.window(i)[0] for i in list(done) + ([active] if active else [])}
    finished = {i: clock.window(i)[1] for i in done}
    base = {
        "active": True, "ended": False, "clock": "10:00:00", "elapsed_min": elapsed, "status": status,
        "current_task_id": active, "sim_task_ids": ids, "task_started_min": started, "task_finished_min": finished,
        "progress": {i: 1.0 if i in done else 0.4 if i == active else 0.0 for i in ids},
        "eta": {"task_id": active, "minutes_exact": eta, "err_min": 3.4, "finish": "10:15"} if eta is not None else None,
        "machine": {"phase": "dig", "idle": False, "idle_min": 0.0, "speed_kmh": 0.0, "weather": "clear", "seatbelt": True},
        "safety": {"level": "SAFE", "reasons": [], "details": []}, "anomaly": {"flag": False},
        "time_s": {"working": 540.0, "travel": 30.0, "idle": 30.0},
        "task_time_s": {active: {"working": 500.0, "travel": 30.0, "idle": 0.0}} if active else {},
        "cycles": {"current": [60.0] * cycles, "current_baseline_s": 62.0, "shift": [(60.0, 62.0)] * cycles},
        "idle_log": [], "weather_changes": 0,
    }
    for k, v in over.items():
        base[k] = {**base[k], **v} if isinstance(base.get(k), dict) and isinstance(v, dict) else v
    return base


def at_task_start(task, offset=1.0, done=(), eta=20.0, **over):
    clock = ScheduleClock(ctx()["tasks"], EXPECTED, to_min("09:00"))
    return live(active=task, done=done, elapsed=clock.window(task)[0] + offset, eta=eta, **over)


# 1 + 2 ------------------------------------------------------------------------------
def test_current_and_next_task_identified():
    out = PLANNER.plan(ctx(live()))
    assert out["available"] and out["current_task"]["task_id"] == "T4"
    assert out["next_task"]["task_id"] == "T1"
    assert [t["task_id"] for t in out["upcoming_tasks"]] == ["T1", "T2", "T3"]
    assert out["state"]["code"] == "ACTIVE" and out["next_best_action"]["action"].startswith("Continue")
    assert "on schedule" in out["next_best_action"]["reason"]


# 3 ----------------------------------------------------------------------------------
def test_early_finish_detected():
    out = PLANNER.plan(ctx(live(elapsed=10.0, eta=8.0)))        # reference ends at 25, projected 18
    assert out["state"]["code"] == "EARLY_FINISH"
    assert out["current_task"]["projected_delta_min"] == pytest.approx(7.0)
    assert out["next_best_action"]["action"].startswith("Projected 7 min early")
    assert "published schedule" in out["next_best_action"]["reason"]


# 4 ----------------------------------------------------------------------------------
def test_idle_detected():
    out = PLANNER.plan(ctx(live(machine={"idle": True, "idle_min": 5.0, "phase": "idle"})))
    assert out["state"]["code"] == "IDLE"
    assert "idle 5 min" in out["next_best_action"]["action"]
    flagged = live(machine={"idle": True, "idle_min": 12.0, "phase": "idle"},
                   anomaly={"flag": True, "type": "excess_idle", "label": "Idle duration", "current": 12.0,
                            "baseline": 4.0, "unit": "min", "possible_causes": ["Truck not available"]})
    out = PLANNER.plan(ctx(flagged))
    assert out["next_best_action"]["category"] == "OPERATIONAL_ISSUE"
    assert "above your usual 4 min" in out["next_best_action"]["action"]


# 5 ----------------------------------------------------------------------------------
def test_weather_guidance_generated_from_forecast():
    rain = next(w for w in FC["windows"] if w["kind"] == "rain")
    # T2 (MEDIUM rain) starts just before the forecast rain window and will run into it
    out = PLANNER.plan(ctx(at_task_start("T2", offset=2.0, done=("T4", "T1"), eta=25.0)))
    assert out["state"]["code"] == "WEATHER_PREPARATION"
    nba = out["next_best_action"]
    assert nba["action"].startswith("Rain expected in ~") and "before the rain window" in nba["action"]
    assert f"from {rain['start']}" in nba["reason"] and "MEDIUM rain sensitivity" in nba["reason"]
    # before the shift: the schedule already puts the rain-sensitive grading first
    pre = PLANNER.plan(ctx(None))
    assert "already places weather-sensitive" in pre["weather_guidance"]["headline"]
    assert pre["weather_guidance"]["trend"]["peak_pct"] == 85
    # raining now on a tolerant task
    tol = PLANNER.plan(ctx(at_task_start("T3", done=("T4", "T1", "T2"), machine={"weather": "rain"})))
    assert any(i["action"] == "Current task is weather-tolerant. Continue according to the published schedule."
               for i in tol["weather_guidance"]["items"])


# 6 + 12 -----------------------------------------------------------------------------
def test_manager_schedule_never_reordered_or_modified():
    pub_before = copy.deepcopy(PUB)
    c = ctx(live(elapsed=10.0, eta=8.0))
    c_before = copy.deepcopy(c)
    out = PLANNER.plan(c)
    assert c == c_before and PUB == pub_before
    assert out["published_order"] == [e["task_id"] for e in sorted(PUB, key=lambda e: e["start_min"])]
    order = [out["current_task"]["task_id"]] + [t["task_id"] for t in out["upcoming_tasks"]]
    assert order == out["published_order"][:len(order)]
    assert "recommended_schedule" not in out and "original_schedule" not in out


# 7 ----------------------------------------------------------------------------------
@pytest.mark.parametrize("level", ["CRITICAL", "WARNING"])
def test_safety_overrides_productivity(level):
    lv = live(elapsed=10.0, eta=8.0, cycles=8,
              safety={"level": level, "reasons": ["person_close"], "details": ["Person 3.0 m away"]})
    lv["cycles"] = {"current": [50.0] * 8, "current_baseline_s": 62.0, "shift": [(50.0, 62.0)] * 8}
    out = PLANNER.plan(ctx(lv))
    assert out["state"]["code"] == "SAFETY_HOLD"
    assert out["next_best_action"]["category"] == f"SAFETY_{level}"
    assert out["next_best_action"]["action"].startswith("SAFETY FIRST")
    assert out["safety_priority"]["active"] and out["safety_priority"]["message"]
    assert all(a["category"] != "PRODUCTIVITY" for a in out["secondary_actions"])
    assert all(a["deferred"] for a in out["secondary_actions"])
    for word in ("faster", "speed up", "hurry", "early"):
        assert word not in out["next_best_action"]["action"].lower()
    # without the safety condition the same facts produce a productivity note
    calm = PLANNER.plan(ctx({**lv, "safety": {"level": "SAFE", "reasons": [], "details": []}}))
    assert any(a["category"] == "PRODUCTIVITY" for a in calm["secondary_actions"])


# 8 ----------------------------------------------------------------------------------
def test_operator_only_receives_assigned_tasks():
    pub = published({"T3": "OP-101", "T5": "OP-101"})
    mine, _ = published_inputs(pub, "OP-101", lambda s: EXPECTED[s["id"]])
    others, _ = published_inputs(pub, "OP-104", lambda s: EXPECTED[s["id"]])
    assert {t["task_id"] for t in mine} == {"T3", "T5"}
    assert {t["task_id"] for t in others} == {"T4", "T1", "T2"}
    out = PLANNER.plan(ctx(None, operator="OP-101", pub=pub))
    assert {t["task_id"] for t in out["upcoming_tasks"]} <= {"T3", "T5"}
    assert PLANNER.plan(ctx(None, operator="OP-102"))["message"] == "No tasks are assigned to you in the published schedule."


# 9 ----------------------------------------------------------------------------------
def test_productivity_metrics_from_telemetry():
    p = live_productivity(live(cycles=6), ctx()["tasks"], "T4")
    assert p["time"]["utilization_pct"] == 95                       # (540 + 30) / 600
    assert p["time"]["idle_min"] == 0.5 and p["time"]["active_min"] == 9.5
    assert p["cycle"]["status"] == "ok" and p["cycle"]["efficiency_pct"] == pytest.approx(3.2)
    few = live_productivity(live(cycles=3, time_s={"working": 30.0, "travel": 0.0, "idle": 0.0}), ctx()["tasks"], "T4")
    assert few["cycle"]["status"] == "collecting" and few["cycle"]["efficiency_pct"] is None
    assert few["time"]["status"] == "collecting" and few["time"]["utilization_pct"] is None


# 10 ---------------------------------------------------------------------------------
def test_no_recommendation_when_data_missing():
    out = PLANNER.plan(ctx(None, publish=False))
    assert not out["available"] and out["next_best_action"] is None
    assert out["message"] == "No published schedule available."
    no_eta = PLANNER.plan(ctx(live(eta=None)))
    assert no_eta["current_task"]["projected_delta_min"] is None and no_eta["state"]["code"] != "EARLY_FINISH"
    unsettled = PLANNER.plan(ctx(live(eta=8.0, cycles=1)))           # ETA not settled on this task yet
    assert unsettled["current_task"]["projected_delta_min"] is None
    assert unsettled["state"]["code"] != "EARLY_FINISH"


# 11 ---------------------------------------------------------------------------------
def test_planner_updates_when_current_task_changes():
    before = PLANNER.plan(ctx(live()))
    after = PLANNER.plan(ctx(at_task_start("T1", offset=0.5, done=("T4",), eta=28.0)))
    assert before["current_task"]["task_id"] == "T4" and after["current_task"]["task_id"] == "T1"
    assert after["next_task"]["task_id"] == "T2"
    assert after["state"]["code"] == "READY_FOR_NEXT_TASK"
    assert after["next_best_action"]["action"].startswith("Next assigned task: Load haul trucks")
    later = PLANNER.plan(ctx(at_task_start("T1", offset=5.0, done=("T4",), eta=24.0)))
    assert later["state"]["code"] != "READY_FOR_NEXT_TASK"


def test_preparation_uses_task_data():
    out = PLANNER.plan(ctx(live()))
    prep = out["next_task"]["preparation"]
    assert prep[0] == "Relocate to Bench 3, face north after completing T4."
    assert any("Task type changes" in p for p in prep)
    assert out["next_task"]["transition"]["relocation"] is True


def test_shift_summary_is_factual():
    lv = at_task_start("T1", offset=10.0, done=("T4",), eta=18.0)
    lv["task_finished_min"] = {"T4": 31.0}                           # 6 min past its 25-min reference
    lv["task_time_s"] = {"T4": {"working": 1200.0, "travel": 60.0, "idle": 360.0}}
    lv["idle_log"] = [{"start": "09:12:00", "minutes": 6.0, "task_id": "T4", "progress": 0.4}]
    c = ctx(lv)
    s = shift_summary(lv, c["tasks"], ScheduleClock(c["tasks"], EXPECTED, 540), 3.4)
    assert s["tasks_completed"] == 1 and s["tasks_scheduled"] == 5
    assert s["schedule_adherence_pct"] == 0
    assert "6 min idle during T4 (from 09:12:00)." in s["opportunities"]
    assert any(o.startswith("T4") and "after its live schedule reference, including 6 min idle" in o for o in s["opportunities"])
    text = json.dumps(s).lower()
    assert "rank" not in text and "score" not in text.replace("not a performance score", "")
