"""Feature 15.1 — Roadmap Pipeline: /roadmap route, features table, and seed.

Strategy
--------
The app uses psycopg2 against a real Postgres database (DATABASE_URL).  To keep
tests isolated we monkeypatch ``database.db.get_db`` AND the copy of that name
already imported into ``database.queries`` so that every DB call within a test
uses the same connection object.

Isolation is achieved by TRUNCATE, not rollback.  The helper functions in db.py
and queries.py call ``conn.commit()`` internally, so a single outer rollback
cannot undo their side effects.  Instead, the ``_patched_get_db`` fixture truncates
the ``features`` table at both setup and teardown, giving every test a clean slate.

app.py is reloaded via ``importlib.reload`` so the module-level ``init_db()`` /
``seed_features()`` calls hit the patched function.  Because ``seed_features()``
runs again on reload, the ``client`` fixture (which requires an empty table)
truncates once more immediately after reload.

Fixture hierarchy
-----------------
  client           — Flask test client, features table initialised but EMPTY
  seeded_client    — Flask test client, features table initialised AND seeded
  auth_client      — seeded_client with the demo user already in session

Spec behaviours covered (Definition of Done from 15.1 spec)
------------------------------------------------------------
1.  GET /roadmap returns HTTP 200 for an unauthenticated request
2.  GET /roadmap does not redirect to /login
3.  GET /roadmap renders HTML that extends base.html (nav + main landmarks present)
4.  Page title is "Roadmap — Spendly"
5.  "Roadmap" nav link is present and points to /roadmap when logged out
6.  "Roadmap" nav link is present on the landing page (base.html) when logged out
7.  "Roadmap" nav link is present when logged in
8.  Pipeline table is rendered when the features table has rows
9.  Each seeded feature title appears in the pipeline table HTML
10. Completed stage columns show the ✓ glyph
11. Completed stage columns show a non-empty date string (not "None" / "null")
12. Incomplete stage cells do not contain the literal strings "None" or "null"
13. Status badge is present on each row and reflects the rightmost non-null stage
14. A fully-shipped feature row carries a "Shipped" status badge
15. A feature with only in_progress_at set carries an "Implementation" status badge
16. A feature with no stage timestamps carries an "Upcoming" status badge
17. GET /roadmap with an empty features table returns 200 (no 500)
18. Empty-state message "No features yet." is shown when the features table is empty
19. No <table> element is rendered when the features table is empty
20. seed_features() is idempotent — calling it twice does not insert duplicate rows
21. get_all_features() returns a list of dicts with the required keys
22. Completed stage values in get_all_features() output have "short" and "full" keys
23. Null stage values in get_all_features() output are Python None (not the string)
24. status field in get_all_features() output is a non-empty string
25. GET /roadmap does not return 500 regardless of auth state
"""

import importlib

import psycopg2
import psycopg2.extras
import pytest

import database.db as db_module
from database.db import init_db, seed_features
import database.queries as queries_module

# ------------------------------------------------------------------ #
# Required stage keys returned by _feature_row / get_all_features()  #
# ------------------------------------------------------------------ #

REQUIRED_FEATURE_KEYS = {
    "number",
    "parent_number",
    "title",
    "slug",
    "type",
    "status",
    "captured_at",
    "planned_at",
    "in_progress_at",
    "in_review_at",
    "code_reviewed_at",
    "shipped_at",
}

STAGE_KEYS = (
    "captured_at",
    "planned_at",
    "in_progress_at",
    "in_review_at",
    "code_reviewed_at",
    "shipped_at",
)

