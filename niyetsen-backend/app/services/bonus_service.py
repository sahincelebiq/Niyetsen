"""Persistent, idempotent FAZ 4 bonus-task flow."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.config import BONUS_POINTS
from app.models.schemas import BonusOffer, BonusOfferResponse
from app.services.bonus_pool import pick_bonus
from app.storage.base import Repository

# Şahin: Yaptım anında +10 değil; kısa süre görevle kal.
BONUS_MIN_COMPLETE_SECONDS = 45


class BonusTooSoonError(Exception):
    """Teklifin üzerinden min süre geçmeden tamamlama."""


def _response(offer: BonusOffer) -> BonusOfferResponse:
    return BonusOfferResponse(
        id=offer.id,
        title=offer.title,
        tiny_instruction=offer.tiny_instruction,
        category=offer.category,
        day=offer.day,
        status=offer.status,
        points=BONUS_POINTS,
        offered_at=offer.offered_at,
    )


def offer_for_day(
    repository: Repository,
    user_id: str,
    day: date,
    path_name: str = "",
) -> BonusOfferResponse:
    existing = repository.get_bonus_for_day(user_id, day)
    if existing:
        return _response(existing)
    if not path_name:
        from app.services import persona_service

        path_name = persona_service.active_path_name(repository, user_id)
    definition = pick_bonus(user_id, day, path_name=path_name)
    offer = repository.save_bonus_offer(BonusOffer(
        id=str(uuid.uuid4()),
        user_id=user_id,
        bonus_key=definition.key,
        title=definition.title,
        tiny_instruction=definition.tiny_instruction,
        category=definition.category,
        day=day,
    ))
    return _response(offer)


def active_offer(repository: Repository, user_id: str) -> BonusOfferResponse | None:
    offer = repository.get_active_bonus(user_id)
    return _response(offer) if offer else None


def today_offer(
    repository: Repository, user_id: str, day: date
) -> BonusOfferResponse | None:
    offer = repository.get_bonus_for_day(user_id, day)
    return _response(offer) if offer else None


def complete(
    repository: Repository,
    user_id: str,
    offer_id: str,
    completion_id: str,
) -> bool:
    offer = repository.get_active_bonus(user_id)
    if offer is not None and offer.id == offer_id:
        offered_at = offer.offered_at
        if offered_at.tzinfo is None:
            offered_at = offered_at.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - offered_at).total_seconds()
        if elapsed < BONUS_MIN_COMPLETE_SECONDS:
            raise BonusTooSoonError(
                "Bonus görevi henüz yeni. Metni oku, hareketi yap, sonra onayla."
            )
    return repository.claim_bonus_completion(
        user_id, offer_id, completion_id
    )
