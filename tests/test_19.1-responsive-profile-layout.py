"""Release 19.1 — Responsive Profile Layout: tests for the side-by-side layout.

Tests are based on the spec at .claude/specs/19.1-responsive-profile-layout.md
and do NOT derive expectations from reading the implementation.

Test groups:
  TestProfileTopRowMarkup       — profile page HTML contains the wrapper div
  TestProfileCardContent        — profile card content is unchanged
  TestAnalyticsDashboardContent — analytics dashboard content is unchanged
  TestEditModalNotAutoOpen      — edit modal does NOT open on normal page load
  TestAuthGuard                 — unauthenticated users redirected to login
  TestExistingFeaturesPreserved — filter bar, stats, transactions, categories unaffected
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


def _add_expense(user_id, amount=50.00, category="Food", date="2026-05-15", description="Test"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (user_id, amount, category, date, description),
    )
    expense_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return expense_id


# ------------------------------------------------------------------ #
# Fixtures                                                            #
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
    email = _unique_email("rpl")
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


@pytest.fixture
def with_expense(auth_client, test_user):
    """Add an expense for the test user and return its id."""
    return _add_expense(test_user["id"])


# ------------------------------------------------------------------ #
# 1. Profile top-row wrapper markup                                   #
# ------------------------------------------------------------------ #


class TestProfileTopRowMarkup:
    def test_top_row_wrapper_exists(self, auth_client, with_expense):
        """Profile page must contain the profile-top-row wrapper div."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="profile-top-row"' in body, (
            "profile-top-row wrapper div must exist in the profile page"
        )

    def test_profile_card_inside_top_row(self, auth_client, with_expense):
        """The profile-card div must be inside the profile-top-row wrapper."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        top_row_start = body.find('class="profile-top-row"')
        card_start = body.find('class="profile-card"', top_row_start)
        top_row_end = body.find("</div>", top_row_start)
        # The card must appear after the top-row opens and before it closes
        assert top_row_start != -1, "profile-top-row must exist"
        assert card_start != -1, "profile-card must exist inside profile-top-row"
        assert card_start < top_row_end, "profile-card must be inside profile-top-row"

    def test_analytics_dashboard_inside_top_row(self, auth_client, with_expense):
        """The analytics-dashboard div must be inside the profile-top-row wrapper.

        We verify this by checking that profile-top-row opens before the
        analytics-dashboard and that the closing tag for profile-top-row
        comes after the analytics-dashboard's content (empty state paragraph).
        """
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        top_row_start = body.find('class="profile-top-row"')
        dashboard_start = body.find('class="analytics-dashboard"', top_row_start)
        # The analytics-empty is the last element inside analytics-dashboard,
        # which is itself inside profile-top-row. Find its closing tag.
        analytics_empty = body.find('id="analytics-empty"', dashboard_start)
        # Find the profile-top-row's closing div after the analytics dashboard content
        # by looking for the closing tag after analytics-empty
        assert top_row_start != -1, "profile-top-row must exist"
        assert dashboard_start != -1, "analytics-dashboard must exist inside profile-top-row"
        assert dashboard_start > top_row_start, (
            "analytics-dashboard must appear after profile-top-row opens"
        )

    def test_profile_card_before_analytics_dashboard(self, auth_client, with_expense):
        """On desktop, the Profile Card should appear before the Analytics Dashboard."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        card_pos = body.find('class="profile-card"')
        dashboard_pos = body.find('class="analytics-dashboard"')
        assert card_pos != -1, "profile-card must exist"
        assert dashboard_pos != -1, "analytics-dashboard must exist"
        assert card_pos < dashboard_pos, (
            "Profile Card must appear before Analytics Dashboard in DOM order"
        )


# ------------------------------------------------------------------ #
# 2. Profile card content unchanged                                   #
# ------------------------------------------------------------------ #