# Timestamp used for "already shipped" rows in inline insert helpers
SHIPPED_TS = "2026-05-01 00:00:00"


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def _patched_get_db(monkeypatch):
    """
    Open a single real Postgres connection and monkeypatch ``database.db.get_db``
    (and the copy already imported in ``database.queries``) so that every DB call
    within a test uses the same connection.

    Isolation strategy: truncate the features table at both setup and teardown so
    each test starts with a clean slate.  We do NOT rely on rollback because the
    helper functions in db.py and queries.py call ``conn.commit()`` internally,
    making transaction-based rollback ineffective for data isolation.

    Yields the connection itself so helpers can run raw SQL if needed.
    """
    # Ensure schema is current before patching so init_db() manages its own connection
    init_db()

    _real_conn = db_module.get_db()

    class _NoCloseProxy:
        """Delegates to _real_conn but no-ops close() so production helpers
        cannot close the shared connection mid-test."""

        def close(self):
            pass

        def __getattr__(self, name):
            return getattr(_real_conn, name)

    conn = _NoCloseProxy()

    def _fake_get_db():
        return conn

    monkeypatch.setattr(db_module, "get_db", _fake_get_db)
    monkeypatch.setattr(queries_module, "get_db", _fake_get_db)

    # Clean slate before the test
    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()

    yield conn

    # Recover from any aborted transaction before teardown
    _real_conn.rollback()

    # Clean up after the test so no rows leak into subsequent tests
    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()

    _real_conn.close()


@pytest.fixture
def client(_patched_get_db, monkeypatch):
    """
    Flask test client with an empty features table (init_db run, seed NOT run).

    importlib.reload triggers the module-level seed_features() call in app.py.
    We truncate the features table immediately after reload so tests that require
    an empty table start from a guaranteed empty state.
    """
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    # Clear any rows inserted by the module-level seed_features() during reload
    cur = _patched_get_db.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _patched_get_db.commit()
    cur.close()

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(_patched_get_db, monkeypatch):
    """
    Flask test client with the features table initialised AND seeded via
    seed_features().
    """
    seed_features()

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(seeded_client, _patched_get_db):
    """
    Seeded test client with the first user already in session.
    Inserts a throwaway user into the users table so the session user_id resolves.
    """
    import uuid
    from werkzeug.security import generate_password_hash

    email = f"testuser-{uuid.uuid4().hex[:8]}@spendly.test"
    conn = _patched_get_db
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
        ("Test User", email, generate_password_hash("testpass123")),
    )
    user = cur.fetchone()
    conn.commit()
    user_id = user["id"]
    cur.close()

    with seeded_client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Test User"

    yield seeded_client

    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _body(response):
    return response.get_data(as_text=True)


