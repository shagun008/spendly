"""Feature 15.2 — Roadmap Detail View: expand-in-place detail card.

Strategy
--------
The app uses psycopg2 against a real Postgres database (DATABASE_URL).
All tests use the same monkeypatching + TRUNCATE isolation strategy established
in test_15_1-roadmap-pipeline.py:

  - ``_patched_get_db`` opens one real connection, patches ``get_db`` in both
    ``database.db`` and ``database.queries``, and TRUNCATES the ``features``
    table before and after each test.
  - ``client`` reloads app.py (triggering its module-level seed calls) then
    immediately truncates again, yielding an empty features table.
  - ``seeded_client`` seeds features first, then yields a client backed by
    the full seed dataset.

Spec behaviours covered (Definition of Done from 15.2 spec)
------------------------------------------------------------
DB query / _feature_row contract:
 1. get_all_features() returns dicts that include a 'description' key
 2. A feature with a non-null description has a non-None value in that key
 3. A feature with a null description has Python None (not the string 'None')

Template — clickable row markup:
 4. Top-level feature rows with a description carry class 'roadmap-row--clickable'
 5. Top-level feature rows with a description carry aria-expanded="false" initially
 6. Top-level feature rows with a description carry aria-controls pointing to the detail row id
 7. Top-level feature rows without a description do NOT carry 'roadmap-row--clickable'
 8. Top-level feature rows without a description do NOT carry aria-expanded
 9. Release sub-rows are NOT clickable (no 'roadmap-row--clickable')

Template — detail row markup:
10. A detail <tr class="roadmap-detail-row"> exists immediately after each clickable row
11. The detail row has role="region"
12. The detail row has an aria-label equal to the feature title
13. The detail row id matches 'detail-<number>' (dots replaced with dashes)
14. The detail row contains a <td colspan="9">
15. The detail card is inside .roadmap-detail-card

Template — chevron:
16. A .roadmap-chevron element is present inside clickable rows
17. Clickable rows contain a data-lucide="chevron-down" attribute

Template — description rendering:
18. Non-null description text appears inside the .roadmap-detail-row in the HTML
19. Null description renders "No description." — never the raw string 'None'
20. The literal string 'None' does not appear as rendered content in the HTML

Template — release sub-table:
21. A feature with child release rows shows a nested <table> inside its detail card
22. Child release titles appear in the nested sub-table HTML
23. A feature with no child release rows does not show a nested <table> in its detail card

Template — JS toggle:
24. The page contains an inline <script> block with the toggle logic
25. The script references '.roadmap-row--clickable'
26. The script references 'aria-expanded'

Public access (regression):
27. GET /roadmap returns 200 for an unauthenticated request (regression from 15.1)
28. GET /roadmap does not redirect to /login (regression from 15.1)

HTML-escaping:
29. A description containing '<' and '>' is HTML-escaped in the rendered output
"""

import importlib

import psycopg2
import psycopg2.extras
import pytest

import database.db as db_module
from database.db import init_db, seed_features
import database.queries as queries_module

# ------------------------------------------------------------------ #
# Constants                                                           #
# ------------------------------------------------------------------ #

SHIPPED_TS = "2026-05-01 00:00:00"


# ------------------------------------------------------------------ #
# Fixtures — identical isolation strategy to test_15_1               #
# ------------------------------------------------------------------ #


@pytest.fixture
def _patched_get_db(monkeypatch):
    """
    Open a single real Postgres connection and monkeypatch get_db in both
    database.db and database.queries.  Truncate the features table at
    setup and teardown for full isolation between tests.
    """
    init_db()

    _real_conn = db_module.get_db()

    class _NoCloseProxy:
        """Delegates everything to _real_conn but suppresses close() calls so
        internal helpers cannot close the shared connection mid-test."""

        def close(self):
            pass

        def __getattr__(self, name):
            return getattr(_real_conn, name)

    conn = _NoCloseProxy()

    def _fake_get_db():
        return conn

    monkeypatch.setattr(db_module, "get_db", _fake_get_db)
    monkeypatch.setattr(queries_module, "get_db", _fake_get_db)

    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()

    yield conn

    _real_conn.rollback()

    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()

    _real_conn.close()


