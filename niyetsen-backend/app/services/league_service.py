"""
Niyetsen — Lig Servisi (faz8.13/4, 2026-08-10: leaderboard öne çekildi)
=======================================================================
Online rekabet: opt-in TAKMA ADLI gelişim ligi. PvP değil — indiren
kullanıcıların gelişim rekabeti.

KVKK / mağaza uyumu (kilitli ilkeler):
- Katılım tamamen isteğe bağlı (opt-in); çıkışta üyelik SİLİNİR (iz yok).
- Gerçek isim/e-posta/fotoğraf/GPS ASLA sızmaz — yalnız rumuz + hazır
  avatar + bölge etiketi + tamamlanan görev + zincir görünür.
- Sıralama: tamamlanan görev (birincil) + zincir (ikincil). Puan/ceza
  sıralamaz — utandırma yasağı (kaçırma/ceza ligde yok).
- Bölge serbest metin (örn. "İstanbul"); konum izni istenmez.
- Presence/Realtime yok — yığında Supabase Realtime kullanılmıyor.
"""
from __future__ import annotations

import re

from app.models.schemas import LeagueMember, LeagueResponse
from app.storage.base import Repository

MAX_BOARD = 50

# Rumuz: 2-24 karakter; harf/rakam/boşluk/altçizgi. E-posta ve URL benzeri
# girdiler reddedilir (gerçek kimlik sızıntısını zorlaştırır).
_ALIAS_RE = re.compile(r"^[\w ÇçĞğİıÖöŞşÜü.\-]{2,24}$")
_REGION_RE = re.compile(r"^[\w ÇçĞğİıÖöŞşÜü.\-]{2,40}$")

# Hazır simge anahtarları — fotoğraf URL'si değil. Zincir yoldaşı / İlkbahar
# setinden türetilmiş kapalı liste.
LEAGUE_AVATARS = frozenset({
    "filiz",
    "yaprak",
    "agac",
    "tomurcuk",
    "fidan",
    "orman",
    "kartal",
    "aslan",
    "geyik",
    "kedi",
    "kus",
    "kelebek",
})


class LeagueError(ValueError):
    """400 — geçersiz rumuz / avatar / bölge."""


def _rank_snapshot(repository: Repository, user_id: str) -> tuple[int, int]:
    """Sıralama anahtarı: tamamlanan görev + zincir. Puan yok."""
    completed = repository.count_completed_tasks(user_id)
    state = repository.get_state(user_id)
    return int(completed), int(state.streak_len)


def normalize_alias(alias: str) -> str:
    cleaned = " ".join((alias or "").split()).strip()
    if "@" in cleaned or "://" in cleaned:
        raise LeagueError("Rumuzda e-posta/bağlantı kullanma — gizliliğin için.")
    if not _ALIAS_RE.match(cleaned):
        raise LeagueError("Rumuz 2-24 karakter olmalı (harf, rakam, boşluk).")
    return cleaned


def normalize_avatar(avatar: str | None) -> str | None:
    if avatar is None:
        return None
    cleaned = avatar.strip().lower()
    if cleaned == "":
        return None
    if "@" in cleaned or "://" in cleaned:
        raise LeagueError("Avatar hazır simge olmalı — fotoğraf/bağlantı yok.")
    if cleaned not in LEAGUE_AVATARS:
        raise LeagueError(
            "Avatar hazır listedeki bir simge olmalı — fotoğraf yüklenmez."
        )
    return cleaned


def normalize_region(region: str | None) -> str | None:
    if region is None:
        return None
    cleaned = " ".join(region.split()).strip()
    if cleaned == "":
        return None
    if "@" in cleaned or "://" in cleaned:
        raise LeagueError("Bölge adı olarak e-posta/bağlantı kullanma.")
    if not _REGION_RE.match(cleaned):
        raise LeagueError("Bölge 2-40 karakter olmalı (örn. İstanbul). Konum izni yok.")
    return cleaned


def _profile_from_existing(member: dict | None) -> tuple[str | None, str | None]:
    if not member:
        return None, None
    return member.get("avatar"), member.get("region")


def join(
    repository: Repository,
    user_id: str,
    alias: str,
    avatar: str | None = None,
    region: str | None = None,
) -> LeagueResponse:
    cleaned = normalize_alias(alias)
    existing = repository.league_get_member(user_id)
    keep_avatar, keep_region = _profile_from_existing(existing)
    avatar_val = normalize_avatar(avatar) if avatar is not None else keep_avatar
    region_val = normalize_region(region) if region is not None else keep_region
    score, streak = _rank_snapshot(repository, user_id)
    repository.league_upsert_member(
        user_id, cleaned, score, streak, avatar=avatar_val, region=region_val
    )
    return get_board(repository, user_id)


def update_profile(
    repository: Repository,
    user_id: str,
    alias: str | None = None,
    avatar: str | None = None,
    region: str | None = None,
) -> LeagueResponse:
    member = repository.league_get_member(user_id)
    if not member:
        raise LeagueError("Önce rumuzla lige katıl.")
    cleaned = normalize_alias(alias) if alias is not None else member["alias"]
    avatar_val = (
        normalize_avatar(avatar) if avatar is not None else member.get("avatar")
    )
    region_val = (
        normalize_region(region) if region is not None else member.get("region")
    )
    score, streak = _rank_snapshot(repository, user_id)
    repository.league_upsert_member(
        user_id, cleaned, score, streak, avatar=avatar_val, region=region_val
    )
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


def _member_payload(row: dict, *, rank: int, is_me: bool) -> LeagueMember:
    completed = int(row.get("score") or 0)
    return LeagueMember(
        alias=row["alias"],
        score=completed,
        completed_tasks=completed,
        streak=int(row.get("streak") or 0),
        avatar=row.get("avatar"),
        region=row.get("region"),
        rank=rank,
        is_me=is_me,
    )


def get_board(
    repository: Repository,
    user_id: str,
    region: str | None = None,
) -> LeagueResponse:
    region_filter = normalize_region(region) if region else None
    member = repository.league_get_member(user_id)
    if member:
        # Her görüntülemede kendi anlık görüntün tazelenir — pano canlı kalır.
        score, streak = _rank_snapshot(repository, user_id)
        if (
            score != member.get("score")
            or streak != member.get("streak")
        ):
            repository.league_upsert_member(
                user_id,
                member["alias"],
                score,
                streak,
                avatar=member.get("avatar"),
                region=member.get("region"),
            )
            member = {
                **member,
                "score": score,
                "streak": streak,
            }

    rows = repository.league_top(MAX_BOARD, region=region_filter)
    members: list[LeagueMember] = []
    my_rank: int | None = None
    for index, row in enumerate(rows, start=1):
        is_me = _same_user_id(row.get("user_id"), user_id)
        if is_me:
            my_rank = index
        members.append(_member_payload(row, rank=index, is_me=is_me))
    if member is not None and my_rank is None:
        # İlk 50 dışında da gerçek sıranı gör (release QA T9). Degrade: hata
        # panoyu düşürmez, yalnız sıra boş kalır.
        try:
            my_rank = repository.league_rank(user_id, region=region_filter)
        except Exception:  # noqa: BLE001
            my_rank = None
    return LeagueResponse(
        opted_in=member is not None,
        alias=member["alias"] if member else None,
        avatar=member.get("avatar") if member else None,
        region=member.get("region") if member else None,
        my_rank=my_rank,
        members=members,
    )
