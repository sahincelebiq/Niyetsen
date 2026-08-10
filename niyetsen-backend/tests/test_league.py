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


def test_board_refreshes_own_score_snapshot():
    user = "lig_taze"
    client.post("/league/join", headers={"X-User-Id": user}, json={"alias": "Taze"})
    _give_points(user, "Özgüven", 150)
    board = client.get("/league", headers={"X-User-Id": user}).json()
    me = next(m for m in board["members"] if m["is_me"])
    assert me["score"] >= 150  # anlık görüntü tazelendi