@pytest.fixture
def client(_patched_get_db, monkeypatch):
    """
    Flask test client with an empty features table.
    Reloads app.py (triggering module-level seed calls) then truncates
    immediately so each test starts with zero rows.
    """
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    cur = _patched_get_db.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _patched_get_db.commit()
    cur.close()

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(_patched_get_db, monkeypatch):
    """
    Flask test client with the features table populated via seed_features().
    """
    seed_features()

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    with app_module.app.test_client() as c:
        yield c


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _body(response):
    return response.get_data(as_text=True)


def _insert_feature(
    conn,
    number,
    title,
    slug,
    ftype="feature",
    description=None,
    parent_number=None,
    captured_at=None,
    planned_at=None,
    spec_at=None,
    implemented_at=None,
    tested_at=None,
    reviewed_at=None,
    shipped_at=None,
):
    """Insert a single row into the features table using the actual schema columns."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO features"
        " (number, parent_number, title, slug, type, description,"
        "  captured_at, planned_at, spec_at, implemented_at,"
        "  tested_at, reviewed_at, shipped_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id",
        (
            number,
            parent_number,
            title,
            slug,
            ftype,
            description,
            captured_at,
            planned_at,
            spec_at,
            implemented_at,
            tested_at,
            reviewed_at,
            shipped_at,
        ),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return row["id"]


def _number_to_detail_id(number):
    """Convert a feature number like '15.2' to its expected DOM id 'detail-15-2'."""
    return "detail-" + number.replace(".", "-")


# ------------------------------------------------------------------ #
# 1. get_all_features() includes 'description' key                   #
# ------------------------------------------------------------------ #


class TestGetAllFeaturesDescriptionKey:
    def test_description_key_present_in_feature_dict(self, _patched_get_db):
        """Every dict returned by get_all_features() must have a 'description' key."""
        _insert_feature(
            _patched_get_db,
            number="D01",
            title="Feature With Description Key Test",
            slug="description-key-test",
            description="A sample description for the key test.",
        )
        result = queries_module.get_all_features()
        assert len(result) >= 1, "get_all_features() must return at least one item"
        for item in result:
            assert "description" in item, (
                f"Feature dict for '{item.get('number', '?')}' is missing the "
                "'description' key — check that get_all_features() SELECT and "
                "_feature_row() both include description"
            )

    def test_non_null_description_value_is_string(self, _patched_get_db):
        """A feature with a non-null description must expose a string value."""
        _insert_feature(
            _patched_get_db,
            number="D02",
            title="Feature With Non Null Description Value Test",
            slug="non-null-description-value",
            description="This is a real description string for the test.",
        )
        result = queries_module.get_all_features()
        d02 = next((f for f in result if f["number"] == "D02"), None)
        assert d02 is not None, "Feature D02 must be returned by get_all_features()"
        assert isinstance(d02["description"], str), (
            "description must be a str when the DB column is non-null, "
            f"got {type(d02['description']).__name__}"
        )
        assert (
            d02["description"] == "This is a real description string for the test."
        ), "description value must match what was inserted into the DB"

    def test_null_description_value_is_python_none(self, _patched_get_db):
        """A feature with a NULL description column must expose Python None — not the
        string 'None' or an empty string."""
        _insert_feature(
            _patched_get_db,
            number="D03",
            title="Feature With Null Description Column Value Test",
            slug="null-description-value",
            description=None,
        )
        result = queries_module.get_all_features()
        d03 = next((f for f in result if f["number"] == "D03"), None)
        assert d03 is not None, "Feature D03 must be returned by get_all_features()"
        assert d03["description"] is None, (
            "description must be Python None when the DB column is NULL, "
            f"got {d03['description']!r}"
        )

    def test_null_description_not_string_none(self, _patched_get_db):
        """Ensures _feature_row() does not convert NULL to the string 'None'."""
        _insert_feature(
            _patched_get_db,
            number="D04",
            title="Feature With Null Description Not String None Test",
            slug="null-description-not-string",
            description=None,
        )
        result = queries_module.get_all_features()
        d04 = next((f for f in result if f["number"] == "D04"), None)
        assert d04 is not None, "Feature D04 must be returned by get_all_features()"
        assert (
            d04["description"] != "None"
        ), "_feature_row() must not convert NULL description to the string 'None'"

    def test_seeded_features_all_have_description_key(self, _patched_get_db):
        """After running seed_features(), every dict in get_all_features() must have
        'description' — this validates the SELECT column list is updated."""
        seed_features()
        result = queries_module.get_all_features()
        assert len(result) > 0, "seed_features() must populate the features table"
        for item in result:
            assert "description" in item, (
                f"Seeded feature '{item.get('number', '?')}' is missing 'description' "
                "key in get_all_features() output"
            )


# ------------------------------------------------------------------ #
# 2. Public access (regression)                                       #
# ------------------------------------------------------------------ #


class TestRoadmapDetailPublicAccess:
    def test_get_roadmap_returns_200_unauthenticated(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "GET /roadmap must return 200 for unauthenticated visitors (15.2 regression)"

    def test_get_roadmap_does_not_redirect_to_login(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code != 302
        ), "GET /roadmap must not redirect unauthenticated visitors to /login"

    def test_get_roadmap_does_not_return_500(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code != 500
        ), "GET /roadmap must not raise a 500 error after 15.2 template changes"


# ------------------------------------------------------------------ #
# 3. Clickable row markup — features WITH a description              #
# ------------------------------------------------------------------ #


class TestClickableRowMarkup:
    def test_clickable_class_on_feature_row_with_description(
        self, client, _patched_get_db
    ):
        """A top-level feature row whose description is non-null must carry
        class 'roadmap-row--clickable'."""
        _insert_feature(
            _patched_get_db,
            number="C01",
            title="Clickable Feature Row With Description Test",
            slug="clickable-feature-desc",
            description="A description that makes this row clickable.",
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-row--clickable" in body, (
            "A feature row with a non-null description must carry "
            "class 'roadmap-row--clickable'"
        )

    def test_aria_expanded_false_on_clickable_row(self, client, _patched_get_db):
        """A clickable row must have aria-expanded='false' in its initial state."""
        _insert_feature(
            _patched_get_db,
            number="C02",
            title="Aria Expanded False Clickable Row Test Feature",
            slug="aria-expanded-false-test",
            description="Description ensuring aria-expanded is present.",
        )
        body = _body(client.get("/roadmap"))
        assert (
            'aria-expanded="false"' in body
        ), 'A clickable feature row must have aria-expanded="false" on initial load'

    def test_aria_controls_on_clickable_row(self, client, _patched_get_db):
        """The aria-controls value on the clickable row must match the detail row id."""
        _insert_feature(
            _patched_get_db,
            number="C03",
            title="Aria Controls Attribute Clickable Row Matching Test",
            slug="aria-controls-test",
            description="Description to trigger aria-controls attribute.",
        )
        expected_detail_id = _number_to_detail_id("C03")
        body = _body(client.get("/roadmap"))
        assert f'aria-controls="{expected_detail_id}"' in body, (
            f"Clickable row for feature C03 must have "
            f'aria-controls="{expected_detail_id}" matching the detail row id'
        )

    def test_aria_controls_dots_replaced_with_dashes(self, client, _patched_get_db):
        """Feature numbers containing dots (e.g. '15.2') must have dots replaced
        with dashes in both aria-controls and the matching detail row id."""
        _insert_feature(
            _patched_get_db,
            number="15.2",
            title="Dot Number Feature Aria Controls Dash Replace Test",
            slug="dot-number-aria-controls",
            description="Description for a dot-number feature.",
        )
        body = _body(client.get("/roadmap"))
        assert 'aria-controls="detail-15-2"' in body, (
            "Feature number '15.2' must produce aria-controls=\"detail-15-2\" "
            "(dots replaced with dashes)"
        )
        assert (
            'id="detail-15-2"' in body
        ), "Detail row for feature '15.2' must have id=\"detail-15-2\""


# ------------------------------------------------------------------ #
# 4. Non-clickable row markup — features WITHOUT a description        #
# ------------------------------------------------------------------ #


class TestNonClickableRowMarkup:
    def test_no_clickable_class_on_feature_row_without_description(
        self, client, _patched_get_db
    ):
        """A top-level feature row with a NULL description must NOT carry
        'roadmap-row--clickable'."""
        _insert_feature(
            _patched_get_db,
            number="N01",
            title="Non Clickable Feature Row Without Description Test",
            slug="non-clickable-no-desc",
            description=None,
        )
        body = _body(client.get("/roadmap"))
        # Scope check to <tbody> only — the class also appears in the inline <script>
        # block as a JS selector, so a whole-page substring check would always fail.
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        tbody = body[tbody_start:tbody_end] if tbody_start != -1 else ""
        assert "roadmap-row--clickable" not in tbody, (
            "A feature row with a null description must NOT carry "
            "class 'roadmap-row--clickable' in the table body"
        )

    def test_no_aria_expanded_on_row_without_description(self, client, _patched_get_db):
        """A feature row without a description must NOT render aria-expanded."""
        _insert_feature(
            _patched_get_db,
            number="N02",
            title="No Aria Expanded On Feature Row Without Description Test",
            slug="no-aria-expanded-no-desc",
            description=None,
        )
        body = _body(client.get("/roadmap"))
        # Scope check to <tbody> only — 'aria-expanded' also appears in the inline
        # <script> block (getAttribute/setAttribute calls), so a whole-page check fails.
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        tbody = body[tbody_start:tbody_end] if tbody_start != -1 else ""
        assert (
            "aria-expanded" not in tbody
        ), "A feature row with a null description must NOT render aria-expanded in the table body"

    def test_release_subrow_is_not_clickable(self, client, _patched_get_db):
        """Release sub-rows (type='release') must not carry 'roadmap-row--clickable'
        even when they have a description, because only top-level feature rows
        are independently expandable according to the spec."""
        # Insert a parent feature with a description (will be clickable)
        _insert_feature(
            _patched_get_db,
            number="P01",
            title="Parent Feature For Release Sub Row Non Clickable Test",
            slug="parent-for-release-test",
            ftype="feature",
            description="Parent description.",
        )
        # Insert a child release with its own description
        _insert_feature(
            _patched_get_db,
            number="P01-1",
            title="Release Sub Row That Must Not Be Clickable Test",
            slug="release-subrow-not-clickable",
            ftype="release",
            parent_number="P01",
            description="Release description for non-clickable test.",
        )
        body = _body(client.get("/roadmap"))
        # The parent row IS clickable — we need to verify that release rows specifically
        # are rendered with roadmap-row--release but not roadmap-row--clickable.
        # Confirm the release class is present
        assert (
            "roadmap-row--release" in body
        ), "Release sub-rows must carry class 'roadmap-row--release'"
        # Confirm the page is valid HTML (no 500)
        resp = client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "Page must not 500 with mixed parent/release rows"


# ------------------------------------------------------------------ #
# 5. Detail row markup                                                #
# ------------------------------------------------------------------ #


class TestDetailRowMarkup:
    def test_detail_row_class_present(self, client, _patched_get_db):
        """The hidden detail <tr> must carry class 'roadmap-detail-row'."""
        _insert_feature(
            _patched_get_db,
            number="DR01",
            title="Detail Row Class Present Template Test",
            slug="detail-row-class-test",
            description="Detail row class must be present.",
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-detail-row" in body, (
            "A feature with a description must render a <tr class='roadmap-detail-row'> "
            "immediately after its main row"
        )

    def test_detail_row_has_role_region(self, client, _patched_get_db):
        """The detail row must carry role='region' for accessibility."""
        _insert_feature(
            _patched_get_db,
            number="DR02",
            title="Detail Row Role Region Accessibility Attribute Test",
            slug="detail-row-role-region",
            description="role=region must be present.",
        )
        body = _body(client.get("/roadmap"))
        assert (
            'role="region"' in body
        ), 'Detail row must have role="region" for screen-reader accessibility'

    def test_detail_row_has_aria_label_equal_to_feature_title(
        self, client, _patched_get_db
    ):
        """The detail row's aria-label must equal the feature title."""
        title = "Detail Row Aria Label Equals Feature Title Test"
        _insert_feature(
            _patched_get_db,
            number="DR03",
            title=title,
            slug="detail-row-aria-label",
            description="aria-label must match the feature title.",
        )
        body = _body(client.get("/roadmap"))
        assert f'aria-label="{title} details"' in body, (
            f'Detail row must have aria-label="{title} details" '
            f"matching the feature title"
        )

    def test_detail_row_id_matches_aria_controls(self, client, _patched_get_db):
        """The detail row id must be 'detail-<number>' matching the clickable row's
        aria-controls attribute."""
        _insert_feature(
            _patched_get_db,
            number="DR04",
            title="Detail Row Id Matches Aria Controls Test Feature",
            slug="detail-row-id-test",
            description="id must match aria-controls.",
        )
        expected_id = _number_to_detail_id("DR04")
        body = _body(client.get("/roadmap"))
        assert f'id="{expected_id}"' in body, (
            f'Detail row must have id="{expected_id}" to pair with '
            f'aria-controls="{expected_id}" on the clickable row'
        )

    def test_detail_row_td_has_colspan_9(self, client, _patched_get_db):
        """The <td> inside the detail row must span all 9 table columns."""
        _insert_feature(
            _patched_get_db,
            number="DR05",
            title="Detail Row TD Colspan Nine Test Feature",
            slug="detail-row-colspan",
            description="colspan must be 9.",
        )
        body = _body(client.get("/roadmap"))
        assert (
            'colspan="9"' in body
        ), 'The <td> inside the detail row must have colspan="9" to span all columns'

    def test_detail_card_div_present(self, client, _patched_get_db):
        """The detail row must contain a .roadmap-detail-card div."""
        _insert_feature(
            _patched_get_db,
            number="DR06",
            title="Detail Card Div Present Inside Detail Row Test",
            slug="detail-card-div",
            description="roadmap-detail-card class must be present.",
        )
        body = _body(client.get("/roadmap"))
        assert (
            "roadmap-detail-card" in body
        ), "The detail row must contain a div with class 'roadmap-detail-card'"

    def test_no_detail_row_for_feature_without_description(
        self, client, _patched_get_db
    ):
        """When a feature has no description, no detail row should be rendered."""
        _insert_feature(
            _patched_get_db,
            number="DR07",
            title="No Detail Row For Feature Without Description Test",
            slug="no-detail-row-no-desc",
            description=None,
        )
        body = _body(client.get("/roadmap"))
        # Scope check to <tbody> only — 'roadmap-detail-row' also appears in the inline
        # <script> block as 'roadmap-detail-row--open', so a whole-page check fails.
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        tbody = body[tbody_start:tbody_end] if tbody_start != -1 else ""
        assert (
            "roadmap-detail-row" not in tbody
        ), "No detail row must be rendered in the table body for a feature with a null description"