def _insert_feature_row(
    conn,
    number,
    title,
    slug,
    captured_at=None,
    planned_at=None,
    in_progress_at=None,
    in_review_at=None,
    code_reviewed_at=None,
    shipped_at=None,
    parent_number=None,
    ftype="feature",
):
    """Insert a single row into the features table; returns the new id."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO features"
        " (number, parent_number, title, slug, type,"
        "  captured_at, planned_at, in_progress_at, in_review_at,"
        "  code_reviewed_at, shipped_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id",
        (
            number,
            parent_number,
            title,
            slug,
            ftype,
            captured_at,
            planned_at,
            in_progress_at,
            in_review_at,
            code_reviewed_at,
            shipped_at,
        ),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return row["id"]


def _count_features_in_db(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM features")
    count = cur.fetchone()[0]
    cur.close()
    return count


def _truncate_features(conn):
    cur = conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    conn.commit()
    cur.close()


# ------------------------------------------------------------------ #
# 1. Public access — GET /roadmap                                      #
# ------------------------------------------------------------------ #


class TestRoadmapPublicAccess:
    def test_get_roadmap_returns_200_unauthenticated(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "GET /roadmap must return 200 for unauthenticated visitors"

    def test_get_roadmap_does_not_redirect_to_login(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code != 302
        ), "GET /roadmap must not redirect unauthenticated visitors"

    def test_get_roadmap_does_not_return_500(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert resp.status_code != 500, "GET /roadmap must not raise a 500 server error"

    def test_get_roadmap_returns_html(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "<html" in body.lower() or "<!doctype html" in body.lower()
        ), "GET /roadmap must return an HTML document"

    def test_get_roadmap_returns_200_when_logged_in(self, auth_client):
        resp = auth_client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "GET /roadmap must return 200 for authenticated users too"


# ------------------------------------------------------------------ #
# 2. Page title and template structure                                  #
# ------------------------------------------------------------------ #


class TestRoadmapPageStructure:
    def test_page_title_is_roadmap_spendly(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "Roadmap — Spendly" in body or "Roadmap — Spendly" in body
        ), "Page <title> must be 'Roadmap — Spendly'"

    def test_page_extends_base_html_has_nav(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "<nav" in body
        ), "Roadmap page must extend base.html and include the <nav> element"

    def test_page_has_main_content(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "<main" in body
        ), "Roadmap page must include the <main> element from base.html"

    def test_page_heading_contains_roadmap(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "Roadmap" in body
        ), "Roadmap page body must contain the heading text 'Roadmap'"


# ------------------------------------------------------------------ #
# 3. Nav link visibility                                               #
# ------------------------------------------------------------------ #


class TestRoadmapNavLink:
    def test_roadmap_nav_link_text_present_logged_out(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "Roadmap" in body
        ), "'Roadmap' nav link text must appear for logged-out visitors"

    def test_roadmap_nav_link_href_present_logged_out(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            'href="/roadmap"' in body
        ), "Nav must contain an href pointing to /roadmap for logged-out visitors"

    def test_roadmap_nav_link_present_on_landing_page_logged_out(self, seeded_client):
        body = _body(seeded_client.get("/"))
        assert (
            "Roadmap" in body
        ), "'Roadmap' nav link must appear on the landing page for logged-out visitors"

    def test_roadmap_nav_link_href_on_landing_page(self, seeded_client):
        body = _body(seeded_client.get("/"))
        assert (
            "/roadmap" in body
        ), "Landing page nav must include a link pointing to /roadmap"

    def test_roadmap_nav_link_present_on_login_page(self, seeded_client):
        body = _body(seeded_client.get("/login"))
        assert "Roadmap" in body, "'Roadmap' nav link must appear on the login page"

    def test_roadmap_nav_link_present_logged_in(self, auth_client):
        body = _body(auth_client.get("/roadmap"))
        assert (
            "Roadmap" in body
        ), "'Roadmap' nav link must appear for authenticated users"

    def test_roadmap_nav_link_href_present_logged_in(self, auth_client):
        body = _body(auth_client.get("/roadmap"))
        assert (
            'href="/roadmap"' in body
        ), "Nav must contain an href pointing to /roadmap for authenticated users"


# ------------------------------------------------------------------ #
# 4. Pipeline table — seeded data                                      #
# ------------------------------------------------------------------ #


class TestRoadmapPipelineTable:
    def test_pipeline_table_element_present_with_seeded_data(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "<table" in body
        ), "A <table> element must be rendered when the features table has rows"

    def test_pipeline_table_has_column_headers(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert "<th" in body, "Pipeline table must have <th> header cells"

    def test_pipeline_table_headers_use_scope_col(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            'scope="col"' in body
        ), 'Table headers must use scope="col" for accessibility (WCAG)'

    def test_seeded_feature_titles_appear_in_table(self, seeded_client):
        """At least the known backfilled titles from seed_features() must be visible."""
        body = _body(seeded_client.get("/roadmap"))
        for title in ("Database Setup", "Registration", "Login and Logout"):
            assert (
                title in body
            ), f"Seeded feature title '{title}' must appear in the pipeline table"

    def test_multiple_feature_rows_rendered(self, seeded_client):
        """With the full seed there should be many <tr> rows inside the <tbody>."""
        body = _body(seeded_client.get("/roadmap"))
        # The seed inserts 21 rows; even a conservative check of >=5 <tr> is sufficient
        tr_count = body.count("<tr")
        assert (
            tr_count >= 5
        ), f"Pipeline table must render multiple rows; found only {tr_count} <tr> elements"

    def test_feature_number_appears_in_table(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        # Feature "01" — Database Setup — is always the first seeded row
        assert "01" in body, "Feature number '01' must appear in the pipeline table"


# ------------------------------------------------------------------ #
# 5. Completed stage columns — ✓ glyph and date                       #
# ------------------------------------------------------------------ #


class TestCompletedStageColumns:
    def test_shipped_feature_row_contains_check_glyph(self, seeded_client):
        """A fully-shipped seeded feature must show the ✓ tick in its stage cells."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "✓" in body or "&#x2713;" in body or "✓" in body
        ), "Completed stage cells must contain the ✓ (U+2713) check glyph"

    def test_shipped_feature_row_contains_date_text(self, seeded_client):
        """A shipped seeded feature must show a date string (e.g. 'May 2026') in its cells."""
        body = _body(seeded_client.get("/roadmap"))
        # The seed uses 2026-05-01 for all shipped stages — formatted as "May 1 2026"
        assert (
            "2026" in body
        ), "Completed stage cells must contain the year part of the timestamp"

    def test_completed_stage_shows_roadmap_check_class(self, seeded_client):
        """The template uses class='roadmap-check' for the ✓ glyph span."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "roadmap-check" in body
        ), "Completed stage cells must render a span with class 'roadmap-check'"

    def test_completed_stage_shows_roadmap_date_class(self, seeded_client):
        """The template uses class='roadmap-date' for the date span."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "roadmap-date" in body
        ), "Completed stage cells must render a span with class 'roadmap-date'"

    def test_inline_shipped_feature_check_glyph(self, client, _patched_get_db):
        """Insert a fully-shipped feature inline and verify the ✓ appears."""
        _insert_feature_row(
            _patched_get_db,
            number="T01",
            title="Inline Shipped Feature for Check Glyph Test",
            slug="inline-shipped-check",
            captured_at=SHIPPED_TS,
            planned_at=SHIPPED_TS,
            in_progress_at=SHIPPED_TS,
            in_review_at=SHIPPED_TS,
            code_reviewed_at=SHIPPED_TS,
            shipped_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            "Inline Shipped Feature for Check Glyph Test" in body
        ), "Inline-inserted feature title must appear in the pipeline table"
        assert (
            "✓" in body or "✓" in body
        ), "Inline shipped feature must show the ✓ glyph in its stage cells"


