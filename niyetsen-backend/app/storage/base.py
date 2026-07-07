"""
Niyetsen — Depolama arayüzü (soyut sözleşme).
Ayrı dosyada: hem repository.py (InMemory + repo seçici) hem de
supabase_repository.py bunu import eder; repository.py çalışma zamanında
supabase_repository'yi GEÇ import ettiği için (USE_SUPABASE_DB=true iken)
Repository'nin burada, iki yönlü bağımlılık yaratmayan bir yerde durması gerekir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.models.schemas import GameState, Plan, Task


class Repository(ABC):
    """Tek gerçek arayüz. Yeni backend eklemek = bu sınıfı implemente etmek."""

    @abstractmethod
    def get_state(self, user_id: str) -> GameState: ...

    @abstractmethod
    def save_state(self, state: GameState) -> None: ...

    @abstractmethod
    def save_plan(self, user_id: str, plan: Plan) -> None: ...

    @abstractmethod
    def get_plan(self, user_id: str) -> Optional[Plan]: ...

    @abstractmethod
    def get_task(self, user_id: str, task_id: str) -> Optional[Task]: ...

    @abstractmethod
    def update_task(self, user_id: str, task: Task) -> None: ...

    @abstractmethod
    def get_proof_attempts(self, user_id: str, task_id: str) -> int: ...

    @abstractmethod
    def incr_proof_attempts(self, user_id: str, task_id: str) -> int: ...
