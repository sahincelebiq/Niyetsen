from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.gemini_client import GeminiUnavailable
from app.main import app
from app.models.schemas import (
    GameState, Plan, PlanDay, ProofResult, Task, UserProfile,
)
from app.services import proof_service, task_lifecycle_service
from app.services import consent_service
from app.models.schemas import ConsentChoice, ConsentUpdate
from app.storage.repository import InMemoryRepository, repo

client = TestClient(app)


def _image(mime_type: str = "image/png") -> bytes:
    signature = b"\x89PNG\r\n\x1a\n" if mime_type == "image/png" else b"\xff\xd8\xff"
    return signature + (b"\0" * 200)


def _plan(task_id: str, task_date: date, categories: list[str] | None = None) -> Plan:
    return Plan(
        id=f"plan-{task_id}",
        duration_days=1,
        batch_generated_until=1,
        start_date=task_date,
        days=[
            PlanDay(
                day=1,
                tasks=[
                    Task(
                        id=task_id,
                        day=1,
                        title="20 dakika yürüyüş",
                        categories=categories or ["İrade"],
                        date=task_date,
                    )
                ],
            )
        ],
    )


def _allow_proof(user_id: str) -> None:
    consent_service.update(repo, user_id, ConsentUpdate(
        privacy_policy=ConsentChoice(accepted=True),
        kvkk_explicit_consent=ConsentChoice(accepted=True),
        proof_photo_processing=ConsentChoice(accepted=True),
    ))


