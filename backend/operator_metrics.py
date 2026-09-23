"""Operator productivity metrics — operational facts from live telemetry, never a skill score.

Everything comes from the simulator's own accounting (seconds working / repositioning / idle, each
cycle's duration) and the operator's historical cycle baseline. When there is not enough data a metric
is returned as None with status "collecting" instead of a misleading number. No rankings, no
comparisons between operators.
"""
from __future__ import annotations

from statistics import mean

# ================= CONFIG =================
MIN_CYCLES = 5              # cycles needed before cycle efficiency is shown
MIN_ELAPSED_MIN = 2.0       # shift minutes needed before utilisation is shown
RECENT_CYCLES = 5           # "current cycle" = mean of the last N cycles on the current task
IDLE_OPPORTUNITY_MIN = 2.0  # idle episodes at least this long are listed as opportunities
TRAVEL_ABOVE_AVG = 1.5      # task travel time above this x shift average is noted
CYCLE_NOTE_PCT = 3.0        # shift cycle difference below this is not called out
# ==========================================


def efficiency_pct(current_s: float, baseline_s: float) -> float:
    """Positive = shorter cycles than baseline."""
    return round((baseline_s - current_s) / baseline_s * 100.0, 1)


def _cycle_block(pairs: list[tuple[float, float]], recent: int | None = None) -> dict:
    """pairs: (actual cycle s, baseline s). Returns current/baseline/efficiency or 'collecting'."""
    if len(pairs) < MIN_CYCLES:
        return {"status": "collecting", "n": len(pairs), "needed": MIN_CYCLES,
                "current_s": None, "baseline_s": None, "efficiency_pct": None}
    use = pairs[-recent:] if recent else pairs
    cur, base = mean(p[0] for p in use), mean(p[1] for p in use)
    return {"status": "ok", "n": len(use), "current_s": round(cur, 1), "baseline_s": round(base, 1),
            "efficiency_pct": efficiency_pct(cur, base)}


def time_breakdown(live: dict) -> dict:
    ts = live["time_s"]
    working, travel, idle = ts["working"] / 60, ts["travel"] / 60, ts["idle"] / 60
    total = working + travel + idle
    ok = total >= MIN_ELAPSED_MIN
    return {"status": "ok" if ok else "collecting", "elapsed_min": round(total, 1),
            "working_min": round(working, 1), "travel_min": round(travel, 1), "idle_min": round(idle, 1),
            "active_min": round(working + travel, 1),
            "utilization_pct": round((working + travel) / total * 100) if ok else None}


def live_productivity(live: dict | None, tasks: list[dict], current_id: str | None) -> dict:
    if not live:
        return {"status": "collecting", "note": "Available once your shift is running.", "time": None,
                "cycle": None, "shift_cycle": None, "tasks_completed": 0, "tasks_total": len(tasks)}
    cyc = live["cycles"]
    cur_pairs = [(c, cyc["current_baseline_s"]) for c in cyc["current"]] if cyc.get("current_baseline_s") else []
    done = sum(live["status"].get(t["task_id"]) == "done" for t in tasks)
    tb = time_breakdown(live)
    return {
        "status": tb["status"], "time": tb,
        "cycle": {**_cycle_block(cur_pairs, RECENT_CYCLES), "task_id": current_id},
        "shift_cycle": _cycle_block(cyc["shift"]),
        "tasks_completed": done, "tasks_total": len(tasks),
        "note": "Operational metrics from live machine telemetry — not a rating of the operator.",
    }


def shift_summary(live: dict | None, tasks: list[dict], clock, err_min: float) -> dict:
    """End-of-shift roll-up + factual productivity observations."""
    if not live:
        return {"available": False}
    tb = time_breakdown(live)
    sc = _cycle_block(live["cycles"]["shift"])
    ids = [t["task_id"] for t in tasks] or live["sim_task_ids"]
    done = [i for i in ids if live["status"].get(i) == "done"]
    fin = live["task_finished_min"]

    adherence, late = None, []
    if tasks and clock and done:
        on_time = 0
        for i in done:
            ref_end = clock.window(i)[1]
            diff = fin[i] - ref_end
            if diff <= err_min:
                on_time += 1
            else:
                late.append((i, diff))
        adherence = round(on_time / len(done) * 100)

    opp: list[str] = []
    names = {t["task_id"]: t["name"] for t in tasks}
    order = ids
    for ep in live["idle_log"]:
        if ep["minutes"] < IDLE_OPPORTUNITY_MIN or not ep.get("task_id"):
            continue
        tid = ep["task_id"]
        prev = order[order.index(tid) - 1] if tid in order and order.index(tid) > 0 else None
        where = (f"between {prev} and {tid}" if prev and (ep.get("progress") or 0) < 0.02
                 else f"during {tid}")
        opp.append(f"{ep['minutes']:.0f} min idle {where} (from {ep['start']}).")
    travel = {i: live["task_time_s"].get(i, {}).get("travel", 0.0) / 60 for i in done}
    if len(travel) >= 2:
        avg = mean(travel.values())
        above = [i for i, v in travel.items() if v >= 0.5 and v > TRAVEL_ABOVE_AVG * avg]
        if above:
            opp.append(f"{len(above)} task{'s' if len(above) != 1 else ''} had repositioning time above the shift "
                       f"average ({', '.join(above)}; average {avg:.1f} min).")
    for i, diff in late:
        idle_i = live["task_time_s"].get(i, {}).get("idle", 0.0) / 60
        extra = f", including {idle_i:.0f} min idle" if idle_i >= 1 else ""
        opp.append(f"{i} {names.get(i, '')} finished {diff:.0f} min after its live schedule reference{extra}.".replace("  ", " "))
    if sc["status"] == "ok" and abs(sc["efficiency_pct"]) >= CYCLE_NOTE_PCT:
        word = "shorter" if sc["efficiency_pct"] > 0 else "longer"
        opp.append(f"Average cycle time was {abs(sc['efficiency_pct']):.0f}% {word} than your historical baseline "
                   f"({sc['current_s']} s vs {sc['baseline_s']} s).")

    return {
        "available": True, "tasks_completed": len(done), "tasks_scheduled": len(ids),
        "time": tb, "cycle": sc, "schedule_adherence_pct": adherence,
        "adherence_basis": (f"{len(done)} completed task{'s' if len(done) != 1 else ''} finishing within the ETA band "
                            f"(± {err_min} min) of the live schedule reference") if adherence is not None else
                           ("No published schedule for this shift" if not tasks else "No tasks completed yet"),
        "weather_disruptions": live["weather_changes"], "opportunities": opp,
        "note": "Operational observations from this shift's telemetry — not a performance score and not compared "
                "with other operators.",
    }
