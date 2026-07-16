"""Release 20.1 — Profile Card Layout & Dropdown Updates.

Tests run against the real Supabase database (via DATABASE_URL). Each test
creates its own user, logs in, exercises the profile UI, and tears down its
data. All assertions are based on the spec at
.claude/specs/20.1-profile-card-layout-dropdown-updates.md — not on the
implementation.

Test classes:
  TestDropdownIconsDistinct      — trigger icon differs from "My Profile" icon
  TestDropdownItemsThree         — dropdown has My Profile, Change Password, Log Out in order
  TestChangePasswordReachable    — modal markup present and trigger wired to navbar
  TestProfileCardStatRows        — profile card contains the three stat rows
  TestOldElementsRemoved         — old button + standalone stats-row are gone
  TestAuthGuard                  — anonymous users redirected to /login
  TestStatValuesWithExpenses     — stat values render correctly with expenses
  TestStatValuesZeroExpenses     — graceful degradation with zero expenses
"""

import importlib
import uuid

import pytest

import database.db as db_module
from database.db import get_db, create_user, init_db

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _unique_email(prefix="user"):
    """Return a unique email so tests don't collide in the shared DB."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.spendly.com"


def _create_user_and_get_id(email, password="password123"):
    """Create a user in the DB and return the user id."""
    name = email.split("@")[0].replace("-", " ").title()
    return create_user(name, email, password)


def _delete_user(user_id):
    """Remove a user and their expenses (cascade) from the DB."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def _add_expense(user_id, amount, category, expense_date, description="test"):
    """Insert an expense for the given user."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (%s, %s, %s, %s, %s)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    cur.close()
    conn.close()


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #


@pytest.fixture
def app():
    """Ensure the app module is initialised."""
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    return app_module.app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def test_user():
    """Create a test user and yield (user_id, email, password). Cleans up after."""
    email = _unique_email("prof")
    password = "testpassword123"
    user_id = _create_user_and_get_id(email, password)
    yield {"id": user_id, "email": email, "password": password}
    _delete_user(user_id)


@pytest.fixture
def auth_client(client, test_user):
    """Test client with the test user logged in."""
    client.post(
        "/login",
        data={
            "email": test_user["email"],
            "password": test_user["password"],
        },
    )
    return client


# ------------------------------------------------------------------ #
# 1. Dropdown icons are distinct                                      #
# ------------------------------------------------------------------ #


class TestDropdownIconsDistinct:
    def test_trigger_uses_user_icon(self, auth_client):
        """The dropdown trigger must use the Lucide 'user' icon."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # The trigger button contains a user icon
        trigger_match = _find_trigger(body)
        assert trigger_match, "nav-user-trigger button must exist"
        assert (
            'data-lucide="user"' in trigger_match
        ), "Trigger must use the Lucide 'user' icon"

    def test_my_profile_uses_user_circle_icon(self, auth_client):
        """The 'My Profile' menu item must use a distinct icon from the trigger."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The My Profile dropdown item must use user-circle, not user
        assert (
            'data-lucide="user-circle"' in body
        ), "My Profile item must use the distinct 'user-circle' Lucide icon"

    def test_trigger_and_my_profile_do_not_share_icon(self, auth_client):
        """Trigger icon and My Profile icon must differ."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        trigger = _find_trigger(body)
        assert trigger is not None
        # The trigger should NOT contain user-circle (that belongs to My Profile)
        assert (
            'data-lucide="user-circle"' not in trigger
        ), "Trigger must not use the same icon as My Profile"


# ------------------------------------------------------------------ #
# 2. Dropdown has three items in order                                 #
# ------------------------------------------------------------------ #


class TestDropdownItemsThree:
    def test_dropdown_has_three_menu_items(self, auth_client):
        """Dropdown must contain exactly three menu items."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert body.count('role="menuitem"') == 3, (
            "Dropdown must contain exactly three menu items (My Profile, "
            "Change Password, Log Out)"
        )

    def test_change_password_item_present(self, auth_client):
        """Dropdown must contain a 'Change Password' item with the trigger id."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            'id="nav-change-password"' in body
        ), "Dropdown must contain a Change Password item with id='nav-change-password'"
        assert "Change Password" in body, "Dropdown must show 'Change Password' text"

    def test_change_password_uses_lock_icon(self, auth_client):
        """The Change Password item must use the Lucide 'lock' icon."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            'data-lucide="lock"' in body
        ), "Change Password item must use the 'lock' Lucide icon"

    def test_item_order_my_profile_before_change_password(self, auth_client):
        """My Profile must appear before Change Password in the dropdown."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        dropdown = _find_dropdown(body)
        assert dropdown is not None, "Dropdown must exist"
        assert dropdown.index("My Profile") < dropdown.index(
            "Change Password"
        ), "My Profile must appear before Change Password"

    def test_item_order_change_password_before_logout(self, auth_client):
        """Change Password must appear before Log Out in the dropdown."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        dropdown = _find_dropdown(body)
        assert dropdown is not None, "Dropdown must exist"
        assert dropdown.index("Change Password") < dropdown.index(
            "Log Out"
        ), "Change Password must appear before Log Out"


# ------------------------------------------------------------------ #
# 3. Change Password reachable via modal                               #
# ------------------------------------------------------------------ #


class TestChangePasswordReachable:
    def test_change_password_modal_markup_present(self, auth_client):
        """The Change Password modal markup must be present on the profile page."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            'id="change-password-modal"' in body
        ), "Change Password modal markup must exist on the profile page"

    def test_change_password_trigger_wired_to_modal(self, auth_client):
        """The navbar Change Password trigger must open the change-password modal."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The JS must reference both the navbar trigger and the modal
        assert (
            "nav-change-password" in body
        ), "JS must reference the navbar Change Password trigger"
        assert (
            "change-password-modal" in body
        ), "JS must reference the change-password modal"


# ------------------------------------------------------------------ #
# 4. Profile card stat rows                                            #
# ------------------------------------------------------------------ #


class TestProfileCardStatRows:
    def test_profile_card_has_stat_rows(self, auth_client):
        """Profile card must contain three stat rows."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            body.count("profile-stat-row") == 3
        ), "Profile card must contain exactly three stat rows"

    def test_stat_row_shows_total_spent_label(self, auth_client):
        """One stat row must be labelled 'Total Spent This Month'."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            "Total Spent This Month" in body
        ), "Profile card must show 'Total Spent This Month' stat"

    def test_stat_row_shows_transactions_label(self, auth_client):
        """One stat row must be labelled 'Transactions'."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "Transactions" in body, "Profile card must show 'Transactions' stat"

    def test_stat_row_shows_top_category_label(self, auth_client):
        """One stat row must be labelled 'Top Category'."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "Top Category" in body, "Profile card must show 'Top Category' stat"

    def test_stat_rows_inside_profile_card(self, auth_client):
        """The stat rows must live inside the profile-card container."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        card = _find_profile_card(body)
        assert card is not None, "profile-card must exist"
        assert (
            "profile-stat-row" in card
        ), "Stat rows must be inside the profile-card container"


