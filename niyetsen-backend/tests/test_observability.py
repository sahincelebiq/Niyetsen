"""Sentry no-op ve KVKK temizliği. Ağ çağrısı yok."""
from app.core.observability import _before_send, capture_exception, init_observability


def test_init_without_dsn_is_noop(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SENTRY_DSN", "")
    init_observability()
    capture_exception(RuntimeError("olmamalı"), step="test")


def test_before_send_drops_body_and_masks_pii():
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signatureX"
    padded = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiJ1c2VyIn0.signatureX="
    )
    event = {
        "message": f"kullanici kullanici@ornek.com token={token}",
        "extra": {"note": padded},
        "request": {
            "url": f"https://api.niyetsen.com/chat?access_token={token}",
            "data": "sohbet metni burada",
            "cookies": "session=secret",
            "query_string": "access_token=abc",
            "headers": {
                "Authorization": f"Bearer {token}",
                "Cookie": "session=secret",
                "X-Request-Id": "istek-1",
                "User-Agent": "Niyetsen",
                "Content-Type": "application/json",
            },
        },
        "spans": [{
            "data": {
                "url.full": f"https://api.niyetsen.com/chat?access_token={token}",
                "http.query": f"access_token={token}",
                "http.method": "POST",
            },
        }],
    }

    cleaned = _before_send(event, {})

    assert cleaned is not None
    request = cleaned["request"]
    assert "data" not in request
    assert "cookies" not in request
    assert "query_string" not in request
    assert request["url"] == "https://api.niyetsen.com/chat"
    assert set(request["headers"]) == {
        "X-Request-Id",
        "User-Agent",
        "Content-Type",
    }
    assert "kullanici@ornek.com" not in cleaned["message"]
    assert "[e-posta]" in cleaned["message"]
    assert token not in cleaned["message"]
    assert "[token]" in cleaned["message"]
    assert cleaned["extra"]["note"] == "[token]"
    span = cleaned["spans"][0]["data"]
    assert "http.query" not in span
    assert span["url.full"] == "https://api.niyetsen.com/chat"
    assert token not in span["url.full"]


def test_before_send_filters_header_lists():
    event = {
        "request": {
            "headers": [
                ["Authorization", "Bearer secret"],
                ["Cookie", "session=secret"],
                ["X-Request-Id", "istek-1"],
                ["User-Agent", "Niyetsen"],
                ["Content-Type", "application/json"],
            ],
        },
    }

    cleaned = _before_send(event, {})

    assert cleaned is not None
    names = [item[0] for item in cleaned["request"]["headers"]]
    assert names == ["X-Request-Id", "User-Agent", "Content-Type"]


def test_transactions_use_the_same_scrubber(monkeypatch):
    import sentry_sdk

    from app.config import settings
    from app.core import observability

    captured: dict = {}

    def fake_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(observability, "_initialized", False)
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://public@example.ingest.sentry.io/1")
    monkeypatch.setattr(sentry_sdk, "init", fake_init)
    observability.init_observability()

    assert captured["before_send"] is observability._before_send
    assert captured["before_send_transaction"] is observability._before_send
    assert captured["send_default_pii"] is False
    assert captured["include_local_variables"] is False
    assert captured["max_request_body_size"] == "never"
    logging = next(
        item for item in captured["integrations"]
        if item.identifier == "logging"
    )
    assert logging._handler is None
