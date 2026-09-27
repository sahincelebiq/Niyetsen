"""Plan kartı alt adımları.

`plan_step_notes.body` JSON listedir (kolon zaten prod'da, 2000 karakter).
Adım tamamlamak +50 yazmaz ve zinciri tek başına uzatmaz — puan, Bugün'de
kanıt / etkinlik yoluyla kalır. Böylece checklist puan çiftlemez.
"""
from __future__ import annotations

import json
import uuid

from app.models.schemas import TaskStep, TaskStepIn
from app.storage.base import Repository

MAX_STEPS = 12
MAX_BODY = 2000


class TaskStepError(ValueError):
    pass


class TaskNotFound(TaskStepError):
    pass


def list_steps(repository: Repository, user_id: str, task_id: str) -> list[TaskStep]:
    if repository.get_task(user_id, task_id) is None:
        raise TaskNotFound("Görev bulunamadı.")
    return repository.get_task_steps(user_id, task_id)


def replace_steps(
    repository: Repository,
    user_id: str,
    task_id: str,
    incoming: list[TaskStepIn],
) -> list[TaskStep]:
    if repository.get_task(user_id, task_id) is None:
        raise TaskNotFound("Görev bulunamadı.")
    if len(incoming) > MAX_STEPS:
        raise TaskStepError("Bir karta en fazla 12 adım sığar.")
    steps: list[TaskStep] = []
    for index, item in enumerate(incoming):
        title = item.title.strip()
        if not title:
            raise TaskStepError("Adım başlığı boş olamaz.")
        step_id = item.id.strip() if _valid_id(item.id) else uuid.uuid4().hex[:12]
        steps.append(TaskStep(id=step_id, title=title[:80], done=item.done, order=index))
    encoded = json.dumps(
        [step.model_dump() for step in steps],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(encoded) > MAX_BODY:
        raise TaskStepError("Adımlar kayda sığmadı. Birkaçını kısalt.")
    repository.save_task_steps(user_id, task_id, steps)
    return steps


def _valid_id(value: str) -> bool:
    token = (value or "").strip()
    if not token or len(token) > 40:
        return False
    return all(ch.isalnum() or ch in "-_" for ch in token)