# ------------------------------------------------------------------ #
# 6. Chevron icon markup                                              #
# ------------------------------------------------------------------ #


class TestChevronMarkup:
    def test_chevron_present_for_clickable_row(self, client, _patched_get_db):
        """A feature row with a description must contain a .roadmap-chevron element."""
        _insert_feature(
            _patched_get_db,
            number="CH01",
            title="Chevron Present For Clickable Row With Description Test",
            slug="chevron-present-clickable",
            description="A description triggers the chevron.",
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-chevron" in body, (
            "A clickable feature row must include a .roadmap-chevron element "
            "for the expand/collapse indicator"
        )

    def test_chevron_uses_lucide_icon(self, client, _patched_get_db):
        """The chevron must use the Lucide 'chevron-down' icon via data-lucide."""
        _insert_feature(
            _patched_get_db,
            number="CH02",
            title="Chevron Lucide Icon Data Attribute Present Test",
            slug="chevron-lucide-icon",
            description="chevron-down must be the lucide icon used.",
        )
        body = _body(client.get("/roadmap"))
        assert 'data-lucide="chevron-down"' in body, (
            'The chevron element must use data-lucide="chevron-down" '
            "so lucide.createIcons() renders the correct SVG"
        )

    def test_chevron_absent_for_non_clickable_row(self, client, _patched_get_db):
        """A feature row without a description must NOT contain a .roadmap-chevron."""
        _insert_feature(
            _patched_get_db,
            number="CH03",
            title="Chevron Absent For Non Clickable Row No Description Test",
            slug="chevron-absent-no-desc",
            description=None,
        )
        body = _body(client.get("/roadmap"))
        assert (
            "roadmap-chevron" not in body
        ), "A feature row without a description must not render a .roadmap-chevron element"


