"""
Authentication and authorization module for Emoji Team Generator.
Handles admin hashing, session checks, CSRF validation, rate limiting,
and participant identity token resolution.
"""

import time
import secrets
from functools import wraps
from flask import session, request, jsonify, g, current_app, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, get_active_session

# In-memory tracking of failed login attempts for rate limiting:
# ip_address -> list of timestamp floats
_failed_login_attempts = {}


def record_failed_login(ip_address: str):
    """Records a failed login attempt for the given IP address."""
    now = time.time()
    attempts = _failed_login_attempts.get(ip_address, [])
    # Filter attempts within window
    window = current_app.config.get("ADMIN_RATE_LIMIT_WINDOW_SECONDS", 300)
    attempts = [t for t in attempts if now - t < window]
    attempts.append(now)
    _failed_login_attempts[ip_address] = attempts


def is_login_rate_limited(ip_address: str) -> bool:
    """Checks whether the IP address has exceeded the maximum allowed failed attempts."""
    now = time.time()
    max_attempts = current_app.config.get("ADMIN_RATE_LIMIT_MAX_ATTEMPTS", 5)
    window = current_app.config.get("ADMIN_RATE_LIMIT_WINDOW_SECONDS", 300)

    attempts = _failed_login_attempts.get(ip_address, [])
    valid_attempts = [t for t in attempts if now - t < window]
    _failed_login_attempts[ip_address] = valid_attempts
    return len(valid_attempts) >= max_attempts


def clear_failed_logins(ip_address: str):
    """Clears failed login history upon successful authentication."""
    _failed_login_attempts.pop(ip_address, None)


def create_admin_account(username: str, password: str, conn=None) -> bool:
    """
    Creates an admin account with salted password hash.
    Returns True if created, False if username already exists.
    """
    if not username or not password or len(password) < 6:
        raise ValueError("Admin username must be provided and password must be at least 6 characters.")

    db = conn or get_db()
    hashed = generate_password_hash(password)
    try:
        with db:
            db.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (username.strip(), hashed)
            )
        return True
    except Exception:
        return False


def verify_admin_credentials(username: str, password: str, conn=None):
    """
    Verifies admin credentials securely.
    Returns admin row dict if valid, or None if invalid.
    """
    if not username or not password:
        return None

    db = conn or get_db()
    row = db.execute(
        "SELECT id, username, password_hash FROM admins WHERE username = ? COLLATE NOCASE",
        (username.strip(),)
    ).fetchone()

    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def get_current_admin():
    """Returns the currently logged-in admin dict, or None."""
    admin_id = session.get("admin_id")
    if not admin_id:
        return None

    db = get_db()
    row = db.execute("SELECT id, username, created_at FROM admins WHERE id = ?", (admin_id,)).fetchone()
    return dict(row) if row else None


def admin_required(view_func):
    """
    Decorator to protect administrative endpoints.
    Returns 401 JSON error for API requests or redirects to login for page routes.
    """
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        admin = get_current_admin()
        if not admin:
            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please log in as an administrator."
                }), 401
            return redirect(url_for("admin_login_page"))

        # Verify CSRF for state-changing admin requests
        if request.method in ("POST", "PATCH", "DELETE", "PUT") and request.path.startswith("/api/admin/"):
            # Exclude login endpoint from CSRF session check
            if request.path != "/api/admin/login":
                req_csrf = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
                session_csrf = session.get("csrf_token")
                if not session_csrf or not req_csrf or not secrets.compare_digest(req_csrf, session_csrf):
                    return jsonify({
                        "success": False,
                        "error": "Invalid or missing CSRF token. Please refresh and try again."
                    }), 403

        g.admin = admin
        return view_func(*args, **kwargs)
    return decorated_function


def get_current_participant():
    """
    Resolves the participant associated with the current request via cookie or Authorization header.
    Only returns participants who belong to the current active session.
    """
    token = request.cookies.get(current_app.config["PARTICIPANT_COOKIE_NAME"])
    auth_header = request.headers.get("Authorization")
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if not token:
        return None

    db = get_db()
    active_session = get_active_session(db)
    if not active_session:
        return None

    row = db.execute("""
        SELECT p.id, p.session_id, p.name, p.normalized_name, p.selected_emoji,
               p.token, p.team_id, p.created_at, t.team_name
        FROM participants p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.token = ? AND p.session_id = ?
    """, (token, active_session["id"])).fetchone()

    return dict(row) if row else None


def init_default_admin(app):
    """
    Auto-provisions the initial admin account if configured in environment
    and no admin exists in the database.
    """
    username = app.config.get("INITIAL_ADMIN_USERNAME")
    password = app.config.get("INITIAL_ADMIN_PASSWORD")
    if not username or not password:
        return

    with app.app_context():
        db = get_db()
        count = db.execute("SELECT COUNT(*) as cnt FROM admins").fetchone()["cnt"]
        if count == 0:
            create_admin_account(username, password, conn=db)
            print(f"[AUTH] Initial administrator account '{username}' created successfully.")
