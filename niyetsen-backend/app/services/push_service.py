"""Expo Push delivery; scheduling and consent stay outside this transport."""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
TOKEN_PATTERN = re.compile(r"^(Expo(nent)?PushToken)\[[A-Za-z0-9_-]+\]$")


@dataclass(frozen=True)
class PushMessage:
    token: str
    title: str
    body: str
    data: dict[str, str]


def is_valid_expo_token(token: str) -> bool:
    return bool(TOKEN_PATTERN.fullmatch((token or "").strip()))


def emotional_penalty_body(streak_len: int) -> str:
    if streak_len > 0:
        return (
            f"{streak_len} günlük zincirin seni bekliyor. "
            "Yarın en küçük halkayla yeniden tutunabilirsin."
        )
    return "Bugün eksik kaldı; yarın yeni bir halka için yeniden başlayabilirsin."


def send(messages: list[PushMessage], timeout: float = 15) -> list[dict]:
    payload = [
        {
            "to": message.token,
            "title": message.title,
            "body": message.body,
            "data": message.data,
            "sound": "default",
        }
        for message in messages
        if is_valid_expo_token(message.token)
    ]
    if not payload:
        return []
    response = httpx.post(
        EXPO_PUSH_URL,
        json=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    data = body.get("data", [])
    return data if isinstance(data, list) else [data]