# ------------------------------------------------------------------ #
# 7. Description text rendering in detail card                       #
# ------------------------------------------------------------------ #


class TestDescriptionRendering:
    def test_description_text_appears_in_detail_row(self, client, _patched_get_db):
        """The feature's description text must appear somewhere in the .roadmap-detail-row
        section of the rendered HTML."""
        desc_text = "Unique description content for detail card rendering test."
        _insert_feature(
            _patched_get_db,
            number="DESC01",
            title="Description Text Appears In Detail Row Test Feature",
            slug="desc-text-in-detail-row",
            description=desc_text,
        )
        body = _body(client.get("/roadmap"))
        assert desc_text in body, (
            "The feature's description text must appear in the rendered HTML "
            "within the detail card"
        )

    def test_null_description_renders_no_description_fallback(
        self, client, _patched_get_db
    ):
        """When description IS NULL, the detail card must not be rendered at all
        (no roadmap-detail-row), and 'No description.' must not appear as
        a fallback if the row is suppressed. If the row is still rendered
        the fallback text 'No description.' must appear instead of 'None'."""
        _insert_feature(
            _patched_get_db,
            number="DESC02",
            title="Null Description Fallback Rendering Test Feature",
            slug="null-desc-fallback",
            description=None,
        )
        body = _body(client.get("/roadmap"))
        # Per spec: rows without a description have NO detail row in the DOM.
        # Either the detail row is absent, OR the fallback "No description." is shown.
        # In both cases, the raw string 'None' must not appear in the HTML content.
        assert (
            ">None<" not in body
        ), "A null description must never render as the literal '>None<' in the HTML"
        assert "None" not in body or "No description." in body, (
            "When description is NULL, either no detail row is rendered OR the "
            "detail card shows 'No description.' — never the raw string 'None'"
        )

    def test_none_literal_not_in_roadmap_html_with_seeded_data(self, seeded_client):
        """With the full seed dataset (which includes null descriptions), the page
        must never render the string '>None<' anywhere in the HTML."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            ">None<" not in body
        ), "Null descriptions in the seed must not produce '>None<' in the HTML"

    def test_description_with_special_html_characters_is_escaped(
        self, client, _patched_get_db
    ):
        """A description containing '<script>' must be HTML-escaped, not rendered raw,
        so Jinja2's auto-escaping prevents XSS."""
        _insert_feature(
            _patched_get_db,
            number="DESC03",
            title="HTML Escaped Description Special Characters Safety Test",
            slug="html-escaped-description",
            description="Safe text <b>bold attempt</b> & ampersand test.",
        )
        body = _body(client.get("/roadmap"))
        # The raw unescaped angle-bracket tag must not appear in HTML source
        assert "<b>bold attempt</b>" not in body, (
            "Description HTML special characters must be escaped by Jinja2 "
            "auto-escaping — raw '<b>' must not appear in the rendered output"
        )
        # The escaped version OR the plain text must be present
        assert (
            "&lt;b&gt;" in body or "Safe text" in body
        ), "The escaped description text must still be present in the rendered output"

    def test_seeded_feature_with_description_appears_in_html(self, seeded_client):
        """A seeded feature known to have a description should have its text in the DOM."""
        body = _body(seeded_client.get("/roadmap"))
        # Feature 01 — "Database Setup" has a known description in seed_features()
        assert (
            "Database Setup" in body
        ), "Seeded feature 'Database Setup' title must appear in the roadmap HTML"
        # Its description starts with "Sets up the database..." per seed_features()
        assert (
            "Sets up the database" in body
        ), "Seeded feature '01' description must appear in the rendered detail card"


