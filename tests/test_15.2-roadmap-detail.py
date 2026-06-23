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

Template — parent row markup (15.2 as modified by 15.7):
 4. Parent feature rows (features with children) carry class 'roadmap-parent-row'
 5. Parent feature rows carry aria-expanded="false" initially
 6. Parent feature rows carry aria-controls pointing to the parent container id
 7. Top-level feature rows without children do NOT carry 'roadmap-parent-row'
 8. Release sub-rows carry data-parent attribute matching their parent number

Template — group row markup (15.7):
 9. A group row with class 'roadmap-group-row' and data-group="foundational" exists
10. Features 01–10 carry data-parent-group="foundational"
11. Features 11+ do NOT carry data-parent-group

Template — chevron:
12. A .roadmap-chevron element is present inside parent rows
13. Parent rows contain a data-lucide="chevron-down" attribute
14. Non-parent feature rows do NOT contain a .roadmap-chevron

Template — JS toggle (15.7):
15. The page contains an inline <script> block with toggle logic
16. The script references '.roadmap-parent-row'
17. The script references '.roadmap-group-row'
18. The script references 'aria-expanded'
19. lucide.createIcons() is still called

Public access (regression):
20. GET /roadmap returns 200 for an unauthenticated request (regression from 15.1)
21. GET /roadmap does not redirect to /login (regression from 15.1)

Detail row removal (15.7):
22. No 'roadmap-detail-row' elements exist in the rendered HTML
23. No 'roadmap-detail-card' elements exist in the rendered HTML
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
# 3. Parent row markup — features WITH children                      #
# ------------------------------------------------------------------ #


class TestParentRowMarkup:
    def test_parent_row_class_on_feature_with_children(
        self, client, _patched_get_db
    ):
        """A top-level feature row with child releases must carry
        class 'roadmap-parent-row'."""
        _insert_feature(
            _patched_get_db,
            number="C01",
            title="Parent Feature With Children Test",
            slug="parent-with-children",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="C01-1",
            title="Child Release For Parent Row Test",
            slug="child-release-parent-row",
            ftype="release",
            parent_number="C01",
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-parent-row" in body, (
            "A feature row with child releases must carry "
            "class 'roadmap-parent-row'"
        )

    def test_aria_expanded_false_on_parent_row(self, client, _patched_get_db):
        """A parent row must have aria-expanded='false' in its initial state."""
        _insert_feature(
            _patched_get_db,
            number="C02",
            title="Aria Expanded False Parent Row Test Feature",
            slug="aria-expanded-false-parent",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="C02-1",
            title="Child For Aria Expanded Parent Test",
            slug="child-aria-expanded-parent",
            ftype="release",
            parent_number="C02",
        )
        body = _body(client.get("/roadmap"))
        assert (
            'aria-expanded="false"' in body
        ), 'A parent feature row must have aria-expanded="false" on initial load'

    def test_aria_controls_on_parent_row(self, client, _patched_get_db):
        """The aria-controls value on the parent row must reference its parent id."""
        _insert_feature(
            _patched_get_db,
            number="C03",
            title="Aria Controls Attribute Parent Row Test",
            slug="aria-controls-parent",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="C03-1",
            title="Child For Aria Controls Parent Test",
            slug="child-aria-controls-parent",
            ftype="release",
            parent_number="C03",
        )
        body = _body(client.get("/roadmap"))
        assert 'aria-controls="parent-C03"' in body, (
            "Parent row for feature C03 must have "
            'aria-controls="parent-C03"'
        )

    def test_aria_controls_dots_replaced_with_dashes(self, client, _patched_get_db):
        """Feature numbers containing dots (e.g. '15.2') must have dots replaced
        with dashes in aria-controls."""
        _insert_feature(
            _patched_get_db,
            number="15.2",
            title="Dot Number Feature Aria Controls Dash Replace Test",
            slug="dot-number-aria-controls",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="15.2-1",
            title="Child Of Dot Number Parent Test",
            slug="child-dot-number-parent",
            ftype="release",
            parent_number="15.2",
        )
        body = _body(client.get("/roadmap"))
        assert 'aria-controls="parent-15-2"' in body, (
            "Feature number '15.2' must produce aria-controls=\"parent-15-2\" "
            "(dots replaced with dashes)"
        )


# ------------------------------------------------------------------ #
# 4. Non-parent row markup — features WITHOUT children                #
# ------------------------------------------------------------------ #


