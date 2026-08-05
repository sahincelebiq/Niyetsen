"""Niyetsen — profil/onboarding kuralları."""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.schemas import ProfileUpdate, UserProfile


def zodiac_for(birth_date: date) -> str:
    month_day = (birth_date.month, birth_date.day)
    signs = [
        ((1, 20), "Kova"), ((2, 19), "Balık"), ((3, 21), "Koç"),
        ((4, 20), "Boğa"), ((5, 21), "İkizler"), ((6, 22), "Yengeç"),
        ((7, 23), "Aslan"), ((8, 23), "Başak"), ((9, 23), "Terazi"),
        ((10, 23), "Akrep"), ((11, 22), "Yay"), ((12, 22), "Oğlak"),
    ]
    sign = "Oğlak"
    for boundary, candidate in signs:
        if month_day >= boundary:
            sign = candidate
    return sign


def build_profile(update: ProfileUpdate, current: UserProfile) -> UserProfile:
    if update.birth_date > date.today():
        raise ValueError("Doğum tarihi gelecekte olamaz.")
    consent_at = current.kvkk_consent_at
    if update.kvkk_consent and consent_at is None:
        consent_at = datetime.now(timezone.utc)

    return UserProfile(
        name=update.name.strip(),
        birth_date=update.birth_date,
        zodiac_sign=zodiac_for(update.birth_date),
        # FAZ 8: isteğe bağlı — gönderilmezse mevcut değer korunur.
        gender=update.gender if update.gender is not None else current.gender,
        timezone=update.timezone,
        preferred_language=(
            update.preferred_language
            if update.preferred_language is not None
            else current.preferred_language
        ),
        notif_hour=update.notif_hour,
        notif_minute=update.notif_minute,
        irade_modu_active=update.irade_modu_active,
        kvkk_consent_at=consent_at,
        onboarding_complete=consent_at is not None,
    )
