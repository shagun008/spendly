"""Tests for Feature 24.1 — Home Page Routing.

Spec: .claude/specs/24.1-home-page-routing.md

Scope
-----
- `GET /` is repurposed to render a new public marketing homepage
  (`templates/home.html`) instead of the authenticated app.
- `/platform` remains the authenticated application entry point, unchanged.
- Protected routes still redirect unauthenticated users to `/login`.
- Logout now redirects to `/` (the new homepage) instead of the old landing
  page.
- Navigation links (logo, home) on the homepage point to `/`.
- The "Get Started" button on the homepage links to `/login`.
- SEO metadata (title, meta description) is present on the homepage.
- A favicon is referenced in `base.html`.
- No unused JS from the mockup is loaded on the homepage (mockup had an
  inline `<style>` block and its own Lucide `<script>` tag — those must not
  leak into the shipped page beyond the single CDN load already in
  `base.html`).
- Inline CSS from the mockup has been extracted into `static/css/home.css`.
- Lucide icons and Google Fonts reuse the existing CDN/link tags already in
  `base.html` (no second/duplicate CDN load).

No database changes are introduced by this feature, so these tests focus on
routing, template rendering, and auth-guard behaviour rather than DB side
effects. Where a route touches the database indirectly (e.g. `/platform`,
which needs a logged-in session), we only exercise the routing/auth-guard
contract, not DB reads/writes, consistent with the "no DB changes" scope of
this spec.

Fixture strategy
-----------------
Following the pattern already established in this repo for pure
template/routing tests (see `tests/test_21.1-oxos-profile-page-mvp.py`): the
`app` module is reloaded fresh per test and `TESTING`/`SECRET_KEY` are set on
the Flask app config. No SQLite/`init_db()` fixtures are used because this
project's database layer is PostgreSQL via Supabase (`database/db.py`,
`psycopg2`) reached through a `DATABASE_URL` environment variable — not an
in-memory SQLite DB. Session state for "logged in" tests is set directly via
`client.session_transaction()` to avoid requiring a live database connection
for a feature that makes no database changes.
"""

import importlib

import pytest

# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def app():
    """Reload the app module fresh for each test and configure for testing."""
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    return app_module.app


