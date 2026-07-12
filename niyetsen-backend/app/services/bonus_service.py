"""Persistent, idempotent FAZ 4 bonus-task flow."""
from __future__ import annotations

import uuid
from datetime import date

from app.config import BONUS_POINTS
from app.models.schemas import BonusOffer, BonusOfferResponse
from app.services.bonus_pool import pick_bonus
from app.storage.base import Repository


def _response(offer: BonusOffer) -> BonusOfferResponse:
    return BonusOfferResponse(
        id=offer.id,
        title=offer.title,
        tiny_instruction=offer.tiny_instruction,
        category=offer.category,
        day=offer.day,
        status=offer.status,
        points=BONUS_POINTS,
    )


def offer_for_day(
    repository: Repository, user_id: str, day: date
) -> BonusOfferResponse:
    existing = repository.get_bonus_for_day(user_id, day)
    if existing:
        return _response(existing)
    definition = pick_bonus(user_id, day)
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


def complete(
    repository: Repository,
    user_id: str,
    offer_id: str,
    completion_id: str,
) -> bool:
    return repository.claim_bonus_completion(
        user_id, offer_id, completion_id
    )