# ------------------------------------------------------------------ #
# 5. Old elements removed                                              #
# ------------------------------------------------------------------ #


class TestOldElementsRemoved:
    def test_old_change_password_button_gone(self, auth_client):
        """The old standalone 'Change password' button must be removed."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            'id="change-password-btn"' not in body
        ), "Old 'Change password' button (id='change-password-btn') must be removed"

    def test_standalone_stats_row_gone(self, auth_client):
        """The old standalone stats-row block must be removed."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            'class="stats-row"' not in body
        ), "Standalone stats-row block must be removed from the profile page"


# ------------------------------------------------------------------ #
# 6. Auth guard                                                        #
# ------------------------------------------------------------------ #


class TestAuthGuard:
    def test_anonymous_user_redirected_to_login(self, client):
        """Anonymous users must be redirected to /login when visiting /profile."""
        resp = client.get("/profile")
        assert (
            resp.status_code == 302
        ), "Anonymous user must be redirected from /profile"
        assert "/login" in resp.headers.get(
            "Location", ""
        ), "Anonymous user must be redirected to /login"


# ------------------------------------------------------------------ #
# 7. Stat values with expenses                                         #
# ------------------------------------------------------------------ #


class TestStatValuesWithExpenses:
    def test_stat_values_render_with_expenses(self, auth_client, test_user):
        """Stat rows must render correct values when the user has expenses."""
        uid = test_user["id"]
        _add_expense(uid, 150.50, "Food", "2026-06-15", "Lunch")
        _add_expense(uid, 75.00, "Food", "2026-06-20", "Dinner")
        _add_expense(uid, 200.00, "Transport", "2026-06-22", "Taxi")

        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert resp.status_code == 200
        # Total spent = 150.50 + 75.00 + 200.00 = 425.50
        assert "425.50" in body, "Total spent must reflect the sum of expenses"
        # Transaction count = 3
        assert (
            ">3<" in body or ">3 <" in body or " 3 " in body
        ), "Transaction count must reflect the number of expenses"
        # Top category = Food (225.50 > 200.00)
        assert "Food" in body, "Top category must be the highest-spend category"


# ------------------------------------------------------------------ #
# 8. Stat values with zero expenses (graceful degradation)             #
# ------------------------------------------------------------------ #


class TestStatValuesZeroExpenses:
    def test_stat_rows_render_with_zero_expenses(self, auth_client):
        """Stat rows must still render when the user has no expenses."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert (
            body.count("profile-stat-row") == 3
        ), "Stat rows must render even with zero expenses"

    def test_total_spent_shows_zero(self, auth_client):
        """Total spent must show 0.00 when the user has no expenses."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "0.00" in body, "Total spent must show 0.00 with no expenses"

    def test_top_category_shows_placeholder(self, auth_client):
        """Top category must show a placeholder when the user has no expenses."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert (
            "—" in body
        ), "Top category must show an em-dash placeholder with no expenses"


# ------------------------------------------------------------------ #
# Parsing helpers                                                      #
# ------------------------------------------------------------------ #


def _find_trigger(body):
    """Return the HTML of the nav-user-trigger button, or None."""
    import re

    m = re.search(
        r'<button[^>]*id="nav-user-trigger"[^>]*>(.*?)</button>', body, re.DOTALL
    )
    return m.group(1) if m else None


def _find_dropdown(body):
    """Return the HTML of the nav-user-dropdown, or None."""
    import re

    m = re.search(
        r'<div[^>]*id="nav-user-dropdown"[^>]*>(.*?)</div>\s*(?:</div>|<a|</nav>)',
        body,
        re.DOTALL,
    )
    # Fallback: grab until the menu's closing div before the next major element
    if not m:
        m = re.search(r'id="nav-user-dropdown"[^>]*>(.*?)</div>', body, re.DOTALL)
    return m.group(1) if m else None


def _find_profile_card(body):
    """Return the HTML of the profile-card container, or None."""
    import re

    m = re.search(
        r'class="profile-card"[^>]*>(.*?)</div>\s*<div class="analytics-dashboard"',
        body,
        re.DOTALL,
    )
    if not m:
        m = re.search(r'class="profile-card"[^>]*>(.*?)<!-- Analytics', body, re.DOTALL)
    return m.group(1) if m else None
