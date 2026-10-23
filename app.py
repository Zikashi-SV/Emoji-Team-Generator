"""
Emoji Team Generator - Main Flask Application.
Provides RESTful JSON APIs and serves frontend templates.
"""

import datetime
import secrets
import sqlite3
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
    g
)
from config import Config
from database import (
    get_db,
    close_db,
    init_db,
    get_active_session,
    normalize_participant_name
)
from auth import (
    admin_required,
    verify_admin_credentials,
    is_login_rate_limited,
    record_failed_login,
    clear_failed_logins,
    get_current_admin,
    get_current_participant,
    init_default_admin
)
from team_allocator import (
    generate_and_save_teams,
    get_session_teams_with_members
)


def create_app(config_class=Config):
    """Application factory for Emoji Team Generator."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Initialize tables and default admin if configured
    with app.app_context():
        init_db(app)
        init_default_admin(app)

    # -------------------------------------------------------------
    # HTML Page Routes
    # -------------------------------------------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/emoji-selection")
    def emoji_selection_page():
        return render_template("emoji-selection.html")

    @app.route("/waiting-room")
    def waiting_room_page():
        return render_template("waiting-room.html")

    @app.route("/results")
    def results_page():
        return render_template("results.html")

    @app.route("/admin/login")
    def admin_login_page():
        if get_current_admin():
            return redirect(url_for("admin_dashboard_page"))
        return render_template("admin-login.html")

    @app.route("/admin/dashboard")
    @admin_required
    def admin_dashboard_page():
        return render_template("admin-dashboard.html")

    # -------------------------------------------------------------
    # Public Participant & Session APIs
    # -------------------------------------------------------------
    @app.route("/api/health", methods=["GET"])
    def api_health():
        return jsonify({
            "success": True,
            "status": "healthy",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }), 200

    @app.route("/api/session", methods=["GET"])
    def api_get_session():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session found."}), 404

        # Count registered participants
        count_row = db.execute(
            "SELECT COUNT(*) as count FROM participants WHERE session_id = ?",
            (sess["id"],)
        ).fetchone()
        participant_count = count_row["count"] if count_row else 0

        return jsonify({
            "success": True,
            "data": {
                "id": sess["id"],
                "session_name": sess["session_name"],
                "expected_participants": sess["expected_participants"],
                "participant_count": participant_count,
                "team_count": sess["team_count"],
                "max_team_size": sess["max_team_size"],
                "team_formation_mode": sess["team_formation_mode"],
                "registration_status": sess["registration_status"],
                "allow_emoji_reuse": bool(sess["allow_emoji_reuse"]),
                "results_published": bool(sess["results_published"])
            }
        }), 200

    @app.route("/api/emojis", methods=["GET"])
    def api_get_emojis():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session found."}), 404

        # Query all selected emojis in this session
        taken_rows = db.execute(
            "SELECT selected_emoji FROM participants WHERE session_id = ?",
            (sess["id"],)
        ).fetchall()
        taken_emojis = {r["selected_emoji"] for r in taken_rows}

        allow_reuse = bool(sess["allow_emoji_reuse"])

        catalog = []
        for item in app.config["CURATED_EMOJIS"]:
            is_taken = item["emoji"] in taken_emojis
            catalog.append({
                "emoji": item["emoji"],
                "label": item["label"],
                "category": item["category"],
                "available": True if allow_reuse else (not is_taken)
            })

        return jsonify({
            "success": True,
            "data": {
                "allow_emoji_reuse": allow_reuse,
                "emojis": catalog
            }
        }), 200

    @app.route("/api/participants/register", methods=["POST"])
    def api_register_participant():
        data = request.get_json(silent=True) or {}
        raw_name = data.get("name", "")
        selected_emoji = data.get("selected_emoji", "")

        # 1. Validate name input
        if not isinstance(raw_name, str):
            return jsonify({"success": False, "error": "Name must be a valid text string."}), 400

        name = raw_name.strip()
        if not name:
            return jsonify({"success": False, "error": "Name cannot be empty or whitespace only."}), 400

        if len(name) < 2:
            return jsonify({"success": False, "error": "Name must be at least 2 characters long."}), 400

        if len(name) > 50:
            return jsonify({"success": False, "error": "Name cannot exceed 50 characters."}), 400

        # 2. Validate emoji input
        curated_chars = {item["emoji"] for item in app.config["CURATED_EMOJIS"]}
        if not selected_emoji or selected_emoji not in curated_chars:
            return jsonify({"success": False, "error": "Please select a valid emoji from the curated collection."}), 400

        db = get_db()

        try:
            # Begin transaction
            with db:
                sess = get_active_session(db)
                if not sess:
                    return jsonify({"success": False, "error": "No active event session found."}), 404

                # 3. Check registration open/closed status
                if sess["registration_status"] != "open":
                    return jsonify({"success": False, "error": "Registration is currently closed by the administrator."}), 403

                # 4. Check participant capacity limit
                count_row = db.execute(
                    "SELECT COUNT(*) as count FROM participants WHERE session_id = ?",
                    (sess["id"],)
                ).fetchone()
                current_count = count_row["count"] if count_row else 0
                expected_limit = sess["expected_participants"]

                if expected_limit and current_count >= expected_limit:
                    return jsonify({
                        "success": False,
                        "error": f"Registration is full! The limit of {expected_limit} participants has been reached."
                    }), 403

                # 5. Check duplicate normalized name
                normalized = normalize_participant_name(name)
                existing_name = db.execute(
                    "SELECT id FROM participants WHERE session_id = ? AND normalized_name = ?",
                    (sess["id"], normalized)
                ).fetchone()
                if existing_name:
                    return jsonify({
                        "success": False,
                        "error": f"The name '{name}' is already registered in this session. Please choose a different name."
                    }), 409

                # 6. Check emoji uniqueness (if reuse is disabled)
                if not sess["allow_emoji_reuse"]:
                    existing_emoji = db.execute(
                        "SELECT id FROM participants WHERE session_id = ? AND selected_emoji = ?",
                        (sess["id"], selected_emoji)
                    ).fetchone()
                    if existing_emoji:
                        return jsonify({
                            "success": False,
                            "error": f"The emoji {selected_emoji} is already selected by another participant. Please pick a different emoji."
                        }), 409

                # 7. Insert participant record with unique token
                token = secrets.token_urlsafe(32)
                cur = db.execute("""
                    INSERT INTO participants (session_id, name, normalized_name, selected_emoji, token)
                    VALUES (?, ?, ?, ?, ?)
                """, (sess["id"], name, normalized, selected_emoji, token))
                participant_id = cur.lastrowid

            # Prepare successful response and set secure cookie
            resp = jsonify({
                "success": True,
                "data": {
                    "participant": {
                        "id": participant_id,
                        "name": name,
                        "selected_emoji": selected_emoji,
                        "token": token
                    }
                }
            })
            resp.set_cookie(
                app.config["PARTICIPANT_COOKIE_NAME"],
                token,
                max_age=app.config["PARTICIPANT_COOKIE_MAX_AGE"],
                httponly=True,
                samesite="Lax",
                secure=app.config["SESSION_COOKIE_SECURE"]
            )
            return resp, 201

        except sqlite3.IntegrityError:
            return jsonify({
                "success": False,
                "error": "A registration conflict occurred with this name or emoji. Please try again."
            }), 409

    @app.route("/api/participants/me", methods=["GET"])
    def api_get_current_participant():
        participant = get_current_participant()
        if not participant:
            return jsonify({"success": True, "data": None}), 200

        db = get_db()
        sess = get_active_session(db)
        results_published = bool(sess["results_published"]) if sess else False

        # Only reveal team assignment if results are published
        team_name = participant["team_name"] if results_published else None

        return jsonify({
            "success": True,
            "data": {
                "id": participant["id"],
                "name": participant["name"],
                "selected_emoji": participant["selected_emoji"],
                "team_id": participant["team_id"] if results_published else None,
                "team_name": team_name,
                "created_at": participant["created_at"]
            }
        }), 200

    @app.route("/api/results", methods=["GET"])
    def api_get_results():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session found."}), 404

        if not sess["results_published"]:
            return jsonify({
                "success": False,
                "error": "Team results have not been published by the administrator yet."
            }), 403

        teams_data = get_session_teams_with_members(sess["id"], conn=db)

        return jsonify({
            "success": True,
            "data": {
                "session_name": sess["session_name"],
                "published": True,
                "teams": teams_data
            }
        }), 200

    # -------------------------------------------------------------
    # Administrator Authentication APIs
    # -------------------------------------------------------------
    @app.route("/api/admin/login", methods=["POST"])
    def api_admin_login():
        client_ip = request.remote_addr or "127.0.0.1"

        if is_login_rate_limited(client_ip):
            return jsonify({
                "success": False,
                "error": "Too many failed login attempts. Please wait 5 minutes before trying again."
            }), 429

        data = request.get_json(silent=True) or {}
        username = data.get("username", "")
        password = data.get("password", "")

        admin = verify_admin_credentials(username, password)
        if not admin:
            record_failed_login(client_ip)
            return jsonify({
                "success": False,
                "error": "Invalid username or password."
            }), 401

        # Clear failed attempts on success
        clear_failed_logins(client_ip)

        # Establish authenticated session
        session["admin_id"] = admin["id"]
        session["admin_username"] = admin["username"]
        session["csrf_token"] = secrets.token_hex(32)

        return jsonify({
            "success": True,
            "data": {
                "username": admin["username"],
                "csrf_token": session["csrf_token"]
            }
        }), 200

    @app.route("/api/admin/logout", methods=["POST"])
    def api_admin_logout():
        session.clear()
        return jsonify({"success": True, "message": "Logged out successfully."}), 200

    @app.route("/api/admin/me", methods=["GET"])
    @admin_required
    def api_admin_me():
        admin = get_current_admin()
        return jsonify({
            "success": True,
            "data": {
                "id": admin["id"],
                "username": admin["username"],
                "csrf_token": session.get("csrf_token")
            }
        }), 200

    # -------------------------------------------------------------
    # Administrator Dashboard & Management APIs
    # -------------------------------------------------------------
    @app.route("/api/admin/dashboard", methods=["GET"])
    @admin_required
    def api_admin_dashboard():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        count_row = db.execute(
            "SELECT COUNT(*) as count FROM participants WHERE session_id = ?",
            (sess["id"],)
        ).fetchone()
        participant_count = count_row["count"] if count_row else 0

        teams_count_row = db.execute(
            "SELECT COUNT(*) as count FROM teams WHERE session_id = ?",
            (sess["id"],)
        ).fetchone()
        team_count = teams_count_row["count"] if teams_count_row else 0

        return jsonify({
            "success": True,
            "data": {
                "session": {
                    "id": sess["id"],
                    "session_name": sess["session_name"],
                    "expected_participants": sess["expected_participants"],
                    "team_count": sess["team_count"],
                    "max_team_size": sess["max_team_size"],
                    "team_formation_mode": sess["team_formation_mode"],
                    "registration_status": sess["registration_status"],
                    "allow_emoji_reuse": bool(sess["allow_emoji_reuse"]),
                    "results_published": bool(sess["results_published"]),
                    "created_at": sess["created_at"],
                    "updated_at": sess["updated_at"]
                },
                "participant_count": participant_count,
                "generated_teams_count": team_count,
                "csrf_token": session.get("csrf_token")
            }
        }), 200

    @app.route("/api/admin/participants", methods=["GET"])
    @admin_required
    def api_admin_participants():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        rows = db.execute("""
            SELECT p.id, p.name, p.selected_emoji, p.created_at, p.team_id, t.team_name
            FROM participants p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.session_id = ?
            ORDER BY p.id DESC
        """, (sess["id"],)).fetchall()

        participants = [dict(r) for r in rows]
        return jsonify({
            "success": True,
            "data": {
                "total": len(participants),
                "participants": participants
            }
        }), 200

    @app.route("/api/admin/participants/<int:participant_id>", methods=["DELETE"])
    @admin_required
    def api_admin_delete_participant(participant_id: int):
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        with db:
            row = db.execute(
                "SELECT id, name FROM participants WHERE id = ? AND session_id = ?",
                (participant_id, sess["id"])
            ).fetchone()

            if not row:
                return jsonify({"success": False, "error": "Participant not found."}), 404

            db.execute("DELETE FROM participants WHERE id = ? AND session_id = ?", (participant_id, sess["id"]))

        return jsonify({
            "success": True,
            "message": f"Participant '{row['name']}' was removed successfully."
        }), 200

    @app.route("/api/admin/session/config", methods=["PATCH"])
    @admin_required
    def api_admin_update_config():
        data = request.get_json(silent=True) or {}
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        session_name = data.get("session_name")
        expected_participants = data.get("expected_participants")
        team_count = data.get("team_count")
        max_team_size = data.get("max_team_size")
        allow_emoji_reuse = data.get("allow_emoji_reuse")
        team_formation_mode = data.get("team_formation_mode")

        updates = []
        params = []

        if session_name is not None:
            name_clean = str(session_name).strip()
            if not name_clean:
                return jsonify({"success": False, "error": "Session name cannot be empty."}), 400
            updates.append("session_name = ?")
            params.append(name_clean)

        if expected_participants is not None:
            try:
                exp_int = int(expected_participants)
                if exp_int < 1:
                    raise ValueError
                updates.append("expected_participants = ?")
                params.append(exp_int)
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Expected participants must be a positive integer."}), 400

        if team_count is not None:
            try:
                tc_int = int(team_count)
                if tc_int < 1:
                    raise ValueError
                updates.append("team_count = ?")
                params.append(tc_int)
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Number of teams must be a positive integer."}), 400

        if max_team_size is not None:
            try:
                mts_int = int(max_team_size)
                if mts_int < 1:
                    raise ValueError
                updates.append("max_team_size = ?")
                params.append(mts_int)
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Maximum team size must be a positive integer."}), 400

        if allow_emoji_reuse is not None:
            updates.append("allow_emoji_reuse = ?")
            params.append(1 if allow_emoji_reuse else 0)

        if team_formation_mode is not None:
            if team_formation_mode not in ("team_count", "max_size"):
                return jsonify({"success": False, "error": "Invalid team formation mode."}), 400
            updates.append("team_formation_mode = ?")
            params.append(team_formation_mode)

        if not updates:
            return jsonify({"success": False, "error": "No configuration parameters provided for update."}), 400

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(sess["id"])

        sql = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
        with db:
            db.execute(sql, tuple(params))

        updated_sess = get_active_session(db)
        return jsonify({
            "success": True,
            "message": "Session configuration updated successfully.",
            "data": {
                "session_name": updated_sess["session_name"],
                "expected_participants": updated_sess["expected_participants"],
                "team_count": updated_sess["team_count"],
                "max_team_size": updated_sess["max_team_size"],
                "allow_emoji_reuse": bool(updated_sess["allow_emoji_reuse"]),
                "team_formation_mode": updated_sess["team_formation_mode"]
            }
        }), 200

    @app.route("/api/admin/session/registration", methods=["POST"])
    @admin_required
    def api_admin_toggle_registration():
        data = request.get_json(silent=True) or {}
        status = data.get("status")
        if status not in ("open", "closed"):
            return jsonify({"success": False, "error": "Status must be either 'open' or 'closed'."}), 400

        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        with db:
            db.execute(
                "UPDATE sessions SET registration_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, sess["id"])
            )

        return jsonify({
            "success": True,
            "message": f"Registration is now {status}.",
            "data": {"registration_status": status}
        }), 200

    @app.route("/api/admin/teams/generate", methods=["POST"])
    @admin_required
    def api_admin_generate_teams():
        data = request.get_json(silent=True) or {}
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        mode = data.get("mode") or sess["team_formation_mode"] or "team_count"
        team_count = data.get("team_count") or sess["team_count"] or 4
        max_team_size = data.get("max_team_size") or sess["max_team_size"] or 5

        try:
            team_count = int(team_count)
            max_team_size = int(max_team_size)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Team settings must be integers."}), 400

        try:
            teams, total_assigned = generate_and_save_teams(
                session_id=sess["id"],
                mode=mode,
                team_count=team_count,
                max_team_size=max_team_size,
                conn=db
            )
            return jsonify({
                "success": True,
                "message": f"Successfully generated {len(teams)} teams for {total_assigned} participants.",
                "data": {
                    "teams": teams,
                    "total_assigned": total_assigned,
                    "published": bool(sess["results_published"])
                }
            }), 200
        except ValueError as val_err:
            return jsonify({"success": False, "error": str(val_err)}), 400
        except Exception as exc:
            return jsonify({"success": False, "error": f"Failed to generate teams: {exc}"}), 500

    @app.route("/api/admin/teams", methods=["GET"])
    @admin_required
    def api_admin_get_teams():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        teams = get_session_teams_with_members(sess["id"], conn=db)
        return jsonify({
            "success": True,
            "data": {
                "teams": teams,
                "published": bool(sess["results_published"]),
                "session_name": sess["session_name"]
            }
        }), 200

    @app.route("/api/admin/teams/publish", methods=["POST"])
    @admin_required
    def api_admin_publish_teams():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        # Verify teams exist before publishing
        teams = get_session_teams_with_members(sess["id"], conn=db)
        if not teams:
            return jsonify({"success": False, "error": "No teams generated yet. Please generate teams before publishing."}), 400

        with db:
            db.execute(
                "UPDATE sessions SET results_published = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (sess["id"],)
            )

        return jsonify({
            "success": True,
            "message": "Team results have been published successfully!",
            "data": {"results_published": True}
        }), 200

    @app.route("/api/admin/teams/unpublish", methods=["POST"])
    @admin_required
    def api_admin_unpublish_teams():
        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        with db:
            db.execute(
                "UPDATE sessions SET results_published = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (sess["id"],)
            )

        return jsonify({
            "success": True,
            "message": "Team results are now hidden from participants.",
            "data": {"results_published": False}
        }), 200

    @app.route("/api/admin/session/reset", methods=["POST"])
    @admin_required
    def api_admin_reset_session():
        data = request.get_json(silent=True) or {}
        if not data.get("confirm"):
            return jsonify({
                "success": False,
                "error": "Explicit confirmation is required to reset the session. Set confirm: true."
            }), 400

        db = get_db()
        sess = get_active_session(db)
        if not sess:
            return jsonify({"success": False, "error": "No active session."}), 404

        with db:
            # Delete participants and teams for this session
            db.execute("DELETE FROM participants WHERE session_id = ?", (sess["id"],))
            db.execute("DELETE FROM teams WHERE session_id = ?", (sess["id"],))
            # Reset session state
            db.execute("""
                UPDATE sessions
                SET results_published = 0,
                    registration_status = 'open',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (sess["id"],))

        return jsonify({
            "success": True,
            "message": "Session has been reset successfully. All participants and teams have been cleared."
        }), 200

    # -------------------------------------------------------------
    # Generic Error Handlers returning JSON for API requests
    # -------------------------------------------------------------
    @app.errorhandler(400)
    def handle_bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Bad request. Please verify your submission."}), 400
        return "Bad Request", 400

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Resource not found."}), 404
        return render_template("index.html"), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Method not allowed on this endpoint."}), 405
        return "Method Not Allowed", 405

    @app.errorhandler(500)
    def handle_server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "An internal server error occurred."}), 500
        return "Internal Server Error", 500

    return app


# Default app instance
app = create_app()

if __name__ == "__main__":
    import socket

    def get_local_ip():
        """Finds the local IP address of this machine."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't actually send packets, just determines the routing interface IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    local_ip = get_local_ip()

    print("=" * 65)
    print("🚀 Emoji Team Generator is running!")
    print("=" * 65)
    print("👉 On YOUR laptop:")
    print("   Participant view: http://localhost:5000")
    print("   Admin panel:      http://localhost:5000/admin/login")
    print("-" * 65)
    print("📱 On your FRIENDS' phones / laptops (Same Wi-Fi or Hotspot):")
    print(f"   Participant view: http://{local_ip}:5000")
    print(f"   Admin panel:      http://{local_ip}:5000/admin/login")
    print("=" * 65)

    # Listen on 0.0.0.0 so devices on your Wi-Fi / Hotspot can connect
    app.run(host="0.0.0.0", port=5000, debug=True)
