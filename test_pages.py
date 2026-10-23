"""
Automated tests for frontend HTML templates rendering and HTTP page routes.
"""

def test_html_pages_render_successfully(client):
    """Test that all frontend pages render without syntax or template errors."""
    pages = [
        ("/", "Welcome to the Team Shuffle"),
        ("/emoji-selection", "Pick Your Team Avatar"),
        ("/waiting-room", "Waiting Room"),
        ("/results", "Official Team Rosters"),
        ("/admin/login", "Administrator Access")
    ]
    for url, text_marker in pages:
        res = client.get(url)
        assert res.status_code == 200
        assert text_marker in res.get_data(as_text=True)


def test_admin_dashboard_redirects_unauthenticated(client):
    """Test that accessing /admin/dashboard directly redirects to /admin/login when not authenticated."""
    res = client.get("/admin/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert "/admin/login" in res.headers["Location"]


def test_admin_dashboard_accessible_when_authenticated(admin_client):
    """Test that accessing /admin/dashboard succeeds for authenticated admin."""
    res = admin_client.get("/admin/dashboard")
    assert res.status_code == 200
    assert "Admin Dashboard" in res.get_data(as_text=True)
