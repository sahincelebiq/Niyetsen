"""Niyetsen — merkezi HTTP rate limiter."""
from __future__ import annotations

import hashlib

from fastapi import Request
from slowapi import Limiter


def _identity(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization:
        return hashlib.sha256(authorization.encode()).hexdigest()
    user_id = request.headers.get("x-user-id")
    if user_id:
        return f"dev:{user_id}"
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_identity)
