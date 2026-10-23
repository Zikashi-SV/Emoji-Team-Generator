"""
Automated tests for team formation algorithms (Mode A & Mode B),
distribution balance, edge cases, and persistence.
"""

from database import connect_db, get_active_session
from team_allocator import allocate_teams_by_count, allocate_teams_by_max_size


def test_mode_a_balanced_distribution():
    """Test Mode A distributes participants evenly with at most difference of 1."""
    # 20 participants into 4 teams -> exactly 5 each
    participants_20 = [{"id": i, "name": f"P{i}", "selected_emoji": "🚀"} for i in range(1, 21)]
    teams_4 = allocate_teams_by_count(participants_20, 4)
    assert len(teams_4) == 4
    for team in teams_4:
        assert len(team) == 5

    # 23 participants into 4 teams -> sizes [6, 6, 6, 5] (differ by at most 1)
    participants_23 = [{"id": i, "name": f"P{i}", "selected_emoji": "🚀"} for i in range(1, 24)]
    teams_uneven = allocate_teams_by_count(participants_23, 4)
    assert len(teams_uneven) == 4
    sizes = [len(t) for t in teams_uneven]
    assert max(sizes) - min(sizes) <= 1
    assert sum(sizes) == 23


def test_mode_b_max_size_enforcement():
    """Test Mode B creates needed teams and ensures no team exceeds max size."""
    # 23 participants with max team size 5 -> 5 teams with max size <= 5
    participants_23 = [{"id": i, "name": f"P{i}", "selected_emoji": "🚀"} for i in range(1, 24)]
    teams = allocate_teams_by_max_size(participants_23, 5)
    assert len(teams) == 5
    for team in teams:
        assert len(team) <= 5
        assert len(team) >= 4  # Balanced distribution
    assert sum(len(t) for t in teams) == 23


def test_zero_participants_handling(admin_client):
    """Test team generation fails with clean error when 0 participants exist."""
    res = admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 4},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert res.status_code == 400
    assert "no participants" in res.get_json()["error"].lower()


def test_invalid_team_settings_rejected(admin_client, client):
    """Test invalid team counts or max sizes are rejected."""
    # Register 1 participant so zero-participant check passes
    client.post("/api/participants/register", json={"name": "Solo", "selected_emoji": "🦁"})

    # Invalid team count: 0
    res1 = admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 0},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert res1.status_code == 400

    # Invalid max size: -2
    res2 = admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "max_size", "max_team_size": -2},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert res2.status_code == 400


def test_team_generation_and_persistence(app, admin_client, client):
    """Test end-to-end team generation and database persistence."""
    # Register 6 participants with curated emojis
    emojis = ["🚀", "⚡", "🔥", "💎", "⭐", "🎯"]
    for i, em in enumerate(emojis, 1):
        r = client.post("/api/participants/register", json={"name": f"Player {i}", "selected_emoji": em})
        assert r.status_code == 201

    # Generate 2 teams
    gen_res = admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 2},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.get_json()["data"]
    assert len(gen_data["teams"]) == 2
    assert gen_data["total_assigned"] == 6

    # Verify each team has 3 members
    for team in gen_data["teams"]:
        assert len(team["members"]) == 3

    # Verify every participant is assigned exactly once in DB
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        sess = get_active_session(conn)
        rows = conn.execute("SELECT team_id FROM participants WHERE session_id = ?", (sess["id"],)).fetchall()
        assert len(rows) == 6
        assert all(r["team_id"] is not None for r in rows)
        conn.close()

    # Regeneration before publication
    regen_res = admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 3},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert regen_res.status_code == 200
    assert len(regen_res.get_json()["data"]["teams"]) == 3
