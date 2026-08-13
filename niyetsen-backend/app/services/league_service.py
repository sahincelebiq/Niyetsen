"""
Niyetsen — Lig Servisi (faz8.13/4, 2026-08-10: leaderboard öne çekildi)
=======================================================================
Online rekabet: opt-in TAKMA ADLI gelişim ligi. PvP değil — indiren
kullanıcıların gelişim rekabeti.

KVKK / mağaza uyumu (kilitli ilkeler):
- Katılım tamamen isteğe bağlı (opt-in); çıkışta üyelik SİLİNİR (iz yok).
- Gerçek isim/e-posta/veri ASLA sızmaz — yalnız kullanıcının seçtiği rumuz
  + toplam puan + zincir uzunluğu görünür.
- Utandırma yok: listede yalnız KAZANIMLAR (puan/zincir) sıralanır;
  kaçırılan görev, ceza, düşüş gösterilmez (Wrapped kuralıyla aynı ton).
"""
from __future__ import annotations

import re

from app.config import CATEGORIES
from app.models.schemas import LeagueMember, LeagueResponse
from app.storage.base import Repository

MAX_BOARD = 50

# Rumuz: 2-24 karakter; harf/rakam/boşluk/altçizgi. E-posta ve URL benzeri
# girdiler reddedilir (gerçek kimlik sızıntısını zorlaştırır).
_ALIAS_RE = re.compile(r"^[\w ÇçĞğİıÖöŞşÜü.\-]{2,24}$")


class LeagueError(ValueError):
    """400 — geçersiz rumuz vb."""


def _total_score(repository: Repository, user_id: str) -> tuple[int, int]:
    state = repository.get_state(user_id)
    total = sum(state.points.get(c, 0) for c in CATEGORIES)
    return total, state.streak_len


def normalize_alias(alias: str) -> str:
    cleaned = " ".join((alias or "").split()).strip()
    if "@" in cleaned or "://" in cleaned:
        raise LeagueError("Rumuzda e-posta/bağlantı kullanma — gizliliğin için.")
    if not _ALIAS_RE.match(cleaned):
        raise LeagueError("Rumuz 2-24 karakter olmalı (harf, rakam, boşluk).")
    return cleaned


def join(repository: Repository, user_id: str, alias: str) -> LeagueResponse:
    cleaned = normalize_alias(alias)
    score, streak = _total_score(repository, user_id)
    repository.league_upsert_member(user_id, cleaned, score, streak)
    return get_board(repository, user_id)


def leave(repository: Repository, user_id: str) -> LeagueResponse:
    repository.league_remove_member(user_id)
    return get_board(repository, user_id)


def _same_user_id(left: object, right: object) -> bool:
    """PostgREST uuid vs JWT text — büyük/küçük harf ve str() farkını yut."""
    a = str(left or "").strip()
    b = str(right or "").strip()
    if not a or not b:
        return False
    return a == b or a.casefold() == b.casefold()


def get_board(repository: Repository, user_id: str) -> LeagueResponse:
    member = repository.league_get_member(user_id)
    if member:
        # Her görüntülemede kendi anlık görüntün tazelenir — pano canlı kalır.
        score, streak = _total_score(repository, user_id)
        if score != member.get("score") or streak != member.get("streak"):
            repository.league_upsert_member(
                user_id, member["alias"], score, streak
            )
            member = {"alias": member["alias"], "score": score, "streak": streak}

    rows = repository.league_top(MAX_BOARD)
    members: list[LeagueMember] = []
    my_rank: int | None = None
    for index, row in enumerate(rows, start=1):
        is_me = _same_user_id(row.get("user_id"), user_id)
        if is_me:
            my_rank = index
        members.append(LeagueMember(
            alias=row["alias"],
            score=int(row.get("score") or 0),
            streak=int(row.get("streak") or 0),
            rank=index,
            is_me=is_me,
        ))
    return LeagueResponse(
        opted_in=member is not None,
        alias=member["alias"] if member else None,
        my_rank=my_rank,
        members=members,
    )
