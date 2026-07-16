"""
Geliştirici hesabı ayrımı (FAZ 7.5).
=====================================
Şahin'in geliştirici hesabı (DEV_ACCOUNT_EMAILS) mağaza satın alması olmadan
tam erişim alır; NORMAL KULLANICILAR ETKİLENMEZ — onlar standart deneme →
paywall akışında kalır. Eşleşme JWT'deki doğrulanmış e-posta claim'iyle yapılır
(kullanıcı kendi e-postasını taklit edemez; Supabase imzalı token).

Not: Store incelemesine dev hesabı bilgisi sızmaz — bu yalnız backend'de
bir abonelik kısa devresi; arayüzde hiçbir "geliştirici" izi yoktur.
"""
from __future__ import annotations

from threading import Lock

from app.config import settings

_dev_user_ids: set[str] = set()
_lock = Lock()


def _normalized_allowlist() -> set[str]:
    return {email.strip().lower() for email in settings.DEV_ACCOUNT_EMAILS if email.strip()}


def register_if_dev(user_id: str, email: str | None) -> None:
    """JWT doğrulaması sonrası çağrılır; e-posta allowlist'teyse işaretler."""
    if not user_id or not email:
        return
    if email.strip().lower() in _normalized_allowlist():
        with _lock:
            _dev_user_ids.add(user_id)


def is_dev(user_id: str) -> bool:
    with _lock:
        return user_id in _dev_user_ids


def reset() -> None:
    """Testler için."""
    with _lock:
        _dev_user_ids.clear()
