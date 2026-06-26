"""Release 19.2 — Navbar User Menu: desktop dropdown and mobile swap tests.

Tests run against the real Supabase database (via DATABASE_URL). Each test
creates its own user, logs in, exercises the navbar UI, and tears down its
data. All assertions are based on the spec at
.claude/specs/19.2-navbar-user-menu.md — not on the implementation.

Test classes:
  TestDesktopUserIconShown       — user icon appears when logged in, not when logged out
  TestDesktopDropdownItems       — dropdown contains "My Profile" and "Log Out"
  TestDesktopDropdownRemovedOld  — old username text link and standalone Logout link are gone
  TestDesktopDropdownAria       — trigger and dropdown have correct ARIA attributes
  TestMobileUserIconSwap        — hamburger is replaced by user icon on mobile when logged in
  TestMobileHamburgerUnchanged   — hamburger remains when logged out
  TestMobileMenuRelabelled      — mobile menu shows "My Profile" and "Log Out"
  TestNavLinksPreserved          — Features, Roadmap, Sign in, Get started still present
  TestLogoutLinkWorks            — Log Out link actually logs the user out
"""

import importlib
import uuid

import pytest
import psycopg2
import psycopg2.extras

import database.db as db_module
from database.db import get_db, create_user, init_db, seed_features


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


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app():
    """Ensure the app module is initialised (module-level init_db runs once)."""
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
    email = _unique_email("nav")
    password = "testpassword123"
    user_id = _create_user_and_get_id(email, password)
    yield {"id": user_id, "email": email, "password": password}
    _delete_user(user_id)


@pytest.fixture
def auth_client(client, test_user):
    """Test client with the test user logged in."""
    client.post("/login", data={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    return client


# ------------------------------------------------------------------ #
# 1. Desktop user icon shown                                          #
# ------------------------------------------------------------------ #

class TestDesktopUserIconShown:
    def test_user_icon_present_when_logged_in(self, auth_client):
        """Desktop nav must show the user icon trigger when user is logged in."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'id="nav-user-trigger"' in body, (
            "User icon trigger button must exist in navbar when logged in"
        )
        assert 'data-lucide="user"' in body, (
            "User icon must use Lucide user icon"
        )

    def test_user_icon_absent_when_logged_out(self, client):
        """Desktop nav must NOT show user icon when user is logged out."""
        resp = client.get("/profile")
        # Unauthenticated user gets redirected to login, but landing page is public
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'id="nav-user-trigger"' not in body, (
            "User icon trigger must NOT appear when logged out"
        )

    def test_trigger_has_aria_label(self, auth_client):
        """User icon button must have an aria-label for accessibility."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'aria-label="User menu"' in body, (
            "User icon trigger must have aria-label='User menu'"
        )


# ------------------------------------------------------------------ #
# 2. Desktop dropdown items                                           #
# ------------------------------------------------------------------ #

class TestDesktopDropdownItems:
    def test_dropdown_contains_my_profile(self, auth_client):
        """Dropdown must contain a 'My Profile' link pointing to /profile."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "My Profile" in body, "Dropdown must show 'My Profile' text"
        assert 'href="{{ url_for(\'profile\') }}"' in body or 'href="/profile"' in body, (
            "My Profile must link to /profile"
        )

    def test_dropdown_contains_log_out(self, auth_client):
        """Dropdown must contain a 'Log Out' link pointing to /logout."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "Log Out" in body, "Dropdown must show 'Log Out' text"
        assert 'href="{{ url_for(\'logout\') }}"' in body or 'href="/logout"' in body, (
            "Log Out must link to /logout"
        )

    def test_logout_spelling_is_log_out(self, auth_client):
        """The link text must be 'Log Out' (two words), not 'Logout' (one word)."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # "Logout" as a single word should not appear as a link
        # (it may appear in route names, but not as visible link text)
        assert ">Logout<" not in body, (
            "Link text must be 'Log Out' (two words), not 'Logout'"
        )
        assert ">Log Out<" in body, "Link text must be 'Log Out'"

    def test_dropdown_has_two_items(self, auth_client):
        """Dropdown must contain exactly two menu items."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert body.count('role="menuitem"') == 2, (
            "Dropdown must contain exactly two menu items"
        )


