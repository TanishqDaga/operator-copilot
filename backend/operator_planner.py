"""Operator Task Planner — execution guidance on top of the manager's PUBLISHED schedule.

The manager decides WHAT and WHEN (planner.py). This module never sequences, reorders or reassigns
anything: it receives one operator's published tasks in published order plus live facts (ETA, machine
state, current weather, forecast, safety, telemetry) and answers
    what should I focus on now · what should I prepare next · will weather affect my next task ·
    am I idle · am I ahead of or behind the published schedule.
Every recommendation carries a reason built from those facts. Priority is decided centrally by
priority.rank_guidance: safety > machine issue > current task > weather > productivity.
"""
from __future__ import annotations

import priority
from operator_metrics import live_productivity
from safety import V_WET
from schedule_clock import ScheduleClock
from simulator import TRAM_M_PER_MIN
from weather import hhmm, hour_at, to_min

# ================= CONFIG =================
EARLY_MIN = 3.0             # projected this many live min ahead of the reference -> EARLY_FINISH
LATE_MIN = 3.0              # ... behind -> called out in the reason (never "speed up")
APPROACH_MIN = 5.0          # ETA at or below this -> APPROACHING_COMPLETION
APPROACH_PROGRESS = 0.85
READY_WINDOW_MIN = 1.0      # after a task completes, announce the next assigned task for this long
DELTA_MIN_CYCLES = 3        # early/late is judged only after this many cycles on the current task (ETA settles)
IDLE_ALERT_MIN = 2.0
UPCOMING_N = 3
TRAVEL_SHARE_HIGH = 0.20    # repositioning share of active time on a task worth mentioning
TRAVEL_SHARE_MIN_ACTIVE = 2.0
CYCLE_FAST_PCT = 5.0
CYCLE_SLOW_PCT = 8.0
# ==========================================

STATE_LABEL = {
    "ACTIVE": "Active", "APPROACHING_COMPLETION": "Approaching completion", "EARLY_FINISH": "Early finish",
    "WAITING": "Waiting", "IDLE": "Idle", "TRAVELING": "Travelling", "WEATHER_PREPARATION": "Weather preparation",
    "SAFETY_HOLD": "Safety hold", "READY_FOR_NEXT_TASK": "Ready for next task",
}
WINDOW_FACTOR = {"rain": "rain", "wind": "wind", "low_visibility": "visibility"}
WINDOW_WORD = {"rain": "rain", "wind": "strong wind", "low_visibility": "low visibility"}
SAFETY_MESSAGE = "Safety condition detected. Follow the active safety procedure."


def _mins(x: float | None) -> str:
    return "—" if x is None else "<1" if x < 1 else f"{x:.0f}"


def _value(w: dict) -> str:
    return {"rain": f"{w['peak']}% rain", "wind": f"{w['peak']} km/h wind",
            "low_visibility": f"{w['peak']} m visibility"}[w["kind"]]


def _overlaps(w: dict, t: dict) -> bool:
    return w["start_min"] < t["end_min"] and w["end_min"] > t["start_min"]


def _item(category: str, action: str, reason: str, **kw) -> dict:
    return {"category": category, "action": action, "reason": reason, **kw}


