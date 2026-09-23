"""Priority arbitration between everything the copilot may tell the operator at once.

A schedule recommendation is advisory (40). Anything safety-related always outranks it, so the
planner can never say "do this now because of weather" while a safety rule is active.
"""
from __future__ import annotations

# ================= CONFIG =================
PRIORITY = {
    "SAFETY_CRITICAL": 100,
    "SAFETY_WARNING": 80,
    "OPERATIONAL_ANOMALY": 60,
    "SCHEDULE_RECOMMENDATION": 40,
    "INFORMATIONAL": 20,
}
# ==========================================

MESSAGES = {
    "SAFETY_CRITICAL": "Safety issue takes priority over schedule recommendation.",
    "SAFETY_WARNING": "Safety issue takes priority over schedule recommendation.",
    "OPERATIONAL_ANOMALY": "Operational anomaly takes priority over schedule recommendation.",
}


def active_items(state: dict, schedule_rec: dict | None = None) -> list[dict]:
    """Everything currently asking for attention, highest priority first."""
    items = []
    level = (state.get("safety") or {}).get("level", "SAFE")
    if level in ("CRITICAL", "WARNING"):
        kind = f"SAFETY_{level}"
        items.append({"type": kind, "priority": PRIORITY[kind],
                      "title": ", ".join((state.get("safety") or {}).get("details", [])[:1]) or level})
    anom = state.get("anomaly") or {}
    if anom.get("flag"):
        items.append({"type": "OPERATIONAL_ANOMALY", "priority": PRIORITY["OPERATIONAL_ANOMALY"],
                      "title": anom.get("label") or anom.get("type")})
    if schedule_rec:
        items.append({"type": "SCHEDULE_RECOMMENDATION", "priority": PRIORITY["SCHEDULE_RECOMMENDATION"],
                      "title": schedule_rec.get("label")})
    for n in state.get("notices") or []:
        items.append({"type": "INFORMATIONAL", "priority": PRIORITY["INFORMATIONAL"], "title": n.get("text")})
    return sorted(items, key=lambda x: -x["priority"])


def resolve(state: dict, schedule_rec: dict | None = None) -> dict:
    """Top item plus whether the schedule recommendation is currently outranked."""
    items = active_items(state, schedule_rec)
    top = items[0] if items else None
    outranked = bool(top and top["priority"] > PRIORITY["SCHEDULE_RECOMMENDATION"])
    return {"top": top, "items": items, "schedule_suppressed": outranked,
            "message": MESSAGES.get(top["type"]) if outranked else None}


# ---------------------------------------------------------------- operator execution guidance
# Used by operator_planner.py. Safety always first; productivity always last.
GUIDANCE_PRIORITY = {
    "SAFETY_CRITICAL": 100,
    "SAFETY_WARNING": 80,
    "OPERATIONAL_ISSUE": 60,
    "CURRENT_TASK": 50,
    "WEATHER": 40,
    "PRODUCTIVITY": 20,
}
SAFETY_GUIDANCE = ("SAFETY_CRITICAL", "SAFETY_WARNING")


def rank_guidance(items: list[dict], safety_level: str = "SAFE") -> dict:
    """Pick the single next best action from guidance items ({category, action, reason, ...}).

    While a safety rule is active, productivity items are dropped entirely and everything below safety
    is marked deferred, so nothing can nudge the operator to hurry through a safety condition."""
    hold = safety_level in ("WARNING", "CRITICAL")
    kept = []
    for i, it in enumerate(items):
        if hold and it["category"] == "PRODUCTIVITY":
            continue
        kept.append({**it, "priority": GUIDANCE_PRIORITY[it["category"]],
                     "deferred": hold and it["category"] not in SAFETY_GUIDANCE, "_i": i})
    kept.sort(key=lambda x: (-x["priority"], -x.get("urgency", 0), x["_i"]))
    for k in kept:
        k.pop("_i")
    return {"top": kept[0] if kept else None, "rest": kept[1:], "safety_hold": hold}