# ------------------------------------------------------------------ #
# 3. Desktop dropdown — old elements removed                          #
# ------------------------------------------------------------------ #

class TestDesktopDropdownRemovedOld:
    def test_no_standalone_logout_link(self, auth_client):
        """The old standalone 'Logout' text link must be removed from desktop nav."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The old standalone logout was an <a> with class nav-link containing "Logout"
        # After the feature, only "Log Out" in the dropdown should exist
        # Check there's no standalone nav-link with "Logout" text
        import re
        # Find all nav-link elements
        nav_links = re.findall(r'<a[^>]*class="nav-link[^"]*"[^>]*>[^<]*</a>', body)
        for link in nav_links:
            assert "Logout" not in link, (
                f"Old standalone 'Logout' link must be removed, found: {link}"
            )

    def test_no_username_text_link(self, auth_client, test_user):
        """The old username text link must be replaced by the user icon."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The user's name should NOT appear as a nav-link text
        # (it may appear on the profile page itself, but not in the navbar links)
        import re
        nav_links = re.findall(r'<a[^>]*class="nav-link[^"]*"[^>]*>([^<]*)</a>', body)
        user_name = test_user["email"].split("@")[0].replace("-", " ").title()
        for link_text in nav_links:
            assert user_name not in link_text, (
                f"Username text '{user_name}' must not appear as a nav-link, found: {link_text}"
            )


# ------------------------------------------------------------------ #
# 4. Desktop dropdown — ARIA attributes                               #
# ------------------------------------------------------------------ #

class TestDesktopDropdownAria:
    def test_trigger_has_aria_expanded(self, auth_client):
        """User icon button must have aria-expanded attribute."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'aria-expanded="false"' in body, (
            "Trigger must have aria-expanded='false' initially"
        )

    def test_trigger_has_aria_controls(self, auth_client):
        """User icon button must have aria-controls pointing to the dropdown."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'aria-controls="nav-user-dropdown"' in body, (
            "Trigger must have aria-controls='nav-user-dropdown'"
        )

    def test_dropdown_has_role_menu(self, auth_client):
        """Dropdown container must have role='menu'."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'role="menu"' in body, "Dropdown must have role='menu'"

    def test_dropdown_items_have_role_menuitem(self, auth_client):
        """Each dropdown item must have role='menuitem'."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert body.count('role="menuitem"') >= 2, (
            "Each dropdown item must have role='menuitem'"
        )

    def test_dropdown_has_aria_hidden(self, auth_client):
        """Dropdown must have aria-hidden attribute."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'aria-hidden="true"' in body, (
            "Dropdown must have aria-hidden='true' initially"
        )


# ------------------------------------------------------------------ #
# 5. Mobile user icon swap                                            #
# ------------------------------------------------------------------ #

class TestMobileUserIconSwap:
    def test_hamburger_has_data_user_mode_when_logged_in(self, auth_client):
        """Hamburger button must have data-user-mode='true' when logged in."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'data-user-mode="true"' in body, (
            "Hamburger button must have data-user-mode='true' when logged in"
        )

    def test_hamburger_absent_when_logged_out(self, client):
        """Hamburger button must NOT have data-user-mode when logged out."""
        resp = client.get("/")
        body = resp.get_data(as_text=True)
        assert "data-user-mode" not in body, (
            "Hamburger must not have data-user-mode when logged out"
        )


# ------------------------------------------------------------------ #
# 6. Mobile hamburger unchanged when logged out                       #
# ------------------------------------------------------------------ #