@pytest.fixture
def client(app):
    """Flask test client, logged out by default."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client with a fake user id already in session (no DB row needed
    for the routing/template assertions exercised by this feature)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"
    return client


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _body(response):
    return response.get_data(as_text=True)


# ------------------------------------------------------------------ #
# 1. GET / renders home.html and is publicly accessible                #
# ------------------------------------------------------------------ #


class TestHomepagePublicAccess:
    def test_get_root_returns_200_logged_out(self, client):
        """GET / must return 200 for an unauthenticated visitor."""
        response = client.get("/")
        assert (
            response.status_code == 200
        ), "GET / must be publicly accessible and return 200 when logged out"

    def test_get_root_does_not_redirect_when_logged_out(self, client):
        """GET / must not redirect an unauthenticated visitor to /login."""
        response = client.get("/", follow_redirects=False)
        assert (
            response.status_code != 302
        ), "GET / must not redirect unauthenticated visitors — it is a public page"

    def test_get_root_returns_200_logged_in(self, auth_client):
        """GET / must also return 200 for a logged-in user (still public)."""
        response = auth_client.get("/")
        assert (
            response.status_code == 200
        ), "GET / must remain accessible (200) for logged-in users too"

    def test_get_root_renders_html_document(self, client):
        """GET / must render a full HTML document."""
        body = _body(client.get("/"))
        assert (
            "<!DOCTYPE" in body or "<html" in body.lower()
        ), "GET / must render a full HTML document"

    def test_get_root_extends_base_template(self, client):
        """The homepage must extend base.html — footer/brand markup from the
        base layout should be present."""
        body = _body(client.get("/"))
        assert (
            "Oxos" in body
        ), "Expected base.html brand markup ('Oxos') to render on the homepage"

    def test_get_root_is_not_the_authenticated_platform_page(self, client):
        """GET / must render the new marketing homepage, not the old
        authenticated platform/app content."""
        body = _body(client.get("/"))
        # Business Outcomes / Learnings sections belong to the authenticated
        # /platform page per the previous behaviour — they must not appear
        # on the new public homepage.
        assert (
            "Business Outcomes" not in body
        ), "The public homepage must not render the authenticated /platform content"


# ------------------------------------------------------------------ #
# 2. Homepage is a static marketing page — no form validation needed   #
# ------------------------------------------------------------------ #


class TestHomepageIsStaticMarketingPage:
    def test_homepage_get_has_no_form_elements_requiring_input(self, client):
        """The homepage is a static marketing page — it should not contain
        an input form that requires validation (e.g. no <form> posting user
        data directly on this page)."""
        body = _body(client.get("/"))
        assert (
            "<form" not in body.lower()
        ), "The homepage should not contain a data-entry <form> — it is a static marketing page"

    def test_homepage_post_not_allowed(self, client):
        """POST / should not be a supported method for the static homepage."""
        response = client.post("/")
        assert response.status_code in (
            405,
            404,
        ), "POST / should not be supported on the static marketing homepage"


# ------------------------------------------------------------------ #
# 3. /platform continues to serve the authenticated application        #
# ------------------------------------------------------------------ #


class TestPlatformRouteUnchanged:
    def test_platform_route_exists(self, client):
        """GET /platform must exist as a route."""
        response = client.get("/platform")
        assert response.status_code in (
            200,
            302,
        ), "GET /platform must exist as a route (200 if accessible, 302 if auth-guarded)"

    def test_platform_route_is_distinct_from_home(self, client):
        """/platform must be a distinct route from / (the new homepage)."""
        home_body = _body(client.get("/"))
        platform_response = client.get("/platform", follow_redirects=False)
        # Whatever /platform returns, it must not be identical to the
        # homepage response — they are different pages serving different
        # audiences.
        if platform_response.status_code == 200:
            platform_body = platform_response.get_data(as_text=True)
            assert (
                platform_body != home_body
            ), "/platform must render different content from the public homepage at /"


# ------------------------------------------------------------------ #
# 4. Protected routes still redirect unauthenticated users to /login   #
# ------------------------------------------------------------------ #


class TestProtectedRoutesStillGuarded:
    @pytest.mark.parametrize(
        "path",
        [
            "/profile",
            "/roadmap",
            "/features",
        ],
    )
    def test_protected_get_route_redirects_to_login_when_logged_out(self, client, path):
        """Protected GET routes must redirect unauthenticated users to /login."""
        response = client.get(path, follow_redirects=False)
        assert (
            response.status_code == 302
        ), f"GET {path} must redirect (302) unauthenticated users"
        assert "/login" in response.headers.get(
            "Location", ""
        ), f"GET {path} must redirect unauthenticated users to /login"

    @pytest.mark.parametrize(
        "path,form_data",
        [
            (
                "/profile/add-expense",
                {"amount": "10", "category": "Food", "date": "2026-01-01"},
            ),
            (
                "/profile/edit-expense",
                {
                    "expense_id": "1",
                    "amount": "10",
                    "category": "Food",
                    "date": "2026-01-01",
                },
            ),
            ("/expenses/1/delete", {}),
        ],
    )
    def test_protected_post_route_redirects_to_login_when_logged_out(
        self, client, path, form_data
    ):
        """Protected POST routes (expense mutations) must redirect
        unauthenticated users to /login rather than performing the action."""
        response = client.post(path, data=form_data, follow_redirects=False)
        assert (
            response.status_code == 302
        ), f"POST {path} must redirect (302) unauthenticated users"
        assert "/login" in response.headers.get(
            "Location", ""
        ), f"POST {path} must redirect unauthenticated users to /login"

    def test_platform_route_guard_behavior_unchanged(self, client):
        """/platform's auth-guard behaviour must be unaffected by the
        homepage routing change — if it requires auth, it must redirect to
        /login just like before."""
        response = client.get("/platform", follow_redirects=False)
        if response.status_code == 302:
            assert "/login" in response.headers.get(
                "Location", ""
            ), "/platform must redirect to /login if it requires authentication"


# ------------------------------------------------------------------ #
# 5. Logout redirects to / (the new homepage)                          #
# ------------------------------------------------------------------ #


class TestLogoutRedirectsToHomepage:
    def test_logout_redirects_to_root(self, auth_client):
        """GET /logout must redirect to / (the new public homepage)."""
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302, "GET /logout must issue a redirect"
        location = response.headers.get("Location", "")
        assert (
            location.rstrip("/") == "" or location == "/"
        ), f"GET /logout must redirect to '/' (the new homepage), got '{location}'"

    def test_logout_clears_session(self, auth_client):
        """After logout, the session must no longer be authenticated —
        subsequent requests to protected routes should redirect to /login."""
        auth_client.get("/logout")
        response = auth_client.get("/profile", follow_redirects=False)
        assert (
            response.status_code == 302
        ), "After logout, protected routes must redirect (session cleared)"
        assert "/login" in response.headers.get("Location", "")

    def test_logout_landing_page_is_reachable_and_200(self, auth_client):
        """Following the logout redirect must land on a 200 homepage."""
        response = auth_client.get("/logout", follow_redirects=True)
        assert (
            response.status_code == 200
        ), "Following the logout redirect must land on the public homepage with 200"


# ------------------------------------------------------------------ #
# 6. Navigation links (logo, home) link to /                          #
# ------------------------------------------------------------------ #


class TestNavigationLinksToRoot:
    def test_homepage_logo_links_to_root(self, client):
        """The logo/brand element on the homepage must link to /."""
        body = _body(client.get("/"))
        assert (
            'href="/"' in body
        ), "The homepage logo/brand must link to '/' via href=\"/\""

    def test_base_template_brand_links_to_root(self, client):
        """The shared nav brand (from base.html) must also link to /."""
        body = _body(client.get("/"))
        assert (
            'href="/"' in body
        ), "The base.html nav brand must link to '/' (the homepage)"


# ------------------------------------------------------------------ #
# 7. "Get Started" button links to /login                              #
# ------------------------------------------------------------------ #


class TestGetStartedLinksToLogin:
    def test_get_started_text_present(self, client):
        """The homepage must contain a 'Get Started' (or 'Get started') CTA."""
        body = _body(client.get("/"))
        assert (
            "Get started" in body or "Get Started" in body
        ), "The homepage must contain a 'Get Started' call-to-action"

    def test_get_started_links_to_login(self, client):
        """The 'Get Started' button must link to /login."""
        body = _body(client.get("/"))
        assert (
            'href="/login"' in body
        ), "The 'Get Started' button must link to /login via href=\"/login\""

    def test_no_click_here_style_link_text(self, client):
        """All links must be descriptive — no 'click here' style text per
        the spec's UI/UX notes."""
        body = _body(client.get("/")).lower()
        assert (
            "click here" not in body
        ), "Links must be descriptive; 'click here' style text must not appear"