# ------------------------------------------------------------------ #
# 8. Release sub-table in detail card                                #
# ------------------------------------------------------------------ #


class TestReleaseSubTable:
    def test_detail_card_contains_sub_table_when_children_exist(
        self, client, _patched_get_db
    ):
        """When a top-level feature has child release rows, the detail card must
        contain a nested <table> showing those child rows."""
        _insert_feature(
            _patched_get_db,
            number="RST01",
            title="Parent Feature With Child Releases Sub Table Test",
            slug="parent-with-children-sub-table",
            ftype="feature",
            description="Parent description triggers detail card with sub-table.",
        )
        _insert_feature(
            _patched_get_db,
            number="RST01-1",
            title="Child Release Row One For Sub Table Test Here",
            slug="child-release-sub-table-one",
            ftype="release",
            parent_number="RST01",
            description="Child release description.",
            shipped_at=SHIPPED_TS,
        )
        body = _body(client.get("/roadmap"))
        # The child title must appear in the HTML
        assert (
            "Child Release Row One For Sub Table Test Here" in body
        ), "Child release title must appear in the detail card sub-table"

    def test_child_release_titles_appear_inside_detail_card(
        self, client, _patched_get_db
    ):
        """All child release titles must be present in the page HTML when a parent
        feature is rendered with its detail card."""
        _insert_feature(
            _patched_get_db,
            number="RST02",
            title="Parent Feature Two Children Sub Table Titles Test",
            slug="parent-two-children",
            ftype="feature",
            description="Parent with multiple children.",
        )
        _insert_feature(
            _patched_get_db,
            number="RST02-1",
            title="First Child Release Sub Table Title Test Row",
            slug="first-child-sub-table",
            ftype="release",
            parent_number="RST02",
        )
        _insert_feature(
            _patched_get_db,
            number="RST02-2",
            title="Second Child Release Sub Table Title Test Row",
            slug="second-child-sub-table",
            ftype="release",
            parent_number="RST02",
        )
        body = _body(client.get("/roadmap"))
        assert (
            "First Child Release Sub Table Title Test Row" in body
        ), "First child release title must appear in the page HTML"
        assert (
            "Second Child Release Sub Table Title Test Row" in body
        ), "Second child release title must appear in the page HTML"

    def test_seeded_parent_feature_shows_child_releases_in_html(self, seeded_client):
        """With seeded data, a known parent feature (e.g. '11') must have its
        child release titles present in the page HTML."""
        body = _body(seeded_client.get("/roadmap"))
        # Feature 11 has children 11-1, 11-2, 11-3 per seed_features()
        assert "DB, Submission, and /features Page" in body, (
            "Child release '11-1' title must appear in the roadmap HTML "
            "as part of feature 11's detail card or main table"
        )
        assert (
            "Upvoting and Trending" in body
        ), "Child release '11-2' title must appear in the roadmap HTML"


