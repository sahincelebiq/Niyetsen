"""Versioned, purpose-specific legal consent rules."""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import (
    ConsentItem, ConsentKind, ConsentRecord, ConsentStatus, ConsentUpdate,
)
from app.storage.base import Repository


CURRENT_VERSIONS: dict[ConsentKind, str] = {
    "privacy_policy": settings.PRIVACY_POLICY_VERSION,
    "kvkk_explicit_consent": settings.KVKK_CONSENT_VERSION,
    "ai_chat_processing": settings.AI_CHAT_CONSENT_VERSION,
    "proof_photo_processing": settings.PROOF_PHOTO_CONSENT_VERSION,
    "marketing_communications": settings.MARKETING_CONSENT_VERSION,
}

REQUIRED_FOR: dict[ConsentKind, list[str]] = {
    "privacy_policy": ["chat", "proof"],
    "kvkk_explicit_consent": ["chat", "proof"],
    "ai_chat_processing": ["chat"],
    "proof_photo_processing": ["proof"],
    "marketing_communications": [],
}


def status(repository: Repository, user_id: str) -> ConsentStatus:
    current: dict[str, ConsentRecord] = {
        record.kind: record
        for record in repository.get_consents(user_id)
        if record.version == CURRENT_VERSIONS[record.kind]
    }
    items = {}
    for kind, version in CURRENT_VERSIONS.items():
        record = current.get(kind)
        items[kind] = ConsentItem(
            version=version,
            accepted=bool(record and record.accepted),
            decided_at=record.decided_at if record else None,
            required_for=REQUIRED_FOR[kind],
        )
    needs_reconsent = not (
        items["privacy_policy"].accepted
        and items["kvkk_explicit_consent"].accepted
    )
    return ConsentStatus(
        data_controller=settings.LEGAL_DATA_CONTROLLER,
        contact_email=settings.LEGAL_CONTACT_EMAIL,
        needs_reconsent=needs_reconsent,
        **items,
    )


def update(
    repository: Repository, user_id: str, choices: ConsentUpdate
) -> ConsentStatus:
    now = datetime.now(timezone.utc)
    for kind, choice in choices.model_dump(exclude_none=True).items():
        repository.save_consent(
            user_id,
            ConsentRecord(
                kind=kind,
                version=CURRENT_VERSIONS[kind],
                accepted=choice["accepted"],
                decided_at=now,
            ),
        )
    return status(repository, user_id)


def migrate_legacy_onboarding(
    repository: Repository, user_id: str, accepted_at: datetime
) -> None:
    """Old checkbox covered privacy notice + KVKK only, never AI/photo/marketing."""
    existing = status(repository, user_id)
    for kind in ("privacy_policy", "kvkk_explicit_consent"):
        if not getattr(existing, kind).accepted:
            repository.save_consent(
                user_id,
                ConsentRecord(
                    kind=kind,
                    version=CURRENT_VERSIONS[kind],
                    accepted=True,
                    decided_at=accepted_at,
                ),
            )


def allows(repository: Repository, user_id: str, purpose: str) -> bool:
    snapshot = status(repository, user_id)
    required = {
        "chat": (
            snapshot.privacy_policy,
            snapshot.kvkk_explicit_consent,
            snapshot.ai_chat_processing,
        ),
        "proof": (
            snapshot.privacy_policy,
            snapshot.kvkk_explicit_consent,
            snapshot.proof_photo_processing,
        ),
    }[purpose]
    return all(item.accepted for item in required)
