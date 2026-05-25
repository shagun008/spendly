"""Step 10 — Mobile Navigation: hamburger button + mobile dropdown menu in base.html.

This is a pure front-end feature — no new routes, no DB changes.  Tests fetch
rendered HTML via the Flask test client and assert on the presence/absence of
specific elements, IDs, classes, and text content.

Strategy: monkeypatch database.db.DB_PATH to a fresh tmp file, seed the demo
user, reload app so its module-level init_db/seed_db hits the patched path.
Logged-in tests inject the session directly via session_transaction rather than
going through the real login flow.

Fixture hierarchy:
  client       — unauthenticated Flask test client backed by a fresh tmp DB
  auth_client  — same client with demo user (id=1, name="Demo User") in session

Spec behaviours covered (all assertions are string-based — BeautifulSoup is not
in requirements.txt)
-----------------------------------------------------------------------
Logged-out (GET /):
  1.  Hamburger button id="nav-hamburger" is present in the HTML
  2.  Mobile menu id="nav-mobile-menu" is present in the HTML
  3.  Mobile menu contains a "Sign in" link
  4.  Mobile menu contains a "Get started" link
  5.  Hamburger button has aria-expanded="false" (closed by default)
  6.  Mobile menu does NOT carry the class "is-open" (closed by default)
  7.  Hamburger button contains at least one <span> child (animated bars)

Desktop nav (.nav-links) — logged-out (GET /):
  8.  .nav-links block contains a "Sign in" link
  9.  .nav-links block contains a "Get started" link

Logged-in (GET /profile):
  10. Mobile menu contains an "Add Expense" link
  11. Mobile menu contains an "Analytics" link
  12. Mobile menu contains the username (linked to /profile)
  13. Mobile menu contains a "Logout" link
  14. Mobile menu does NOT carry the class "is-open" (closed by default even when
      logged in)
  15. Hamburger button still has aria-expanded="false" when logged in

Desktop nav (.nav-links) — logged-in (GET /profile):
  16. .nav-links block contains an "Add Expense" link
  17. .nav-links block contains an "Analytics" link
  18. .nav-links block contains the username linked to /profile
  19. .nav-links block contains a "Logout" link
"""

import importlib

import pytest

import database.db as db_module
from database.db import init_db, seed_db

# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Unauthenticated Flask test client backed by a fresh seeded tmp DB.

    Follows the established pattern: patch DB_PATH first, seed, then reload
    app so its module-level init_db/seed_db calls hit the tmp DB.
    """
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test_nav.db"))
    init_db()
    seed_db()

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(client):
    """Test client with the demo user (id=1, name='Demo User') already in session.

    Uses session_transaction to inject the session directly — no real login
    flow required.
    """
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"
    return client


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _body(response):
    """Return the decoded response body as a plain string."""
    return response.get_data(as_text=True)


def _extract_between(html, start_marker, end_marker):
    """Return the substring of *html* between *start_marker* and *end_marker*.

    Returns an empty string when either marker is absent, so callers can
    safely run assertions on the result without a separate existence guard.
    This keeps individual test assertions atomic.
    """
    start_idx = html.find(start_marker)
    if start_idx == -1:
        return ""
    end_idx = html.find(end_marker, start_idx + len(start_marker))
    if end_idx == -1:
        return ""
    return html[start_idx : end_idx + len(end_marker)]


def _mobile_menu_block(html):
    """Extract the HTML fragment that starts at id="nav-mobile-menu".

    The block is delimited by the opening tag that contains
    'id="nav-mobile-menu"' and the *next* closing </div> after all nested
    content.  Because template structures vary, we grab everything from the
    opening tag until a double-closing-div sequence that is only likely to
    appear at the end of the menu block, or until </nav>, whichever comes
    first.  For the assertions in this suite, finding the correct links
    *after* the opening id= tag is sufficient.
    """
    marker = 'id="nav-mobile-menu"'
    idx = html.find(marker)
    if idx == -1:
        return ""
    # walk back to the opening '<' of the tag that contains the id attribute
    tag_start = html.rfind("<", 0, idx)
    if tag_start == -1:
        tag_start = idx
    # find </nav> as a safe upper boundary
    nav_close = html.find("</nav>", tag_start)
    if nav_close == -1:
        return html[tag_start:]
    return html[tag_start:nav_close]


def _nav_links_block(html):
    """Extract the HTML fragment that contains the class 'nav-links'.

    Grabs from the first element carrying 'class="nav-links"' (or
    'nav-links' anywhere in a class attribute) up to the matching closing
    tag boundary.  For assertion purposes, extracting from the class
    attribute forward until </nav> is sufficient and template-agnostic.
    """
    marker = "nav-links"
    idx = html.find(marker)
    if idx == -1:
        return ""
    tag_start = html.rfind("<", 0, idx)
    if tag_start == -1:
        tag_start = idx
    nav_close = html.find("</nav>", tag_start)
    if nav_close == -1:
        return html[tag_start:]
    return html[tag_start:nav_close]


# ------------------------------------------------------------------ #
# 1–7: Logged-out — GET /  (HTML structure of mobile nav elements)    #
# ------------------------------------------------------------------ #


class TestMobileNavLoggedOut:
    """Assertions on the HTML served to unauthenticated users at GET /."""

    def test_hamburger_button_id_present_in_html(self, client):
        """The hamburger toggle button must have id="nav-hamburger"."""
        body = _body(client.get("/"))
        assert (
            'id="nav-hamburger"' in body
        ), 'Expected id="nav-hamburger" in the page HTML for unauthenticated users'

    def test_mobile_menu_id_present_in_html(self, client):
        """The mobile menu container must have id="nav-mobile-menu"."""
        body = _body(client.get("/"))
        assert (
            'id="nav-mobile-menu"' in body
        ), 'Expected id="nav-mobile-menu" in the page HTML for unauthenticated users'

    def test_mobile_menu_contains_sign_in_link(self, client):
        """The mobile menu must contain a 'Sign in' link for logged-out users."""
        body = _body(client.get("/"))
        mobile_block = _mobile_menu_block(body)
        assert mobile_block, 'Could not locate id="nav-mobile-menu" block in the HTML'
        assert (
            "Sign in" in mobile_block or "sign in" in mobile_block.lower()
        ), "Mobile menu must contain a 'Sign in' link for unauthenticated users"

    def test_mobile_menu_contains_get_started_link(self, client):
        """The mobile menu must contain a 'Get started' link for logged-out users."""
        body = _body(client.get("/"))
        mobile_block = _mobile_menu_block(body)
        assert mobile_block, 'Could not locate id="nav-mobile-menu" block in the HTML'
        assert (
            "Get started" in mobile_block or "get started" in mobile_block.lower()
        ), "Mobile menu must contain a 'Get started' link for unauthenticated users"

    def test_hamburger_has_aria_expanded_false(self, client):
        """Hamburger button must have aria-expanded="false" in the initial HTML (menu closed)."""
        body = _body(client.get("/"))
        # Locate the button tag that carries id="nav-hamburger"
        btn_marker = 'id="nav-hamburger"'
        btn_idx = body.find(btn_marker)
        assert btn_idx != -1, 'id="nav-hamburger" not found in the page HTML'
        # Grab the opening tag of the button (everything back to '<')
        tag_start = body.rfind("<", 0, btn_idx)
        tag_end = body.find(">", btn_idx)
        btn_tag = body[tag_start : tag_end + 1] if tag_end != -1 else body[tag_start:]
        assert (
            'aria-expanded="false"' in btn_tag
        ), 'Hamburger button must carry aria-expanded="false" in the initial page HTML (menu is closed on load)'

    def test_mobile_menu_does_not_have_is_open_class_initially(self, client):
        """The mobile menu must NOT carry the 'is-open' class in the initial HTML (closed by default)."""
        body = _body(client.get("/"))
        mobile_block = _mobile_menu_block(body)
        assert mobile_block, 'Could not locate id="nav-mobile-menu" block in the HTML'
        # Extract only the opening tag of the mobile menu element
        tag_end = mobile_block.find(">")
        opening_tag = mobile_block[: tag_end + 1] if tag_end != -1 else mobile_block
        assert (
            "is-open" not in opening_tag
        ), "Mobile menu must NOT have the 'is-open' class in the initial server-rendered HTML"

    def test_hamburger_button_contains_span_children(self, client):
        """The hamburger button must contain at least one <span> element (the animated bars)."""
        body = _body(client.get("/"))
        btn_marker = 'id="nav-hamburger"'
        btn_idx = body.find(btn_marker)
        assert btn_idx != -1, 'id="nav-hamburger" not found in the page HTML'
        # Grab content between the opening button tag and its closing tag
        btn_open_end = body.find(">", btn_idx)
        btn_close = body.find("</button>", btn_idx)
        if btn_open_end != -1 and btn_close != -1:
            inner = body[btn_open_end + 1 : btn_close]
        else:
            inner = body[btn_idx:]
        assert (
            "<span" in inner
        ), "Hamburger button must contain <span> child elements for the animated bar icons"


# ------------------------------------------------------------------ #
# 8–9: Desktop nav — logged-out (GET /)                               #
# ------------------------------------------------------------------ #


class TestDesktopNavLoggedOut:
    """The .nav-links desktop nav block must still contain all expected links
    for unauthenticated users after the mobile nav feature is added."""

    def test_desktop_nav_contains_sign_in_link(self, client):
        """Desktop .nav-links must contain a 'Sign in' link for logged-out users."""
        body = _body(client.get("/"))
        nav_block = _nav_links_block(body)
        assert nav_block, "Could not locate .nav-links block in the page HTML"
        assert (
            "Sign in" in nav_block or "sign in" in nav_block.lower()
        ), "Desktop .nav-links must contain a 'Sign in' link for unauthenticated users"

    def test_desktop_nav_contains_get_started_link(self, client):
        """Desktop .nav-links must contain a 'Get started' link for logged-out users."""
        body = _body(client.get("/"))
        nav_block = _nav_links_block(body)
        assert nav_block, "Could not locate .nav-links block in the page HTML"
        assert (
            "Get started" in nav_block or "get started" in nav_block.lower()
        ), "Desktop .nav-links must contain a 'Get started' link for unauthenticated users"


# ------------------------------------------------------------------ #
# 10–15: Logged-in — GET /profile (mobile menu contents)             #
# ------------------------------------------------------------------ #


class TestMobileNavLoggedIn:
    """Assertions on the HTML served to authenticated users at GET /profile."""

    def test_mobile_menu_contains_add_expense_link(self, auth_client):
        """Mobile menu must contain an 'Add Expense' link for logged-in users."""
        body = _body(auth_client.get("/profile"))
        mobile_block = _mobile_menu_block(body)
        assert (
            mobile_block
        ), 'Could not locate id="nav-mobile-menu" block in /profile HTML'
        assert (
            "Add Expense" in mobile_block or "add expense" in mobile_block.lower()
        ), "Mobile menu must contain an 'Add Expense' link for authenticated users"

    def test_mobile_menu_contains_analytics_link(self, auth_client):
        """Mobile menu must contain an 'Analytics' link for logged-in users."""
        body = _body(auth_client.get("/profile"))
        mobile_block = _mobile_menu_block(body)
        assert (
            mobile_block
        ), 'Could not locate id="nav-mobile-menu" block in /profile HTML'
        assert (
            "Analytics" in mobile_block or "analytics" in mobile_block.lower()
        ), "Mobile menu must contain an 'Analytics' link for authenticated users"

    def test_mobile_menu_contains_username_linked_to_profile(self, auth_client):
        """Mobile menu must contain the username text and link it to /profile."""
        body = _body(auth_client.get("/profile"))
        mobile_block = _mobile_menu_block(body)
        assert (
            mobile_block
        ), 'Could not locate id="nav-mobile-menu" block in /profile HTML'
        assert (
            "Demo User" in mobile_block
        ), "Mobile menu must display the logged-in username ('Demo User') for authenticated users"
        assert (
            "/profile" in mobile_block
        ), "Mobile menu must include a link to /profile for the username"

    def test_mobile_menu_contains_logout_link(self, auth_client):
        """Mobile menu must contain a 'Logout' link for logged-in users."""
        body = _body(auth_client.get("/profile"))
        mobile_block = _mobile_menu_block(body)
        assert (
            mobile_block
        ), 'Could not locate id="nav-mobile-menu" block in /profile HTML'
        assert (
            "Logout" in mobile_block or "logout" in mobile_block.lower()
        ), "Mobile menu must contain a 'Logout' link for authenticated users"

    def test_mobile_menu_does_not_have_is_open_class_when_logged_in(self, auth_client):
        """Mobile menu must NOT carry the 'is-open' class in initial /profile HTML."""
        body = _body(auth_client.get("/profile"))
        mobile_block = _mobile_menu_block(body)
        assert (
            mobile_block
        ), 'Could not locate id="nav-mobile-menu" block in /profile HTML'
        tag_end = mobile_block.find(">")
        opening_tag = mobile_block[: tag_end + 1] if tag_end != -1 else mobile_block
        assert (
            "is-open" not in opening_tag
        ), "Mobile menu must NOT have the 'is-open' class in the initial server-rendered /profile HTML"

    def test_hamburger_has_aria_expanded_false_when_logged_in(self, auth_client):
        """Hamburger button must have aria-expanded="false" on initial load of /profile."""
        body = _body(auth_client.get("/profile"))
        btn_marker = 'id="nav-hamburger"'
        btn_idx = body.find(btn_marker)
        assert btn_idx != -1, 'id="nav-hamburger" not found in /profile HTML'
        tag_start = body.rfind("<", 0, btn_idx)
        tag_end = body.find(">", btn_idx)
        btn_tag = body[tag_start : tag_end + 1] if tag_end != -1 else body[tag_start:]
        assert (
            'aria-expanded="false"' in btn_tag
        ), 'Hamburger button must carry aria-expanded="false" in the initial /profile HTML'


# ------------------------------------------------------------------ #
# 16–19: Desktop nav — logged-in (GET /profile)                      #
# ------------------------------------------------------------------ #


class TestDesktopNavLoggedIn:
    """The .nav-links desktop nav block must still render all expected links
    for authenticated users after the mobile nav feature is added."""

    def test_desktop_nav_contains_add_expense_link(self, auth_client):
        """Desktop .nav-links must contain an 'Add Expense' link for logged-in users."""
        body = _body(auth_client.get("/profile"))
        nav_block = _nav_links_block(body)
        assert nav_block, "Could not locate .nav-links block in /profile HTML"
        assert (
            "Add Expense" in nav_block or "add expense" in nav_block.lower()
        ), "Desktop .nav-links must contain an 'Add Expense' link for authenticated users"

    def test_desktop_nav_contains_analytics_link(self, auth_client):
        """Desktop .nav-links must contain an 'Analytics' link for logged-in users."""
        body = _body(auth_client.get("/profile"))
        nav_block = _nav_links_block(body)
        assert nav_block, "Could not locate .nav-links block in /profile HTML"
        assert (
            "Analytics" in nav_block or "analytics" in nav_block.lower()
        ), "Desktop .nav-links must contain an 'Analytics' link for authenticated users"

    def test_desktop_nav_contains_username_linked_to_profile(self, auth_client):
        """Desktop .nav-links must contain the username linked to /profile."""
        body = _body(auth_client.get("/profile"))
        nav_block = _nav_links_block(body)
        assert nav_block, "Could not locate .nav-links block in /profile HTML"
        assert (
            "Demo User" in nav_block
        ), "Desktop .nav-links must display the logged-in username ('Demo User')"
        assert (
            "/profile" in nav_block
        ), "Desktop .nav-links must link the username to /profile"

    def test_desktop_nav_contains_logout_link(self, auth_client):
        """Desktop .nav-links must contain a 'Logout' link for logged-in users."""
        body = _body(auth_client.get("/profile"))
        nav_block = _nav_links_block(body)
        assert nav_block, "Could not locate .nav-links block in /profile HTML"
        assert (
            "Logout" in nav_block or "logout" in nav_block.lower()
        ), "Desktop .nav-links must contain a 'Logout' link for authenticated users"


# ------------------------------------------------------------------ #
# Sanity: both nav elements are present on every page that uses       #
# base.html (spot-check login page as a second template)              #
# ------------------------------------------------------------------ #


class TestMobileNavPresentOnMultiplePages:
    """The hamburger and mobile menu must appear on every page that extends
    base.html, not only the landing page."""

    def test_hamburger_present_on_login_page(self, client):
        """id="nav-hamburger" must appear on the /login page."""
        body = _body(client.get("/login"))
        assert (
            'id="nav-hamburger"' in body
        ), 'id="nav-hamburger" must be present on the /login page (base.html is shared)'

    def test_mobile_menu_present_on_login_page(self, client):
        """id="nav-mobile-menu" must appear on the /login page."""
        body = _body(client.get("/login"))
        assert (
            'id="nav-mobile-menu"' in body
        ), 'id="nav-mobile-menu" must be present on the /login page (base.html is shared)'

    def test_hamburger_present_on_register_page(self, client):
        """id="nav-hamburger" must appear on the /register page."""
        body = _body(client.get("/register"))
        assert (
            'id="nav-hamburger"' in body
        ), 'id="nav-hamburger" must be present on the /register page (base.html is shared)'

    def test_mobile_menu_present_on_register_page(self, client):
        """id="nav-mobile-menu" must appear on the /register page."""
        body = _body(client.get("/register"))
        assert (
            'id="nav-mobile-menu"' in body
        ), 'id="nav-mobile-menu" must be present on the /register page (base.html is shared)'
