"""faz8.13/4 — Online rekabet: opt-in takma adlı gelişim ligi."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Plan, PlanDay, Task, UserProfile
from app.storage.repository import repo

client = TestClient(app)


def _give_points(user_id: str, category: str, amount: int) -> None:
    state = repo.get_state(user_id)
    state.points[category] = state.points.get(category, 0) + amount
    repo.save_state(state)


def _set_streak(user_id: str, streak: int) -> None:
    state = repo.get_state(user_id)
    state.streak_len = streak
    repo.save_state(state)


def _complete_tasks(user_id: str, n: int) -> None:
    today = date.today()
    days = [
        PlanDay(
            day=i + 1,
            tasks=[
                Task(
                    id=f"{user_id}-t{i}",
                    day=i + 1,
                    title=f"Görev {i}",
                    categories=["Disiplin"],
                    status="done",
                    date=today - timedelta(days=n - i),
                )
            ],
        )
        for i in range(n)
    ]
    repo.save_plan(
        user_id,
        Plan(
            id=f"{user_id}-p",
            duration_days=max(n, 1),
            batch_generated_until=n,
            start_date=today - timedelta(days=max(n, 1) - 1),
            days=days,
        ),
    )


def test_league_requires_opt_in():
    resp = client.get("/league", headers={"X-User-Id": "lig_yok"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["opted_in"] is False
    assert body["alias"] is None
    assert body["avatar"] is None
    assert body["region"] is None


def test_join_ranks_by_completed_tasks_not_points():
    _complete_tasks("lig_a", 3)
    _complete_tasks("lig_b", 1)
    _give_points("lig_b", "İrade", 900)
    a = client.post(
        "/league/join", headers={"X-User-Id": "lig_a"}, json={"alias": "Kartal"}
    )
    b = client.post(
        "/league/join", headers={"X-User-Id": "lig_b"}, json={"alias": "Filiz 7"}
    )
    assert a.status_code == 200 and b.status_code == 200
    board = client.get("/league", headers={"X-User-Id": "lig_b"}).json()
    assert board["opted_in"] is True
    assert board["alias"] == "Filiz 7"
    aliases = [m["alias"] for m in board["members"]]
    assert aliases.index("Kartal") < aliases.index("Filiz 7")
    kartal = next(m for m in board["members"] if m["alias"] == "Kartal")
    assert kartal["score"] == 3
    assert kartal["completed_tasks"] == 3
    me = next(m for m in board["members"] if m["is_me"])
    assert me["rank"] == board["my_rank"]
    assert me["completed_tasks"] == 1


def test_streak_breaks_completed_task_ties():
    _complete_tasks("lig_tie_a", 2)
    _complete_tasks("lig_tie_b", 2)
    _set_streak("lig_tie_a", 8)
    _set_streak("lig_tie_b", 2)
    client.post(
        "/league/join", headers={"X-User-Id": "lig_tie_a"}, json={"alias": "Uzun"}
    )
    client.post(
        "/league/join", headers={"X-User-Id": "lig_tie_b"}, json={"alias": "Kisa"}
    )
    board = client.get("/league", headers={"X-User-Id": "lig_tie_b"}).json()
    aliases = [m["alias"] for m in board["members"]]
    assert aliases.index("Uzun") < aliases.index("Kisa")


def test_alias_rejects_email_like_input():
    """KVKK: rumuzda e-posta/bağlantı yok — gerçek kimlik sızmaz."""
    resp = client.post(
        "/league/join",
        headers={"X-User-Id": "lig_kvkk"},
        json={"alias": "ali@mail.com"},
    )
    assert resp.status_code == 400


def test_leave_removes_membership_completely():
    client.post(
        "/league/join", headers={"X-User-Id": "lig_cikan"}, json={"alias": "Gecici"}
    )
    resp = client.post("/league/leave", headers={"X-User-Id": "lig_cikan"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["opted_in"] is False
    assert all(m["alias"] != "Gecici" for m in body["members"])  # iz yok


def test_board_marks_me_when_user_id_type_differs():
    """PostgREST uuid nesnesi vs JWT text — is_me kaybolmasın."""
    from app.services import league_service

    uid = "86681cf1-aaaa-4bbb-8ccc-ddddeeeeffff"
    assert league_service._same_user_id(uid, uid.upper())
    assert league_service._same_user_id(uid, uid)
    assert not league_service._same_user_id(uid, "other")

    client.post("/league/join", headers={"X-User-Id": uid}, json={"alias": "Ada"})

    class Uuidish:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:
            return self.value

        def __eq__(self, other: object) -> bool:
            return False

    original = repo.league_top

    def fake_top(limit: int = 50, region=None):
        rows = original(limit, region=region)
        for row in rows:
            row["user_id"] = Uuidish(str(row["user_id"]).upper())
        return rows

    repo.league_top = fake_top  # type: ignore[method-assign]
    try:
        board = client.get("/league", headers={"X-User-Id": uid}).json()
    finally:
        repo.league_top = original  # type: ignore[method-assign]
    me = next(m for m in board["members"] if m["alias"] == "Ada")
    assert me["is_me"] is True
    assert board["my_rank"] == me["rank"]


def test_board_refreshes_own_completed_task_snapshot():
    user = "lig_taze"
    client.post("/league/join", headers={"X-User-Id": user}, json={"alias": "Taze"})
    _complete_tasks(user, 4)
    board = client.get("/league", headers={"X-User-Id": user}).json()
    me = next(m for m in board["members"] if m["is_me"])
    assert me["score"] == 4
    assert me["completed_tasks"] == 4


def test_my_rank_visible_beyond_top_50():
    """Release QA T9: ilk 50 dışındaki üye de gerçek sırasını görür."""
    for i in range(51):
        uid = f"lig_kalabalik_{i}"
        repo.league_upsert_member(uid, f"Uye {i}", 1000 - i, 0)
    tail = "lig_sondaki"
    client.post(
        "/league/join", headers={"X-User-Id": tail}, json={"alias": "Sondaki"}
    )
    board = client.get("/league", headers={"X-User-Id": tail}).json()
    assert board["opted_in"] is True
    assert len(board["members"]) == 50          # pano ilk 50 ile sınırlı
    assert all(not m["is_me"] for m in board["members"])
    assert board["my_rank"] == 52               # yine de gerçek sıra döner


def test_join_with_preset_avatar_and_region_label():
    resp = client.post(
        "/league/join",
        headers={"X-User-Id": "lig_istanbul"},
        json={"alias": "Marti", "avatar": "filiz", "region": "İstanbul"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["avatar"] == "filiz"
    assert body["region"] == "İstanbul"
    me = next(m for m in body["members"] if m["is_me"])
    assert me["avatar"] == "filiz"
    assert me["region"] == "İstanbul"
    assert "user_id" not in me
    assert "name" not in me
    assert "email" not in me


def test_region_filter_is_string_label_not_location():
    client.post(
        "/league/join",
        headers={"X-User-Id": "lig_ist"},
        json={"alias": "Bogaz", "region": "İstanbul"},
    )
    client.post(
        "/league/join",
        headers={"X-User-Id": "lig_ank"},
        json={"alias": "Hitit", "region": "Ankara"},
    )
    istanbul = client.get(
        "/league",
        headers={"X-User-Id": "lig_ist"},
        params={"region": "İstanbul"},
    ).json()
    aliases = [m["alias"] for m in istanbul["members"]]
    assert "Bogaz" in aliases
    assert "Hitit" not in aliases
    ankara_viewer = client.get(
        "/league",
        headers={"X-User-Id": "lig_ank"},
        params={"region": "İstanbul"},
    ).json()
    assert ankara_viewer["opted_in"] is True
    assert ankara_viewer["region"] == "Ankara"
    assert ankara_viewer["my_rank"] is None


def test_rejects_photo_like_avatar_and_url_region():
    photo = client.post(
        "/league/join",
        headers={"X-User-Id": "lig_foto"},
        json={"alias": "Foto", "avatar": "https://cdn.example/me.jpg"},
    )
    assert photo.status_code == 400
    region = client.post(
        "/league/join",
        headers={"X-User-Id": "lig_gps"},
        json={"alias": "Konum", "region": "https://maps.example/x"},
    )
    assert region.status_code == 400


def test_patch_updates_alias_avatar_region():
    client.post(
        "/league/join",
        headers={"X-User-Id": "lig_yama"},
        json={"alias": "Eski"},
    )
    resp = client.patch(
        "/league",
        headers={"X-User-Id": "lig_yama"},
        json={"alias": "Yeni", "avatar": "kartal", "region": "İzmir"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["alias"] == "Yeni"
    assert body["avatar"] == "kartal"
    assert body["region"] == "İzmir"


def test_patch_requires_opt_in():
    resp = client.patch(
        "/league",
        headers={"X-User-Id": "lig_yama_yok"},
        json={"alias": "Hayalet"},
    )
    assert resp.status_code == 400


def test_board_never_leaks_profile_identity():
    repo.save_profile(
        "lig_gizli",
        UserProfile(name="Şahin Çelebi"),
    )
    client.post(
        "/league/join",
        headers={"X-User-Id": "lig_gizli"},
        json={"alias": "Rumuz"},
    )
    board = client.get("/league", headers={"X-User-Id": "lig_gizli"}).json()
    dumped = str(board)
    assert "Şahin" not in dumped
    assert "Çelebi" not in dumped
    assert "kutluadalarr7" not in dumped
    for member in board["members"]:
        assert set(member) <= {
            "alias", "score", "completed_tasks", "streak",
            "avatar", "region", "rank", "is_me",
        }
