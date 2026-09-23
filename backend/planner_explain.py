"""Deterministic, template-based explanations for planner decisions. No LLM involved.

Every moved task gets a reason naming the forecast numbers and the task's sensitivity level, e.g.
"Moved 14:30 → 09:00 because rain probability reaches 85% in its original window vs 10% in the new
window, and this task has HIGH rain sensitivity."
"""
from __future__ import annotations

from weather import LOW_VIS_M, RAIN_WINDOW_PCT, WIND_WINDOW_KMH

# ================= CONFIG =================
IMPACT_HIGH = 0.20            # weather delay / base duration at or above this -> impact "high"
IMPACT_MEDIUM = 0.07
CONFIDENCE_STRONG_PCT = 70    # peak rain probability behind a decision -> "strong" recommendation
CONFIDENCE_MODERATE_PCT = 40
OWN_BENEFIT_MIN = 2.0         # a task counts as moved "for its own sake" if it avoids at least this much delay
PRIORITY_TYPE = "SCHEDULE_RECOMMENDATION"
PRIORITY_VALUE = 40
DISCLAIMER = ("Estimated impact only — based on a synthetic forecast and planning-duration assumptions, "
              "not measured productivity.")
# ==========================================

FACTOR_WORD = {"rain": "rain", "wind": "wind", "visibility": "visibility"}
WINDOW_NAME = {"rain": "forecast rain", "wind": "strong-wind", "visibility": "low-visibility"}


def impact_level(delay: float, base: float) -> str:
    r = delay / base if base else 0.0
    return "high" if r >= IMPACT_HIGH else "medium" if r >= IMPACT_MEDIUM else "low"


def confidence(rain_pct: int) -> str:
    return "strong" if rain_pct >= CONFIDENCE_STRONG_PCT else "moderate" if rain_pct >= CONFIDENCE_MODERATE_PCT else "weak"


def bad_factors(w: dict) -> list[str]:
    """Hazard factors present in a window (rain, wind, visibility order)."""
    out = []
    if w["max_rain"] >= RAIN_WINDOW_PCT:
        out.append("rain")
    if w["max_wind"] >= WIND_WINDOW_KMH:
        out.append("wind")
    if w["min_visibility"] < LOW_VIS_M:
        out.append("visibility")
    return out


def _value(w: dict, f: str) -> str:
    return {"rain": f"{w['max_rain']}% rain", "wind": f"{w['max_wind']} km/h wind",
            "visibility": f"{w['min_visibility']} m visibility"}[f]


def _compare(f: str, o: dict, r: dict) -> str:
    ow, rw = o["weather"], r["weather"]
    if f == "rain":
        return (f"rain probability reaches {ow['max_rain']}% in its original window ({o['start']}–{o['end']}) "
                f"vs {rw['max_rain']}% in the new window")
    if f == "wind":
        return f"wind reaches {ow['max_wind']} km/h in its original window vs {rw['max_wind']} km/h in the new window"
    return (f"visibility drops to {ow['min_visibility']} m in its original window vs "
            f"{rw['min_visibility']} m in the new window")


def _dominant(o: dict, r: dict, profile: dict) -> str:
    diffs = {f: abs(o["factor_delay"][f] - r["factor_delay"][f]) for f in o["factor_delay"]}
    f = max(diffs, key=lambda k: (diffs[k], k == "rain"))
    if diffs[f] < 0.5:  # weather made no difference: name the factor the task cares most about
        rank = {"low": 0, "medium": 1, "high": 2}
        f = max(profile, key=lambda k: (rank[profile[k]], k == "rain"))
    return f


def _swapped(o_by: dict, r_by: dict, op_: int, rp: int) -> list[str]:
    """Tasks that changed sides with this one (were behind, now ahead — or the reverse)."""
    if rp > op_:
        ks = [k for k, x in r_by.items() if o_by[k]["position"] > op_ and x["position"] < rp]
    else:
        ks = [k for k, x in r_by.items() if o_by[k]["position"] < op_ and x["position"] > rp]
    return sorted(ks, key=lambda k: r_by[k]["position"])


