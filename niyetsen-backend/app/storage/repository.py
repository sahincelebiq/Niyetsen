"""
Niyetsen — Depolama Katmanı
MVP: bellek-içi (uygulama yeniden başlayınca sıfırlanır — bilinçli, MVP kuralı).
v1: Cursor, SupabaseRepository'yi AYNI arayüzle yazar; routes hiç değişmez.
Tablolar MASTER_PLAN §2'de tanımlı — şema uydurulmaz.
Cursor notu: Repository ABC'si app/storage/base.py'de yaşar (bu dosyayla
supabase_repository.py arasında dairesel import'u önlemek için).
"""
from __future__ import annotations

from typing import Optional

from app.config import settings
from app.models.schemas import GameState, Plan, Task
from app.storage.base import Repository


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._states: dict[str, GameState] = {}
        self._plans: dict[str, Plan] = {}
        self._attempts: dict[tuple[str, str], int] = {}

    def get_state(self, user_id: str) -> GameState:
        if user_id not in self._states:
            self._states[user_id] = GameState(user_id=user_id)
        return self._states[user_id]

    def save_state(self, state: GameState) -> None:
        self._states[state.user_id] = state

    def save_plan(self, user_id: str, plan: Plan) -> None:
        self._plans[user_id] = plan

    def get_plan(self, user_id: str) -> Optional[Plan]:
        return self._plans.get(user_id)

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        plan = self._plans.get(user_id)
        if not plan:
            return None
        for day in plan.days:
            for t in day.tasks:
                if t.id == task_id:
                    return t
        return None

    def update_task(self, user_id: str, task: Task) -> None:
        plan = self._plans.get(user_id)
        if not plan:
            return
        for day in plan.days:
            for i, t in enumerate(day.tasks):
                if t.id == task.id:
                    day.tasks[i] = task
                    return

    def get_proof_attempts(self, user_id: str, task_id: str) -> int:
        return self._attempts.get((user_id, task_id), 0)

    def incr_proof_attempts(self, user_id: str, task_id: str) -> int:
        key = (user_id, task_id)
        self._attempts[key] = self._attempts.get(key, 0) + 1
        return self._attempts[key]


def _build_repo() -> Repository:
    if settings.USE_SUPABASE_DB:
        # Geç import: supabase paketi sadece bu yol seçildiğinde gerekli olsun.
        from app.storage.supabase_repository import SupabaseRepository
        return SupabaseRepository()
    return InMemoryRepository()


# Uygulama genelinde tek örnek. USE_SUPABASE_DB=false (varsayılan, testler dahil)
# iken bellek-içi; true iken gerçek Supabase kalıcılığı.
repo: Repository = _build_repo()