class TestMobileHamburgerUnchanged:
    def test_hamburger_has_span_children_when_logged_out(self, client):
        """When logged out, hamburger must show the standard three-bar icon (span elements)."""
        resp = client.get("/")
        body = resp.get_data(as_text=True)
        # The hamburger button should contain three <span> elements (the bars)
        import re
        hamburger_match = re.search(
            r'<button[^>]*class="nav-hamburger"[^>]*>(.*?)</button>',
            body, re.DOTALL
        )
        assert hamburger_match, "Hamburger button must exist"
        hamburger_content = hamburger_match.group(1)
        span_count = hamburger_content.count("<span")
        assert span_count >= 3, (
            f"Hamburger must show 3 bars (spans) when logged out, found {span_count}"
        )


# ------------------------------------------------------------------ #
# 7. Mobile menu relabelled                                           #
# ------------------------------------------------------------------ #

class TestMobileMenuRelabelled:
    def test_mobile_menu_shows_my_profile(self, auth_client):
        """Mobile menu must show 'My Profile' instead of username text."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "My Profile" in body, "Mobile menu must contain 'My Profile'"

    def test_mobile_menu_shows_log_out(self, auth_client):
        """Mobile menu must show 'Log Out' instead of 'Logout'."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # Check the mobile menu section has "Log Out"
        import re
        # Find the mobile menu container — it's the div with id="nav-mobile-menu"
        # followed by content and a closing </div> before </nav>
        mobile_menu_match = re.search(
            r'id="nav-mobile-menu"[^>]*>(.*?)</div>\s*</nav>',
            body, re.DOTALL
        )
        assert mobile_menu_match, "Mobile menu must exist"
        mobile_content = mobile_menu_match.group(1)
        assert "Log Out" in mobile_content, "Mobile menu must contain 'Log Out'"
        assert "Logout" not in mobile_content.replace("Log Out", ""), (
            "Mobile menu must use 'Log Out' (two words), not 'Logout'"
        )


# ------------------------------------------------------------------ #
# 8. Nav links preserved                                              #
# ------------------------------------------------------------------ #

class TestNavLinksPreserved:
    def test_features_link_present(self, auth_client):
        """Features link must still be present in the navbar."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'href="{{ url_for(\'features\') }}"' in body or 'href="/features"' in body, (
            "Features link must be present"
        )
        assert "Features" in body

    def test_roadmap_link_present(self, auth_client):
        """Roadmap link must still be present in the navbar."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'href="{{ url_for(\'roadmap\') }}"' in body or 'href="/roadmap"' in body, (
            "Roadmap link must be present"
        )
        assert "Roadmap" in body

    def test_sign_in_link_present_when_logged_out(self, client):
        """Sign in link must be present when logged out."""
        resp = client.get("/")
        body = resp.get_data(as_text=True)
        assert "Sign in" in body, "Sign in link must be present when logged out"

    def test_get_started_link_present_when_logged_out(self, client):
        """Get started link must be present when logged out."""
        resp = client.get("/")
        body = resp.get_data(as_text=True)
        assert "Get started" in body, "Get started link must be present when logged out"


# ------------------------------------------------------------------ #
# 9. Logout link works                                                #
# ------------------------------------------------------------------ #

class TestLogoutLinkWorks:
    def test_logout_link_logs_out_user(self, auth_client, test_user):
        """Clicking Log Out must actually log the user out."""
        # Verify user is logged in
        resp = auth_client.get("/profile")
        assert resp.status_code == 200

        # Log out
        resp = auth_client.get("/logout")
        assert resp.status_code == 302

        # Verify user is now logged out — profile should redirect to login
        resp = auth_client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")

    def test_logout_redirects_to_landing(self, auth_client):
        """After logout, user should be redirected to landing or login."""
        resp = auth_client.get("/logout")
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        # Should redirect to landing or login
        assert location in ["/", "/login"] or location.endswith("/login") or location.endswith("/")
