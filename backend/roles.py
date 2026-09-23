"""Demo role abstraction — NOT real security.

The frontend keeps a prototype session in localStorage and sends it as two headers:
    X-Demo-Role: manager | operator
    X-Demo-User: MGR-01 | OP-104 | ...
Anyone can set these headers. Endpoints only depend on `current_user` / `require_manager`, so a real
auth provider (session cookie, OIDC, JWT) can replace this module without touching the routes.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from simulator import OPERATORS

MANAGERS = {"MGR-01": {"name": "J. Okafor", "title": "Site manager (demo)"}}
ROLES = ("manager", "operator")


@dataclass(frozen=True)
class User:
    id: str
    role: str
    name: str


def current_user(x_demo_role: str | None = Header(None), x_demo_user: str | None = Header(None)) -> User:
    if x_demo_role not in ROLES:
        raise HTTPException(401, "Sign in first (demo session: choose Manager or Operator on /login)")
    if x_demo_role == "manager":
        uid = x_demo_user if x_demo_user in MANAGERS else "MGR-01"
        return User(uid, "manager", MANAGERS[uid]["name"])
    if x_demo_user not in OPERATORS:
        raise HTTPException(401, f"Unknown operator {x_demo_user!r}")
    return User(x_demo_user, "operator", OPERATORS[x_demo_user]["name"])


def require_manager(user: User = Depends(current_user)) -> User:
    if user.role != "manager":
        raise HTTPException(403, "Manager role required — operators can view their schedule but not edit the plan")
    return user
