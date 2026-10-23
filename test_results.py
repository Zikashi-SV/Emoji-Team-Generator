"""
Automated tests for publishing results, access controls, unpublishing,
participant removal, and session resets.
"""


def test_results_hidden_before_publication(client, admin_client):
    """Test /api/results returns 403 Forbidden before publication."""
    # Register 2 participants and generate teams
    client.post("/api/participants/register", json={"name": "Alice", "selected_emoji": "🚀"})
    client.post("/api/participants/register", json={"name": "Bob", "selected_emoji": "⚡"})

    admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 2},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )

    # Public results endpoint should be forbidden
    public_res = client.get("/api/results")
    assert public_res.status_code == 403
    assert "not been published" in public_res.get_json()["error"].lower()

    # Admin can preview teams even before publication
    admin_preview = admin_client.get("/api/admin/teams")
    assert admin_preview.status_code == 200
    assert len(admin_preview.get_json()["data"]["teams"]) == 2


def test_results_accessible_after_publication(client, admin_client):
    """Test /api/results becomes accessible after admin publishes."""
    client.post("/api/participants/register", json={"name": "Alice", "selected_emoji": "🚀"})
    client.post("/api/participants/register", json={"name": "Bob", "selected_emoji": "⚡"})

    admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 2},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )

    # Publish
    pub_res = admin_client.post(
        "/api/admin/teams/publish",
        json={},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert pub_res.status_code == 200

    # Public results now return 200
    public_res = client.get("/api/results")
    assert public_res.status_code == 200
    data = public_res.get_json()["data"]
    assert data["published"] is True
    assert len(data["teams"]) == 2

    # Unpublish
    unpub_res = admin_client.post(
        "/api/admin/teams/unpublish",
        json={},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert unpub_res.status_code == 200

    # Should be hidden again
    assert client.get("/api/results").status_code == 403


def test_participant_removal_frees_name_and_emoji(client, admin_client):
    """Test removing a participant allows their name and emoji to be used again."""
    reg = client.post("/api/participants/register", json={"name": "Charlie", "selected_emoji": "🦄"})
    assert reg.status_code == 201
    p_id = reg.get_json()["data"]["participant"]["id"]

    # Trying to register again with same name fails
    assert client.post("/api/participants/register", json={"name": "Charlie", "selected_emoji": "🦁"}).status_code == 409

    # Admin removes participant
    del_res = admin_client.delete(
        f"/api/admin/participants/{p_id}",
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert del_res.status_code == 200

    # Now registration with same name and emoji succeeds
    r2 = client.post("/api/participants/register", json={"name": "Charlie", "selected_emoji": "🦄"})
    assert r2.status_code == 201


def test_session_reset(client, admin_client):
    """Test full session reset clears participants, teams, and resets publication state."""
    # Register participant
    client.post("/api/participants/register", json={"name": "Dan", "selected_emoji": "🦁"})

    # Generate and publish teams
    admin_client.post(
        "/api/admin/teams/generate",
        json={"mode": "team_count", "team_count": 1},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    admin_client.post(
        "/api/admin/teams/publish",
        json={},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )

    # Reset without confirmation rejected
    bad_reset = admin_client.post(
        "/api/admin/session/reset",
        json={},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert bad_reset.status_code == 400

    # Reset with confirmation
    reset_res = admin_client.post(
        "/api/admin/session/reset",
        json={"confirm": True},
        headers={"X-CSRF-Token": admin_client.csrf_token}
    )
    assert reset_res.status_code == 200

    # Session status check
    sess_res = client.get("/api/session")
    sess_data = sess_res.get_json()["data"]
    assert sess_data["participant_count"] == 0
    assert sess_data["results_published"] is False
    assert sess_data["registration_status"] == "open"

    # Results check
    assert client.get("/api/results").status_code == 403
