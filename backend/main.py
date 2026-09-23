"""CAT Operator Copilot — FastAPI app. Integrates simulator, safety rules, anomaly + ETA models,
vision and the explanation layer. A background thread advances the shift once per second; the
frontend polls GET /api/state every second (no websockets).
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ai
import training_rag
import safety
from anomaly import AnomalyDetector
from eta import EtaModel
from simulator import (DATA, DATA_SOURCE, FUEL_TANK_L, MACHINE_ID, OPERATORS, ROOT, START_FUEL_PCT, TASK_TYPES,
                       LiveSim, ensure_history, load_tasks)
from vision import K as VISION_K
from vision import Vision

# ================= CONFIG =================
TICK_S = 1.0
CYCLE_DRIVER_S = 3.0        # recent cycle time must move this much before the ETA is re-attributed
APPROACH_EMA = 0.6          # smoothing of slider-derived approach speed
MAX_APPROACH_MS = 3.0
DEFAULT_OPERATOR = "OP-104"
# ==========================================

CHECKLIST = [
    {"id": "walkaround", "group": "Walk-around", "label": "360° walk-around — no leaks, damage or loose parts"},
    {"id": "undercarriage", "group": "Walk-around", "label": "Tracks, rollers and undercarriage condition"},
    {"id": "bucket", "group": "Walk-around", "label": "Bucket, teeth, pins and quick-coupler locked"},
    {"id": "fluids", "group": "Fluids", "label": "Engine oil, coolant and hydraulic oil at level"},
    {"id": "fuel", "group": "Fluids", "label": "Fuel level sufficient for the shift"},
    {"id": "mirrors", "group": "Cab", "label": "Mirrors and rear-view camera clean and adjusted"},
    {"id": "alarms", "group": "Cab", "label": "Horn, travel alarm and lights tested"},
    {"id": "seatbelt", "group": "Cab", "label": "Seatbelt latches and retracts correctly"},
    {"id": "extinguisher", "group": "Cab", "label": "Fire extinguisher present and charged"},
    {"id": "briefing", "group": "Site", "label": "Pre-start briefing done — exclusion zones and ground crew known"},
]

TRAINING_PATH = DATA / "training.json"
EVENTS_PATH = DATA / "events.json"


def hhmmss(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


class Engine:
    def cycle_baseline(self, op: str, task: dict, weather: str) -> float:
        for k in ((op, task["task_type"], task["terrain"], weather), (op, task["task_type"], task["terrain"]),
                  (op, task["task_type"])):
            if k in self._cycle_hist:
                return self._cycle_hist[k][0]
        return float(np.mean([v[0] for v in self._cycle_hist.values()]))

    def __init__(self):
        tele, hist = ensure_history()
        self.anom = AnomalyDetector()
        self.anom.load_or_train(tele)
        self.eta = EtaModel()
        self.eta.load_or_train(hist)
        work = tele[tele.state == "working"]
        # operator's own historical median cycle time, most specific match first
        self._cycle_hist = {}
        for keys in (["operator_id", "task_type", "terrain", "weather"], ["operator_id", "task_type", "terrain"],
                     ["operator_id", "task_type"]):
            for k, g in work.groupby(keys):
                if len(g) >= 20:
                    self._cycle_hist[tuple(k)] = (float(g.cycle_s.median()), int(len(g)))
        self.vision = Vision()
        self.lock = threading.RLock()
        self.tasks = load_tasks()
        self.plan_name = json.loads((DATA / "tasks.json").read_text(encoding="utf-8"))["shift_plan"]
        self.sim: LiveSim | None = None
        self.shift = {"active": False, "ended": False}
        self.events: list[dict] = []
        self.notes = ""
        self.checklist: dict = {}
        self._reset_runtime()
        self.state = self._build_state()

    # ------------------------------------------------------------------ shift lifecycle
    def _reset_runtime(self):
        self.person_source = "slider"
        self.worker_d: float | None = None
        self.walk: dict | None = None
        self._prev_d: float | None = None
        self._approach = 0.0
        self.tracker = safety.LevelTracker()
        self.safety_out = {"level": "SAFE", "reasons": [], "details": []}
        self.person = {"detected": False, "distance_m": None, "ttc_s": None, "source": "slider",
                       "approach_ms": 0.0, "closing_ms": None}
        self._prev_level = "SAFE"
        self._prev_reasons: set = set()
        self.anomaly = {"flag": False, "type": None, "current": None, "baseline": None}
        self._anom_episode: dict | None = None
        self.anom_episodes: list[dict] = []
        self.eta_ref: dict | None = None
        self.eta_ann = {"changed_by": 0, "reason": None, "at": None}
        self.eta_out: dict | None = None
        self.task_pred_at_start: dict = {}
        self.notices: list[dict] = []
        self._last_hydration: datetime | None = None
        self._last_tick = time.monotonic()
        self.anom.reset()
        self.vision.reset()

    def start_shift(self, operator_id: str, checklist: dict):
        if operator_id not in OPERATORS:
            raise HTTPException(400, "Unknown operator")
        missing = [c["label"] for c in CHECKLIST if not checklist.get(c["id"])]
        if missing:
            raise HTTPException(400, {"message": "Checklist incomplete", "missing": missing})
        with self.lock:
            self._reset_runtime()
            self.sim = LiveSim(operator_id, self.tasks)
            t0 = self.tasks[0]
            self.sim.seed_recent_cycles([self.cycle_baseline(operator_id, t0, "clear")] * 3)
            self.checklist = {"completed_at": hhmmss(self.sim.now()), "items": [c["id"] for c in CHECKLIST]}
            self.shift = {"active": True, "ended": False, "started_at": self.sim.now(), "operator_id": operator_id}
            self.events = []
            self.notes = ""
            self._log("shift", "INFO", f"Shift started — pre-start checklist complete ({len(CHECKLIST)}/{len(CHECKLIST)})",
                      detail=f"{OPERATORS[operator_id]['name']} on {MACHINE_ID}")
            self.state = self._build_state()

    def end_shift(self):
        with self.lock:
            if not self.shift.get("active"):
                return
            if self.sim.idle:
                self.sim.end_idle()
            self._close_anomaly_episode()
            self.shift.update({"active": False, "ended": True, "ended_at": self.sim.now()})
            self._log("shift", "INFO", "Shift ended — handoff report generated")
            self.state = self._build_state()

    # ------------------------------------------------------------------ events
    def _log(self, kind: str, level: str, title: str, detail: str | None = None, **data) -> dict:
        ev = {"id": len(self.events) + 1, "ts": hhmmss(self.sim.now()) if self.sim else hhmmss(datetime.now()),
              "kind": kind, "level": level, "title": title, "detail": detail, **data}
        self.events.append(ev)
        try:
            EVENTS_PATH.write_text(json.dumps(self.events, indent=1, default=str), encoding="utf-8")
        except OSError:
            pass
        return ev

    def _explain_event_async(self, ev: dict, ctx: dict):
        def run():
            res = ai.explain(ctx)
            with self.lock:
                ev["explanation"] = res["text"]
                ev["explanation_source"] = res["source"]
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ per-tick pieces
    def _update_person(self, dt: float):
        if self.person_source == "camera":
            r = self.vision.reading()
            if r and r["detected"]:
                return r["distance_m"], r["approach_ms"], True
            return None, 0.0, bool(r)
        if self.walk and self.worker_d is not None:
            self.worker_d = max(self.walk["to"], self.worker_d - self.walk["speed"] * dt)
            if self.worker_d <= self.walk["to"]:
                self.walk = None
        d = self.worker_d
        raw = 0.0 if (d is None or self._prev_d is None) else (self._prev_d - d) / dt
        raw = float(np.clip(raw, -MAX_APPROACH_MS, MAX_APPROACH_MS))
        self._approach = 0.0 if d is None else APPROACH_EMA * raw + (1 - APPROACH_EMA) * self._approach
        self._prev_d = d
        return d, round(self._approach, 2), True

    def _update_safety(self, d, approach):
        sim = self.sim
        raw = safety.evaluate(d, approach, sim.speed, sim.seatbelt, sim.weather)
        level = self.tracker.update(raw["level"], time.monotonic())
        if level == raw["level"]:
            self.safety_out = {"level": level, "reasons": raw["reasons"], "details": raw["details"]}
        else:  # holding a higher level during DOWNGRADE_HOLD_S: keep showing why
            self.safety_out = {**self.safety_out, "level": level}
        self.person = {"detected": d is not None, "distance_m": None if d is None else round(d, 1),
                       "ttc_s": raw["ttc_s"], "source": self.person_source, "approach_ms": approach,
                       "closing_ms": raw["closing_ms"]}

        reasons = set(self.safety_out["reasons"])
        new_reasons = reasons - self._prev_reasons
        if level != self._prev_level or (new_reasons and level != "SAFE"):
            if level == "SAFE":
                ev = self._log("safety", "SAFE", f"Cleared — back to SAFE from {self._prev_level}")
            else:
                ev = self._log("safety", level, f"{level}: " + ", ".join(self.safety_out["details"][:2]),
                               reasons=sorted(reasons), details=self.safety_out["details"],
                               distance_m=self.person["distance_m"], ttc_s=self.person["ttc_s"],
                               source=self.person_source, speed_kmh=round(sim.speed, 1), weather=sim.weather)
                ctx = ai.build_context(self._build_state())
                ev["context"] = ctx
                ev["explanation"] = ai.template_explain(ctx)
                ev["explanation_source"] = "template"
                if level == "CRITICAL" and ai.llm_available():
                    self._explain_event_async(ev, ctx)
        self._prev_level, self._prev_reasons = level, reasons

        if sim.weather == "heat":
            now = sim.now()
            if self._last_hydration is None or now - self._last_hydration >= timedelta(minutes=safety.HYDRATION_EVERY_MIN):
                self._last_hydration = now
                n = {"ts": hhmmss(now), "text": "Hydration break due — heat conditions",
                     "rule": f"weather == heat, every {safety.HYDRATION_EVERY_MIN} min"}
                self.notices = ([n] + self.notices)[:5]
                self._log("notice", "INFO", n["text"], detail=n["rule"])

    def _close_anomaly_episode(self):
        ep = self._anom_episode
        if ep:
            ep["ended"] = hhmmss(self.sim.now())
            self.anom_episodes.append(ep)
            self._anom_episode = None

    def _update_anomaly(self):
        sim = self.sim
        a = self.anom.evaluate(sim.features(), sim.operator_id, sim.idle)
        if a["flag"] and a["type"] == "excess_idle":
            rate = self.anom.meta["idle_burn_lph"]
            a.update({"idle_burn_lph": rate, "idle_burn_n": self.anom.meta["idle_burn_n"],
                      "idle_fuel_l": round(a["current"] * rate / 60.0, 1)})
        if a["flag"]:
            a["since"] = self._anom_episode["started"] if self._anom_episode else hhmmss(sim.now())
        was = self.anomaly.get("flag")
        if a["flag"] and not was:
            self._anom_episode = {"type": a["type"], "label": a["label"], "unit": a["unit"], "started": hhmmss(sim.now()),
                                  "peak": a["current"], "baseline": a["baseline"]}
            ev = self._log("anomaly", "ANOMALY",
                           f"{a['label']} unusual: {a['current']:g} {a['unit']} vs your usual {a['baseline']:g} {a['unit']}",
                           detail="Possible causes (not confirmed): " + "; ".join(a["possible_causes"]),
                           anomaly_type=a["type"], current=a["current"], baseline=a["baseline"], unit=a["unit"],
                           score=a["score"], threshold=a["threshold"])
            self.anomaly = a
            ctx = ai.build_context(self._build_state())
            ev["context"] = ctx
            ev["explanation"] = ai.template_explain(ctx)
            ev["explanation_source"] = "template"
        elif was and not a["flag"]:
            ep = self._anom_episode
            self._close_anomaly_episode()
            if ep:
                self._log("anomaly", "INFO", f"{ep['label']} back within normal range",
                          detail=f"Peak {ep['peak']:g} {ep['unit']} vs usual {ep['baseline']:g} {ep['unit']}")
        elif a["flag"] and self._anom_episode and a["current"] is not None:
            self._anom_episode["peak"] = max(self._anom_episode["peak"], a["current"])
        self.anomaly = a

    def _eta_inputs(self, task: dict, remaining_frac: float = 1.0) -> dict:
        sim = self.sim
        rem_t = task["tonnes"] - sim.moved_t[task["id"]] if remaining_frac is None else task["tonnes"] * remaining_frac
        is_active = sim.current_task and sim.current_task["id"] == task["id"]
        cyc = sim.recent_cycle_s if is_active else self.cycle_baseline(sim.operator_id, task, sim.weather)
        return {"task_type": task["task_type"], "tonnes": rem_t,
                "distance_m": task["distance_m"] * rem_t / task["tonnes"],
                "experience_yrs": OPERATORS[sim.operator_id]["experience_yrs"],
                "terrain": task["terrain"], "weather": sim.weather, "recent_cycle_s": cyc}

    def _update_eta(self):
        sim = self.sim
        t = sim.current_task
        if not t:
            self.eta_out = None
            return
        inp = self._eta_inputs(t, None)
        rem = self.eta.predict(**inp)
        now = sim.now()
        if t["id"] not in self.task_pred_at_start:
            self.task_pred_at_start[t["id"]] = round(rem, 1)
        ref = self.eta_ref
        if ref is None or ref["task_id"] != t["id"]:
            self.eta_ref = {"task_id": t["id"], "weather": sim.weather, "cycle": inp["recent_cycle_s"], "idle": False}
            self.eta_ann = {"changed_by": 0, "reason": None, "at": None}
        else:
            ann, already = None, 0
            if sim.weather != ref["weather"]:
                before = self.eta.predict(**{**inp, "weather": ref["weather"]})
                ann = (rem - before, f"Weather changed {ref['weather']} → {sim.weather}; the ETA model "
                                     f"re-predicted this task for {sim.weather} conditions")
            elif abs(inp["recent_cycle_s"] - ref["cycle"]) >= CYCLE_DRIVER_S:
                before = self.eta.predict(**{**inp, "recent_cycle_s": ref["cycle"]})
                ann = (rem - before, f"Recent cycle time moved {ref['cycle']:.0f} s → {inp['recent_cycle_s']:.0f} s")
            elif sim.idle and not ref["idle"]:
                ann = (sim.idle_min, f"Machine idle {sim.idle_min:.0f} min — no material moved, finish moves out by the idle time")
            elif ref["idle"] and not sim.idle:
                mins = sim.idle_log[-1]["minutes"] if sim.idle_log else 0
                ann = (mins, f"Work resumed after {mins:.0f} min idle — finish moved out by the idle time")
                already = ref.get("logged", 0)   # the idle-start event already reported part of this slip
            elif sim.idle:  # ongoing idle: slip grows minute by minute, no new event
                self.eta_ann = {**self.eta_ann, "changed_by": round(sim.idle_min),
                                "reason": f"Machine idle {sim.idle_min:.0f} min — no material moved, finish moves out by the idle time"}
            if ann:
                delta = round(ann[0])
                self.eta_ann = {"changed_by": delta, "reason": ann[1], "at": hhmmss(now)}
                inc = delta - (already if ref["idle"] and not sim.idle else 0)
                if abs(inc) >= 1:
                    self._log("eta", "INFO", f"ETA {t['id']} changed by {inc:+d} min", detail=ann[1],
                              task_id=t["id"], changed_by=inc)
                self.eta_ref = {"task_id": t["id"], "weather": sim.weather, "cycle": inp["recent_cycle_s"],
                                "idle": sim.idle, "logged": delta if sim.idle else 0}
        self.eta_out = {"task_id": t["id"], "minutes": round(rem), "minutes_exact": round(rem, 1),
                        "err_min": self.eta.err_min, "changed_by": self.eta_ann["changed_by"],
                        "reason": self.eta_ann["reason"], "changed_at": self.eta_ann["at"],
                        "finish": (now + timedelta(minutes=rem)).strftime("%H:%M"),
                        "recent_cycle_s": round(inp["recent_cycle_s"], 1)}

    def tick(self):
        with self.lock:
            now_m = time.monotonic()
            dt = min(max(now_m - self._last_tick, 0.2), 3.0)
            self._last_tick = now_m
            if not self.shift.get("active"):
                return
            ev = self.sim.tick(dt)
            if ev.get("task_done"):
                tid = ev["task_done"]
                task = next(x for x in self.tasks if x["id"] == tid)
                actual = (self.sim.task_finished[tid] - self.sim.task_started[tid]).total_seconds() / 60
                self._log("task", "INFO", f"{tid} {task['name']} complete",
                          detail=f"{actual:.0f} min actual vs {self.task_pred_at_start.get(tid, 0):.0f} min "
                                 f"predicted at start (± {self.eta.err_min} min)")
                self.anom.reset()
            d, approach, _ = self._update_person(dt)
            self._update_safety(d, approach)
            self._update_anomaly()
            self._update_eta()
            self.state = self._build_state()

    # ------------------------------------------------------------------ sim controls
    def sim_action(self, action: str, value):
        with self.lock:
            if not self.shift.get("active"):
                raise HTTPException(409, "Start the shift first")
            sim = self.sim
            if action == "move_worker":
                self.walk = None
                self.worker_d = None if value in (None, "", "clear") else max(0.3, float(value))
                if self.worker_d is None:
                    self._prev_d = None
            elif action == "walk_worker":
                v = value or {}
                self.worker_d = float(v.get("from", 20))
                self._prev_d = self.worker_d
                self.walk = {"to": float(v.get("to", 1.5)), "speed": float(v.get("speed", 1.4))}
            elif action == "person_source":
                if value == "camera" and not self.vision.available:
                    raise HTTPException(400, f"Camera detection unavailable: {self.vision.error}")
                self.person_source = "camera" if value == "camera" else "slider"
                self.vision.reset()
                self._prev_d = None
            elif action == "trigger_idle":
                mins = float(value or 0)
                if mins > 0:
                    sim.start_idle(mins)
                    self._log("sim", "INFO", f"Simulated idle stretch started ({mins:g} min fast-forwarded)",
                              detail="Synthetic input from the simulation panel")
                elif sim.idle:
                    dur = sim.end_idle()
                    self._log("sim", "INFO", f"Work resumed after {dur:.0f} min idle")
            elif action == "seatbelt_off":
                off = value is None or bool(value)
                if sim.seatbelt == (not off):
                    return self.state
                sim.seatbelt = not off
                self._log("seatbelt", "INFO", "Seatbelt unfastened" if off else "Seatbelt fastened",
                          detail="Rule alerts when the machine moves with the belt unfastened" if off else None)
            elif action == "weather":
                if value not in ("clear", "rain", "heat"):
                    raise HTTPException(400, "weather must be clear|rain|heat")
                if value != sim.weather:
                    prev = sim.weather
                    sim.weather = value
                    if value != "heat":
                        self._last_hydration = None
                    self._log("weather", "INFO", f"Weather changed: {prev} → {value}", weather=value)
            elif action == "tram":
                sim.request_tram()
            else:
                raise HTTPException(400, f"Unknown action {action}")
            self.state = self._build_state()
            return self.state

    # ------------------------------------------------------------------ views
    def _build_state(self) -> dict:
        sim = self.sim
        base = {"data_source": DATA_SOURCE, "machine_id": MACHINE_ID, "plan": self.plan_name,
                "shift": {"active": self.shift.get("active", False), "ended": self.shift.get("ended", False)},
                "vision": {"available": self.vision.available, "source": self.person_source},
                "llm": {"available": ai.llm_available(), "model": ai.LLM_MODEL if ai.llm_available() else None},
                "event_count": len(self.events)}
        if sim is None:
            return {**base, "ts": hhmmss(datetime.now()), "operator_id": None, "task_id": None}
        t = sim.current_task
        op = OPERATORS[sim.operator_id]
        started = self.shift.get("started_at")
        base["shift"].update({"operator_name": op["name"], "experience_yrs": op["experience_yrs"],
                              "started_at": hhmmss(started) if started else None,
                              "sim_offset_min": round(sim.clock_offset / 60)})
        return {
            **base,
            "ts": hhmmss(sim.now()), "operator_id": sim.operator_id, "task_id": t["id"] if t else None,
            "rpm": round(sim.rpm), "fuel_pct": round(sim.fuel_pct, 1), "hyd_temp": round(sim.hyd_temp, 1),
            "speed_kmh": round(sim.speed, 1), "swing": sim.swing, "idle": sim.idle, "idle_min": round(sim.idle_min, 1),
            "payload_t": round(sim.payload, 1), "cycle_s": round(sim.last_cycle_s, 1) if sim.last_cycle_s else None,
            "seatbelt": sim.seatbelt, "weather": sim.weather,
            "person": self.person, "safety": self.safety_out, "anomaly": self.anomaly, "eta": self.eta_out,
            "phase": sim.phase, "fuel_rate_lph": round(sim.fuel_rate, 1),
            "task": None if not t else {**t, "label": TASK_TYPES[t["task_type"]]["label"],
                                        "moved_t": round(sim.moved_t[t["id"]], 1),
                                        "progress": round(sim.moved_t[t["id"]] / t["tonnes"], 3)},
            "cycles": sim.cycles_done, "notices": self.notices,
            "baseline_snapshot": {f: {k: round(v, 1) for k, v in b.items() if k != "n"}
                                  for f, b in self.anom.baselines[sim.operator_id]["idle" if sim.idle else "working"].items()},
            "vision": {**base["vision"], "stale": self.person_source == "camera" and self.vision.reading() is None},
        }

    def tasks_view(self) -> dict:
        with self.lock:
            sim = self.sim
            out = []
            if sim is None:
                return {"plan": self.plan_name, "tasks": [], "err_min": self.eta.err_min}
            cursor = sim.now()
            for t in self.tasks:
                item = {**t, "label": TASK_TYPES[t["task_type"]]["label"], "moved_t": round(sim.moved_t[t["id"]], 1),
                        "progress": round(sim.moved_t[t["id"]] / t["tonnes"], 3)}
                if t["id"] in sim.task_finished:
                    actual = (sim.task_finished[t["id"]] - sim.task_started[t["id"]]).total_seconds() / 60
                    item.update({"status": "done", "actual_min": round(actual, 1),
                                 "predicted_at_start": self.task_pred_at_start.get(t["id"]),
                                 "finished_at": sim.task_finished[t["id"]].strftime("%H:%M")})
                elif sim.current_task and t["id"] == sim.current_task["id"]:
                    e = self.eta_out or {}
                    item.update({"status": "active" if self.shift.get("active") else "incomplete", "eta_min": e.get("minutes"), "finish": e.get("finish"),
                                 "predicted_at_start": self.task_pred_at_start.get(t["id"])})
                    cursor = sim.now() + timedelta(minutes=e.get("minutes_exact", 0))
                else:
                    inp = self._eta_inputs(t, 1.0)
                    mins = self.eta.predict(**inp)
                    cursor = cursor + timedelta(minutes=mins)
                    item.update({"status": "pending", "eta_min": round(mins), "finish": cursor.strftime("%H:%M"),
                                 "cycle_basis_s": round(inp["recent_cycle_s"], 1)})
                item["err_min"] = self.eta.err_min
                out.append(item)
            return {"plan": self.plan_name, "tasks": out, "err_min": self.eta.err_min}

    def training_view(self) -> dict:
        with self.lock:
            data = json.loads(TRAINING_PATH.read_text(encoding="utf-8"))
            mods = {m["id"]: m for m in data["modules"]}
            ev = self.events
            prox = [e for e in ev if e["kind"] == "safety" and e["level"] in ("WARNING", "CRITICAL")
                    and {"person_close", "ttc_low"} & set(e.get("reasons", []))]
            idle = [e for e in ev if e["kind"] == "anomaly" and e.get("anomaly_type") == "excess_idle"]
            belt = [e for e in ev if e["kind"] == "safety" and "seatbelt" in e.get("reasons", [])]
            rain = [e for e in ev if (e["kind"] == "weather" and e.get("weather") == "rain")
                    or (e["kind"] == "safety" and "wet_ground" in e.get("reasons", []))]
            recs = []
            if prox:
                crit = sum(e["level"] == "CRITICAL" for e in prox)
                dists = [e["distance_m"] for e in prox if e.get("distance_m") is not None]
                extra = f", closest {min(dists):g} m" if dists else ""
                recs.append({"module": mods["blind_zone"], "count": len(prox),
                             "reason": f"{len(prox)} proximity event{'s' if len(prox) != 1 else ''} today "
                                       f"({crit} critical{extra})", "event_ids": [e["id"] for e in prox]})
            if idle:
                eps = self.anom_episodes + ([self._anom_episode] if self._anom_episode else [])
                eps = [x for x in eps if x["type"] == "excess_idle"]
                peak = max((x["peak"] for x in eps), default=idle[-1]["current"])
                recs.append({"module": mods["efficient_operation"], "count": len(idle),
                             "reason": f"Idle above your usual baseline — peak {peak:g} min vs your usual "
                                       f"{idle[-1]['baseline']:g} min", "event_ids": [e["id"] for e in idle]})
            if belt:
                recs.append({"module": mods["pre_operation"], "count": len(belt),
                             "reason": f"Machine moved with belt unfastened ({len(belt)} time{'s' if len(belt) != 1 else ''})",
                             "event_ids": [e["id"] for e in belt]})
            if rain:
                recs.append({"module": mods["wet_ground"], "count": len(rain), "reason": "Rain conditions today",
                             "event_ids": [e["id"] for e in rain]})
            booked = {b["slot"] for b in data["bookings"]}
            slots, day = [], datetime.now().date()
            while len(slots) < 6:
                day += timedelta(days=1)
                if day.weekday() < 5:
                    for hm in ("07:30", "13:00"):
                        s = f"{day.isoformat()} {hm}"
                        slots.append({"slot": s, "label": f"{day.strftime('%a %d %b')} · {hm}", "taken": s in booked})
            return {"modules": data["modules"], "recommendations": recs, "bookings": data["bookings"][::-1],
                    "slots": slots[:6]}

    def book(self, module_id: str, slot: str) -> dict:
        with self.lock:
            data = json.loads(TRAINING_PATH.read_text(encoding="utf-8"))
            mod = next((m for m in data["modules"] if m["id"] == module_id), None)
            if not mod:
                raise HTTPException(404, "Unknown module")
            if any(b["slot"] == slot for b in data["bookings"]):
                raise HTTPException(409, "That slot is already booked")
            rec = next((r for r in self.training_view()["recommendations"] if r["module"]["id"] == module_id), None)
            b = {"id": len(data["bookings"]) + 1, "module_id": module_id, "title": mod["title"], "slot": slot,
                 "operator_id": self.sim.operator_id if self.sim else DEFAULT_OPERATOR,
                 "booked_at": datetime.now().isoformat(timespec="seconds"),
                 "reason": rec["reason"] if rec else "Requested by operator"}
            data["bookings"].append(b)
            TRAINING_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
            if self.sim:
                self._log("training", "INFO", f"Instructor booked: {mod['title']}", detail=slot)
            return b

    def summary(self) -> dict:
        with self.lock:
            sim = self.sim
            if sim is None:
                return {"available": False}
            ev = self.events
            end = self.shift.get("ended_at") or sim.now()
            start = self.shift["started_at"]
            safety_ev = [e for e in ev if e["kind"] == "safety" and e["level"] != "SAFE"]
            dists = [e["distance_m"] for e in safety_ev if e.get("distance_m") is not None]
            idle_total = sum(x["minutes"] for x in sim.idle_log) + (sim.idle_min if sim.idle else 0)
            rate = self.anom.meta["idle_burn_lph"]
            cycles = sim.cycle_log
            tv = self.tasks_view()["tasks"]
            eps = self.anom_episodes + ([self._anom_episode] if self._anom_episode else [])
            return {
                "available": True, "data_source": DATA_SOURCE, "ended": self.shift.get("ended", False),
                "operator": {"id": sim.operator_id, **OPERATORS[sim.operator_id]}, "machine_id": MACHINE_ID,
                "plan": self.plan_name, "start": hhmmss(start), "end": hhmmss(end),
                "duration_min": round((end - start).total_seconds() / 60, 1),
                "checklist": self.checklist,
                "production": {
                    "tonnes": round(sum(sim.moved_t.values()), 1), "cycles": len(cycles),
                    "avg_cycle_s": round(float(np.mean([c["cycle_s"] for c in cycles])), 1) if cycles else None,
                    "avg_payload_t": round(float(np.mean([c["payload_t"] for c in cycles])), 2) if cycles else None,
                    "tasks_done": sum(t["status"] == "done" for t in tv), "tasks_total": len(tv), "tasks": tv,
                },
                "safety": {
                    "warning": sum(e["level"] == "WARNING" for e in safety_ev),
                    "critical": sum(e["level"] == "CRITICAL" for e in safety_ev),
                    "closest_m": min(dists) if dists else None,
                    "seatbelt": sum("seatbelt" in e.get("reasons", []) for e in safety_ev),
                    "wet_ground": sum("wet_ground" in e.get("reasons", []) for e in safety_ev),
                    "events": safety_ev,
                },
                "anomalies": eps,
                "idle": {"total_min": round(idle_total, 1), "episodes": sim.idle_log,
                         "fuel_l": round(idle_total * rate / 60, 1), "burn_lph": rate,
                         "burn_n": self.anom.meta["idle_burn_n"]},
                "fuel": {"start_pct": START_FUEL_PCT, "now_pct": round(sim.fuel_pct, 1),
                         "used_l": round((START_FUEL_PCT - sim.fuel_pct) / 100 * FUEL_TANK_L, 1), "tank_l": FUEL_TANK_L},
                "eta_changes": [e for e in ev if e["kind"] == "eta"],
                "weather": sorted({sim.weather} | {e["weather"] for e in ev if e["kind"] == "weather"}),
                "training": self.training_view(),
                "notes": self.notes,
                "event_count": len(ev),
            }

    def meta(self) -> dict:
        return {
            "machine_id": MACHINE_ID, "data_source": DATA_SOURCE, "plan": self.plan_name,
            "operators": [{"id": k, **v} for k, v in OPERATORS.items()], "default_operator": DEFAULT_OPERATOR,
            "checklist": CHECKLIST, "safety": safety.CONSTANTS,
            "eta": self.eta.metrics, "anomaly": {**self.anom.meta, "thresholds": {k: round(v, 3) for k, v in self.anom.thresholds.items()}},
            "vision": {"available": self.vision.available, "error": self.vision.error, "K": VISION_K},
            "llm": {"available": ai.llm_available(), "model": ai.LLM_MODEL, "timeout_s": ai.LLM_TIMEOUT_S},
            "fuel_tank_l": FUEL_TANK_L,
        }


engine = Engine()


def _loop():
    while True:
        t0 = time.monotonic()
        try:
            engine.tick()
        except Exception as exc:  # keep the shift alive; surface in server log
            print("tick error:", repr(exc))
        time.sleep(max(0.0, TICK_S - (time.monotonic() - t0)))


app = FastAPI(title="CAT Operator Copilot", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _start():
    threading.Thread(target=_loop, daemon=True).start()
    threading.Thread(target=engine.vision.warmup, daemon=True).start()


class SimIn(BaseModel):
    action: str
    value: object = None


class ShiftIn(BaseModel):
    operator_id: str = DEFAULT_OPERATOR
    checklist: dict = {}


class NoteIn(BaseModel):
    text: str


class BookIn(BaseModel):
    module_id: str
    slot: str


class ExplainIn(BaseModel):
    event_id: int | None = None


class TrainingAssistantIn(BaseModel):
    question: str
    shift_context: dict = {}


class FrameIn(BaseModel):
    image: str


@app.get("/api/state")
def get_state():
    return engine.state


@app.get("/api/meta")
def get_meta():
    return engine.meta()


@app.get("/api/tasks")
def get_tasks():
    return engine.tasks_view()


@app.get("/api/events")
def get_events():
    with engine.lock:
        return list(reversed(engine.events))


@app.get("/api/training")
def get_training():
    return engine.training_view()


@app.post("/api/training/book")
def post_book(body: BookIn):
    return engine.book(body.module_id, body.slot)


@app.post("/api/training/assistant")
def post_training_assistant(body: TrainingAssistantIn):
    """RAG-based training assistant. Retrieves relevant knowledge chunks and answers
    via LLM (with template fallback). Completely isolated from other engine logic."""
    if not body.question or not body.question.strip():
        raise HTTPException(400, "question must not be empty")
    live_state = engine.state if engine.sim else {}
    return training_rag.answer(body.question.strip(), body.shift_context, live_state)


@app.post("/api/sim")
def post_sim(body: SimIn):
    return engine.sim_action(body.action, body.value)


@app.post("/api/explain")
def post_explain(body: ExplainIn | None = None):
    with engine.lock:
        if body and body.event_id:
            ev = next((e for e in engine.events if e["id"] == body.event_id), None)
            if not ev or "context" not in ev:
                raise HTTPException(404, "No explainable event with that id")
            ctx = ev["context"]
        else:
            ctx = ai.build_context(engine.state) if engine.sim else {"risk": "SAFE", "reasons": []}
    res = ai.explain(ctx)
    return {**res, "context": ctx}


@app.get("/api/summary")
def get_summary():
    return engine.summary()


@app.post("/api/shift/start")
def post_shift_start(body: ShiftIn):
    engine.start_shift(body.operator_id, body.checklist)
    return engine.state


@app.post("/api/shift/end")
def post_shift_end():
    engine.end_shift()
    return engine.state


@app.post("/api/shift/note")
def post_note(body: NoteIn):
    with engine.lock:
        engine.notes = body.text[:2000]
    return {"ok": True}


@app.post("/api/vision/frame")
def post_frame(body: FrameIn):
    res = engine.vision.process(body.image)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error"))
    return {k: v for k, v in res.items() if k != "t"}


# ---- serve the built frontend (single-command demo) ----
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