class TestNonParentRowMarkup:
    def test_no_parent_row_class_on_feature_without_children(
        self, client, _patched_get_db
    ):
        """A top-level feature row with no children must NOT carry
        'roadmap-parent-row'."""
        _insert_feature(
            _patched_get_db,
            number="N01",
            title="Non Parent Feature Without Children Test",
            slug="non-parent-no-children",
            ftype="feature",
        )
        body = _body(client.get("/roadmap"))
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        tbody = body[tbody_start:tbody_end] if tbody_start != -1 else ""
        assert "roadmap-parent-row" not in tbody, (
            "A feature row with no children must NOT carry "
            "class 'roadmap-parent-row' in the table body"
        )

    def test_no_aria_expanded_on_row_without_children(self, client, _patched_get_db):
        """A feature row without children must NOT render aria-expanded."""
        _insert_feature(
            _patched_get_db,
            number="N02",
            title="No Aria Expanded On Feature Row Without Children Test",
            slug="no-aria-expanded-no-children",
            ftype="feature",
        )
        body = _body(client.get("/roadmap"))
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        tbody = body[tbody_start:tbody_end] if tbody_start != -1 else ""
        assert (
            "aria-expanded" not in tbody
        ), "A feature row with no children must NOT render aria-expanded in the table body"

    def test_release_subrow_has_data_parent(self, client, _patched_get_db):
        """Release sub-rows must carry data-parent attribute matching their parent."""
        _insert_feature(
            _patched_get_db,
            number="P01",
            title="Parent Feature For Release Data Parent Test",
            slug="parent-for-release-data-parent",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="P01-1",
            title="Release Sub Row With Data Parent Test",
            slug="release-subrow-data-parent",
            ftype="release",
            parent_number="P01",
        )
        body = _body(client.get("/roadmap"))
        assert (
            "roadmap-row--release" in body
        ), "Release sub-rows must carry class 'roadmap-row--release'"
        assert 'data-parent="P01"' in body, (
            "Release sub-rows must carry data-parent='P01' "
            "matching their parent feature number"
        )


# ------------------------------------------------------------------ #
# 5. Group row markup (15.7)                                          #
# ------------------------------------------------------------------ #


class TestGroupRowMarkup:
    def test_group_row_class_present(self, seeded_client):
        """A group row with class 'roadmap-group-row' must exist."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-row" in body, (
            "A group row with class 'roadmap-group-row' must be present"
        )

    def test_group_row_has_data_group_foundational(self, seeded_client):
        """The group row must carry data-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        assert 'data-group="foundational"' in body, (
            "The group row must carry data-group='foundational'"
        )

    def test_group_row_has_aria_expanded_false(self, seeded_client):
        """The group row must have aria-expanded='false' (collapsed by default)."""
        body = _body(seeded_client.get("/roadmap"))
        # The group row itself has aria-expanded="false"
        assert "roadmap-group-row" in body
        # Find the group row and check its aria-expanded
        idx = body.find('class="roadmap-group-row"')
        assert idx != -1, "Group row class must exist"
        # Look for aria-expanded in the vicinity (before the class, on the same tag)
        tag_start = body.rfind("<tr", 0, idx)
        tag_end = body.find(">", idx)
        group_tag = body[tag_start:tag_end + 1]
        assert 'aria-expanded="false"' in group_tag, (
            "The group row must have aria-expanded='false' (collapsed by default)"
        )

    def test_group_row_has_chevron(self, seeded_client):
        """The group row must contain a chevron icon."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-chevron" in body, (
            "The group row must contain a .roadmap-group-chevron element"
        )

    def test_group_row_has_label(self, seeded_client):
        """The group row must contain the 'Foundational Features' label."""
        body = _body(seeded_client.get("/roadmap"))
        assert "Foundational Features" in body, (
            "The group row must contain the 'Foundational Features' label"
        )

    def test_group_row_has_count_badge(self, seeded_client):
        """The group row must contain a count badge."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-count" in body, (
            "The group row must contain a .roadmap-group-count badge"
        )

    def test_features_01_to_10_have_data_parent_group(self, seeded_client):
        """Features 01–10 must carry data-parent-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        # Features 01-10 should have data-parent-group="foundational"
        for num in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
            assert f'data-parent-group="foundational"' in body, (
                f"Feature {num} must carry data-parent-group='foundational'"
            )

    def test_features_11_plus_no_data_parent_group(self, seeded_client):
        """Features 11+ must NOT carry data-parent-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        # Scope to <tbody> only — the attribute also appears in the inline <script>
        # block (JS selector string), so a whole-page count would be 11 not 10.
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        tbody = body[tbody_start:tbody_end] if tbody_start != -1 else ""
        count = tbody.count('data-parent-group="foundational"')
        assert count == 10, (
            f"Exactly 10 rows should have data-parent-group='foundational' (features 01-10), "
            f"but found {count}"
        )


# ------------------------------------------------------------------ #
# 6. Chevron icon markup                                              #
# ------------------------------------------------------------------ #


