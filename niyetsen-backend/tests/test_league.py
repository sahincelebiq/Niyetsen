"""faz8.13/4 — Online rekabet: opt-in takma adlı gelişim ligi."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.storage.repository import repo

client = TestClient(app)


def _give_points(user_id: str, category: str, amount: int) -> None:
    state = repo.get_state(user_id)
    state.points[category] = state.points.get(category, 0) + amount
    repo.save_state(state)


def test_league_requires_opt_in():
    resp = client.get("/league", headers={"X-User-Id": "lig_yok"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["opted_in"] is False
    assert body["alias"] is None


def test_join_with_alias_and_rank_order():
    _give_points("lig_a", "Disiplin", 300)
    _give_points("lig_b", "İrade", 100)
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
    assert aliases.index("Kartal") < aliases.index("Filiz 7")  # puana göre sıra
    me = next(m for m in board["members"] if m["is_me"])
    assert me["rank"] == board["my_rank"]


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

    def fake_top(limit: int = 50):
        rows = original(limit)
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


def test_board_refreshes_own_score_snapshot():
    user = "lig_taze"
    client.post("/league/join", headers={"X-User-Id": user}, json={"alias": "Taze"})
    _give_points(user, "Özgüven", 150)
    board = client.get("/league", headers={"X-User-Id": user}).json()
    me = next(m for m in board["members"] if m["is_me"])
    assert me["score"] >= 150  # anlık görüntü tazelendi


def test_my_rank_visible_beyond_top_50():
    """Release QA T9: ilk 50 dışındaki üye de gerçek sırasını görür."""
    for i in range(51):
        uid = f"lig_kalabalik_{i}"
        _give_points(uid, "Disiplin", 1000 - i)
        client.post(
            "/league/join", headers={"X-User-Id": uid},
            json={"alias": f"Uye {i}"},
        )
    tail = "lig_sondaki"
    client.post(
        "/league/join", headers={"X-User-Id": tail}, json={"alias": "Sondaki"}
    )
    board = client.get("/league", headers={"X-User-Id": tail}).json()
    assert board["opted_in"] is True
    assert len(board["members"]) == 50          # pano ilk 50 ile sınırlı
    assert all(not m["is_me"] for m in board["members"])
    assert board["my_rank"] == 52               # yine de gerçek sıra döner