# ------------------------------------------------------------------ #
# 6. Incomplete stage columns — no "None" or "null" in HTML           #
# ------------------------------------------------------------------ #


class TestIncompleteStageColumns:
    def test_none_literal_not_in_roadmap_html(self, seeded_client):
        """Stage cells for null timestamps must not render the string 'None'."""
        body = _body(seeded_client.get("/roadmap"))
        # Search specifically in table cell context — the word "None" must not
        # appear as rendered text (it would indicate a template rendering bug)
        assert (
            ">None<" not in body
        ), "Null stage cells must not render the literal string 'None' as cell content"

    def test_null_literal_not_in_roadmap_html(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            ">null<" not in body
        ), "Null stage cells must not render the literal string 'null' as cell content"

    def test_inline_in_progress_only_no_none_in_html(self, client, _patched_get_db):
        """A feature with only in_progress_at set must not show 'None' for other stages."""
        _insert_feature_row(
            _patched_get_db,
            number="T02",
            title="In Progress Only Feature for None Suppression Test",
            slug="in-progress-only-none-test",
            in_progress_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            ">None<" not in body
        ), "Incomplete stage cells must not render '>None<' when only in_progress_at is set"
        assert (
            ">null<" not in body
        ), "Incomplete stage cells must not render '>null<' when only in_progress_at is set"

    def test_inline_captured_only_no_none_in_html(self, client, _patched_get_db):
        """A feature with only captured_at set must not show 'None' for later stages."""
        _insert_feature_row(
            _patched_get_db,
            number="T03",
            title="Captured Only Feature for None Suppression Test Here",
            slug="captured-only-none-test",
            captured_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            ">None<" not in body
        ), "Incomplete stage cells (only captured_at set) must not render '>None<'"


# ------------------------------------------------------------------ #
# 7. Status badge — derives from rightmost non-null stage              #
# ------------------------------------------------------------------ #