class TestChevronMarkup:
    def test_chevron_present_for_parent_row(self, client, _patched_get_db):
        """A feature row with children must contain a .roadmap-chevron element."""
        _insert_feature(
            _patched_get_db,
            number="CH01",
            title="Chevron Present For Parent Row Test",
            slug="chevron-present-parent",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="CH01-1",
            title="Child For Chevron Parent Test",
            slug="child-chevron-parent",
            ftype="release",
            parent_number="CH01",
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-chevron" in body, (
            "A parent feature row must include a .roadmap-chevron element "
            "for the expand/collapse indicator"
        )

    def test_chevron_uses_lucide_icon(self, client, _patched_get_db):
        """The chevron must use the Lucide 'chevron-down' icon via data-lucide."""
        _insert_feature(
            _patched_get_db,
            number="CH02",
            title="Chevron Lucide Icon Data Attribute Present Test",
            slug="chevron-lucide-icon",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="CH02-1",
            title="Child For Chevron Lucide Test",
            slug="child-chevron-lucide",
            ftype="release",
            parent_number="CH02",
        )
        body = _body(client.get("/roadmap"))
        assert 'data-lucide="chevron-down"' in body, (
            'The chevron element must use data-lucide="chevron-down" '
            "so lucide.createIcons() renders the correct SVG"
        )

    def test_chevron_absent_for_non_parent_row(self, client, _patched_get_db):
        """A feature row without children must NOT contain a .roadmap-chevron."""
        _insert_feature(
            _patched_get_db,
            number="CH03",
            title="Chevron Absent For Non Parent Row Test",
            slug="chevron-absent-no-children",
            ftype="feature",
        )
        body = _body(client.get("/roadmap"))
        assert (
            "roadmap-chevron" not in body
        ), "A feature row without children must not render a .roadmap-chevron element"


# ------------------------------------------------------------------ #
# 7. Detail row removal (15.7)                                        #
# ------------------------------------------------------------------ #


class TestDetailRowRemoved:
    def test_no_detail_row_in_html(self, seeded_client):
        """No 'roadmap-detail-row' elements must exist in the rendered HTML."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-detail-row" not in body, (
            "Detail rows must be completely removed from the template"
        )

    def test_no_detail_card_in_html(self, seeded_client):
        """No 'roadmap-detail-card' elements must exist in the rendered HTML."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-detail-card" not in body, (
            "Detail cards must be completely removed from the template"
        )


# ------------------------------------------------------------------ #
# 8. Inline JS toggle script                                          #
# ------------------------------------------------------------------ #


class TestInlineJSToggle:
    def test_script_block_present_in_page(self, seeded_client):
        """The /roadmap page must contain a <script> block for the toggle logic."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "<script>" in body or "<script " in body
        ), "GET /roadmap must include a <script> block containing the toggle logic"

    def test_script_references_parent_row_class(self, seeded_client):
        """The inline script must query for '.roadmap-parent-row' to wire up
        the click event listeners."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-parent-row" in body, (
            "The inline JS must reference '.roadmap-parent-row' to attach "
            "click handlers to parent rows"
        )

    def test_script_references_group_row_class(self, seeded_client):
        """The inline script must query for '.roadmap-group-row' to wire up
        the group toggle."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-row" in body, (
            "The inline JS must reference '.roadmap-group-row' to attach "
            "click handlers to the group row"
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


# ------------------------------------------------------------------ #
# 9. Full seeded-data rendering — integration                        #
# ------------------------------------------------------------------ #


class TestSeededDataIntegration:
    def test_seeded_page_returns_200(self, seeded_client):
        resp = seeded_client.get("/roadmap")
        assert (
            resp.status_code == 200
        ), "GET /roadmap must return 200 with seeded data"

    def test_seeded_page_has_group_row(self, seeded_client):
        """With seeded data, a group row must be present."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-row" in body, (
            "A group row must be present with seeded data"
        )

    def test_seeded_page_has_parent_rows(self, seeded_client):
        """With seeded data, parent features (e.g. 11, 12, 15) must have
        roadmap-parent-row class."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-parent-row" in body, (
            "Parent feature rows must carry 'roadmap-parent-row' with seeded data"
        )

    def test_seeded_page_has_aria_expanded_false(self, seeded_client):
        """On initial page load all expandable rows start collapsed."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            'aria-expanded="false"' in body
        ), 'All parent rows must have aria-expanded="false" on initial load'
        assert (
            'aria-expanded="true"' not in body
        ), "No row should be expanded (aria-expanded='true') on initial page load"

    def test_seeded_page_no_table_error(self, seeded_client):
        """The template must render valid HTML with seeded data."""
        body = _body(seeded_client.get("/roadmap"))
        assert "<table" in body, "Pipeline table must still render with seeded data"
        assert "</table>" in body, "Pipeline table must be properly closed"
        assert "<tbody>" in body or "<tr" in body, "Table body rows must be present"

    def test_seeded_page_no_detail_rows(self, seeded_client):
        """With seeded data, no detail rows should exist."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-detail-row" not in body, (
            "No detail rows must exist with seeded data after 15.7 changes"
        )
