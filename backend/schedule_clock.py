"""Maps the live shift onto the manager's published schedule — read-only, never reorders anything.

Published windows are on the SCHEDULE clock (e.g. T4 09:00–10:34). The demo machine moves the synthetic
tonnage faster than the manager's day-scale planning estimates, so comparing the live clock directly
with published times would make every task look hours early. Instead each published window of this
operator is laid onto the live shift, in published order, with a length equal to the ETA model's
expected duration for that task (x the manager planner's weather factor for its window). Gaps between
published windows keep their share at the plan's overall ratio.

That gives a LIVE REFERENCE: where the operator would be if the shift ran exactly to the published
plan at the ETA model's expected pace. Early/late, time-to-next-task and "rain in N min" are measured
against it. All times here are minutes; live minutes count from the live shift start.
"""
from __future__ import annotations


class ScheduleClock:
    def __init__(self, tasks: list[dict], live_expected: dict[str, float], plan_start: float):
        """tasks: published entries (task_id, start_min, end_min) in published order."""
        plan_total = sum(max(t["end_min"] - t["start_min"], 0.0) for t in tasks)
        live_total = sum(live_expected.get(t["task_id"], 0.0) for t in tasks)
        # live minutes per schedule minute (e.g. 0.25 -> one live minute covers four schedule minutes)
        self.k = live_total / plan_total if plan_total > 0 and live_total > 0 else 1.0
        self.plan_start = float(plan_start)
        self.segments: list[dict] = []
        self._by_task: dict[str, dict] = {}
        plan_c, live_c = self.plan_start, 0.0
        for t in tasks:
            if t["start_min"] > plan_c:
                gap = t["start_min"] - plan_c
                self.segments.append({"task_id": None, "plan_s": plan_c, "plan_e": t["start_min"],
                                      "live_s": live_c, "live_e": live_c + gap * self.k})
                plan_c, live_c = t["start_min"], live_c + gap * self.k
            dur = live_expected.get(t["task_id"]) or max(t["end_min"] - t["start_min"], 1.0) * self.k
            seg = {"task_id": t["task_id"], "plan_s": max(t["start_min"], plan_c), "plan_e": max(t["end_min"], plan_c),
                   "live_s": live_c, "live_e": live_c + dur}
            self.segments.append(seg)
            self._by_task[t["task_id"]] = seg
            plan_c, live_c = seg["plan_e"], seg["live_e"]
        self.plan_end, self.live_end = plan_c, live_c

    @property
    def compression(self) -> float:
        """Schedule minutes per live minute (shown to the operator as a demo time scale)."""
        return 1.0 / self.k if self.k else 1.0

    def window(self, task_id: str) -> tuple[float, float] | None:
        s = self._by_task.get(task_id)
        return (s["live_s"], s["live_e"]) if s else None

    def to_plan(self, live: float) -> float:
        for s in self.segments:
            if s["live_s"] <= live < s["live_e"]:
                f = (live - s["live_s"]) / (s["live_e"] - s["live_s"])
                return s["plan_s"] + f * (s["plan_e"] - s["plan_s"])
        if live < 0 or not self.segments:
            return self.plan_start + live / self.k
        return self.plan_end + (live - self.live_end) / self.k

    def to_live(self, plan: float) -> float:
        for s in self.segments:
            if s["plan_s"] <= plan < s["plan_e"]:
                f = (plan - s["plan_s"]) / (s["plan_e"] - s["plan_s"])
                return s["live_s"] + f * (s["live_e"] - s["live_s"])
        if plan < self.plan_start or not self.segments:
            return (plan - self.plan_start) * self.k
        return self.live_end + (plan - self.plan_end) * self.k