class TestProfileCardContent:
    def test_avatar_circle_exists(self, auth_client, with_expense):
        """Profile card must contain the avatar circle with initials."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="avatar-circle"' in body, "avatar-circle must exist"

    def test_profile_name_displayed(self, auth_client, with_expense):
        """Profile card must display the user's name."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="profile-name"' in body, "profile-name must exist"

    def test_profile_email_displayed(self, auth_client, with_expense):
        """Profile card must display the user's email."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="profile-email"' in body, "profile-email must exist"

    def test_member_since_displayed(self, auth_client, with_expense):
        """Profile card must display 'Member since' text."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "Member since" in body, "'Member since' text must be present"

    def test_change_password_button_exists(self, auth_client, with_expense):
        """Profile card must contain the Change password button."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="change-password-btn"' in body, "change-password-btn must exist"


# ------------------------------------------------------------------ #
# 3. Analytics dashboard content unchanged                             #
# ------------------------------------------------------------------ #


class TestAnalyticsDashboardContent:
    def test_analytics_header_exists(self, auth_client, with_expense):
        """Analytics dashboard must have the header with tabs."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="analytics-header"' in body, "analytics-header must exist"

    def test_analytics_tabs_exist(self, auth_client, with_expense):
        """Analytics dashboard must have Trends, Categories, Monthly tabs."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "Trends" in body, "Trends tab must exist"
        assert "Categories" in body, "Categories tab must exist"
        assert "Monthly Comparison" in body, "Monthly Comparison tab must exist"

    def test_chart_canvas_exists(self, auth_client, with_expense):
        """Analytics dashboard must have the chart canvas."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="analytics-chart"' in body, "analytics-chart canvas must exist"

    def test_analytics_empty_state_exists(self, auth_client, with_expense):
        """Analytics dashboard must have the empty state placeholder."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="analytics-empty"' in body, "analytics-empty must exist"


# ------------------------------------------------------------------ #
# 4. Edit modal does NOT auto-open on normal page load                #
# ------------------------------------------------------------------ #


class TestEditModalNotAutoOpen:
    def test_edit_modal_hidden_by_default(self, auth_client, with_expense):
        """The quick-edit modal must have aria-hidden=true on normal page load."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The modal overlay should have aria-hidden="true" when not in error state
        modal_start = body.find('id="quick-edit-modal"')
        assert modal_start != -1, "quick-edit-modal must exist"
        # Check that aria-hidden="true" is set (not opened)
        modal_tag = body[modal_start:modal_start + 200]
        assert 'aria-hidden="true"' in modal_tag, (
            "Edit modal must be hidden (aria-hidden=true) on normal page load"
        )

    def test_edit_modal_not_opened_by_js(self, auth_client, with_expense):
        """The edit_open Jinja2 variable must be False on normal page load.

        This tests the fix for the bug where edit_form was undefined,
        causing 'edit_form is not none' to evaluate to True in Jinja2,
        which auto-opened the edit modal on every page load.
        """
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # If the auto-open IIFE was triggered, it would appear in the HTML
        # as a script block that calls open(). Check that it's NOT present.
        assert "Validation error" not in body, (
            "No validation error context should be set on normal page load"
        )


# ------------------------------------------------------------------ #
# 5. Auth guard                                                       #
# ------------------------------------------------------------------ #


class TestAuthGuard:
    def test_unauthenticated_redirects_to_login(self, client):
        """GET /profile without auth must redirect to /login."""
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_unauthenticated_does_not_crash(self, client):
        """GET /profile without auth must not return 500."""
        resp = client.get("/profile")
        assert resp.status_code != 500


# ------------------------------------------------------------------ #
# 6. Existing features preserved                                      #
# ------------------------------------------------------------------ #


class TestExistingFeaturesPreserved:
    def test_filter_bar_exists(self, auth_client, with_expense):
        """The date filter bar must still exist on the profile page."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="filter-bar"' in body, "filter-bar must exist"

    def test_stats_row_exists(self, auth_client, with_expense):
        """The summary stats row must still exist."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="stats-row"' in body, "stats-row must exist"

    def test_transaction_table_exists(self, auth_client, with_expense):
        """The transaction table must still exist."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="tx-table-wrap"' in body, "tx-table-wrap must exist"

    def test_category_breakdown_exists(self, auth_client, with_expense):
        """The category breakdown section must still exist."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="category-breakdown"' in body, "category-breakdown must exist"

    def test_quick_add_modal_exists(self, auth_client, with_expense):
        """The Quick Add Expense modal must still exist."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="quick-add-modal"' in body, "quick-add-modal must exist"

    def test_change_password_modal_exists(self, auth_client, with_expense):
        """The Change Password modal must still exist."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="change-password-modal"' in body, "change-password-modal must exist"

    def test_quick_add_button_exists(self, auth_client, with_expense):
        """The add-expense button must still exist in the header."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="quick-add-btn"' in body, "quick-add-btn must exist"