# ------------------------------------------------------------------ #
# 8. SEO metadata (title, meta description) present                    #
# ------------------------------------------------------------------ #


class TestHomepageSEOMetadata:
    def test_homepage_has_a_title_tag(self, client):
        """The homepage must have a non-empty <title> tag."""
        body = _body(client.get("/"))
        assert "<title>" in body, "The homepage must include a <title> tag"
        start = body.find("<title>") + len("<title>")
        end = body.find("</title>", start)
        title_text = body[start:end].strip()
        assert title_text, "The <title> tag on the homepage must not be empty"

    def test_homepage_title_is_not_generic_default(self, client):
        """The homepage title should be specific to Oxos, not a bare
        placeholder like just 'Spendly' with no further context."""
        body = _body(client.get("/"))
        start = body.find("<title>") + len("<title>")
        end = body.find("</title>", start)
        title_text = body[start:end].strip()
        assert (
            "Oxos" in title_text
        ), f"Expected the homepage <title> to reference 'Oxos', got: '{title_text}'"

    def test_homepage_has_meta_description(self, client):
        """The homepage must include a meta description tag for SEO."""
        body = _body(client.get("/"))
        assert (
            'name="description"' in body
        ), 'The homepage must include a <meta name="description"> tag'

    def test_homepage_meta_description_has_content(self, client):
        """The meta description's content attribute must be non-empty."""
        body = _body(client.get("/"))
        idx = body.find('name="description"')
        assert idx != -1, "Expected a meta description tag on the homepage"
        # Look for the content="..." attribute near the description tag
        snippet = body[idx : idx + 400]
        assert (
            'content="' in snippet
        ), "The meta description tag must include a content attribute"
        content_start = snippet.find('content="') + len('content="')
        content_end = snippet.find('"', content_start)
        content_text = snippet[content_start:content_end].strip()
        assert content_text, "The meta description content attribute must not be empty"


