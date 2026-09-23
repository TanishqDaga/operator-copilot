"""Read-only endpoint for the Operator Task Planner. Operators see only their own guidance."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from roles import User, current_user
from simulator import OPERATORS


def create_router(engine) -> APIRouter:
    r = APIRouter(prefix="/api")

    @r.get("/operator/planner")
    def get_operator_planner(operator_id: str | None = None, user: User = Depends(current_user)):
        if user.role == "operator":
            if operator_id and operator_id != user.id:
                raise HTTPException(403, "Operators can only view their own task planner")
            operator_id = user.id
        elif operator_id is None:
            raise HTTPException(400, "operator_id is required for managers")
        if operator_id not in OPERATORS:
            raise HTTPException(404, f"Unknown operator {operator_id}")
        return engine.operator.view(operator_id)

    return r
