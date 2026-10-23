"""
Automated tests for administrator authentication, rate limiting, and access control.
"""

from database import connect_db
from auth import create_admin_account


def test_password_hash_stored_not_plaintext(app):
    """Verify that admin passwords are encrypted with salted hashes, not stored in plaintext."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        raw_password = "SuperSecretAdminPassword99!"
        create_admin_account("secure_admin", raw_password, conn=conn)

        row = conn.execute("SELECT password_hash FROM admins WHERE username = 'secure_admin'").fetchone()
        stored_hash = row["password_hash"]
        assert stored_hash != raw_password
        assert stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:")
        conn.close()


def test_successful_admin_login_and_logout(app, client):
    """Test successful login, session token generation, and logout."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        create_admin_account("chief", "ChiefPass456!", conn=conn)
        conn.close()

    # Successful login
    login_res = client.post("/api/admin/login", json={
        "username": "chief",
        "password": "ChiefPass456!"
    })
    assert login_res.status_code == 200
    login_data = login_res.get_json()["data"]
    assert login_data["username"] == "chief"
    assert "csrf_token" in login_data

    # Check /api/admin/me
    me_res = client.get("/api/admin/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["data"]["username"] == "chief"

    # Logout
    logout_res = client.post("/api/admin/logout")
    assert logout_res.status_code == 200

    # Protected endpoint should now fail
    me_after_logout = client.get("/api/admin/me")
    assert me_after_logout.status_code == 401


def test_incorrect_password_rejected(app, client):
    """Test rejection with generic error when wrong password is supplied."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        create_admin_account("boss", "ValidPassword123!", conn=conn)
        conn.close()

    res = client.post("/api/admin/login", json={
        "username": "boss",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "invalid username or password" in res.get_json()["error"].lower()


def test_nonexistent_user_rejected(client):
    """Test rejection with same generic error when username does not exist."""
    res = client.post("/api/admin/login", json={
        "username": "ghost_admin",
        "password": "SomePassword!"
    })
    assert res.status_code == 401
    assert "invalid username or password" in res.get_json()["error"].lower()


def test_protected_endpoints_inaccessible_without_auth(client):
    """Test that all admin endpoints refuse unauthenticated requests."""
    assert client.get("/api/admin/dashboard").status_code == 401
    assert client.get("/api/admin/participants").status_code == 401
    assert client.post("/api/admin/teams/generate", json={}).status_code == 401
    assert client.post("/api/admin/teams/publish", json={}).status_code == 401
    assert client.post("/api/admin/session/reset", json={}).status_code == 401


def test_participant_token_cannot_access_admin_endpoints(client):
    """Test that a participant session/token does NOT confer admin privileges."""
    # Register participant
    reg = client.post("/api/participants/register", json={"name": "Regular User", "selected_emoji": "🦊"})
    assert reg.status_code == 201

    # Attempt to access admin dashboard with participant cookie
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401


def test_csrf_protection_on_admin_state_changing_requests(app, client):
    """Test that state-changing requests require a valid CSRF token header."""
    with app.app_context():
        conn = connect_db(app.config["DATABASE_PATH"])
        create_admin_account("csrf_admin", "AdminPass123!", conn=conn)
        conn.close()

    # Login to get session
    login_res = client.post("/api/admin/login", json={
        "username": "csrf_admin",
        "password": "AdminPass123!"
    })
    csrf_token = login_res.get_json()["data"]["csrf_token"]

    # Request without CSRF token header should fail with 403
    res_no_csrf = client.post("/api/admin/session/registration", json={"status": "closed"})
    assert res_no_csrf.status_code == 403
    assert "csrf" in res_no_csrf.get_json()["error"].lower()

    # Request with invalid CSRF token header should fail with 403
    res_bad_csrf = client.post(
        "/api/admin/session/registration",
        json={"status": "closed"},
        headers={"X-CSRF-Token": "invalid-token-here"}
    )
    assert res_bad_csrf.status_code == 403

    # Request with correct CSRF token header should succeed
    res_valid_csrf = client.post(
        "/api/admin/session/registration",
        json={"status": "closed"},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert res_valid_csrf.status_code == 200
