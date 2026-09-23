"""Deterministic safety rule engine — the trust anchor. Never routed through the LLM.

    closing = max(machine_speed_ms + person_approach_ms, MIN_CLOSING_MS)
    ttc     = distance / closing                    # time-to-contact, seconds
    level   = SAFE
    distance < D_WARN or ttc < T_WARN   -> WARNING
    distance < D_CRIT or ttc < T_CRIT   -> CRITICAL
    speed > 0 and not seatbelt          -> at least WARNING ('seatbelt')
    weather == rain and speed > V_WET   -> at least WARNING ('wet_ground')
    weather == heat                     -> notice: hydration break due
"""
from __future__ import annotations

# ============================ CONFIG — every safety threshold lives here ============================
D_WARN = 8.0              # m   person closer than this -> WARNING
D_CRIT = 4.0              # m   person closer than this -> CRITICAL
T_WARN = 4.0              # s   time-to-contact below this -> WARNING
T_CRIT = 2.0              # s   time-to-contact below this -> CRITICAL
V_WET = 1.5               # km/h travel speed limit on wet ground
MIN_CLOSING_MS = 0.1      # m/s floor on closing speed so ttc stays finite
HYDRATION_EVERY_MIN = 60  # min between hydration notices in heat
DOWNGRADE_HOLD_S = 2.0    # s a lower level must persist before the banner steps down (upgrades are instant)
# ===================================================================================================

LEVELS = ["SAFE", "WARNING", "CRITICAL"]

CONSTANTS = {
    "D_WARN": D_WARN, "D_CRIT": D_CRIT, "T_WARN": T_WARN, "T_CRIT": T_CRIT, "V_WET": V_WET,
    "MIN_CLOSING_MS": MIN_CLOSING_MS, "HYDRATION_EVERY_MIN": HYDRATION_EVERY_MIN,
    "DOWNGRADE_HOLD_S": DOWNGRADE_HOLD_S,
}


def evaluate(distance_m: float | None, approach_ms: float, speed_kmh: float, seatbelt: bool,
             weather: str) -> dict:
    """Apply the rules. Returns level, reason codes and a human-readable line per reason."""
    level = 0
    reasons: list[str] = []
    details: list[str] = []
    ttc = closing = None

    if distance_m is not None:
        closing = max(speed_kmh / 3.6 + approach_ms, MIN_CLOSING_MS)
        ttc = distance_m / closing
        if distance_m < D_WARN:
            reasons.append("person_close")
            zone = f"critical zone (< {D_CRIT:g} m)" if distance_m < D_CRIT else f"warning zone (< {D_WARN:g} m)"
            details.append(f"Person {distance_m:.1f} m away — inside the {zone}")
        if ttc < T_WARN:
            reasons.append("ttc_low")
            lim = f"{T_CRIT:g} s critical" if ttc < T_CRIT else f"{T_WARN:g} s warning"
            details.append(f"Time-to-contact {ttc:.1f} s at {closing:.1f} m/s closing — below the {lim} limit")
        if distance_m < D_WARN or ttc < T_WARN:
            level = max(level, 1)
        if distance_m < D_CRIT or ttc < T_CRIT:
            level = max(level, 2)

    if speed_kmh > 0 and not seatbelt:
        level = max(level, 1)
        reasons.append("seatbelt")
        details.append(f"Machine moving at {speed_kmh:.1f} km/h with seatbelt unfastened")

    if weather == "rain" and speed_kmh > V_WET:
        level = max(level, 1)
        reasons.append("wet_ground")
        details.append(f"Travelling {speed_kmh:.1f} km/h on wet ground — above the {V_WET:g} km/h limit")

    return {
        "level": LEVELS[level],
        "reasons": reasons,
        "details": details,
        "ttc_s": None if ttc is None else round(ttc, 1),
        "closing_ms": None if closing is None else round(closing, 2),
    }


class LevelTracker:
    """Applies DOWNGRADE_HOLD_S so camera jitter does not flap the banner. Upgrades are immediate."""

    def __init__(self):
        self.level = "SAFE"
        self._lower_since: float | None = None

    def update(self, raw_level: str, t: float) -> str:
        if LEVELS.index(raw_level) >= LEVELS.index(self.level):
            self.level = raw_level
            self._lower_since = None
        else:
            if self._lower_since is None:
                self._lower_since = t
            if t - self._lower_since >= DOWNGRADE_HOLD_S:
                self.level = raw_level
                self._lower_since = None
        return self.level