@pytest.mark.parametrize(
    ("content", "mime_type"),
    [
        (_image(), "image/gif"),
        (b"not-a-real-png" + b"\0" * 200, "image/png"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
    ],
)
def test_proof_upload_rejects_type_signature_and_tiny_files(content, mime_type):
    user_id = f"invalid-proof-{mime_type.replace('/', '-')}-{len(content)}"
    repo.save_plan(user_id, _plan(f"task-{user_id}", date.today()))
    _allow_proof(user_id)
    response = client.post(
        f"/task/task-{user_id}/proof",
        files={"photo": ("proof.png", content, mime_type)},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 400
    assert repo.get_proof_attempts(user_id, f"task-{user_id}") == 0


def test_proof_route_is_ownership_safe():
    owner = "proof-owner"
    repo.save_plan(owner, _plan("private-task", date.today()))
    _allow_proof("proof-attacker")
    response = client.post(
        "/task/private-task/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers={"X-User-Id": "proof-attacker"},
    )
    assert response.status_code == 404
    assert repo.get_proof_attempts(owner, "private-task") == 0


def test_proof_upload_rejects_more_than_five_megabytes():
    user_id = "oversize-proof-user"
    task_id = "oversize-task"
    repo.save_plan(user_id, _plan(task_id, date.today()))
    _allow_proof(user_id)
    content = b"\x89PNG\r\n\x1a\n" + b"\0" * settings.PROOF_MAX_BYTES
    response = client.post(
        f"/task/{task_id}/proof",
        files={"photo": ("proof.png", content, "image/png")},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 400
    assert repo.get_proof_attempts(user_id, task_id) == 0


def test_invalid_location_does_not_consume_proof_attempt():
    user_id = "invalid-location-user"
    task_id = "invalid-location-task"
    repo.save_plan(user_id, _plan(task_id, date.today()))
    _allow_proof(user_id)
    response = client.post(
        f"/task/{task_id}/proof",
        data={"has_location": "true", "latitude": "91", "longitude": "29"},
        files={"photo": ("proof.png", _image(), "image/png")},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 422
    assert repo.get_proof_attempts(user_id, task_id) == 0


def test_third_proof_attempt_is_accepted_without_vision(monkeypatch):
    async def vision_should_not_run(**_kwargs):
        raise AssertionError("Vision üçüncü denemede çağrılmamalı")

    monkeypatch.setattr(proof_service, "generate_json_with_image", vision_should_not_run)
    result = asyncio.run(
        proof_service.evaluate_proof(
            task_title="Yürüyüş",
            image_bytes=_image(),
            mime_type="image/png",
            attempt_no=3,
        )
    )
    assert result.approved is True
    assert result.accepted_by_declaration is True
    assert result.confidence == 60


def test_rejected_proof_is_not_persisted_or_scored(monkeypatch):
    user_id = "rejected-proof-user"
    repo.save_plan(user_id, _plan("rejected-task", date.today()))
    _allow_proof(user_id)

    async def reject(**_kwargs):
        return ProofResult(
            approved=False,
            confidence=25,
            reason="Bir kare daha dener misin?",
            attempt_no=1,
        )

    monkeypatch.setattr(proof_service, "evaluate_proof", reject)
    response = client.post(
        "/task/rejected-task/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 200
    assert response.json()["approved"] is False
    proofs = repo.get_proofs(user_id, "rejected-task")
    assert proofs == []
    assert response.json()["photo_url"] is None
    assert repo.get_task(user_id, "rejected-task").status == "pending"
    assert repo.get_point_log(user_id) == []


def test_approved_proof_persists_task_points_and_event(monkeypatch):
    user_id = "approved-proof-user"
    repo.save_plan(user_id, _plan("approved-task", date.today(), ["İrade", "Disiplin"]))
    _allow_proof(user_id)

    async def approve(**_kwargs):
        return ProofResult(
            approved=True,
            confidence=88,
            reason="Onaylandı",
            attempt_no=1,
        )

    monkeypatch.setattr(proof_service, "evaluate_proof", approve)
    response = client.post(
        "/task/approved-task/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 200
    body = response.json()
    task = repo.get_task(user_id, "approved-task")
    assert task.status == "done"
    assert task.proof_id == body["proof_id"]
    assert repo.get_state(user_id).points["İrade"] == 50
    events = repo.get_point_log(user_id)
    assert [(event.category, event.delta, event.task_id) for event in events] == [
        ("İrade", 50, "approved-task"),
        ("Disiplin", 50, "approved-task"),
    ]


def test_gemini_unavailable_does_not_approve_persist_or_consume_attempt(monkeypatch):
    user_id = "proof-gemini-down"
    task_id = "proof-gemini-down-task"
    repo.save_plan(user_id, _plan(task_id, date.today()))
    _allow_proof(user_id)

    async def unavailable(**_kwargs):
        raise GeminiUnavailable("down")

    monkeypatch.setattr(proof_service, "evaluate_proof", unavailable)
    response = client.post(
        f"/task/{task_id}/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 503
    assert repo.get_task(user_id, task_id).status == "pending"
    assert repo.get_proof_attempts(user_id, task_id) == 0
    assert repo.get_proofs(user_id, task_id) == []
    assert repo.get_point_log(user_id) == []


def test_gemini_image_error_returns_400_without_consuming_attempt(monkeypatch):
    user_id = "proof-gemini-image"
    task_id = "proof-gemini-image-task"
    repo.save_plan(user_id, _plan(task_id, date.today()))
    _allow_proof(user_id)

    async def bad_image(**_kwargs):
        raise proof_service.ProofRejected(
            "Fotoğraf okunamadı veya işlenemedi. Yeni bir kare çekip tekrar dener misin?"
        )

    monkeypatch.setattr(proof_service, "evaluate_proof", bad_image)
    response = client.post(
        f"/task/{task_id}/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 400
    assert "Fotoğraf okunamadı" in response.json()["detail"]
    assert repo.get_proof_attempts(user_id, task_id) == 0


def test_proof_idempotency_key_returns_cached_result_without_double_points(monkeypatch):
    user_id = "proof-idempotent"
    task_id = "proof-idempotent-task"
    repo.save_plan(user_id, _plan(task_id, date.today()))
    _allow_proof(user_id)

    async def approve(**_kwargs):
        return ProofResult(
            approved=True, confidence=90, reason="Onaylandı", attempt_no=1
        )

    monkeypatch.setattr(proof_service, "evaluate_proof", approve)
    headers = {
        "X-User-Id": user_id,
        "X-Idempotency-Key": "camera-capture-1",
    }
    first = client.post(
        f"/task/{task_id}/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers=headers,
    )
    second = client.post(
        f"/task/{task_id}/proof",
        files={"photo": ("proof.png", _image(), "image/png")},
        headers=headers,
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert repo.get_state(user_id).points["İrade"] == 50
    assert len(repo.get_proofs(user_id, task_id)) == 1
    assert len(repo.get_point_log(user_id)) == 1


def test_proof_claim_blocks_concurrent_different_requests():
    repository = InMemoryRepository()
    user_id = "proof-concurrent"
    task_id = "proof-concurrent-task"
    repository.save_plan(user_id, _plan(task_id, date.today()))
    first = repository.begin_proof_attempt(user_id, task_id, "capture-1")
    second = repository.begin_proof_attempt(user_id, task_id, "capture-2")
    assert first.status == "started"
    assert second.status == "in_progress"
    assert first.attempt_no == second.attempt_no == 1


def test_excuse_persists_floor_adjusted_event():
    user_id = "excuse-event-user"
    repo.save_plan(user_id, _plan("excuse-task", date.today(), ["İrade"]))
    state = GameState(user_id=user_id)
    state.points["İrade"] = 10
    state.silent_miss_streak = 4
    repo.save_state(state)

    response = client.post(
        "/task/excuse-task/excuse",
        headers={"X-User-Id": user_id},
    )
    assert response.status_code == 200
    assert repo.get_state(user_id).points["İrade"] == 0
    assert repo.get_state(user_id).silent_miss_streak == 0
    assert repo.get_task(user_id, "excuse-task").status == "missed_excused"
    event = repo.get_point_log(user_id)[0]
    assert event.delta == -10
    assert event.reason == "mazeretli erteleme"


def test_cron_requires_configured_matching_secret(monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "test-cron-secret")
    assert client.post("/cron/close-day").status_code == 401
    assert client.post(
        "/cron/close-day", headers={"X-Cron-Secret": "wrong"}
    ).status_code == 401
    assert client.post(
        "/cron/close-day", headers={"X-Cron-Secret": "test-cron-secret"}
    ).status_code == 200


def test_multi_user_close_day_uses_each_timezone_and_logs_floor():
    repository = InMemoryRepository()
    repository.save_profile("istanbul", UserProfile(timezone="Europe/Istanbul"))
    repository.save_profile("new-york", UserProfile(timezone="America/New_York"))

    for user_id in ("istanbul", "new-york"):
        plan = Plan(
            id=f"plan-{user_id}",
            duration_days=2,
            batch_generated_until=2,
            start_date=date(2026, 7, 9),
            days=[
                PlanDay(day=1, tasks=[Task(
                    id=f"{user_id}-day9", day=1, title="Dün", categories=["İrade"],
                    date=date(2026, 7, 9),
                )]),
                PlanDay(day=2, tasks=[Task(
                    id=f"{user_id}-day10", day=2, title="Bugün", categories=["İrade"],
                    date=date(2026, 7, 10),
                )]),
            ],
        )
        repository.save_plan(user_id, plan)
        state = GameState(user_id=user_id)
        state.points["İrade"] = 10
        repository.save_state(state)

    result = task_lifecycle_service.close_due_users(
        repository,
        datetime(2026, 7, 10, 20, 59, tzinfo=timezone.utc),
    )
    assert result["processed_users"] == 2
    assert repository.get_task("istanbul", "istanbul-day10").status == "missed_silent"
    assert repository.get_task("istanbul", "istanbul-day9").status == "pending"
    assert repository.get_task("new-york", "new-york-day9").status == "missed_silent"
    assert repository.get_task("new-york", "new-york-day10").status == "pending"
    assert repository.get_state("istanbul").points["İrade"] == 0
    assert repository.get_point_log("istanbul")[0].delta == -10

    task_lifecycle_service.close_due_users(
        repository,
        datetime(2026, 7, 10, 20, 59, tzinfo=timezone.utc),
    )
    assert len(repository.get_point_log("istanbul")) == 1
    assert len(repository.get_point_log("new-york")) == 1


def test_same_day_multiple_silent_misses_each_advance_master_streak():
    """MASTER §1.2 says every silent task miss advances n; it is not once/day."""
    repository = InMemoryRepository()
    user_id = "same-day-misses"
    day = date(2026, 7, 11)
    tasks = [
        Task(
            id=f"same-day-{index}",
            day=1,
            title=f"Görev {index}",
            categories=["İrade"],
            date=day,
        )
        for index in range(3)
    ]
    repository.save_plan(user_id, Plan(
        id="same-day-plan",
        duration_days=1,
        batch_generated_until=1,
        start_date=day,
        days=[PlanDay(day=1, tasks=tasks)],
    ))
    state = GameState(user_id=user_id)
    state.points["İrade"] = 500
    repository.save_state(state)

    result = task_lifecycle_service.close_user_day(repository, user_id, day)

    assert result["penalized_tasks"] == 3
    assert repository.get_state(user_id).points["İrade"] == 325
    assert repository.get_state(user_id).silent_miss_streak == 3
    assert [event.delta for event in repository.get_point_log(user_id)] == [
        -25, -50, -100,
    ]
