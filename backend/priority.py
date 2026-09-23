"""Priority engines. Never the LLM.

1. Cab alerts — rank(): severity × time-to-harm × confidence × context. One headline action in the cab;
   everything else is logged quietly (timeline).
2. Planning — resolve() / rank_guidance(): where schedule recommendations and operator execution guidance
   sit relative to safety. Safety always outranks them.
"""
from __future__ import annotations

import safety

# ============================ CONFIG ============================
HEADLINE_PROX = "Worker entering active path — reduce speed."
ETA_SLIP_MIN = 5

SEV_PROX_CRIT = 1.00
SEV_PROX_WARN = 0.70
SEV_BELT_MOVING = 0.65
SEV_BELT_PARKED = 0.45
SEV_IDLE = 0.45
SEV_ETA = 0.40
SEV_TRAIN = 0.20
SEV_WET = 0.55

TTH_IDLE = 0.18
TTH_ETA = 0.15
TTH_TRAIN = 0.12
TTH_BELT_PARKED = 0.28
TTH_BELT_MOVING = 0.55
TTH_WET = 0.35

CONF_SLIDER = 0.95
CONF_CAMERA = 0.70
CONF_BELT = 1.00
CONF_ETA = 0.80
CONF_TRAIN = 1.00
CONF_WET = 1.00
CONF_IDLE_FLOOR = 0.60
CONF_IDLE_SPAN = 0.35

CTX_PROX = 1.00
CTX_BELT_MOVING = 0.85
CTX_BELT_PARKED = 0.50
CTX_PROD_ACTIVE_TASK = 0.90
CTX_PROD_NO_TASK = 0.40
CTX_TRAIN_DURING_PROX = 0.15
CTX_TRAIN_CLEAR = 0.70
CTX_WET = 0.55
# =================================================================

CONSTANTS = {
    "formula": "severity * time_to_harm * confidence * context",
    "HEADLINE_PROX": HEADLINE_PROX,
    "ETA_SLIP_MIN": ETA_SLIP_MIN,
    "SEV_PROX_CRIT": SEV_PROX_CRIT, "SEV_PROX_WARN": SEV_PROX_WARN,
    "SEV_BELT_MOVING": SEV_BELT_MOVING, "SEV_BELT_PARKED": SEV_BELT_PARKED,
    "SEV_IDLE": SEV_IDLE, "SEV_ETA": SEV_ETA, "SEV_TRAIN": SEV_TRAIN,
    "CONF_SLIDER": CONF_SLIDER, "CONF_CAMERA": CONF_CAMERA,
}

_PROX_REASONS = {"person_close", "ttc_low"}


def _clip01(v: float) -> float:
    return round(max(0.0, min(1.0, float(v))), 4)


def _product(s: float, t: float, c: float, r: float) -> float:
    return round(s * t * c * r, 6)


def _tth_from_ttc(ttc_s: float | None) -> float:
    if ttc_s is None:
        return 0.6
    if ttc_s <= safety.T_CRIT:
        return 1.0
    return _clip01(safety.T_CRIT / max(ttc_s, 0.1))


def _idle_confidence(anomaly: dict) -> float:
    score, thr = anomaly.get("score"), anomaly.get("threshold")
    if score is None or thr is None:
        return _clip01(CONF_IDLE_FLOOR + CONF_IDLE_SPAN * 0.5)
    spread = max(abs(float(thr)), 0.01)
    return _clip01(CONF_IDLE_FLOOR + CONF_IDLE_SPAN * min(1.0, max(0.0, (float(thr) - float(score)) / spread)))


def _item(id_: str, source: str, title: str, action: str, href: str,
          severity: float, time_to_harm: float, confidence: float, context: float,
          extra: dict | None = None) -> dict:
    s, t, c, r = _clip01(severity), _clip01(time_to_harm), _clip01(confidence), _clip01(context)
    product = _product(s, t, c, r)
    facts = {"severity": s, "time_to_harm": t, "confidence": c, "context": r, "product": product,
             **(extra or {})}
    return {
        "id": id_, "source": source, "title": title, "action": action, "href": href,
        "score": product, "facts": facts, "why": "",
    }


