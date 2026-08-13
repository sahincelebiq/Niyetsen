"""Canlı 500'lerin kök nedenleri: timestamptz str, jsonb dict, slot yarışı."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.core.datetimes import coerce_datetime
from app.main import app
from app.storage.db_coerce import is_unique_violation, parse_json_object
from app.storage.repository import repo

client = TestClient(app)


def test_coerce_datetime_accepts_z_and_naive() -> None:
    zulu = coerce_datetime("2026-08-10T08:00:00Z")
    assert zulu is not None and zulu.tzinfo is not None
    naive = coerce_datetime(datetime(2026, 8, 10, 8, 0))
    assert naive is not None and naive.tzinfo is timezone.utc
    assert coerce_datetime(None) is None
    assert coerce_datetime("not-a-date") is None
    as_date = coerce_datetime(date(2026, 8, 10))
    assert as_date == datetime(2026, 8, 10, tzinfo=timezone.utc)


def test_parse_json_object_accepts_dict_and_string() -> None:
    """jsonb PostgREST'ten dict gelir; json.loads(dict) TypeError atıyordu."""
    assert parse_json_object({"cards": [{"name": "Yıldız"}]})["cards"][0]["name"] == "Yıldız"
    assert parse_json_object('{"interpretation": "ayna"}')["interpretation"] == "ayna"
    assert parse_json_object(None) == {}
    assert parse_json_object([1, 2]) == {}


def test_unique_violation_detects_postgres_23505() -> None:
    class Fake(Exception):
        code = "23505"

    assert is_unique_violation(Fake("duplicate"))
    assert is_unique_violation(
        Exception('duplicate key value violates unique constraint "plans_user_slot_idx"')
    )
    assert not is_unique_violation(Exception("connection reset"))


def test_duplicate_slot_create_is_idempotent_and_session_ok() -> None:
    user = "slot-race-user"
    first = repo.create_draft_plan(user, name="Plan 1", slot_no=1)
    second = repo.create_draft_plan(user, name="Plan 1", slot_no=1)
    assert first == second
    res = client.get("/chat/session", headers={"X-User-Id": user})
    assert res.status_code == 200
    assert res.json()["active_plan_name"]
