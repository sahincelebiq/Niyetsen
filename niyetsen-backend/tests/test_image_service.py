from app.config import settings
from app.services import image_service


class FakeResponse:
    def __init__(self, results):
        self._results = results

    def raise_for_status(self):
        return None

    def json(self):
        return {"results": self._results}


def _result(index: int) -> dict:
    return {
        "urls": {"regular": f"https://images.unsplash.com/photo-{index}?ixid=x"},
        "user": {"name": f"Fotoğrafçı {index}"},
        "links": {"html": f"https://unsplash.com/photos/{index}"},
    }


def test_normalize_image_query_handles_turkish_and_punctuation():
    assert image_service.normalize_image_query("İstanbul'da yürüyüş!") == (
        "istanbul da yuruyus"
    )


def test_result_pick_is_deterministic():
    results = [_result(index) for index in range(5)]
    first = image_service._pick_result(results, "morning yoga mat")
    second = image_service._pick_result(results, "morning yoga mat")
    assert first == second


def test_unsplash_result_has_crop_quality_and_attribution(monkeypatch):
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "test-key")
    monkeypatch.setattr(
        image_service.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse([_result(1)]),
    )

    image = image_service.get_image("morning yoga mat", categories=["İrade"])
    assert "w=800&h=600&fit=crop&q=82" in image.url
    assert image.attribution == "Photo by Fotoğrafçı 1 on Unsplash"
    assert "utm_source=niyetsen" in image.attribution_url
    assert image.source == "unsplash"


def test_empty_search_uses_category_fallback(monkeypatch):
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "test-key")
    queries = []

    def fake_get(*args, **kwargs):
        query = kwargs["params"]["query"]
        queries.append(query)
        return FakeResponse([] if query == "too abstract" else [_result(2)])

    monkeypatch.setattr(image_service.httpx, "get", fake_get)
    image = image_service.get_image("too abstract", categories=["Sosyallik"])

    assert queries == ["too abstract", "friends meeting cafe"]
    assert image.source == "category_fallback"


def test_compose_image_query_merges_city_and_interest():
    query = image_service.compose_image_query(
        "morning walk",
        title="Sabah yürüyüşü",
        city="İstanbul",
        interests=["koşu", "kahve"],
        categories=["İrade"],
    )
    assert "morning walk" in query
    assert "istanbul" in query


def test_enrich_image_keywords_batch_falls_back_without_gemini(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    items = [("Sabah yürüyüşü", "morning walk", ["İrade"])]
    import asyncio

    result = asyncio.run(
        image_service.enrich_image_keywords_batch(
            items,
            city="İstanbul",
            interests=["koşu"],
        )
    )
    assert len(result) == 1
    assert "istanbul" in result[0]


def test_missing_key_uses_deterministic_placeholder(monkeypatch):
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "")
    first = image_service.get_image("", categories=["Disiplin"])
    second = image_service.get_image("", categories=["Disiplin"])
    assert first.source == "placeholder"
    assert first.url == second.url
    assert "focusedstudydesk" in first.url
