"""Explanation layer. The LLM only *explains* — severity always comes from safety.py.

explain(ctx) tries Claude with a short timeout and falls back instantly to a string template built
from the same JSON on any failure, timeout, refusal, or if the reply contains a number that is not
in the facts.
"""
from __future__ import annotations

import json
import os
import re

import safety

# ================= CONFIG =================
LLM_MODEL = os.environ.get("COPILOT_LLM_MODEL", "claude-opus-5")
LLM_TIMEOUT_S = 6.0
# ==========================================

SYSTEM_PROMPT = """You explain machine-safety and productivity events to a heavy-equipment operator.
Use ONLY the facts in the JSON. Do not invent numbers. 3 short sentences max.
State the action first."""

try:
    import anthropic
    _client = anthropic.Anthropic(timeout=LLM_TIMEOUT_S, max_retries=0) if (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")) else None
except Exception:  # pragma: no cover
    _client = None


def llm_available() -> bool:
    return _client is not None


def build_context(state: dict) -> dict:
    """Facts JSON sent to the LLM / template — only computed values, nothing invented."""
    s, p, a, e = state["safety"], state["person"], state["anomaly"], state["eta"]
    ctx = {"risk": s["level"], "reasons": s["reasons"]}
    if p.get("detected") and p.get("distance_m") is not None:
        ctx["distance_m"] = p["distance_m"]
        if p.get("ttc_s") is not None and p["ttc_s"] < 60:
            ctx["ttc_s"] = p["ttc_s"]
    if "seatbelt" in s["reasons"] or "wet_ground" in s["reasons"]:
        ctx["speed_kmh"] = state["speed_kmh"]
    if state["weather"] != "clear":
        ctx["weather"] = state["weather"]
    if a.get("flag"):
        ctx["anomaly"] = a["type"]
        if a["type"] == "excess_idle":
            ctx["idle_min"] = round(a["current"])
            ctx["baseline_idle_min"] = round(a["baseline"])
        else:
            ctx["anomaly_current"] = a["current"]
            ctx["anomaly_baseline"] = a["baseline"]
            ctx["anomaly_unit"] = a["unit"]
    if e and e.get("changed_by"):
        ctx["eta_change_min"] = e["changed_by"]
        if e.get("reason"):
            ctx["eta_change_reason"] = e["reason"]
    ctx["limits"] = {"warn_distance_m": safety.D_WARN, "critical_distance_m": safety.D_CRIT,
                     "warn_ttc_s": safety.T_WARN, "critical_ttc_s": safety.T_CRIT,
                     "wet_speed_limit_kmh": safety.V_WET}
    return ctx


def _n(x: float) -> str:
    return f"{x:g}" if isinstance(x, (int, float)) and float(x).is_integer() else f"{x:.1f}"


def template_explain(ctx: dict) -> str:
    risk, reasons = ctx.get("risk", "SAFE"), ctx.get("reasons", [])
    lim = ctx.get("limits", {})
    out: list[str] = []
    d, ttc = ctx.get("distance_m"), ctx.get("ttc_s")
    if risk == "CRITICAL" and ("person_close" in reasons or "ttc_low" in reasons):
        tail = f", about {_n(ttc)} s to contact" if ttc is not None else ""
        out.append(f"Stop all movement now — a person is {_n(d)} m from the machine{tail}.")
    elif "person_close" in reasons or "ttc_low" in reasons:
        out.append(f"Slow down and locate the person — they are {_n(d)} m away, inside the "
                   f"{_n(lim.get('warn_distance_m', safety.D_WARN))} m warning zone.")
    if "seatbelt" in reasons:
        out.append(f"Fasten your seatbelt — the machine is moving at {_n(ctx.get('speed_kmh', 0))} km/h unbelted.")
    if "wet_ground" in reasons:
        out.append(f"Reduce travel speed — {_n(ctx.get('speed_kmh', 0))} km/h is above the "
                   f"{_n(lim.get('wet_speed_limit_kmh', safety.V_WET))} km/h wet-ground limit.")
    an = ctx.get("anomaly")
    if an == "excess_idle":
        s = (f"Idle has run {ctx['idle_min']} min against your usual {ctx['baseline_idle_min']} min"
             " — check whether a truck, obstruction or delay is holding you up.")
        out.append(("Check why the machine is idle. " if not out else "") + s)
    elif an:
        out.append(f"Unusual {an.replace('_', ' ')}: {_n(ctx['anomaly_current'])} {ctx['anomaly_unit']} "
                   f"against your usual {_n(ctx['anomaly_baseline'])} {ctx['anomaly_unit']}.")
    if ctx.get("eta_change_min"):
        ch = ctx["eta_change_min"]
        out.append(f"Task ETA has moved {'+' if ch > 0 else ''}{_n(ch)} min.")
    if not out:
        out.append("No action needed — all safety rules are clear and nothing unusual is detected.")
    return " ".join(out[:3])


def _numbers(text: str) -> set[float]:
    return {float(m) for m in re.findall(r"\d+(?:\.\d+)?", text)}


def _allowed_numbers(ctx) -> set[float]:
    vals: set[float] = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            vals.update({float(v), float(round(v)), round(float(v), 1), abs(float(v))})
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            vals.update(_numbers(v))
    walk(ctx)
    return vals | {1.0, 2.0, 3.0}


def explain(ctx: dict) -> dict:
    template = template_explain(ctx)
    if _client is None:
        return {"text": template, "source": "template", "note": "No LLM API key configured"}
    try:
        resp = _client.messages.create(
            model=LLM_MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(ctx)}],
        )
        if resp.stop_reason == "refusal":
            return {"text": template, "source": "template", "note": "LLM declined"}
        text = " ".join(b.text for b in resp.content if b.type == "text").strip()
        if not text:
            raise ValueError("empty response")
        if not _numbers(text) <= _allowed_numbers(ctx):
            return {"text": template, "source": "template", "note": "LLM reply cited a number not in the facts"}
        return {"text": text, "source": "llm", "model": LLM_MODEL}
    except Exception as exc:
        return {"text": template, "source": "template", "note": f"LLM unavailable ({type(exc).__name__})"}
