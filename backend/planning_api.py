"""REST endpoints for the weather-aware planner. Role checks go through roles.py (demo only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from planning_store import PlanningError
from roles import User, current_user, require_manager
from simulator import OPERATORS


class ScenarioIn(BaseModel):
    scenario: str


class AssignIn(BaseModel):
    task_id: str
    operator_id: str | None = None
    machine_id: str | None = None


class OverrideIn(BaseModel):
    task_id: str
    move: str | None = None      # "up" | "down"
    start: str | None = None     # "HH:MM" pinned start
    clear: bool = False


def create_router(engine) -> APIRouter:
    svc = engine.planning
    r = APIRouter(prefix="/api")

    def call(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except PlanningError as e:
            raise HTTPException(e.status, {"message": str(e), **(e.detail or {})} if e.detail else str(e)) from None

    # ---- forecast (any signed-in role) ----
    @r.get("/weather/forecast")
    def get_forecast(user: User = Depends(current_user)):
        return svc.forecast()

    @r.post("/weather/scenario")
    def post_scenario(body: ScenarioIn, user: User = Depends(require_manager)):
        call(svc.set_scenario, body.scenario, user)
        return svc.view()

    # ---- manager planner ----
    @r.get("/planner")
    def get_planner(user: User = Depends(require_manager)):
        return svc.view()

    @r.post("/planner/tasks")
    def post_task(body: dict, user: User = Depends(require_manager)):
        call(svc.create_task, body, user)
        return svc.view()

    @r.put("/planner/tasks/{task_id}")
    def put_task(task_id: str, body: dict, user: User = Depends(require_manager)):
        call(svc.update_task, task_id, body, user)
        return svc.view()

    @r.delete("/planner/tasks/{task_id}")
    def delete_task(task_id: str, user: User = Depends(require_manager)):
        call(svc.delete_task, task_id, user)
        return svc.view()

    @r.post("/planner/assign")
    def post_assign(body: AssignIn, user: User = Depends(require_manager)):
        call(svc.assign, body.task_id, body.operator_id, body.machine_id, user)
        return svc.view()

    @r.post("/planner/recommend")
    def post_recommend(user: User = Depends(require_manager)):
        return call(svc.recommend, user)

    @r.post("/planner/replan")
    def post_replan(user: User = Depends(require_manager)):
        return call(svc.recommend, user, replan=True)

    @r.post("/planner/override")
    def post_override(body: OverrideIn, user: User = Depends(require_manager)):
        return call(svc.override, body.task_id, user, move=body.move, start=body.start, clear=body.clear)

    @r.post("/planner/accept")
    def post_accept(user: User = Depends(require_manager)):
        return call(svc.accept, user)

    @r.post("/planner/publish")
    def post_publish(user: User = Depends(require_manager)):
        return call(svc.publish, user)

    @r.post("/planner/reset")
    def post_reset(user: User = Depends(require_manager)):
        return call(svc.reset, user)

    # ---- operator ----
    @r.get("/operator/schedule")
    def get_operator_schedule(operator_id: str | None = None, user: User = Depends(current_user)):
        if user.role == "operator":
            if operator_id and operator_id != user.id:
                raise HTTPException(403, "Operators can only view their own schedule")
            operator_id = user.id
        elif operator_id is None:
            raise HTTPException(400, "operator_id is required for managers")
        if operator_id not in OPERATORS:
            raise HTTPException(404, f"Unknown operator {operator_id}")
        return svc.operator_schedule(operator_id)

    @r.post("/operator/schedule/ack")
    def post_ack(user: User = Depends(current_user)):
        if user.role != "operator":
            raise HTTPException(403, "Only the assigned operator can acknowledge a schedule")
        return call(svc.acknowledge, user.id)

    return r