class OperatorProductivityPlanner:
    """Stateless: plan(ctx) -> guidance. ctx is built by operator_service.build_context()."""

    def plan(self, ctx: dict) -> dict:
        op, pub, live, tasks = ctx["operator"], ctx.get("published"), ctx.get("live"), ctx["tasks"]
        base = {"operator": op, "synthetic": True, "schedule_id": pub["schedule_id"] if pub else None,
                "forecast_summary": ctx["forecast"]["summary"], "published_order": [t["task_id"] for t in tasks]}
        empty = {"available": False, "state": None, "next_best_action": None, "secondary_actions": [],
                 "current_task": None, "next_task": None, "upcoming_tasks": [], "time_to_next_task": None,
                 "estimated_current_task_remaining": None, "weather_guidance": None,
                 "productivity": live_productivity(live, tasks, None), "safety_priority": None, "schedule_clock": None}
        if not pub:
            return {**base, **empty, "message": "No published schedule available."}
        if not tasks:
            return {**base, **empty, "message": "No tasks are assigned to you in the published schedule."}

        clock = ScheduleClock(tasks, ctx["live_expected"], to_min(ctx["shift"]["start"]))
        running = bool(live and live.get("active"))
        status = {t["task_id"]: (live["status"].get(t["task_id"], "pending") if live else "scheduled") for t in tasks}
        cur = next((t for t in tasks if status[t["task_id"]] == "active"), None) if running else None
        open_ = [t for t in tasks if status[t["task_id"]] != "done" and t is not cur]
        nxt = open_[0] if open_ else None
        f = self._facts(ctx, clock, cur, nxt, running)

        cur_item = self._current(ctx, f, cur, nxt, tasks, status)
        items = [*self._safety(live, running), *self._operational(live, cur, running), cur_item,
                 *self._weather(ctx, f, cur, open_, running), *self._productivity(ctx, f, cur, nxt, running)]
        level = live["safety"]["level"] if running else "SAFE"
        ranked = priority.rank_guidance([i for i in items if i], level)
        top = ranked["top"]
        state = "SAFETY_HOLD" if ranked["safety_hold"] else cur_item["state"]
        detail = "Safety condition active. Follow safety procedure." if state == "SAFETY_HOLD" else cur_item["detail"]

        prev_for_next = cur or self._last_done(tasks, status, live)
        upcoming = []
        for i, t in enumerate(open_[:UPCOMING_N]):
            prev = prev_for_next if i == 0 else open_[i - 1]
            upcoming.append({**self._view(t, status), **self._prep(ctx, prev, t, status)})
        next_task = None
        if nxt:
            next_task = {**upcoming[0], "time_to_next_task_min": f["ttn"], "gap_after_current_min": f["gap"],
                         "reference_start_in_min": None if f["next_ref_in"] is None else round(f["next_ref_in"], 1)}

        return {
            **base, "available": True, "message": None, "live": running,
            "state": {"code": state, "label": STATE_LABEL[state], "detail": detail},
            "next_best_action": top, "secondary_actions": ranked["rest"],
            "current_task": self._current_view(ctx, f, cur, nxt, status, cur_item) if cur else None,
            "next_task": next_task, "upcoming_tasks": upcoming,
            "time_to_next_task": None if f["ttn"] is None else round(f["ttn"]),
            "estimated_current_task_remaining": None if f["rem"] is None else round(f["rem"]),
            "weather_guidance": self._weather_view(ctx, f, cur, nxt, items),
            "productivity": live_productivity(live, tasks, cur["task_id"] if cur else None),
            "safety_priority": {"active": ranked["safety_hold"], "level": level,
                                "message": SAFETY_MESSAGE if ranked["safety_hold"] else None,
                                "order": ["Critical safety", "Safety warning", "Machine / operational issue",
                                          "Current assigned task", "Weather guidance", "Productivity"]},
            "schedule_clock": {"now": hhmm(f["plan_now"]) if f["plan_now"] is not None else None,
                               "compression": round(clock.compression, 1), "live_clock": (live or {}).get("clock"),
                               "note": "Published windows are on the schedule clock. The demo machine moves the synthetic "
                                       "tonnage faster than the manager's planning estimates, so each window is mapped onto the "
                                       "live shift using the ETA model's expected duration for that task."},
            "tasks_completed": sum(s == "done" for s in status.values()), "tasks_total": len(tasks),
        }

    # ------------------------------------------------------------------ facts
    def _facts(self, ctx, clock, cur, nxt, running) -> dict:
        live = ctx.get("live") or {}
        el = live.get("elapsed_min") if running else None
        eta = live.get("eta")
        rem = eta["minutes_exact"] if cur and eta and eta.get("task_id") == cur["task_id"] else None
        ref = clock.window(cur["task_id"]) if cur else None
        settled = len(live.get("cycles", {}).get("current", [])) >= DELTA_MIN_CYCLES
        delta = ref[1] - (el + rem) if ref and rem is not None and settled else None   # + early / - late (live min)
        next_ref_in = clock.window(nxt["task_id"])[0] - el if nxt and el is not None else None
        ttn = gap = None
        if next_ref_in is not None:
            ttn = max(rem or 0.0, next_ref_in) if cur else max(0.0, next_ref_in)
            gap = next_ref_in - rem if cur and rem is not None else None
        plan_now = clock.to_plan(el) if el is not None else None
        return {"clock": clock, "elapsed": el, "rem": rem, "err": eta.get("err_min") if eta else None,
                "eta_finish": eta.get("finish") if rem is not None else None, "ref": ref, "delta": delta,
                "next_ref_in": next_ref_in, "ttn": ttn, "gap": gap, "plan_now": plan_now,
                "proj_plan": clock.to_plan(el + rem) if rem is not None else None,
                "progress": live.get("progress", {}).get(cur["task_id"]) if cur else None}

    def _threat(self, ctx, f, t) -> dict | None:
        """First forecast hazard window that the task is sensitive to and that is active now or begins
        before the task is projected to finish (schedule clock)."""
        if f["plan_now"] is None or f["proj_plan"] is None:
            return None
        for w in ctx["forecast"]["windows"]:
            fac = WINDOW_FACTOR[w["kind"]]
            if t["weather_sensitivity"][fac] not in ("medium", "high"):
                continue
            if w["start_min"] <= f["plan_now"] < w["end_min"]:
                return {"w": w, "factor": fac, "mode": "active", "live_in": 0.0}
            if f["plan_now"] < w["start_min"] < f["proj_plan"]:
                return {"w": w, "factor": fac, "mode": "upcoming",
                        "live_in": f["clock"].to_live(w["start_min"]) - f["elapsed"]}
        return None

    @staticmethod
    def _last_done(tasks, status, live):
        done = [t for t in tasks if status[t["task_id"]] == "done"]
        if not done or not live:
            return None
        return max(done, key=lambda t: live["task_finished_min"].get(t["task_id"], 0))

    # ------------------------------------------------------------------ guidance items
    @staticmethod
    def _safety(live, running) -> list[dict]:
        if not running or live["safety"]["level"] not in ("WARNING", "CRITICAL"):
            return []
        s = live["safety"]
        why = "; ".join(s["details"]) or "Safety rule active"
        if s["level"] == "CRITICAL":
            return [_item("SAFETY_CRITICAL", "SAFETY FIRST — stop and follow the critical safety procedure.",
                          f"{why}. Safety always takes priority over task and productivity guidance.")]
        return [_item("SAFETY_WARNING", "SAFETY FIRST — follow the active safety procedure before continuing.",
                      f"{why}. Safety always takes priority over task and productivity guidance.")]

    @staticmethod
    def _operational(live, cur, running) -> list[dict]:
        if not running or not live["anomaly"].get("flag"):
            return []
        a = live["anomaly"]
        causes = "; ".join(a.get("possible_causes") or [])
        if a["type"] == "excess_idle":
            task = f"resume {cur['name']}" if cur else "resume the assigned task"
            return [_item("OPERATIONAL_ISSUE",
                          f"Machine idle {a['current']:.0f} min — above your usual {a['baseline']:.0f} min. Check attachment/setup, then {task}.",
                          f"Idle duration flagged by the anomaly model against your own history. Possible causes (not confirmed): {causes}.")]
        return [_item("OPERATIONAL_ISSUE",
                      f"Check the machine — {a['label'].lower()} unusual ({a['current']:g} {a['unit']} vs your usual {a['baseline']:g} {a['unit']}).",
                      f"Flagged by the anomaly model. Possible causes (not confirmed): {causes}.")]

    def _current(self, ctx, f, cur, nxt, tasks, status) -> dict:
        live, pub = ctx.get("live"), ctx["published"]
        sid = pub["schedule_id"]

        def item(state, action, reason, detail):
            return _item("CURRENT_TASK", action, reason, state=state, detail=detail)

        if not live:
            first = nxt
            if ctx.get("other_operator"):
                return item("WAITING", f"The live machine is signed in to {ctx['other_operator']}. Your first assigned task is "
                                       f"{first['task_id']} {first['name']} at {first['start']}.",
                            "Live telemetry belongs to another operator's shift, so no live guidance is shown for you.",
                            f"Next task begins at {first['start']} (published).")
            return item("READY_FOR_NEXT_TASK",
                        f"Complete the pre-start checklist, then begin {first['task_id']} {first['name']} at {first['location']}.",
                        f"{first['task_id']} is your first assigned task in published schedule {sid} ({first['start']}–{first['end']}). "
                        f"The machine is released only after every pre-start item is confirmed.",
                        f"First task {first['task_id']} at {first['start']} (published).")
        done = sum(s == "done" for s in status.values())
        if live.get("ended") and not live.get("active"):
            return item("WAITING", "Shift ended — review the shift summary and complete the handoff notes.",
                        f"{done}/{len(tasks)} of your assigned tasks were completed this shift.", "Shift ended.")
        if not cur:
            if nxt is None:
                return item("WAITING", "All your assigned tasks are complete — complete post-task checks and contact your manager for the next assignment.",
                            f"{done}/{len(tasks)} assigned tasks in {sid} are complete. The operator planner never creates new work.",
                            "No remaining assigned tasks.")
            return item("WAITING", f"The live machine is on {live.get('current_task_id') or 'no task'}, which is not one of your assigned tasks — check with your manager before continuing.",
                        f"Your next assigned task in {sid} is {nxt['task_id']} {nxt['name']} ({nxt['start']}).",
                        f"Next assigned task {nxt['task_id']}.")

        m, rem, delta = live["machine"], f["rem"], f["delta"]
        eta_txt = f"ETA {_mins(rem)} min" if rem is not None else "ETA not available yet"
        prev = self._last_done(tasks, status, live)
        started = live["task_started_min"].get(cur["task_id"])
        threat = self._threat(ctx, f, cur)

        if m["idle"]:
            im = m["idle_min"]
            action = (f"Machine idle {im:.0f} min — resume {cur['name']}, or check attachment/setup if something is blocking work."
                      if im >= IDLE_ALERT_MIN else f"Machine idle — resume {cur['name']} when ready.")
            return item("IDLE", action,
                        f"No productive machine activity for {_mins(im)} min on {cur['task_id']}. Idle time moves the finish out "
                        f"minute for minute ({eta_txt}).", f"No productive machine activity detected for {_mins(im)} min.")
        if prev and started is not None and f["elapsed"] - started <= READY_WINDOW_MIN:
            return item("READY_FOR_NEXT_TASK",
                        f"Next assigned task: {cur['name']} — begin at {cur['location']} according to the published schedule.",
                        f"{prev['task_id']} {prev['name']} is complete. {cur['task_id']} is next in {sid} (published "
                        f"{cur['start']}–{cur['end']}). Complete required post-task checks before starting.",
                        f"{prev['task_id']} complete — {cur['task_id']} is next.")
        if m["phase"] == "tram":
            wet = f" on wet ground — the {V_WET:g} km/h wet-ground limit applies" if m["weather"] == "rain" else ""
            return item("TRAVELING", f"Finish repositioning, then continue {cur['name']} — {eta_txt}.",
                        f"Machine is tramming at {m['speed_kmh']:.1f} km/h{wet}.", "Machine repositioning within the task.")
        if threat:
            w, fac = threat["w"], threat["factor"]
            lvl = cur["weather_sensitivity"][fac].upper()
            if threat["mode"] == "upcoming":
                return item("WEATHER_PREPARATION",
                            f"{WINDOW_WORD[w['kind']].capitalize()} expected in ~{_mins(threat['live_in'])} min — prioritise completing the "
                            f"current {cur['label'].lower()} section before the {WINDOW_WORD[w['kind']]} window.",
                            f"Forecast {_value(w)} from {w['start']} (schedule clock). {cur['task_id']} has {lvl} {fac} sensitivity and "
                            f"is projected to finish at {hhmm(f['proj_plan'])} (schedule clock) — {eta_txt}.",
                            f"{WINDOW_WORD[w['kind']].capitalize()} window begins before this task is projected to finish.")
            limit = f"the {V_WET:g} km/h wet-ground travel limit" if fac == "rain" else "site weather limits"
            return item("WEATHER_PREPARATION",
                        f"Forecast {WINDOW_WORD[w['kind']]} window is active — continue {cur['name']} within {limit}, and report to your "
                        f"manager if conditions stop the task.",
                        f"Forecast {_value(w)} {w['start']}–{w['end']} (schedule clock); {cur['task_id']} has {lvl} {fac} sensitivity. "
                        f"Current conditions at the machine: {m['weather']}. The published schedule is unchanged.",
                        f"Forecast {WINDOW_WORD[w['kind']]} window active.")
        if delta is not None and delta >= EARLY_MIN:
            after = f"preparation for {nxt['name']}" if nxt else "the shift handover"
            ref_left = f["ref"][1] - f["elapsed"]
            return item("EARLY_FINISH",
                        f"Projected {delta:.0f} min early — continue {cur['name']}, then use the time for post-task checks and {after}.",
                        f"ETA model: {_mins(rem)} min remaining; the live schedule reference for {cur['task_id']} ends in "
                        f"{_mins(ref_left)} min. The next task still follows the published schedule.",
                        f"Projected {delta:.0f} min ahead of schedule.")
        if (rem is not None and rem <= APPROACH_MIN) or (f["progress"] or 0) >= APPROACH_PROGRESS:
            if nxt:
                where = "same location" if nxt["location"] == cur["location"] else nxt["location"]
                action = f"Current task nearly complete (~{_mins(rem)} min) — prepare for {nxt['name']} ({where})."
                tail = f" Next assigned: {nxt['task_id']} {nxt['name']} ({nxt['start']}–{nxt['end']})."
            else:
                action, tail = f"Last assigned task nearly complete (~{_mins(rem)} min) — plan post-task checks and handover.", ""
            err = f" ± {f['err']}" if f["err"] is not None else ""
            return item("APPROACHING_COMPLETION", action,
                        f"{(f['progress'] or 0):.0%} of {cur['tonnes']:g} t moved; {eta_txt}{err}.{tail}",
                        f"Current task estimated to finish in {_mins(rem)} min.")
        reason = self._pace_reason(ctx, f, cur)
        if nxt:
            reason += f" {nxt['task_id']} {nxt['name']} is next in ~{_mins(f['ttn'])} min."
        else:
            reason += " This is your last assigned task."
        trend = self._trend(ctx, f["plan_now"])
        if trend and trend["rising"]:
            reason += f" Rain probability increases later in the shift ({trend['peak_pct']}% at {trend['peak_at']})."
        return item("ACTIVE", f"Continue {cur['name']} — {eta_txt}.", reason.strip(), "Current task progressing normally.")

    @staticmethod
    def _pace_reason(ctx, f, cur) -> str:
        delta = f["delta"]
        if delta is None:
            return (f"Early/late is assessed after {DELTA_MIN_CYCLES} cycles on this task, once the ETA has settled."
                    if f["rem"] is not None else "ETA not available yet.")
        if delta <= -LATE_MIN:
            live = ctx["live"]
            causes = []
            idle_i = live["task_time_s"].get(cur["task_id"], {}).get("idle", 0.0) / 60
            if idle_i >= 1:
                causes.append(f"{idle_i:.0f} min idle on this task")
            if live["machine"]["weather"] != "clear":
                causes.append(f"{live['machine']['weather']} conditions")
            why = f" ({', '.join(causes)})" if causes else ""
            return (f"Running about {-delta:.0f} min behind the live schedule reference{why}. Keep a safe, steady pace — "
                    f"the updated ETA is visible to your manager.")
        return f"Current task is on schedule (within ±{LATE_MIN:g} min of the live schedule reference)."

    def _weather(self, ctx, f, cur, open_, running) -> list[dict]:
        out, windows = [], ctx["forecast"]["windows"]
        live = ctx.get("live") or {}
        if running and cur and live["machine"]["weather"] == "rain":
            lvl = cur["weather_sensitivity"]["rain"]
            if lvl in ("medium", "high"):
                out.append(_item("WEATHER", f"It is raining now and {cur['task_id']} has {lvl.upper()} rain sensitivity — keep travel at or "
                                            f"below {V_WET:g} km/h on wet ground; slower cycles are expected.",
                                 "Current weather at the machine (simulated). The published schedule is unchanged; report to your manager "
                                 "if conditions stop the task.", urgency=2))
            else:
                out.append(_item("WEATHER", "Current task is weather-tolerant. Continue according to the published schedule.",
                                 f"It is raining now; {cur['task_id']} has LOW rain sensitivity.", urgency=2))
        anchor = cur or (open_[0] if open_ else None)
        if anchor:
            for w in windows:
                fac = WINDOW_FACTOR[w["kind"]]
                if anchor["weather_sensitivity"][fac] == "high" and anchor["end_min"] <= w["start_min"]:
                    out.append(_item("WEATHER", f"Current schedule already places weather-sensitive {anchor['label'].lower()} "
                                                f"({anchor['task_id']}) before the {WINDOW_WORD[w['kind']]} window ({w['start']}).",
                                     f"{anchor['task_id']} is scheduled {anchor['start']}–{anchor['end']}; forecast {_value(w)} "
                                     f"from {w['start']} (schedule clock).", urgency=1))
                    break
        rain = next((w for w in windows if w["kind"] == "rain" and (f["plan_now"] is None or w["end_min"] > f["plan_now"])), None)
        if rain and open_:
            before = 0
            for t in open_:
                if t["end_min"] <= rain["start_min"]:
                    before += 1
                else:
                    break
            if before:
                which = f"next {before} tasks are" if before != 1 else "next task is"
                out.append(_item("WEATHER", f"Your {which} scheduled before the forecast rain window ({rain['start']}).",
                                 f"Forecast {_value(rain)} {rain['start']}–{rain['end']} (schedule clock); "
                                 f"{', '.join(t['task_id'] for t in open_[:before])} end{'s' if before == 1 else ''} before it."))
        for t in open_[:UPCOMING_N]:
            for w in windows:
                if not _overlaps(w, t):
                    continue
                fac = WINDOW_FACTOR[w["kind"]]
                lvl = t["weather_sensitivity"][fac]
                if lvl == "low":
                    out.append(_item("WEATHER", f"{t['task_id']} {t['name']} is weather-tolerant and scheduled during forecast "
                                                f"{WINDOW_WORD[w['kind']]} ({_value(w)}) — continue according to the published schedule.",
                                     f"{t['task_id']} has LOW {fac} sensitivity; the manager placed it in this window deliberately."))
                else:
                    out.append(_item("WEATHER", f"{t['task_id']} {t['name']} is scheduled during forecast {WINDOW_WORD[w['kind']]} "
                                                f"({_value(w)}) — expect slower progress.",
                                     f"{t['task_id']} has {lvl.upper()} {fac} sensitivity; the manager's plan already allows about "
                                     f"{t['delay_min']:.0f} min for weather in that window."))
                break
        vis = next((w for w in windows if w["kind"] == "low_visibility" and f["plan_now"] is not None
                    and w["start_min"] > f["plan_now"]), None)
        if vis:
            out.append(_item("WEATHER", f"Forecast indicates worsening visibility later (down to {vis['peak']} m at {vis['peak_at']}).",
                             f"Low-visibility window {vis['start']}–{vis['end']} (schedule clock)."))
        return out[:5]

    def _productivity(self, ctx, f, cur, nxt, running) -> list[dict]:
        if not running or not cur:
            return []
        live, out = ctx["live"], []
        pairs = live["cycles"]["current"]
        base = live["cycles"].get("current_baseline_s")
        if base and len(pairs) >= 5:
            recent = pairs[-5:]
            avg = sum(recent) / len(recent)
            eff = (base - avg) / base * 100
            detail = f"Last {len(recent)} cycles average {avg:.1f} s vs your historical {base:.1f} s for {cur['label'].lower()} ({eff:+.0f}%)."
            if eff >= CYCLE_FAST_PCT:
                out.append(_item("PRODUCTIVITY", "Current task is progressing faster than your baseline.", detail))
            elif eff <= -CYCLE_SLOW_PCT:
                wx = f" Current weather: {live['machine']['weather']}." if live["machine"]["weather"] != "clear" else ""
                out.append(_item("PRODUCTIVITY", f"Cycles are {abs(eff):.0f}% longer than your baseline — check digging conditions and truck spotting.",
                                 detail + wx))
        tt = live["task_time_s"].get(cur["task_id"])
        if tt:
            active = (tt["working"] + tt["travel"]) / 60
            if active >= TRAVEL_SHARE_MIN_ACTIVE and tt["travel"] / 60 / active >= TRAVEL_SHARE_HIGH:
                out.append(_item("PRODUCTIVITY", "Minimise unnecessary repositioning between passes.",
                                 f"Repositioning is {tt['travel'] / 60 / active:.0%} of active time on {cur['task_id']} so far "
                                 f"({tt['travel'] / 60:.1f} of {active:.1f} min)."))
        if nxt and nxt["location"] == cur["location"]:
            out.append(_item("PRODUCTIVITY", "Next task is at the same location — transition should be short.",
                             f"{cur['task_id']} and {nxt['task_id']} are both at {cur['location']}."))
        return out

    # ------------------------------------------------------------------ views
    @staticmethod
    def _view(t, status) -> dict:
        r = t.get("recommendation") or {}
        return {"task_id": t["task_id"], "name": t["name"], "location": t["location"], "task_type": t["task_type"],
                "label": t["label"], "machine": t["machine"], "start": t["start"], "end": t["end"],
                "planned_min": t["effective_min"], "weather_sensitivity": t["weather_sensitivity"],
                "status": status[t["task_id"]], "tonnes": t["tonnes"],
                "manager_note": r.get("operator_note"), "manager_label": r.get("label")}

    def _prep(self, ctx, prev, t, status) -> dict:
        prep, reloc = [], None
        if prev:
            reloc = prev["location"] != t["location"]
            prep.append(f"Relocate to {t['location']} after completing {prev['task_id']}." if reloc
                        else f"Same location as {prev['task_id']} — no relocation needed.")
            if prev["task_type"] != t["task_type"]:
                prep.append(f"Task type changes ({prev['label']} → {t['label']}) — check attachment and setup before starting.")
            if prev["machine"] != t["machine"]:
                prep.append(f"Assigned to {t['machine']} — confirm the machine handover with your manager.")
        else:
            prep.append("Complete the pre-start checklist before starting.")
        tram = None
        if t.get("distance_m"):
            speed = TRAM_M_PER_MIN[t["terrain"]]
            tram = round(t["distance_m"] / speed, 1)
            prep.append(f"Task travel distance {t['distance_m']:g} m on {t['terrain']} ground (≈ {tram:g} min tramming at {speed:g} m/min).")
        deps = [d for d in t.get("depends_on") or [] if status.get(d) != "done"]
        if deps:
            prep.append(f"Starts after {', '.join(deps)} {'is' if len(deps) == 1 else 'are'} complete.")
        for w in ctx["forecast"]["windows"]:
            fac = WINDOW_FACTOR[w["kind"]]
            if _overlaps(w, t) and t["weather_sensitivity"][fac] in ("medium", "high"):
                prep.append(f"Forecast {WINDOW_WORD[w['kind']]} during its window ({_value(w)}) — "
                            f"{t['weather_sensitivity'][fac].upper()} {fac} sensitivity.")
                break
        return {"preparation": prep,
                "transition": {"relocation": reloc, "from": prev["location"] if prev else None, "to": t["location"],
                               "task_travel_m": t.get("distance_m"), "tram_min": tram}}

    def _current_view(self, ctx, f, cur, nxt, status, cur_item) -> dict:
        live = ctx["live"]
        delta = f["delta"]
        sched = None if delta is None else "early" if delta >= EARLY_MIN else "late" if delta <= -LATE_MIN else "on_schedule"
        upcoming = next((w for w in ctx["forecast"]["windows"] if f["plan_now"] is not None and w["end_min"] > f["plan_now"]), None)
        return {
            **self._view(cur, status), "progress": f["progress"], "eta_min": None if f["rem"] is None else round(f["rem"], 1),
            "eta_err_min": f["err"], "eta_finish": f["eta_finish"],
            "projected_delta_min": None if delta is None else round(delta, 1), "schedule_status": sched,
            "reference_end_in_min": round(f["ref"][1] - f["elapsed"], 1) if f["ref"] else None,
            "current_weather": live["machine"]["weather"],
            "upcoming_weather": (f"{WINDOW_WORD[upcoming['kind']].capitalize()} {_value(upcoming)} at {upcoming['peak_at']} "
                                 f"(window {upcoming['start']}–{upcoming['end']})") if upcoming else "No hazard window ahead in the forecast.",
            "guidance": cur_item["action"],
            "next": {"task_id": nxt["task_id"], "name": nxt["name"], "start": nxt["start"]} if nxt else None,
            "transition": self._prep(ctx, cur, nxt, status)["transition"] if nxt else None,
        }

    @staticmethod
    def _trend(ctx, plan_now) -> dict | None:
        hours = ctx["forecast"]["hours"]
        if not hours:
            return None
        ref = plan_now if plan_now is not None else hours[0]["start_min"]
        now_h = hour_at(hours, ref)
        ahead = [h for h in hours if h["start_min"] + 60 > ref]
        peak = max(ahead, key=lambda h: h["rain_probability"]) if ahead else now_h
        rising = peak["rain_probability"] >= now_h["rain_probability"] + 10
        when = "now" if plan_now is not None else "at shift start"
        text = (f"Rain probability {now_h['rain_probability']}% {when} → {peak['rain_probability']}% at {peak['time']}"
                if rising else f"Rain probability stays at or below {peak['rain_probability']}% for the rest of the shift")
        return {"now_pct": now_h["rain_probability"], "peak_pct": peak["rain_probability"], "peak_at": peak["time"],
                "rising": rising, "text": text}

    def _weather_view(self, ctx, f, cur, nxt, items) -> dict:
        live = ctx.get("live") or {}
        w_items = [{"action": i["action"], "reason": i["reason"]} for i in items if i and i["category"] == "WEATHER"]
        nextw = next((w for w in ctx["forecast"]["windows"] if f["plan_now"] is None or w["end_min"] > f["plan_now"]), None)
        trend = self._trend(ctx, f["plan_now"])
        return {"current": live.get("machine", {}).get("weather") if live.get("active") else None,
                "schedule_now": hhmm(f["plan_now"]) if f["plan_now"] is not None else None,
                "trend": trend, "next_window": nextw, "items": w_items,
                "headline": w_items[0]["action"] if w_items else (trend["text"] if trend else None),
                "forecast_summary": ctx["forecast"]["summary"], "synthetic": True}
