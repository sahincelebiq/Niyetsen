"""Niyetsen — merkezi HTTP rate limiter."""
from __future__ import annotations

import hashlib

import jwt
from fastapi import Request
from slowapi import Limiter


def _identity(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            # Authentication is still performed by get_current_user. Reading the
            # unverified sub here only keeps refreshed JWTs in one user bucket.
            subject = jwt.decode(
                token, options={"verify_signature": False}
            ).get("sub")
            if subject:
                return f"user:{subject}"
        except jwt.PyJWTError:
            pass
        return f"token:{hashlib.sha256(token.encode()).hexdigest()}"
    user_id = request.headers.get("x-user-id")
    if user_id:
        return f"dev:{user_id}"
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_identity)