# ------------------------------------------------------------------ #
# 9. A favicon is referenced in base.html                              #
# ------------------------------------------------------------------ #


class TestFaviconReferenced:
    def test_homepage_response_includes_favicon_link(self, client):
        """The rendered homepage (via base.html) must include a favicon
        <link rel="icon"> tag."""
        body = _body(client.get("/"))
        assert (
            'rel="icon"' in body
        ), 'base.html must include a <link rel="icon"> favicon tag'

    def test_favicon_link_points_to_static_asset(self, client):
        """The favicon link's href must point to a static asset path."""
        body = _body(client.get("/"))
        idx = body.find('rel="icon"')
        assert idx != -1, 'Expected a favicon <link rel="icon"> tag'
        snippet = body[max(0, idx - 200) : idx + 200]
        assert (
            "/static/" in snippet
        ), "The favicon link must reference a /static/ asset path"

    def test_favicon_referenced_on_other_pages_too(self, client):
        """Since the favicon lives in base.html, it must also appear on
        other pages that extend base.html (e.g. /login)."""
        body = _body(client.get("/login"))
        assert (
            'rel="icon"' in body
        ), "The favicon link from base.html must also appear on /login"


# ------------------------------------------------------------------ #
# 10. No unused JS from the mockup is loaded on the homepage            #
# ------------------------------------------------------------------ #


class TestNoUnusedMockupJS:
    def test_lucide_cdn_script_loaded_exactly_once(self, client):
        """The homepage must load the Lucide CDN script exactly once (from
        base.html) — the mockup's own separate <script> tag for Lucide must
        not be duplicated."""
        body = _body(client.get("/"))
        count = body.count('src="https://unpkg.com/lucide')
        assert (
            count == 1
        ), f"Expected exactly one Lucide CDN <script> tag on the homepage, found {count}"

    def test_no_duplicate_chart_js_or_unrelated_bundles(self, client):
        """The homepage is a public marketing page and must not load
        authenticated-only JS bundles (e.g. Chart.js used by the analytics
        dashboard) beyond what base.html already includes globally."""
        body = _body(client.get("/"))
        # Chart.js is loaded globally in base.html for the whole app; this
        # test only guards against a *second* extra load specific to the
        # mockup, not the shared base.html include itself.
        count = body.count("chart.js@4.4.0")
        assert (
            count <= 1
        ), f"Expected at most one Chart.js CDN reference (from base.html), found {count}"


# ------------------------------------------------------------------ #
# 11. Inline CSS extracted to static/css/home.css, no duplicates        #
# ------------------------------------------------------------------ #