def collect(snapshot: dict) -> list[dict]:
    items: list[dict] = []
    s = snapshot.get("safety") or {}
    p = snapshot.get("person") or {}
    reasons = set(s.get("reasons") or [])
    level = s.get("level") or "SAFE"
    speed = float(snapshot.get("speed_kmh") or 0.0)
    moving = speed > 0
    dist, ttc = p.get("distance_m"), p.get("ttc_s")
    src = p.get("source") or snapshot.get("person_source") or "slider"
    has_task = bool(snapshot.get("has_task", True))
    ctx_prod = CTX_PROD_ACTIVE_TASK if has_task else CTX_PROD_NO_TASK

    prox_live = bool(reasons & _PROX_REASONS) and level in ("WARNING", "CRITICAL")
    if prox_live:
        crit = level == "CRITICAL"
        items.append(_item(
            "prox", "safety", HEADLINE_PROX,
            "Reduce speed and hold until the person is clear of the travel and swing path.",
            "/safety",
            SEV_PROX_CRIT if crit else SEV_PROX_WARN,
            _tth_from_ttc(ttc),
            CONF_CAMERA if src == "camera" else CONF_SLIDER,
            CTX_PROX,
            {"level": level, "distance_m": dist, "ttc_s": ttc, "person_source": src},
        ))

    unbelted = not snapshot.get("seatbelt", True)
    if unbelted:
        items.append(_item(
            "seatbelt", "safety",
            "Seatbelt unfastened" + (" while moving" if moving else ""),
            "Fasten the seatbelt before the machine travels.",
            "/safety",
            SEV_BELT_MOVING if moving else SEV_BELT_PARKED,
            TTH_BELT_MOVING if moving else TTH_BELT_PARKED,
            CONF_BELT,
            CTX_BELT_MOVING if moving else CTX_BELT_PARKED,
            {"speed_kmh": round(speed, 1), "moving": moving},
        ))

    if "wet_ground" in reasons:
        items.append(_item(
            "wet_ground", "safety",
            f"Wet-ground travel above {safety.V_WET:g} km/h",
            f"Reduce travel speed to {safety.V_WET:g} km/h or below.",
            "/safety",
            SEV_WET, TTH_WET, CONF_WET, CTX_WET,
            {"speed_kmh": round(speed, 1), "limit_kmh": safety.V_WET},
        ))

    a = snapshot.get("anomaly") or {}
    if a.get("flag"):
        cur, base, unit = a.get("current"), a.get("baseline"), a.get("unit") or ""
        label = a.get("label") or a.get("type") or "Anomaly"
        vs = f"{cur:g} {unit} vs usual {base:g} {unit}" if cur is not None and base is not None else label
        items.append(_item(
            "anomaly", "productivity",
            f"Idle anomaly — {vs}",
            "Check why the machine is off-task, then resume work.",
            "/anomaly",
            SEV_IDLE, TTH_IDLE, _idle_confidence(a), ctx_prod,
            {"type": a.get("type"), "current": cur, "baseline": base, "unit": unit},
        ))

    eta = snapshot.get("eta") or {}
    slip = abs(float(eta.get("changed_by") or 0))
    eta_reason = eta.get("reason") or ""
    if slip >= ETA_SLIP_MIN and eta_reason:
        items.append(_item(
            "eta", "productivity",
            f"Task delay — ETA slipped {int(round(slip))} min",
            "Plan has moved out; recover cycle time after the cab is clear.",
            "/dashboard",
            SEV_ETA, TTH_ETA, CONF_ETA, ctx_prod,
            {"changed_by": eta.get("changed_by"), "reason": eta_reason, "task_id": eta.get("task_id")},
        ))

    if prox_live:
        items.append(_item(
            "train_prox", "training",
            "Training nudge — blind-zone awareness",
            "Logged for after this hazard is clear. Do not coach in the cab while a person is in the path.",
            "/training",
            SEV_TRAIN, TTH_TRAIN, CONF_TRAIN, CTX_TRAIN_DURING_PROX,
            {"module": "blind_zone"},
        ))

    return items


def _why(items: list[dict]) -> None:
    if not items:
        return
    top = items[0]
    f = top["facts"]
    top["why"] = (
        f"Product {f['product']:.3f} = severity {f['severity']:.2f} × time-to-harm {f['time_to_harm']:.2f} "
        f"× confidence {f['confidence']:.2f} × context {f['context']:.2f}."
    )
    if len(items) > 1:
        n = items[1]
        top["why"] += f" Ahead of “{n['title']}” ({n['facts']['product']:.3f})."


def rank(snapshot: dict) -> dict:
    items = collect(snapshot)
    items.sort(key=lambda it: (it["score"], it["id"]), reverse=True)
    for i, it in enumerate(items, start=1):
        it["rank"] = i
    _why(items)
    n_quiet = max(0, len(items) - 1)
    headline = items[0] if items else None
    quiet = f"{n_quiet} other item{'s' if n_quiet != 1 else ''} logged, not urgent." if n_quiet else None
    return {
        "items": items,
        "empty": not items,
        "policy": "severity_x_tth_x_confidence_x_context",
        "headline": headline,
        "quiet_count": n_quiet,
        "quiet": quiet,
    }


# ================================================================ planning priority
# Where the weather-aware schedule recommendation and the operator task planner's guidance sit
# relative to safety. A schedule recommendation is advisory (40); anything safety-related always
# outranks it, so the planner can never say "do this now because of weather" while a safety rule is active.
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