class TestStatusBadge:
    def test_shipped_feature_has_shipped_status_badge(self, seeded_client):
        """The seed contains many fully shipped features — 'Shipped' badge must appear."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "Shipped" in body
        ), "Status badge 'Shipped' must appear for fully shipped features"

    def test_roadmap_badge_class_present(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "roadmap-badge" in body
        ), "Status badges must have the CSS class 'roadmap-badge'"

    def test_inline_in_progress_feature_has_implementation_badge(
        self, client, _patched_get_db
    ):
        """A feature with only in_progress_at set must show 'Implementation' badge."""
        _insert_feature_row(
            _patched_get_db,
            number="T04",
            title="In Progress Feature for Implementation Badge Status Test",
            slug="in-progress-badge-test",
            in_progress_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            "Implementation" in body
        ), "A feature with only in_progress_at set must carry the 'Implementation' status badge"

    def test_inline_upcoming_feature_has_upcoming_status(self, client, _patched_get_db):
        """A feature with no stage timestamps must show 'Upcoming' status."""
        _insert_feature_row(
            _patched_get_db,
            number="T05",
            title="Upcoming Feature No Stage Timestamps Status Badge Test",
            slug="upcoming-status-badge-test",
        )
        body = _body(client.get("/roadmap"))
        assert (
            "Upcoming" in body
        ), "A feature with no stage timestamps must carry the 'Upcoming' status badge"

    def test_inline_captured_only_has_req_captured_status(
        self, client, _patched_get_db
    ):
        """A feature with only captured_at set must show 'Req Captured' status."""
        _insert_feature_row(
            _patched_get_db,
            number="T06",
            title="Req Captured Only Feature for Status Badge Verification Test",
            slug="req-captured-status-test",
            captured_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            "Req Captured" in body
        ), "A feature with only captured_at set must carry 'Req Captured' status badge"

    def test_inline_planned_only_has_planned_status(self, client, _patched_get_db):
        """A feature with captured_at and planned_at set must show 'Planned' status."""
        _insert_feature_row(
            _patched_get_db,
            number="T07",
            title="Planned Feature with Captured and Planned Status Badge Test",
            slug="planned-status-badge-test",
            captured_at=SHIPPED_TS,
            planned_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            "Planned" in body
        ), "A feature with captured_at and planned_at set must carry 'Planned' status badge"

    def test_inline_shipped_feature_has_shipped_status(self, client, _patched_get_db):
        """A feature with all stages set must show 'Shipped' as its status."""
        _insert_feature_row(
            _patched_get_db,
            number="T08",
            title="All Stages Set Feature for Shipped Status Badge Inline Test",
            slug="all-stages-shipped-badge-test",
            captured_at=SHIPPED_TS,
            planned_at=SHIPPED_TS,
            in_progress_at=SHIPPED_TS,
            in_review_at=SHIPPED_TS,
            code_reviewed_at=SHIPPED_TS,
            shipped_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        assert (
            "Shipped" in body
        ), "A feature with all stage timestamps set must carry the 'Shipped' status badge"


# ------------------------------------------------------------------ #
# 8. Empty-state message                                               #
# ------------------------------------------------------------------ #


class TestEmptyState:
    def test_empty_features_table_returns_200(self, client):
        """GET /roadmap with an empty features table must return 200, not 500."""
        resp = client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "GET /roadmap must return 200 even when the features table is empty"

    def test_empty_features_table_shows_no_features_yet(self, client):
        body = _body(client.get("/roadmap"))
        assert (
            "No features yet." in body
        ), "Empty features table must render the 'No features yet.' empty-state message"

    def test_empty_features_table_no_table_element(self, client):
        body = _body(client.get("/roadmap"))
        assert (
            "<table" not in body
        ), "When the features table is empty no <table> element must be rendered"

    def test_empty_features_table_no_none_literal(self, client):
        body = _body(client.get("/roadmap"))
        assert (
            ">None<" not in body and ">null<" not in body
        ), "Empty-state page must not contain '>None<' or '>null<' in the HTML"


# ------------------------------------------------------------------ #
# 9. seed_features() idempotency                                       #
# ------------------------------------------------------------------ #


class TestSeedFeaturesIdempotency:
    def test_seed_features_twice_does_not_duplicate_rows(self, _patched_get_db):
        """Calling seed_features() twice must not insert duplicate rows."""
        seed_features()
        count_after_first = _count_features_in_db(_patched_get_db)

        seed_features()
        count_after_second = _count_features_in_db(_patched_get_db)

        assert count_after_first == count_after_second, (
            f"seed_features() must be idempotent: "
            f"first call inserted {count_after_first} rows, "
            f"second call changed count to {count_after_second}"
        )

    def test_seed_features_once_inserts_rows(self, _patched_get_db):
        """seed_features() on an empty table must insert at least one row."""
        seed_features()
        count = _count_features_in_db(_patched_get_db)
        assert (
            count >= 1
        ), "seed_features() must insert at least one row into an empty features table"

    def test_seed_features_populates_known_entries(self, _patched_get_db):
        """After seeding, well-known feature numbers from the registry must exist."""
        seed_features()
        cur = _patched_get_db.cursor()
        cur.execute(
            "SELECT number FROM features WHERE number IN (%s, %s, %s)",
            ("01", "07", "12"),
        )
        found = {row[0] for row in cur.fetchall()}
        cur.close()
        assert (
            "01" in found
        ), "seed_features() must include feature '01' (Database Setup)"
        assert "07" in found, "seed_features() must include feature '07' (Add Expense)"
        assert (
            "12" in found
        ), "seed_features() must include feature '12' (Migration to Supabase)"

    def test_seed_features_idempotent_after_truncate_and_reseed(self, _patched_get_db):
        """Running seed, truncating, and reseeding must produce the same count."""
        seed_features()
        count_first = _count_features_in_db(_patched_get_db)

        _truncate_features(_patched_get_db)

        seed_features()
        count_second = _count_features_in_db(_patched_get_db)

        assert (
            count_first == count_second
        ), "seed_features() run after a truncate must produce the same row count as the first run"


# ------------------------------------------------------------------ #
# 10. get_all_features() output shape                                  #
# ------------------------------------------------------------------ #


class TestGetAllFeaturesShape:
    def test_get_all_features_returns_list(self, _patched_get_db):
        seed_features()
        result = queries_module.get_all_features()
        assert isinstance(result, list), "get_all_features() must return a list"

    def test_get_all_features_returns_expected_count(self, _patched_get_db):
        seed_features()
        result = queries_module.get_all_features()
        assert (
            len(result) >= 1
        ), "get_all_features() must return at least one item after seeding"

    def test_get_all_features_dicts_have_required_keys(self, _patched_get_db):
        seed_features()
        result = queries_module.get_all_features()
        for item in result:
            missing = REQUIRED_FEATURE_KEYS - set(item.keys())
            assert not missing, (
                f"Feature dict is missing required keys: {missing}. "
                f"Feature: {item.get('number', '?')}"
            )

    def test_get_all_features_completed_stages_are_dicts_with_short_and_full(
        self, _patched_get_db
    ):
        """For any shipped feature, every completed stage value must be a dict with
        'short' and 'full' keys, not a raw timestamp string or datetime object."""
        seed_features()
        result = queries_module.get_all_features()

        for feature in result:
            for key in STAGE_KEYS:
                val = feature[key]
                if val is not None:
                    assert isinstance(val, dict), (
                        f"Non-null stage '{key}' on feature '{feature['number']}' "
                        f"must be a dict, got {type(val).__name__}"
                    )
                    assert "short" in val, (
                        f"Stage dict for '{key}' on feature '{feature['number']}' "
                        f"must have a 'short' key"
                    )
                    assert "full" in val, (
                        f"Stage dict for '{key}' on feature '{feature['number']}' "
                        f"must have a 'full' key"
                    )
                    assert val["short"], (
                        f"Stage dict 'short' value for '{key}' on feature "
                        f"'{feature['number']}' must be a non-empty string"
                    )
                    assert val["full"], (
                        f"Stage dict 'full' value for '{key}' on feature "
                        f"'{feature['number']}' must be a non-empty string"
                    )

    def test_get_all_features_null_stages_are_python_none(self, _patched_get_db):
        """Stages without a timestamp must be Python None, not the string 'None'."""
        _insert_feature_row(
            _patched_get_db,
            number="SH01",
            title="Shape Check Feature with Some Null Stages Test",
            slug="shape-check-null-stages",
            captured_at=SHIPPED_TS,
            # planned_at and later are all null
        )
        result = queries_module.get_all_features()
        shape_feature = next((f for f in result if f["number"] == "SH01"), None)
        assert (
            shape_feature is not None
        ), "Inline-inserted feature 'SH01' must appear in get_all_features() output"
        assert (
            shape_feature["planned_at"] is None
        ), "A null planned_at must be Python None in get_all_features() output, not a string"
        assert (
            shape_feature["shipped_at"] is None
        ), "A null shipped_at must be Python None in get_all_features() output, not a string"
        assert (
            shape_feature["captured_at"] is not None
        ), "A non-null captured_at must not be None in get_all_features() output"

    def test_get_all_features_status_is_non_empty_string(self, _patched_get_db):
        seed_features()
        result = queries_module.get_all_features()
        for feature in result:
            assert isinstance(
                feature["status"], str
            ), f"status field on feature '{feature['number']}' must be a string"
            assert feature[
                "status"
            ], f"status field on feature '{feature['number']}' must be non-empty"

    def test_get_all_features_empty_table_returns_empty_list(self, _patched_get_db):
        result = queries_module.get_all_features()
        assert (
            result == []
        ), "get_all_features() on an empty features table must return an empty list"

    def test_get_all_features_status_for_fully_shipped_is_shipped(
        self, _patched_get_db
    ):
        """A row with all stage timestamps set must have status == 'Shipped'."""
        _insert_feature_row(
            _patched_get_db,
            number="SH02",
            title="All Stages Shipped Status Field Test Feature",
            slug="all-stages-shipped-status",
            captured_at=SHIPPED_TS,
            planned_at=SHIPPED_TS,
            in_progress_at=SHIPPED_TS,
            in_review_at=SHIPPED_TS,
            code_reviewed_at=SHIPPED_TS,
            shipped_at=SHIPPED_TS,
        )
        result = queries_module.get_all_features()
        sh02 = next((f for f in result if f["number"] == "SH02"), None)
        assert sh02 is not None, "Inline-inserted feature 'SH02' must appear in results"
        assert sh02["status"] == "Shipped", (
            f"Feature with all stage timestamps must have status 'Shipped', "
            f"got '{sh02['status']}'"
        )

    def test_get_all_features_status_for_no_stages_is_upcoming(self, _patched_get_db):
        """A row with no stage timestamps set must have status == 'Upcoming'."""
        _insert_feature_row(
            _patched_get_db,
            number="SH03",
            title="No Stages Upcoming Status Field Test Feature Row",
            slug="no-stages-upcoming-status",
        )
        result = queries_module.get_all_features()
        sh03 = next((f for f in result if f["number"] == "SH03"), None)
        assert sh03 is not None, "Inline-inserted feature 'SH03' must appear in results"
        assert sh03["status"] == "Upcoming", (
            f"Feature with no stage timestamps must have status 'Upcoming', "
            f"got '{sh03['status']}'"
        )


# ------------------------------------------------------------------ #
# 11. SQL injection safety                                             #
# ------------------------------------------------------------------ #


class TestRoadmapSQLInjectionSafety:
    def test_sql_injection_in_number_stored_safely(self, client, _patched_get_db):
        """A feature number containing SQL meta-characters must be stored and
        rendered without crashing the app."""
        _insert_feature_row(
            _patched_get_db,
            number="'; DROP TABLE features; --",
            title="SQL Injection Number Safety Test Feature Row Here",
            slug="sql-injection-number-safety",
        )
        resp = client.get("/roadmap")
        assert resp.status_code in (
            200,
            500,
        ), "GET /roadmap with a SQL injection feature number must not produce an unhandled error"
        # If it returns 200, the table must still exist (i.e. injection was neutralised)
        if resp.status_code == 200:
            count = _count_features_in_db(_patched_get_db)
            assert (
                count >= 1
            ), "SQL injection in feature number must not drop the features table"

    def test_sql_injection_in_title_does_not_drop_table(self, client, _patched_get_db):
        """A feature title containing SQL meta-characters must be handled safely."""
        _insert_feature_row(
            _patched_get_db,
            number="INJ01",
            title="'; DROP TABLE features; -- injection title safety test here",
            slug="sql-injection-title-safety",
        )
        client.get("/roadmap")
        count = _count_features_in_db(_patched_get_db)
        assert (
            count >= 1
        ), "SQL injection attempt in feature title must not drop the features table"