class TestInlineCSSExtractedToHomeCSS:
    def test_homepage_links_home_css_stylesheet(self, client):
        """The homepage must link static/css/home.css as an external
        stylesheet."""
        body = _body(client.get("/"))
        assert "css/home.css" in body, "The homepage must link to static/css/home.css"

    def test_home_css_is_served_successfully(self, client):
        """static/css/home.css must be served with a 200 response."""
        response = client.get("/static/css/home.css")
        assert (
            response.status_code == 200
        ), "GET /static/css/home.css must return 200 — the file must exist and be servable"

    def test_homepage_has_no_inline_style_block(self, client):
        """The homepage template must not contain an inline <style> block —
        all styling must live in the extracted home.css file."""
        body = _body(client.get("/"))
        assert (
            "<style" not in body.lower()
        ), "The homepage must not contain an inline <style> block; CSS must be extracted to home.css"

    def test_home_css_stylesheet_linked_only_once(self, client):
        """home.css must not be linked more than once on the homepage."""
        body = _body(client.get("/"))
        count = body.count("css/home.css")
        assert (
            count == 1
        ), f"Expected home.css to be linked exactly once, found {count} references"


# ------------------------------------------------------------------ #
# 12. Lucide icons use the existing CDN already in base.html            #
# ------------------------------------------------------------------ #


class TestLucideUsesExistingCDN:
    def test_homepage_does_not_load_a_second_lucide_cdn(self, client):
        """The homepage must not load its own separate Lucide CDN script —
        it must rely on the one already declared in base.html."""
        body = _body(client.get("/"))
        lucide_script_urls = [
            "unpkg.com/lucide",
        ]
        for url in lucide_script_urls:
            count = body.count(url)
            assert (
                count == 1
            ), f"Expected the Lucide CDN reference '{url}' to appear exactly once (from base.html), found {count}"

    def test_homepage_uses_lucide_data_attributes(self, client):
        """The homepage should use Lucide's data-lucide attribute convention
        for icons, consistent with the rest of the app."""
        body = _body(client.get("/"))
        assert (
            "data-lucide=" in body
        ), "Expected the homepage to use Lucide's data-lucide icon convention"


# ------------------------------------------------------------------ #
# 13. Google Fonts use the existing fonts in base.html                  #
# ------------------------------------------------------------------ #


class TestGoogleFontsReused:
    def test_homepage_does_not_load_a_second_google_fonts_stylesheet(self, client):
        """The homepage must not add a second/duplicate Google Fonts
        <link> — it must reuse the single one already in base.html."""
        body = _body(client.get("/"))
        count = body.count("fonts.googleapis.com/css2")
        assert (
            count == 1
        ), f"Expected exactly one Google Fonts stylesheet link (from base.html), found {count}"

    def test_google_fonts_reference_dm_serif_and_dm_sans(self, client):
        """The shared Google Fonts link must reference DM Serif Display and
        DM Sans, matching the CSS variables documented for the project."""
        body = _body(client.get("/"))
        idx = body.find("fonts.googleapis.com/css2")
        assert idx != -1, "Expected a Google Fonts stylesheet link on the homepage"
        snippet = body[idx : idx + 200]
        assert (
            "DM+Serif+Display" in snippet
        ), "Expected the Google Fonts link to reference DM+Serif+Display"
        assert (
            "DM+Sans" in snippet
        ), "Expected the Google Fonts link to reference DM+Sans"


# ------------------------------------------------------------------ #
# Edge cases                                                           #
# ------------------------------------------------------------------ #


class TestHomepageEdgeCases:
    def test_trailing_slash_variants_do_not_error(self, client):
        """GET / must not 500 regardless of query string noise."""
        response = client.get("/?utm_source=test&ref=abc")
        assert (
            response.status_code == 200
        ), "GET / with query params must still return 200, not error"

    def test_homepage_not_found_paths_return_404(self, client):
        """A nonsense nested path under / must not incorrectly render the
        homepage — it should 404."""
        response = client.get("/this-route-does-not-exist")
        assert (
            response.status_code == 404
        ), "Unknown routes must return 404, not silently fall back to the homepage"

    def test_homepage_head_request_supported_or_gracefully_rejected(self, client):
        """A HEAD request to / should not raise a server error."""
        response = client.head("/")
        assert response.status_code in (
            200,
            405,
        ), "HEAD / must not raise a server error (500)"