def explain_task(task: dict, o: dict, r: dict, o_by: dict, r_by: dict, hours: list[dict]) -> dict:
    prof = task["weather_sensitivity"]
    op_, rp = o["position"], r["position"]
    d_o, d_r = o["delay_min"], r["delay_min"]
    f = _dominant(o, r, prof)
    lvl = prof[f].upper()
    rain_ref = max(o["weather"]["max_rain"], r["weather"]["max_rain"])
    conf = confidence(rain_ref) if f == "rain" else "moderate"
    bad_new = bad_factors(r["weather"])
    tolerant_bad = next((b for b in bad_new if prof[b] == "low"), None)
    exposed_bad = next((b for b in bad_new if prof[b] == "high"), None)
    delay_txt = f"Estimated weather delay {d_o:.0f} → {d_r:.0f} min."
    moved = "earlier" if rp < op_ else "later" if rp > op_ else "unchanged"
    source, note = "planner", None

    if r["locked"]:
        source, moved = "locked", "unchanged"
        label = "In progress" if r.get("live_status") == "active" else "Completed"
        reason = "Already started in the live shift — the planner never re-orders done or active tasks."
    elif r.get("override"):
        source = "manager_override"
        ov = r["override"]
        how = f"pinned to start at {ov['start']}" if ov.get("start") else f"placed at position {ov.get('position')}"
        was = f" Planner recommendation was {ov['recommended_start']}." if ov.get("recommended_start") else ""
        label = "Manager override"
        reason = f"Manager override — {how}.{was} The planner keeps this decision and plans the other tasks around it. {delay_txt}"
    elif moved == "unchanged":
        label = "No change"
        shift = abs(r["start_min"] - o["start_min"])
        reason = f"Keeps position {rp}."
        if shift >= 10:
            reason += f" Starts {o['start']} → {r['start']} because other tasks were re-sequenced."
        reason += f" Forecast in its window: up to {r['weather']['max_rain']}% rain. Estimated weather delay {d_r:.0f} min."
    elif d_o - d_r >= OWN_BENEFIT_MIN and prof[f] != "low":
        label = f"Moved {moved} — {FACTOR_WORD[f]} sensitive"
        reason = (f"Moved {o['start']} → {r['start']} because {_compare(f, o, r)}, and this task has {lvl} "
                  f"{FACTOR_WORD[f]} sensitivity. {delay_txt}")
        when = "later" if moved == "earlier" else "earlier"
        note = (f"{FACTOR_WORD[f].capitalize()} risk is higher {when} ({_value(o['weather'], f)} in its original "
                f"window). This task is {lvl} {FACTOR_WORD[f]}-sensitive, so it was scheduled in this window.")
    elif tolerant_bad:
        others = [k for k in _swapped(o_by, r_by, op_, rp) if r_by[k]["weather_sensitivity"][tolerant_bad] != "low"]
        label = f"Moved {moved} — weather tolerant"
        keep = f" for {', '.join(others)}" if others else ""
        reason = (f"Moved into the {r['start']}–{r['end']} {WINDOW_NAME[tolerant_bad]} window "
                  f"({_value(r['weather'], tolerant_bad)}) because this task has LOW {FACTOR_WORD[tolerant_bad]} "
                  f"sensitivity, preserving the better window{keep} (weather-sensitive work). {delay_txt}")
        note = f"Weather-tolerant task scheduled during {WINDOW_NAME[tolerant_bad]} ({_value(r['weather'], tolerant_bad)})."
        f, conf = tolerant_bad, confidence(r["weather"]["max_rain"]) if tolerant_bad == "rain" else "moderate"
    elif moved == "earlier":
        who = ", ".join(_swapped(o_by, r_by, op_, rp)) or "other tasks"
        label = "Moved earlier"
        reason = f"Starts earlier ({o['start']} → {r['start']}) because {who} moved later to a better-suited window. {delay_txt}"
    else:
        ahead = _swapped(o_by, r_by, op_, rp)
        label = "Moved later — made room"
        reason = (f"Shifted {o['start']} → {r['start']} to make room for {', '.join(ahead) or 'other tasks'}, which "
                  f"gain{'s' if len(ahead) == 1 else ''} more from the earlier window. {lvl} {FACTOR_WORD[f]} sensitivity; "
                  f"up to {r['weather']['max_rain']}% rain in its new window. {delay_txt}")

    conflict = None
    if exposed_bad and not r["locked"]:
        conflict = (f"HIGH {FACTOR_WORD[exposed_bad]}-sensitive task scheduled during {WINDOW_NAME[exposed_bad]} "
                    f"({_value(r['weather'], exposed_bad)}) — expect delays or consider an override.")
    return {
        "task_id": task["id"], "priority_type": PRIORITY_TYPE, "priority": PRIORITY_VALUE, "source": source,
        "original_position": op_, "recommended_position": rp, "moved": moved, "label": label, "reason": reason,
        "operator_note": note, "original_window": f"{o['start']}–{o['end']}", "recommended_window": f"{r['start']}–{r['end']}",
        "dominant_factor": f, "sensitivity_level": prof[f], "weather_impact": impact_level(d_r, r["base_min"]),
        "confidence": conf, "delay_original_min": d_o, "delay_recommended_min": d_r, "weather_conflict": conflict,
    }


