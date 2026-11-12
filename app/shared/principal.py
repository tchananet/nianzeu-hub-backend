from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastapi import Request

from app.shared.errors import AppError


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    session_id: UUID


class PrincipalResolver(Protocol):
    def __call__(self, request: Request) -> Principal: ...


def require_principal(request: Request) -> Principal:
    """Override this dependency with I01's resolver when assembling the application."""
    raise AppError("AUTH_REQUIRED", 401, "Authentication required")
