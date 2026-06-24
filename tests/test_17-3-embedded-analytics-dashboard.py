"""Release 17.3 — Embedded Analytics Dashboard tests.

Tests run against the real Supabase database (via DATABASE_URL). Each test
creates its own user, logs in, exercises the analytics dashboard, and
tears down its data.

Test classes:
  TestRouteRemoval        — /analytics route returns 404
  TestNavRemoval          — Analytics nav link is gone from base.html
  TestDashboardRendering  — profile page contains dashboard markup
  TestEmptyState          — user with no expenses sees empty state
  TestAuthGuard           — unauthenticated access redirects to /login
  TestDataEmbedding       — trends and monthly data are embedded as JSON
  TestChartJSCDN          — Chart.js CDN script tag is present
  TestDashboardJS         — analytics-dashboard.js script tag is present
"""

import importlib
import uuid

import pytest
import psycopg2
import psycopg2.extras

import database.db as db_module
from database.db import get_db, create_user


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _unique_email(prefix="user"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.spendly.com"


def _create_user_and_get_id(email, password="password123"):
    name = email.split("@")[0].replace("-", " ").title()
    return create_user(name, email, password)


def _delete_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def _add_expense(user_id, amount, category, date_str, description=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (%s, %s, %s, %s, %s)",
        (user_id, amount, category, date_str, description),
    )
    conn.commit()
    cur.close()
    conn.close()


def _count_expenses(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["cnt"]


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app():
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_user():
    email = _unique_email("ead")
    password = "password123"
    user_id = _create_user_and_get_id(email, password)
    yield {"id": user_id, "email": email, "password": password}
    _delete_user(user_id)


@pytest.fixture
def auth_client(client, test_user):
    client.post("/login", data={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    return client


# ------------------------------------------------------------------ #
# 1. Route removal                                                     #
# ------------------------------------------------------------------ #

class TestRouteRemoval:
    def test_analytics_route_returns_404(self, auth_client):
        """The /analytics route must no longer exist."""
        resp = auth_client.get("/analytics")
        assert resp.status_code == 404, "/analytics should return 404"

    def test_analytics_post_returns_404(self, auth_client):
        """POST /analytics must no longer exist."""
        resp = auth_client.post("/analytics")
        assert resp.status_code == 404, "POST /analytics should return 404"


# ------------------------------------------------------------------ #
# 2. Nav removal                                                       #
# ------------------------------------------------------------------ #

class TestNavRemoval:
    def test_analytics_not_in_nav(self, auth_client):
        """The Analytics nav link must be removed."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert ">Analytics</a>" not in body, (
            "Analytics nav link must not appear anywhere in the page"
        )

    def test_analytics_not_in_mobile_nav(self, auth_client):
        """The Analytics nav link must be removed from mobile nav too."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="nav-mobile-menu"' in body, "Mobile menu must still exist"
        assert ">Analytics</a>" not in body


# ------------------------------------------------------------------ #
# 3. Dashboard rendering                                                #
# ------------------------------------------------------------------ #

class TestDashboardRendering:
    def test_dashboard_section_present(self, auth_client):
        """Profile page must contain the analytics dashboard section."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'class="analytics-dashboard"' in body, (
            "analytics-dashboard section must exist"
        )

    def test_dashboard_has_canvas(self, auth_client):
        """Dashboard must contain a canvas element for charts."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="analytics-chart"' in body, "canvas#analytics-chart must exist"

    def test_dashboard_has_trends_tab(self, auth_client):
        """Dashboard must have a Trends tab."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'data-view="trends"' in body, "Trends tab must exist"

    def test_dashboard_has_categories_tab(self, auth_client):
        """Dashboard must have a Categories tab."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'data-view="categories"' in body, "Categories tab must exist"

    def test_dashboard_has_monthly_tab(self, auth_client):
        """Dashboard must have a Monthly Comparison tab."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'data-view="monthly"' in body, "Monthly Comparison tab must exist"

    def test_dashboard_has_tablist_role(self, auth_client):
        """Tabs must be wrapped in a container with role=tablist."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'role="tablist"' in body, "Tabs must have role=tablist"

    def test_dashboard_between_card_and_filter(self, auth_client):
        """Dashboard must appear between the profile card and the filter bar."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        dashboard_pos = body.find('class="analytics-dashboard"')
        filter_pos = body.find('class="filter-bar"')
        card_pos = body.find('class="profile-card"')
        assert dashboard_pos > card_pos, "Dashboard must come after profile card"
        assert dashboard_pos < filter_pos, "Dashboard must come before filter bar"


# ------------------------------------------------------------------ #
# 4. Empty state                                                       #
# ------------------------------------------------------------------ #

class TestEmptyState:
    def test_empty_state_element_exists(self, auth_client):
        """The empty state paragraph must exist in the dashboard."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="analytics-empty"' in body, "Empty state element must exist"

    def test_empty_state_shown_when_no_expenses(self, auth_client, test_user):
        """When user has zero expenses, data-has-expenses should be false."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The test fixture creates a user with no expenses
        # Jinja2 may render with single or double quotes
        assert 'data-has-expenses' in body, "data-has-expenses attribute must exist"
        assert 'data-has-expenses="false"' in body or "data-has-expenses='false'" in body, (
            "data-has-expenses must be false when user has no expenses"
        )

    def test_empty_state_hidden_when_has_expenses(self, auth_client, test_user):
        """When user has expenses, data-has-expenses should be true."""
        _add_expense(test_user["id"], 50.00, "Food", "2026-06-20", "Lunch")
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'data-has-expenses' in body, "data-has-expenses attribute must exist"
        assert 'data-has-expenses="true"' in body or "data-has-expenses='true'" in body, (
            "data-has-expenses must be true when user has expenses"
        )


# ------------------------------------------------------------------ #
# 5. Auth guard                                                        #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_profile_redirects_when_not_logged_in(self, client):
        """Visiting /profile without auth must redirect to /login."""
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_profile_401_on_analytics_endpoint_without_auth(self, client):
        """The /analytics endpoint must not be accessible without auth."""
        resp = client.get("/analytics")
        # Should be 404 (route removed), not 302 or 500
        assert resp.status_code == 404


# ------------------------------------------------------------------ #
# 6. Data embedding                                                     #
# ------------------------------------------------------------------ #

class TestDataEmbedding:
    def test_trends_data_embedded(self, auth_client, test_user):
        """Trends data must be embedded as JSON in the dashboard container."""
        _add_expense(test_user["id"], 25.00, "Food", "2026-06-15", "Breakfast")
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "data-trends=" in body, "data-trends attribute must exist"
        # Verify it contains JSON array with date and total
        assert "2026-06-15" in body, "Trends data must include the expense date"

    def test_monthly_data_embedded(self, auth_client, test_user):
        """Monthly comparison data must be embedded as JSON."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "data-monthly=" in body, "data-monthly attribute must exist"
        # Should contain current_month and previous_month keys
        assert "current_month" in body, "Monthly data must include current_month"
        assert "previous_month" in body, "Monthly data must include previous_month"

    def test_categories_data_embedded(self, auth_client, test_user):
        """Category breakdown data must be embedded as JSON."""
        _add_expense(test_user["id"], 100.00, "Transport", "2026-06-18", "Bus pass")
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "data-categories=" in body, "data-categories attribute must exist"

    def test_trends_empty_array_when_no_expenses(self, auth_client, test_user):
        """Trends data should be an empty JSON array when user has no expenses."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "data-trends='[]'" in body, (
            "Trends must be empty array when user has no expenses"
        )


# ------------------------------------------------------------------ #
# 7. Chart.js CDN                                                      #
# ------------------------------------------------------------------ #

class TestChartJSCDN:
    def test_chartjs_cdn_present(self, auth_client):
        """The Chart.js CDN script tag must be present in the page."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "chart.js" in body, "Chart.js CDN must be loaded"
        assert "cdn.jsdelivr.net" in body, "Chart.js must be loaded from CDN"

    def test_chartjs_cdn_in_head(self, auth_client):
        """Chart.js CDN should appear before the page content."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        cdn_pos = body.find("chart.js")
        content_pos = body.find('<div class="profile-page">')
        assert cdn_pos < content_pos, "Chart.js CDN should load before page content"


# ------------------------------------------------------------------ #
# 8. Dashboard JS                                                      #
# ------------------------------------------------------------------ #

class TestDashboardJS:
    def test_dashboard_js_script_present(self, auth_client):
        """The analytics-dashboard.js script tag must be present."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "analytics-dashboard.js" in body, (
            "analytics-dashboard.js script tag must be present"
        )

    def test_dashboard_js_loads_after_content(self, auth_client):
        """Dashboard JS should load after the page content (before closing body)."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        js_pos = body.find("analytics-dashboard.js")
        content_pos = body.find('<div class="profile-page">')
        assert js_pos > content_pos, "Dashboard JS should load after page content"
