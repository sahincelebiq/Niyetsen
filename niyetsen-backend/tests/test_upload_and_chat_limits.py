from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.main import app
from app.models.schemas import ChatMessage, ChatRequest
from app.services import proof_service

client = TestClient(app)


def _jpeg_with_exif() -> bytes:
    payload = b"Exif\x00\x00GPSFAKE"
    app1 = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload
    return b"\xff\xd8" + app1 + b"\xff\xda" + (b"\x00" * 200)


def test_jpeg_exif_gps_is_stripped_before_vision():
    raw = _jpeg_with_exif()
    assert b"GPSFAKE" in raw
    cleaned = proof_service.prepare_upload(raw, "image/jpeg")
    assert cleaned.startswith(b"\xff\xd8")
    assert b"GPSFAKE" not in cleaned
    assert b"Exif" not in cleaned


def test_png_prepare_upload_keeps_signature():
    png = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 200)
    assert proof_service.prepare_upload(png, "image/png") == png


def test_chat_message_rejects_over_4000_chars():
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="x" * 4001)


def test_chat_request_rejects_more_than_40_messages():
    with pytest.raises(ValidationError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hi") for _ in range(41)]
        )


def test_chat_endpoint_returns_422_for_oversized_content():
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "x" * 4001}]},
        headers={"X-User-Id": "limit-user"},
    )
    assert response.status_code == 422
