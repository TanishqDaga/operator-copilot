"""Connects the weather-aware planner to the live shift.

- Durations: the manager's planning estimate if set, else the existing ETA model (clear weather,
  assigned operator's experience + historical cycle baseline). The ETA model itself is untouched.
- Done / active tasks are locked: recommend/replan/override never move them.
- Publishing stores the schedule in planning.json and, if a shift is running, re-sequences only the
  PENDING tasks in LiveSim. The active task stays active; nothing reshuffles on its own afterwards.
- Every decision is logged as a "planning" event on the existing timeline.
"""
from __future__ import annotations

import copy
from datetime import datetime

import priority
from planner import UNASSIGNED, WeatherAwarePlanner, lane_of
from planning_store import MACHINES, PlanningError, PlanningStore
from roles import User
from simulator import OPERATORS, TASK_TYPES
from weather import SCENARIOS, hhmm, to_min


class PlanningService:
    def __init__(self, engine, default_operator: str, store: PlanningStore | None = None):
        self.engine = engine
        self.default_operator = default_operator
        self.store = store or PlanningStore()
        self._eta_cache: dict[tuple, float] = {}

    # ------------------------------------------------------------------ durations
    def eta_baseline(self, task: dict) -> float:
        op = task.get("assigned_operator") or self.default_operator
        key = (task["task_type"], task["tonnes"], task["distance_m"], task["terrain"], op)
        if key not in self._eta_cache:
            eng = self.engine
            self._eta_cache[key] = round(eng.eta.predict(
                task_type=task["task_type"], tonnes=task["tonnes"], distance_m=task["distance_m"],
                experience_yrs=OPERATORS[op]["experience_yrs"], terrain=task["terrain"], weather="clear",
                recent_cycle_s=eng.cycle_baseline(op, task, "clear")), 1)
        return self._eta_cache[key]

    def duration(self, task: dict) -> tuple[float, str]:
        if task.get("estimated_duration_min"):
            return float(task["estimated_duration_min"]), "manager_estimate"
        return self.eta_baseline(task), "eta_model"

    # ------------------------------------------------------------------ live shift
    def live_status(self) -> dict:
        eng = self.engine
        sim = eng.sim
        if sim is None or not eng.shift.get("active"):
            return {"running": False, "done": [], "active": None, "operator_id": None}
        return {"running": True, "done": [t["id"] for t in sim.tasks if t["id"] in sim.task_finished],
                "active": sim.current_task["id"] if sim.current_task else None, "operator_id": sim.operator_id}

    def _locked(self) -> list[dict]:
        st = self.live_status()
        pub = {e["task_id"]: e for e in (self.store.published or {}).get("tasks") or []}
        out = []
        for tid in st["done"] + ([st["active"]] if st["active"] else []):
            e = pub.get(tid)
            out.append({"task_id": tid, "status": "active" if tid == st["active"] else "done",
                        "start": e["start_min"] if e else None, "end": e["end_min"] if e else None})
        return out

    def _guard_editable(self, task_id: str, verb: str):
        st = self.live_status()
        if task_id == st["active"]:
            raise PlanningError(f"{task_id} is in progress in the live shift — it can't be {verb}", 409)
        if task_id in st["done"]:
            raise PlanningError(f"{task_id} is already completed this shift — it can't be {verb}", 409)

    def compute(self) -> dict:
        sh = self.store.shift
        planner = WeatherAwarePlanner(self.store.forecast, sh["start"], sh["end"], self.duration)
        return planner.plan(self.store.tasks, self.store.overrides, self._locked())

    def _log(self, title: str, detail: str | None = None, **data):
        eng = self.engine
        return eng._log("planning", "INFO", title, detail=detail, pre_shift=not eng.shift.get("active"), **data)

    # ------------------------------------------------------------------ views
    def view(self) -> dict:
        with self.engine.lock:
            s = self.store
            current = self.compute()
            rec = s.data["recommendation"]
            st = self.live_status()
            tasks = []
            for t in s.tasks:
                dur, src = self.duration(t)
                status = ("active" if t["id"] == st["active"] else "done" if t["id"] in st["done"]
                          else "pending" if st["running"] else "planned")
                tasks.append({**t, "label": TASK_TYPES[t["task_type"]]["label"], "planned_min": dur,
                              "duration_source": src, "eta_model_min": self.eta_baseline(t), "live_status": status,
                              "override": s.overrides.get(t["id"])})
            pub = s.published
            return {
                "plan_name": s.data["plan_name"], "synthetic": True,
                "shift": {**s.shift, "date": datetime.now().date().isoformat()},
                "forecast": s.forecast, "tasks": tasks, "tasks_version": s.data["tasks_version"],
                "original_schedule": current["original_schedule"],
                "preview_summary": current["summary"],
                "recommendation": rec, "stale": s.stale_reason() if rec else None,
                "overrides": s.overrides, "plan_status": s.data["plan_status"],
                "published": {k: v for k, v in pub.items() if k != "tasks"} if pub else None,
                "published_order": [e["task_id"] for e in pub["tasks"]] if pub else [],
                "history": s.data["history"], "live": st,
                "operators": [{"id": k, "name": v["name"], "experience_yrs": v["experience_yrs"]} for k, v in OPERATORS.items()],
                "machines": MACHINES,
                "scenarios": [{"value": k, "label": v["label"]} for k, v in SCENARIOS.items()],
            }

    def forecast(self) -> dict:
        return self.store.forecast

    # ------------------------------------------------------------------ task CRUD
    def create_task(self, payload: dict, user: User) -> dict:
        with self.engine.lock:
            t = self.store.create(payload)
            self._log(f"Task {t['id']} added to the plan", detail=f"{t['name']} · by {user.name}", task_id=t["id"])
            return t

    def update_task(self, task_id: str, payload: dict, user: User) -> dict:
        with self.engine.lock:
            self.store.get(task_id)
            self._guard_editable(task_id, "edited")
            return self.store.update(task_id, payload)

    def delete_task(self, task_id: str, user: User) -> dict:
        with self.engine.lock:
            self.store.get(task_id)
            self._guard_editable(task_id, "deleted")
            t = self.store.delete(task_id)
            pub = self.store.published
            note = ""
            if pub and any(e["task_id"] == task_id for e in pub["tasks"]):
                pub["tasks"] = [e for e in pub["tasks"] if e["task_id"] != task_id]
                pub["modified_after_publish"] = f"{task_id} deleted after publishing — republish to refresh windows"
                self.store.save()
                note = " Removed from the published schedule."
            sim = self.engine.sim
            if self.live_status()["running"] and any(x["id"] == task_id for x in sim.tasks[sim.task_idx + 1:]):
                sim.reorder_pending([x for x in sim.tasks[sim.task_idx + 1:] if x["id"] != task_id])
                note += " Removed from the live shift's pending tasks."
            self._log(f"Task {task_id} deleted", detail=f"{t['name']} · by {user.name}.{note}", task_id=task_id)
            return {"deleted": task_id, "note": note.strip() or None}

    def assign(self, task_id: str, operator_id: str | None, machine_id: str | None, user: User) -> dict:
        with self.engine.lock:
            self.store.get(task_id)
            self._guard_editable(task_id, "reassigned")
            t = self.store.assign(task_id, operator_id, machine_id)
            self._log(f"{task_id} assigned", detail=f"{operator_id or 'no operator'} on {machine_id or 'no machine'} · by {user.name}",
                      task_id=task_id)
            return t

    # ------------------------------------------------------------------ planning actions
    def set_scenario(self, scenario: str, user: User) -> dict:
        with self.engine.lock:
            fc = self.store.set_scenario(scenario)
            self._log(f"Forecast scenario set: {fc['label']}", detail=f"{fc['summary']} (synthetic forecast)",
                      forecast_id=fc["forecast_id"])
            return fc

    def _store_result(self, res: dict, status: str | None = None):
        self.store.set_recommendation(res, status or ("overridden" if self.store.overrides else "recommended"))

    def recommend(self, user: User, replan: bool = False) -> dict:
        with self.engine.lock:
            if not self.store.tasks:
                raise PlanningError("No tasks to plan — add a task first")
            res = self.compute()
            self._store_result(res)
            sm = res["summary"]
            title = "Replan — future tasks recalculated" if replan else "Weather-aware schedule generated"
            locked = [x["task_id"] for x in res["recommended_schedule"] if x["locked"]]
            detail = f"{sm['tasks_moved']} task{'s' if sm['tasks_moved'] != 1 else ''} reordered based on forecast"
            if locked:
                detail += f"; {', '.join(locked)} locked (already started)"
            self._log(title, detail=detail, forecast_summary=sm["forecast_summary"], moved_tasks=sm["moved_task_ids"],
                      estimated_time_saved_min=sm["estimated_time_saved_min"], original_order=sm["original_order"],
                      recommended_order=sm["recommended_order"], forecast_id=res["forecast_id"])
        return self.view()

    def _ensure_fresh(self) -> dict:
        if self.store.stale_reason():
            self._store_result(self.compute())
        return self.store.data["recommendation"]

    def override(self, task_id: str, user: User, *, move: str | None = None, start: str | None = None,
                 clear: bool = False) -> dict:
        with self.engine.lock:
            task = self.store.get(task_id)
            self._guard_editable(task_id, "re-ordered")
            rec = self._ensure_fresh()
            entry = next(e for e in rec["recommended_schedule"] if e["task_id"] == task_id)
            now = datetime.now().isoformat(timespec="seconds")
            sh = self.store.shift
            if clear:
                self.store.set_override(task_id, None)
                title, detail = "Manager override cleared", f"{task_id} returns to the planner's recommendation"
            elif start:
                try:
                    m = to_min(start)
                except (ValueError, AttributeError):
                    raise PlanningError("start must be a time like 14:00") from None
                if not to_min(sh["start"]) <= m < to_min(sh["end"]):
                    raise PlanningError(f"{start} is outside the shift ({sh['start']}–{sh['end']})")
                if m < to_min(task["earliest_start"]):
                    raise PlanningError(f"{task_id} can't start before its earliest start {task['earliest_start']}")
                prev = self.store.overrides.get(task_id) or {}
                self.store.set_override(task_id, {"start": hhmm(m), "by": user.id, "at": now,
                                                  "recommended_start": prev.get("recommended_start") or entry["start"]})
                title, detail = "Manager override", f"{task_id}: recommended {entry['start']} → manager {hhmm(m)}"
            elif move in ("up", "down"):
                if (entry.get("override") or {}).get("start"):
                    raise PlanningError(f"{task_id} has a pinned start time — clear it before moving", 409)
                lane = [e for e in rec["recommended_schedule"] if (e["machine"] or UNASSIGNED) == lane_of(task)
                        and not (e.get("override") or {}).get("start")]
                idx = next(i for i, e in enumerate(lane) if e["task_id"] == task_id)
                tgt = idx - 1 if move == "up" else idx + 1
                if not 0 <= tgt < len(lane):
                    raise PlanningError(f"{task_id} is already {'first' if move == 'up' else 'last'} on {task.get('assigned_machine') or 'its lane'}")
                if lane[tgt]["locked"]:
                    raise PlanningError(f"Can't move {task_id} ahead of {lane[tgt]['task_id']}, which has already started", 409)
                prev = self.store.overrides.get(task_id) or {}
                self.store.set_override(task_id, {"position": tgt + 1, "by": user.id, "at": now,
                                                  "recommended_start": prev.get("recommended_start") or entry["start"],
                                                  "recommended_position": entry["position"]})
                title = "Manager override"
                detail = f"{task_id} moved {move}: position {idx + 1} → {tgt + 1} on {task.get('assigned_machine') or 'unassigned lane'}"
            else:
                raise PlanningError("Provide move (up|down), start (HH:MM) or clear")
            res = self.compute()
            self._store_result(res)
            new = next(e for e in res["recommended_schedule"] if e["task_id"] == task_id)
            if not clear:
                detail += f" (now {new['start']}–{new['end']})"
            self._log(title, detail=detail, task_id=task_id, conflicts=len(res["conflicts"]))
        return self.view()

    def accept(self, user: User) -> dict:
        with self.engine.lock:
            dropped = sorted(self.store.overrides)
            self.store.data["overrides"] = {}
            res = self.compute()
            self._store_result(res, "accepted")
            extra = f"; overrides cleared for {', '.join(dropped)}" if dropped else ""
            self._log("Recommendation accepted", detail=f"{user.name} accepted the planner's sequence{extra}",
                      recommended_order=res["summary"]["recommended_order"])
        return self.view()

    def publish(self, user: User) -> dict:
        with self.engine.lock:
            s = self.store
            if not s.tasks:
                raise PlanningError("Nothing to publish — the plan has no tasks")
            reason = s.stale_reason()
            if reason:
                raise PlanningError(f"{reason} — generate the weather-aware plan again before publishing", 409)
            rec = s.data["recommendation"]
            unassigned = [f"{e['task_id']} ({', '.join(w for w in e['warnings'] if w.startswith('No '))})"
                          for e in rec["recommended_schedule"] if not e["operator"] or not e["machine"]]
            if unassigned:
                raise PlanningError("Every task needs an operator and a machine before publishing: " + "; ".join(unassigned),
                                    400, {"tasks": unassigned})
            if rec["conflicts"]:
                raise PlanningError("Conflicting assignments: " + "; ".join(c["message"] for c in rec["conflicts"]),
                                    409, {"conflicts": rec["conflicts"]})
            late = [f"{e['task_id']} ends {e['end']}" for e in rec["recommended_schedule"] if e["end_min"] > to_min(s.shift["end"]) + 0.5]
            if late:
                raise PlanningError(f"Schedule runs past shift end {s.shift['end']}: {', '.join(late)} — shorten, remove or reassign a task")
            by_id = {t["id"]: t for t in s.tasks}
            # a started task keeps the explanation it was published with ("why now" stays visible mid-shift)
            prev = {e["task_id"]: e for e in (s.published or {}).get("tasks") or []}
            entries = [{**e, "recommendation": prev[e["task_id"]]["recommendation"]} if e["locked"] and e["task_id"] in prev
                       else e for e in rec["recommended_schedule"]]
            record = {
                "schedule_id": s.next_schedule_id(), "created_at": datetime.now().isoformat(timespec="seconds"),
                "manager_id": user.id, "manager_name": user.name, "forecast_id": rec["forecast_id"],
                "forecast_scenario": s.data["forecast_scenario"], "forecast_summary": rec["summary"]["forecast_summary"],
                "overrides": copy.deepcopy(s.overrides), "status": "published", "summary": rec["summary"],
                "acknowledged": {},
                "tasks": [{**copy.deepcopy(e), "task": copy.deepcopy(by_id[e["task_id"]])} for e in entries],
            }
            s.publish(record)
            pending = self.apply_to_live()
            sm = rec["summary"]
            live = f"; live shift pending tasks now {', '.join(pending)}" if pending is not None else ""
            self._log("Daily schedule published",
                      detail=f"{record['schedule_id']} · {len(record['tasks'])} tasks · est. {sm['estimated_time_saved_min']} min "
                             f"saved vs original (forecast-based estimate){live}",
                      schedule_id=record["schedule_id"], recommended_order=sm["recommended_order"],
                      original_order=sm["original_order"], overrides=sorted(record["overrides"]))
        return self.view()

    def reset(self, user: User) -> dict:
        with self.engine.lock:
            if self.live_status()["running"]:
                raise PlanningError("End the running shift before resetting the demo plan", 409)
            self.store.reset()
            self._log("Demo plan reset", detail=f"Tasks and forecast restored from tasks.json by {user.name}")
        return self.view()

    # ------------------------------------------------------------------ execution
    def execution_tasks(self, operator_id: str | None) -> list[dict]:
        """Task order LiveSim should run: the published schedule (this operator's tasks, or all if none
        are assigned to them), else the manager's original order."""
        pub = self.store.published
        if pub and pub["tasks"]:
            snaps = [e["task"] for e in sorted(pub["tasks"], key=lambda e: (e["start_min"], e["machine"] or ""))]
            mine = [t for t in snaps if t.get("assigned_operator") == operator_id]
            return copy.deepcopy(mine or snaps)
        return copy.deepcopy(self.store.tasks)

    def apply_to_live(self) -> list[str] | None:
        eng = self.engine
        sim = eng.sim
        if sim is None or not eng.shift.get("active"):
            return None
        before = [t["id"] for t in sim.tasks[sim.task_idx + 1:]]
        sim.reorder_pending(self.execution_tasks(sim.operator_id))
        after = [t["id"] for t in sim.tasks[sim.task_idx + 1:]]
        if before != after:
            cur = sim.current_task["id"] if sim.current_task else "No task"
            self._log("Live shift re-sequenced — future tasks only",
                      detail=f"{cur} stays active. Pending {' → '.join(before) or '—'} becomes {' → '.join(after) or '—'}")
        return after

    # ------------------------------------------------------------------ operator view
    def operator_schedule(self, operator_id: str) -> dict:
        with self.engine.lock:
            s = self.store
            eng = self.engine
            op = {"id": operator_id, "name": OPERATORS[operator_id]["name"]}
            fc = s.forecast
            base = {"operator": op, "shift": s.shift, "synthetic": True,
                    "forecast": {"summary": fc["summary"], "label": fc["label"], "windows": fc["windows"],
                                 "hours": fc["hours"], "forecast_id": fc["forecast_id"]}}
            pub = s.published
            if not pub:
                return {**base, "published": False, "tasks": [],
                        "message": "No schedule published yet — today's plan will appear here once the manager publishes it."}
            sim = eng.sim
            live = sim is not None and sim.operator_id == operator_id and (eng.shift.get("active") or eng.shift.get("ended"))
            active_id = sim.current_task["id"] if live and eng.shift.get("active") and sim.current_task else None
            out = []
            for e in sorted(pub["tasks"], key=lambda e: e["start_min"]):
                if e["operator"] != operator_id:
                    continue
                status = ("done" if live and e["task_id"] in sim.task_finished else "active" if e["task_id"] == active_id
                          else "pending" if live else "scheduled")
                r = e.get("recommendation") or {}
                out.append({
                    "task_id": e["task_id"], "name": e["name"], "location": e["location"], "task_type": e["task_type"],
                    "label": TASK_TYPES[e["task_type"]]["label"], "machine": e["machine"], "start": e["start"],
                    "end": e["end"], "status": status, "weather": e["weather"], "weather_sensitivity": e["weather_sensitivity"],
                    "planned_min": e["effective_min"],
                    "recommendation": {k: r.get(k) for k in ("label", "reason", "operator_note", "moved", "source",
                                                             "weather_impact", "confidence", "weather_conflict",
                                                             "dominant_factor", "sensitivity_level", "priority_type")},
                })
            open_ = [x for x in out if x["status"] in ("active", "pending", "scheduled")]
            current = next((x for x in out if x["status"] == "active"), None)
            nxt = next((x for x in open_ if x is not current), None)
            prio = priority.resolve(eng.state if live else {}, (current or nxt or {}).get("recommendation"))
            return {**base, "published": True, "schedule_id": pub["schedule_id"], "published_at": pub["created_at"],
                    "published_by": pub["manager_name"], "modified_after_publish": pub.get("modified_after_publish"),
                    "tasks": out, "current_id": current["task_id"] if current else None,
                    "next_id": nxt["task_id"] if nxt else None,
                    "remaining_ids": [x["task_id"] for x in open_ if x is not current and x is not nxt],
                    "live": bool(live), "priority": prio, "acknowledged_at": pub["acknowledged"].get(operator_id),
                    "message": None if out else "No tasks are assigned to you in the published schedule."}

    def acknowledge(self, operator_id: str) -> dict:
        with self.engine.lock:
            pub = self.store.published
            if not pub:
                raise PlanningError("No published schedule to acknowledge", 404)
            pub["acknowledged"][operator_id] = datetime.now().isoformat(timespec="seconds")
            self.store.save()
            self._log(f"Schedule {pub['schedule_id']} acknowledged", detail=f"{OPERATORS[operator_id]['name']} ({operator_id})")
        return self.operator_schedule(operator_id)

    # ------------------------------------------------------------------ context for /api/state
    def live_context(self, state: dict) -> dict:
        """Cheap (called every tick): forecast is a first-class context input next to current weather."""
        s = self.store
        fc = s.forecast
        pub = s.published
        entry = next((e for e in pub["tasks"] if e["task_id"] == state.get("task_id")), None) if pub else None
        rec = (entry or {}).get("recommendation")
        prio = priority.resolve(state, rec)
        return {
            "current_weather": {"condition": state.get("weather"), "source": "simulation (current conditions)"},
            "forecast": {"forecast_id": fc["forecast_id"], "scenario": fc["scenario"], "label": fc["label"],
                         "summary": fc["summary"], "synthetic": True, "hours": fc["hours"], "windows": fc["windows"]},
            "active_weather_window": {"task_id": entry["task_id"], "start": entry["start"], "end": entry["end"],
                                      **entry["weather"]} if entry else None,
            "task_weather_risk": {"task_id": entry["task_id"], "sensitivity": entry["weather_sensitivity"],
                                  "impact": rec.get("weather_impact"), "dominant_factor": rec.get("dominant_factor"),
                                  "conflict": rec.get("weather_conflict")} if entry and rec else None,
            "schedule_recommendation": {**{k: rec.get(k) for k in ("label", "reason", "operator_note", "priority_type",
                                                                     "priority", "confidence")},
                                        "suppressed": prio["schedule_suppressed"]} if rec else None,
            "priority": prio,
            "published_schedule_id": pub["schedule_id"] if pub else None,
        }