def build_summary(forecast: dict, orig: list[dict], rec: list[dict], recs: dict, conflicts: list[dict],
                  shift_end: int) -> dict:
    o_total = sum(x["effective_min"] for x in orig)
    r_total = sum(x["effective_min"] for x in rec)
    saved = round(o_total - r_total)
    moved = [k for k, v in recs.items() if v["moved"] != "unchanged" and v["source"] == "planner"]
    by_id = {x["task_id"]: x for x in rec}
    parts = [forecast["summary"].rstrip(".") + "."]
    for x in rec:
        k, v = x["task_id"], recs[x["task_id"]]
        if v["source"] != "planner":
            continue
        if v["label"].endswith("tolerant"):
            parts.append(f"{k} {x['name']} is weather-tolerant and has been shifted into the {x['start']}–{x['end']} window.")
        elif v["label"].endswith("sensitive"):
            parts.append(f"{k} {x['name']} is {v['dominant_factor']}-sensitive and has been moved to {x['start']}–{x['end']}.")
    overrides = [k for k, v in recs.items() if v["source"] == "manager_override"]
    if overrides:
        parts.append(f"Manager override kept for {', '.join(overrides)}.")
    if saved > 0:
        parts.append(f"Estimated time saved vs original sequence: {saved} min.")
    elif saved < 0:
        parts.append(f"This sequence is estimated to take {-saved} min longer than the original.")
    else:
        parts.append("No estimated time difference vs the original sequence.")
    warnings = [f"{x['task_id']}: {w}" for x in rec for w in x["warnings"]]
    return {
        "tasks_total": len(rec), "tasks_moved": len(moved), "moved_task_ids": moved,
        "original_order": [x["task_id"] for x in orig], "recommended_order": [x["task_id"] for x in rec],
        "original_total_min": round(o_total, 1), "recommended_total_min": round(r_total, 1),
        "estimated_time_saved_min": saved,
        "original_finish": max((x["end"] for x in orig), default=None),
        "recommended_finish": max((x["end"] for x in rec), default=None),
        "forecast_summary": forecast["summary"], "headline": " ".join(parts), "disclaimer": DISCLAIMER,
        "warnings": warnings, "conflicts": conflicts,
        "fits_shift": all(x["end_min"] <= shift_end + 0.5 for x in rec),
    }
