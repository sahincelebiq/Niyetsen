from app.services import push_service


def test_push_token_validation():
    assert push_service.is_valid_expo_token("ExpoPushToken[abc_123-xyz]")
    assert push_service.is_valid_expo_token("ExponentPushToken[abc123]")
    assert not push_service.is_valid_expo_token("https://example.com")
    assert not push_service.is_valid_expo_token("")


def test_penalty_copy_uses_loss_without_blame():
    copy = push_service.emotional_penalty_body(23)
    assert "23 günlük zincirin" in copy
    assert "yine" not in copy.casefold()
    assert "tembel" not in copy.casefold()


def test_send_filters_tokens_and_posts_batch(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"status": "ok"}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr(push_service.httpx, "post", fake_post)
    result = push_service.send([
        push_service.PushMessage(
            token="ExpoPushToken[valid]",
            title="Niyetsen",
            body="Halkan seni bekliyor.",
            data={"url": "/daily"},
        ),
        push_service.PushMessage(
            token="invalid",
            title="ignored",
            body="ignored",
            data={},
        ),
    ])
    assert result == [{"status": "ok"}]
    assert captured["url"] == push_service.EXPO_PUSH_URL
    assert len(captured["json"]) == 1
