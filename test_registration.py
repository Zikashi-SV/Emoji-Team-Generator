"""
Automated tests for participant registration workflow and edge cases.
"""

from database import connect_db, get_active_session


def test_valid_registration(client):
    """Test standard registration with valid name and curated emoji."""
    res = client.post("/api/participants/register", json={
        "name": "Alice Wonderland",
        "selected_emoji": "🚀"
    })
    assert res.status_code == 201
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["participant"]["name"] == "Alice Wonderland"
    assert body["data"]["participant"]["selected_emoji"] == "🚀"
    assert "token" in body["data"]["participant"]

    # Verify session status counter reflects new registration
    sess_res = client.get("/api/session")
    assert sess_res.status_code == 200
    sess_data = sess_res.get_json()["data"]
    assert sess_data["participant_count"] == 1


def test_empty_or_whitespace_name_rejected(client):
    """Test empty, whitespace-only, or non-string names are rejected with 400."""
    res1 = client.post("/api/participants/register", json={"name": "", "selected_emoji": "🚀"})
    assert res1.status_code == 400
    assert "empty" in res1.get_json()["error"].lower()

    res2 = client.post("/api/participants/register", json={"name": "     ", "selected_emoji": "🚀"})
    assert res2.status_code == 400

    res3 = client.post("/api/participants/register", json={"name": None, "selected_emoji": "🚀"})
    assert res3.status_code == 400


def test_name_length_boundaries(client):
    """Test min length (2 chars) and max length (50 chars) validation."""
    # 1 character - should fail
    res_short = client.post("/api/participants/register", json={"name": "A", "selected_emoji": "🚀"})
    assert res_short.status_code == 400
    assert "at least 2" in res_short.get_json()["error"]

    # Exactly 2 characters - should pass
    res_two = client.post("/api/participants/register", json={"name": "Al", "selected_emoji": "🚀"})
    assert res_two.status_code == 201

    # 51 characters - should fail
    too_long = "A" * 51
    res_long = client.post("/api/participants/register", json={"name": too_long, "selected_emoji": "⭐"})
    assert res_long.status_code == 400
    assert "exceed 50" in res_long.get_json()["error"]

    # Exactly 50 characters - should pass
    exact_50 = "B" * 50
    res_valid_50 = client.post("/api/participants/register", json={"name": exact_50, "selected_emoji": "⚡"})
    assert res_valid_50.status_code == 201


def test_duplicate_name_case_insensitive_and_spaces(client):
    """
    Test duplicate name prevention:
    'Arun', 'arun', and '  ARUN  ' must be treated as duplicates.
    """
    # First registration
    r1 = client.post("/api/participants/register", json={"name": "Arun", "selected_emoji": "🦁"})
    assert r1.status_code == 201

    # Exact lowercase duplicate
    r2 = client.post("/api/participants/register", json={"name": "arun", "selected_emoji": "🦄"})
    assert r2.status_code == 409
    assert "already registered" in r2.get_json()["error"]

    # Uppercase with leading/trailing spaces
    r3 = client.post("/api/participants/register", json={"name": "   ARUN   ", "selected_emoji": "🔥"})
    assert r3.status_code == 409
    assert "already registered" in r3.get_json()["error"]


def test_emoji_uniqueness_when_reuse_disabled(client):
    """Test emoji uniqueness is enforced when allow_emoji_reuse is 0."""
    # First participant claims 🚀
    r1 = client.post("/api/participants/register", json={"name": "Bob", "selected_emoji": "🚀"})
    assert r1.status_code == 201

    # Second participant attempts to claim 🚀
    r2 = client.post("/api/participants/register", json={"name": "Charlie", "selected_emoji": "🚀"})
    assert r2.status_code == 409
    assert "already selected" in r2.get_json()["error"]


def test_emoji_uniqueness_when_reuse_enabled(app, client):
    """Test emoji reuse allows multiple participants to pick the same emoji."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        sess = get_active_session(conn)
        conn.execute("UPDATE sessions SET allow_emoji_reuse = 1 WHERE id = ?", (sess["id"],))
        conn.commit()
        conn.close()

    r1 = client.post("/api/participants/register", json={"name": "Participant One", "selected_emoji": "🚀"})
    assert r1.status_code == 201

    r2 = client.post("/api/participants/register", json={"name": "Participant Two", "selected_emoji": "🚀"})
    assert r2.status_code == 201


def test_registration_when_closed(app, client):
    """Test registration attempt while registration status is closed."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        sess = get_active_session(conn)
        conn.execute("UPDATE sessions SET registration_status = 'closed' WHERE id = ?", (sess["id"],))
        conn.commit()
        conn.close()

    res = client.post("/api/participants/register", json={"name": "Late Comers", "selected_emoji": "🚀"})
    assert res.status_code == 403
    assert "closed" in res.get_json()["error"].lower()


def test_registration_at_participant_limit(app, client):
    """Test registration stops once expected_participants limit is reached."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        sess = get_active_session(conn)
        conn.execute("UPDATE sessions SET expected_participants = 2 WHERE id = ?", (sess["id"],))
        conn.commit()
        conn.close()

    # Participant 1
    r1 = client.post("/api/participants/register", json={"name": "P1", "selected_emoji": "🚀"})
    assert r1.status_code == 201

    # Participant 2
    r2 = client.post("/api/participants/register", json={"name": "P2", "selected_emoji": "⚡"})
    assert r2.status_code == 201

    # Participant 3 (exceeds limit 2)
    r3 = client.post("/api/participants/register", json={"name": "P3", "selected_emoji": "🔥"})
    assert r3.status_code == 403
    assert "limit" in r3.get_json()["error"].lower()


def test_participant_session_me_endpoint(client):
    """Test /api/participants/me securely identifies the current registered user."""
    # Before registration
    me_before = client.get("/api/participants/me")
    assert me_before.status_code == 200
    assert me_before.get_json()["data"] is None

    # Register
    reg = client.post("/api/participants/register", json={"name": "Diana Prince", "selected_emoji": "👑"})
    assert reg.status_code == 201

    # Now /api/participants/me returns the participant using the cookie set
    me_after = client.get("/api/participants/me")
    assert me_after.status_code == 200
    me_data = me_after.get_json()["data"]
    assert me_data["name"] == "Diana Prince"
    assert me_data["selected_emoji"] == "👑"