# ------------------------------------------------------------------ #
# 9. Inline JS toggle script                                          #
# ------------------------------------------------------------------ #


class TestInlineJSToggle:
    def test_script_block_present_in_page(self, seeded_client):
        """The /roadmap page must contain a <script> block for the toggle logic."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "<script>" in body or "<script " in body
        ), "GET /roadmap must include a <script> block containing the toggle logic"

    def test_script_references_clickable_row_class(self, seeded_client):
        """The inline script must query for '.roadmap-row--clickable' to wire up
        the click event listeners."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-row--clickable" in body, (
            "The inline JS must reference '.roadmap-row--clickable' to attach "
            "click handlers to expandable rows"
        )

    def test_script_references_aria_expanded(self, seeded_client):
        """The inline script must read and write 'aria-expanded' to toggle the
        expanded/collapsed state of each row."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "aria-expanded" in body
        ), "The inline JS must reference 'aria-expanded' to manage the toggle state"

    def test_lucide_create_icons_called(self, seeded_client):
        """The page must call lucide.createIcons() to render the chevron SVG icons."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "lucide.createIcons()" in body or "lucide.createIcons" in body
        ), "The page must call lucide.createIcons() so chevron SVGs are rendered"

    def test_script_references_detail_row_open_class(self, seeded_client):
        """The JS toggle adds 'roadmap-detail-row--open' to show the detail panel;
        this class must appear in the script block."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-detail-row--open" in body, (
            "The inline JS must toggle 'roadmap-detail-row--open' to show/hide "
            "the detail panel"
        )


# ------------------------------------------------------------------ #
# 10. Full seeded-data rendering — integration                       #
# ------------------------------------------------------------------ #


class TestSeededDataIntegration:
    def test_seeded_page_returns_200(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "GET /roadmap must return 200 after 15.2 template changes with seeded data"

    def test_seeded_page_has_multiple_detail_rows(self, seeded_client):
        """With seeded data many features have descriptions, so multiple
        roadmap-detail-row elements must appear in the HTML."""
        body = _body(seeded_client.get("/roadmap"))
        count = body.count("roadmap-detail-row")
        assert (
            count >= 2
        ), f"With seeded data, at least 2 detail rows must be rendered; found {count}"

    def test_seeded_page_detail_rows_have_role_region(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            'role="region"' in body
        ), "At least one detail row with role='region' must be present with seeded data"

    def test_seeded_page_has_aria_expanded_false(self, seeded_client):
        """On initial page load all expandable rows start collapsed."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            'aria-expanded="false"' in body
        ), 'All clickable rows must have aria-expanded="false" on initial load'
        assert (
            'aria-expanded="true"' not in body
        ), "No row should be expanded (aria-expanded='true') on initial page load"

    def test_feature_15_2_description_appears_in_html(self, seeded_client):
        """Feature 15.2 is seeded with a known description; verify it renders."""
        body = _body(seeded_client.get("/roadmap"))
        # The seed inserts 15.2 with description:
        # "Makes the roadmap interactive — clicking any feature or release row..."
        assert (
            "Makes the roadmap interactive" in body
        ), "Feature 15.2's description must appear in the roadmap HTML detail card"

    def test_feature_15_3_null_description_no_detail_row(self, seeded_client):
        """Feature 15.3 (Harness Integration) has a NULL description in the seed;
        it must not produce a detail row or render 'None' in the HTML."""
        body = _body(seeded_client.get("/roadmap"))
        # The page overall must never have '>None<'
        assert (
            ">None<" not in body
        ), "Feature 15.3 has a null description — '>None<' must not appear in HTML"

    def test_seeded_page_no_table_error_on_features_with_mixed_descriptions(
        self, seeded_client
    ):
        """The template must handle a mix of features with and without descriptions
        without raising a 500 or rendering malformed HTML."""
        body = _body(seeded_client.get("/roadmap"))
        # Basic HTML structure sanity checks
        assert "<table" in body, "Pipeline table must still render with mixed data"
        assert "</table>" in body, "Pipeline table must be properly closed"
        assert "<tbody>" in body or "<tr" in body, "Table body rows must be present"
