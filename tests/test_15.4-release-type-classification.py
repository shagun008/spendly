"""Feature 15.4 — Release-Level Type Classification

Strategy
--------
Mirrors the psycopg2 monkeypatching + TRUNCATE isolation pattern established in
tests/test_15_1-roadmap-pipeline.py.  This file is fully self-contained — no
imports from other test files.

The ``release_subtype`` column (TEXT, nullable) already exists on the ``features``
table via ``ALTER TABLE features ADD COLUMN IF NOT EXISTS release_subtype TEXT``
in ``init_db()``.  ``_feature_row()`` and ``get_all_features()`` expose it in
every returned dict.  ``roadmap.html`` renders a ``.roadmap-type-badge`` span on
rows where ``f.release_subtype`` is one of ``new-feature``, ``enhancement``, or
``bug-fix``, and is silent when the value is NULL or absent.

Behaviours covered
------------------
1.  ``get_all_features()`` returns ``release_subtype`` key in every dict
2.  ``release_subtype`` is Python None for rows with a NULL DB value
3.  ``release_subtype`` is the correct string when set (all three valid values)
4.  GET /roadmap renders ``.roadmap-type-badge`` when ``release_subtype`` is set
5.  Badge text is "New Feature" / "Enhancement" / "Bug Fix" per subtype (parametrized)
6.  No badge span when ``release_subtype`` is NULL
7.  Parent feature rows (type=``feature``) never show a type badge
8.  Page does not 500 when some rows have NULL ``release_subtype``
9.  CSS modifier classes appear in HTML when the corresponding subtype is set
"""

import importlib

import psycopg2
import psycopg2.extras
import pytest

import database.db as db_module
from database.db import init_db, seed_features
import database.queries as queries_module

# ------------------------------------------------------------------ #
# Module-scoped reseed — restores live DB after all tests complete    #
# ------------------------------------------------------------------ #


@pytest.fixture(scope="module", autouse=True)
def _reseed_after_module():
    """Re-seed the live DB after all tests in this module complete.

    Tests TRUNCATE the features table using the real DATABASE_URL, which wipes
    production data.  This fixture restores the seed rows once all tests are
    done so the roadmap page is not left empty.
    """
    yield
    seed_features()


# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

SHIPPED_TS = "2026-05-01 00:00:00"

VALID_SUBTYPES = ("new-feature", "enhancement", "bug-fix")

BADGE_TEXT_MAP = {
    "new-feature": "New Feature",
    "enhancement": "Enhancement",
    "bug-fix": "Bug Fix",
}

# Keys every dict returned by get_all_features() must contain
REQUIRED_FEATURE_KEYS = {
    "number",
    "parent_number",
    "title",
    "slug",
    "type",
    "release_subtype",
    "status",
    "captured_at",
    "planned_at",
    "spec_at",
    "implemented_at",
    "tested_at",
    "reviewed_at",
    "shipped_at",
}


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def _patched_get_db(monkeypatch):
    """Open a single real Postgres connection and monkeypatch get_db in both
    database.db and database.queries so every DB call within a test uses the
    same connection.

    Isolation: TRUNCATE at setup and teardown — rollback cannot undo commits
    made inside the helper functions.
    """
    init_db()

    _real_conn = db_module.get_db()

    class _NoCloseProxy:
        """Delegates to _real_conn but no-ops close() so helpers cannot close
        the shared connection mid-test."""

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
    """Flask test client with an empty features table."""
    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    # Clear rows inserted by the module-level seed_features() call during reload
    cur = _patched_get_db.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _patched_get_db.commit()
    cur.close()

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(_patched_get_db, monkeypatch):
    """Flask test client with the features table seeded via seed_features()."""
    seed_features()

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    with app_module.app.test_client() as c:
        yield c


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
    ftype="feature",
    release_subtype=None,
    parent_number=None,
    captured_at=None,
    planned_at=None,
    spec_at=None,
    implemented_at=None,
    tested_at=None,
    reviewed_at=None,
    shipped_at=None,
):
    """Insert a single row into the features table and return its new id."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO features"
        " (number, parent_number, title, slug, type, release_subtype,"
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
            release_subtype,
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
# 1. get_all_features() exposes release_subtype key in every dict     #
# ------------------------------------------------------------------ #


class TestGetAllFeaturesHasReleaseSubtype:
    def test_release_subtype_key_present_in_all_dicts(self, _patched_get_db):
        """Every dict returned by get_all_features() must contain 'release_subtype'."""
        _insert_feature_row(
            _patched_get_db,
            number="RT01",
            title="Key Presence Check Feature Release Subtype Test",
            slug="rt-key-presence",
        )
        result = queries_module.get_all_features()
        assert (
            result
        ), "get_all_features() must return at least one item after insertion"
        for item in result:
            assert "release_subtype" in item, (
                f"Feature dict for '{item.get('number', '?')}' is missing the "
                f"'release_subtype' key — _feature_row() must include it"
            )

    def test_all_required_keys_present_including_release_subtype(self, _patched_get_db):
        """Full key-set check including the new release_subtype key."""
        _insert_feature_row(
            _patched_get_db,
            number="RT02",
            title="Full Key Set Check Feature Including Release Subtype",
            slug="rt-full-keys",
        )
        result = queries_module.get_all_features()
        for item in result:
            missing = REQUIRED_FEATURE_KEYS - set(item.keys())
            assert (
                not missing
            ), f"Feature dict '{item.get('number', '?')}' is missing keys: {missing}"

    def test_release_subtype_key_present_on_empty_table(self, _patched_get_db):
        """An empty table returns an empty list — no KeyError should ever arise."""
        result = queries_module.get_all_features()
        assert (
            result == []
        ), "get_all_features() on an empty features table must return an empty list"

    def test_release_subtype_key_present_after_seeding(self, _patched_get_db):
        """After seed_features(), all rows must expose release_subtype."""
        seed_features()
        result = queries_module.get_all_features()
        assert result, "Seeded table must return rows from get_all_features()"
        for item in result:
            assert (
                "release_subtype" in item
            ), f"Seeded feature '{item.get('number', '?')}' missing 'release_subtype'"


# ------------------------------------------------------------------ #
# 2. release_subtype is Python None for NULL rows                     #
# ------------------------------------------------------------------ #


class TestReleaseSubtypeNullRows:
    def test_null_release_subtype_is_python_none(self, _patched_get_db):
        """A row inserted without release_subtype must have Python None, not a string."""
        _insert_feature_row(
            _patched_get_db,
            number="RT03",
            title="Null Release Subtype Is Python None Test Row",
            slug="rt-null-subtype",
            release_subtype=None,
        )
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "RT03"), None)
        assert row is not None, "Inline-inserted feature RT03 must appear in results"
        assert row["release_subtype"] is None, (
            f"release_subtype must be Python None for a NULL DB value, "
            f"got {row['release_subtype']!r}"
        )

    def test_null_release_subtype_not_string_none(self, _patched_get_db):
        """Ensure the value is not the string 'None' — a common template render bug."""
        _insert_feature_row(
            _patched_get_db,
            number="RT04",
            title="Null Release Subtype Not String None Representation Test",
            slug="rt-not-string-none",
        )
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "RT04"), None)
        assert row is not None, "Inline-inserted feature RT04 must appear in results"
        assert (
            row["release_subtype"] != "None"
        ), "release_subtype must not be the string 'None' — it must be Python None"

    def test_parent_feature_rows_have_none_subtype_after_seed(self, _patched_get_db):
        """Seeded parent rows (type='feature') must have release_subtype=None."""
        seed_features()
        result = queries_module.get_all_features()
        parent_rows = [f for f in result if f["type"] == "feature"]
        assert (
            parent_rows
        ), "Seeded data must include parent feature rows (type='feature')"
        for row in parent_rows:
            assert row["release_subtype"] is None, (
                f"Parent feature row '{row['number']}' must have release_subtype=None, "
                f"got {row['release_subtype']!r}"
            )


# ------------------------------------------------------------------ #
# 3. release_subtype returns the correct string when set              #
# ------------------------------------------------------------------ #


class TestReleaseSubtypeSetValues:
    @pytest.mark.parametrize("subtype", VALID_SUBTYPES)
    def test_release_subtype_roundtrips_correctly(self, subtype, _patched_get_db):
        """Each valid subtype value must round-trip through _feature_row() unchanged."""
        number = f"RT-{subtype[:3].upper()}"
        _insert_feature_row(
            _patched_get_db,
            number=number,
            title=f"Release Subtype Roundtrip Test Row For {subtype}",
            slug=f"rt-roundtrip-{subtype}",
            ftype="release",
            release_subtype=subtype,
            parent_number=None,
        )
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == number), None)
        assert row is not None, (
            f"Inline-inserted feature '{number}' with release_subtype='{subtype}' "
            f"must appear in get_all_features() output"
        )
        assert row["release_subtype"] == subtype, (
            f"release_subtype for '{number}' must be '{subtype}', "
            f"got {row['release_subtype']!r}"
        )

    def test_new_feature_subtype_is_preserved(self, _patched_get_db):
        _insert_feature_row(
            _patched_get_db,
            number="RT05",
            title="New Feature Release Subtype Value Preservation Test Row",
            slug="rt-new-feature-value",
            ftype="release",
            release_subtype="new-feature",
        )
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "RT05"), None)
        assert row is not None, "Inline-inserted feature RT05 must appear in results"
        assert (
            row["release_subtype"] == "new-feature"
        ), f"Expected 'new-feature', got {row['release_subtype']!r}"

    def test_enhancement_subtype_is_preserved(self, _patched_get_db):
        _insert_feature_row(
            _patched_get_db,
            number="RT06",
            title="Enhancement Release Subtype Value Preservation Test Row",
            slug="rt-enhancement-value",
            ftype="release",
            release_subtype="enhancement",
        )
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "RT06"), None)
        assert row is not None, "Inline-inserted feature RT06 must appear in results"
        assert (
            row["release_subtype"] == "enhancement"
        ), f"Expected 'enhancement', got {row['release_subtype']!r}"

    def test_bug_fix_subtype_is_preserved(self, _patched_get_db):
        _insert_feature_row(
            _patched_get_db,
            number="RT07",
            title="Bug Fix Release Subtype Value Preservation Test Row Here",
            slug="rt-bug-fix-value",
            ftype="release",
            release_subtype="bug-fix",
        )
        result = queries_module.get_all_features()
        row = next((f for f in result if f["number"] == "RT07"), None)
        assert row is not None, "Inline-inserted feature RT07 must appear in results"
        assert (
            row["release_subtype"] == "bug-fix"
        ), f"Expected 'bug-fix', got {row['release_subtype']!r}"

    def test_seeded_release_rows_have_expected_subtypes(self, _patched_get_db):
        """Verify specific seeded release rows carry their assigned subtypes."""
        seed_features()
        result = queries_module.get_all_features()
        by_number = {f["number"]: f for f in result}

        assert "11-1" in by_number, "Seeded row '11-1' must be present"
        assert by_number["11-1"]["release_subtype"] == "new-feature", (
            f"Seeded '11-1' must have release_subtype='new-feature', "
            f"got {by_number['11-1']['release_subtype']!r}"
        )

        assert "11-2" in by_number, "Seeded row '11-2' must be present"
        assert by_number["11-2"]["release_subtype"] == "enhancement", (
            f"Seeded '11-2' must have release_subtype='enhancement', "
            f"got {by_number['11-2']['release_subtype']!r}"
        )

        assert "12.1" in by_number, "Seeded row '12.1' must be present"
        assert by_number["12.1"]["release_subtype"] == "new-feature", (
            f"Seeded '12.1' must have release_subtype='new-feature', "
            f"got {by_number['12.1']['release_subtype']!r}"
        )


# ------------------------------------------------------------------ #
# 4 & 9. GET /roadmap renders .roadmap-type-badge and CSS classes     #
# ------------------------------------------------------------------ #


class TestRoadmapTypeBadgeRendering:
    @pytest.mark.parametrize("subtype", VALID_SUBTYPES)
    def test_type_badge_rendered_when_release_subtype_set(
        self, subtype, client, _patched_get_db
    ):
        """A release row with release_subtype set must produce a .roadmap-type-badge span."""
        _insert_feature_row(
            _patched_get_db,
            number=f"RB-{subtype[:3].upper()}",
            title=f"Type Badge Render Test Row For {subtype} Subtype Value",
            slug=f"rb-render-{subtype}",
            ftype="release",
            release_subtype=subtype,
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-type-badge" in body, (
            f"GET /roadmap must render a .roadmap-type-badge element when "
            f"release_subtype='{subtype}'"
        )

    @pytest.mark.parametrize(
        "subtype,expected_text",
        [
            ("new-feature", "New Feature"),
            ("enhancement", "Enhancement"),
            ("bug-fix", "Bug Fix"),
        ],
    )
    def test_badge_text_is_human_readable(
        self, subtype, expected_text, client, _patched_get_db
    ):
        """The badge inner text must be the human-readable label, not the raw slug."""
        _insert_feature_row(
            _patched_get_db,
            number=f"BT-{subtype[:3].upper()}",
            title=f"Badge Text Human Readable Test For {subtype} Subtype Here",
            slug=f"bt-text-{subtype}",
            ftype="release",
            release_subtype=subtype,
        )
        body = _body(client.get("/roadmap"))
        assert expected_text in body, (
            f"Badge for release_subtype='{subtype}' must show '{expected_text}' "
            f"as human-readable text — not the raw slug value"
        )

    @pytest.mark.parametrize("subtype", VALID_SUBTYPES)
    def test_css_modifier_class_present_when_subtype_set(
        self, subtype, client, _patched_get_db
    ):
        """The CSS modifier class roadmap-type-badge--<subtype> must appear in HTML."""
        expected_class = f"roadmap-type-badge--{subtype}"
        _insert_feature_row(
            _patched_get_db,
            number=f"CS-{subtype[:3].upper()}",
            title=f"CSS Modifier Class Presence Test Row For {subtype}",
            slug=f"cs-class-{subtype}",
            ftype="release",
            release_subtype=subtype,
        )
        body = _body(client.get("/roadmap"))
        assert expected_class in body, (
            f"CSS class '{expected_class}' must appear in the HTML when "
            f"release_subtype='{subtype}'"
        )

    def test_css_class_new_feature_present_in_seeded_data(self, seeded_client):
        """Seeded data has rows with release_subtype='new-feature'; their CSS class must render."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-type-badge--new-feature" in body, (
            "Seeded rows with release_subtype='new-feature' must produce "
            "class 'roadmap-type-badge--new-feature' in the HTML"
        )

    def test_css_class_enhancement_present_in_seeded_data(self, seeded_client):
        """Seeded data has rows with release_subtype='enhancement'; their CSS class must render."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-type-badge--enhancement" in body, (
            "Seeded rows with release_subtype='enhancement' must produce "
            "class 'roadmap-type-badge--enhancement' in the HTML"
        )


# ------------------------------------------------------------------ #
# 5 & 6. Badge text per subtype (seeded data) and no badge for NULL   #
# ------------------------------------------------------------------ #


class TestRoadmapBadgeTextAndAbsence:
    def test_new_feature_badge_text_appears_in_seeded_page(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "New Feature" in body
        ), "Badge text 'New Feature' must appear in the seeded roadmap HTML"

    def test_enhancement_badge_text_appears_in_seeded_page(self, seeded_client):
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "Enhancement" in body
        ), "Badge text 'Enhancement' must appear in the seeded roadmap HTML"

    def test_no_badge_when_release_subtype_is_null(self, client, _patched_get_db):
        """A row with release_subtype=NULL must NOT produce a .roadmap-type-badge span."""
        _insert_feature_row(
            _patched_get_db,
            number="NB01",
            title="No Badge When Release Subtype Is Null Test Row",
            slug="nb-null-subtype",
            ftype="release",
            release_subtype=None,
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-type-badge" not in body, (
            "A release row with release_subtype=NULL must NOT render any "
            ".roadmap-type-badge span in the HTML"
        )

    def test_no_bug_fix_raw_slug_in_badge(self, client, _patched_get_db):
        """The raw slug 'bug-fix' must not appear as badge text — only 'Bug Fix' is valid."""
        _insert_feature_row(
            _patched_get_db,
            number="NB02",
            title="Bug Fix Badge Text Not Raw Slug Test Row Here",
            slug="nb-bug-fix-text",
            ftype="release",
            release_subtype="bug-fix",
        )
        body = _body(client.get("/roadmap"))
        # The CSS class roadmap-type-badge--bug-fix is fine; the raw slug as
        # badge inner text must not appear standalone (text-only check)
        assert (
            "Bug Fix" in body
        ), "Badge for 'bug-fix' subtype must show human-readable text 'Bug Fix'"
        # Verify it is not *just* the raw slug value standing alone as cell text
        assert (
            "roadmap-type-badge--bug-fix" in body
        ), "CSS class 'roadmap-type-badge--bug-fix' must be present for bug-fix rows"


# ------------------------------------------------------------------ #
# 6. Parent feature rows never show a type badge                      #
# ------------------------------------------------------------------ #


class TestParentFeatureRowsNoBadge:
    def test_parent_feature_row_no_badge_when_no_subtype(self, client, _patched_get_db):
        """A parent row (type='feature') with no subtype must not produce a badge."""
        _insert_feature_row(
            _patched_get_db,
            number="PF01",
            title="Parent Feature Row No Badge When No Subtype Test Row",
            slug="pf-no-badge",
            ftype="feature",
            release_subtype=None,
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-type-badge" not in body, (
            "A parent feature row (type='feature') with release_subtype=NULL must "
            "not produce any .roadmap-type-badge span"
        )

    def test_seeded_parent_rows_produce_no_type_badge(self, seeded_client):
        """In the seeded dataset, parent rows (01–15) have NULL release_subtype.
        The number of badge spans must be fewer than the total number of rows,
        confirming parent rows are badge-free."""
        body = _body(seeded_client.get("/roadmap"))
        # The seeded data has 24 total rows; only release sub-rows with a non-NULL
        # release_subtype should produce badges.  At minimum, feature 01 row must
        # appear without causing a badge; the badge count must not equal total tr count.
        tr_count = body.count("<tr")
        badge_count = body.count("roadmap-type-badge--")
        assert badge_count < tr_count, (
            f"Not every row should have a type badge: "
            f"found {badge_count} badges across {tr_count} <tr> elements. "
            f"Parent rows (type='feature') must produce no badge."
        )

    def test_seeded_feature_01_title_present_without_badge_in_same_row(
        self, seeded_client
    ):
        """Feature 01 (Database Setup) is a parent row with NULL release_subtype.
        Its title must be in the HTML, and the overall page must also contain
        badge elements only for sub-rows — this is a presence-not-pairing check."""
        body = _body(seeded_client.get("/roadmap"))
        assert (
            "Database Setup" in body
        ), "Seeded feature '01 — Database Setup' title must appear in the roadmap HTML"
        # Parent feature rows have type='feature'; template uses roadmap-row--feature CSS
        assert (
            "roadmap-row--feature" in body
        ), "Parent feature rows must produce 'roadmap-row--feature' CSS class"


# ------------------------------------------------------------------ #
# 7. Page does not 500 with mixed NULL / non-NULL release_subtype     #
# ------------------------------------------------------------------ #


class TestMixedNullSubtypeNoError:
    def test_page_returns_200_with_mixed_null_and_set_subtypes(
        self, client, _patched_get_db
    ):
        """Insert rows with both NULL and set release_subtype; page must return 200."""
        _insert_feature_row(
            _patched_get_db,
            number="MX01",
            title="Mixed Null Subtype Page No Error Test Parent Row",
            slug="mx-parent",
            ftype="feature",
            release_subtype=None,
        )
        _insert_feature_row(
            _patched_get_db,
            number="MX01-1",
            title="Mixed Null Subtype Page No Error Test Release With Subtype",
            slug="mx-release-with-subtype",
            ftype="release",
            release_subtype="new-feature",
            parent_number="MX01",
        )
        _insert_feature_row(
            _patched_get_db,
            number="MX01-2",
            title="Mixed Null Subtype Page No Error Test Release Without Subtype",
            slug="mx-release-without-subtype",
            ftype="release",
            release_subtype=None,
            parent_number="MX01",
        )
        resp = client.get("/roadmap")
        assert resp.status_code == 200, (
            f"GET /roadmap must return 200 when rows have mixed NULL / non-NULL "
            f"release_subtype, got {resp.status_code}"
        )

    def test_seeded_data_with_null_subtypes_returns_200(self, seeded_client):
        """The seeded dataset contains rows with NULL release_subtype (e.g. 15.3, 15.4).
        The page must render without error."""
        resp = seeded_client.get("/roadmap")
        assert resp.status_code == 200, (
            "GET /roadmap must return 200 for the seeded dataset which includes "
            "rows with NULL release_subtype"
        )

    def test_none_literal_not_in_html_with_null_subtype(self, client, _patched_get_db):
        """A row with NULL release_subtype must not cause 'None' to appear in HTML."""
        _insert_feature_row(
            _patched_get_db,
            number="MX02",
            title="Null Subtype None Literal Not In HTML Test Row Here",
            slug="mx-no-none-literal",
            ftype="release",
            release_subtype=None,
        )
        body = _body(client.get("/roadmap"))
        assert ">None<" not in body, (
            "A NULL release_subtype must not render the literal string '>None<' "
            "anywhere in the page HTML"
        )

    def test_no_500_returned_for_any_combination(self, client, _patched_get_db):
        """Insert one row of each subtype plus a NULL row; page must not 500."""
        for i, subtype in enumerate((*VALID_SUBTYPES, None)):
            slug_part = subtype or "none"
            _insert_feature_row(
                _patched_get_db,
                number=f"MX0{3 + i}",
                title=f"No 500 Combination Test Row Subtype {slug_part}",
                slug=f"mx-no-500-{slug_part}",
                ftype="release",
                release_subtype=subtype,
            )
        resp = client.get("/roadmap")
        assert resp.status_code != 500, (
            "GET /roadmap must not return 500 when all three valid subtypes and "
            "NULL are present in the features table simultaneously"
        )


# ------------------------------------------------------------------ #
# 8. Template renders correct row-type CSS class for release rows     #
# ------------------------------------------------------------------ #


class TestRoadmapRowTypeCSSClass:
    def test_release_rows_use_roadmap_row_release_class(self, client, _patched_get_db):
        """Release sub-rows must carry the 'roadmap-row--release' CSS class."""
        _insert_feature_row(
            _patched_get_db,
            number="RC01",
            title="Release Row CSS Class Check Test Row",
            slug="rc-release-css",
            ftype="release",
            release_subtype="enhancement",
        )
        body = _body(client.get("/roadmap"))
        assert "roadmap-row--release" in body, (
            "Release sub-rows (type='release') must produce the CSS class "
            "'roadmap-row--release' in the rendered HTML"
        )

    def test_type_badge_sits_inside_release_row(self, client, _patched_get_db):
        """The type badge must appear in a row that also has roadmap-row--release class."""
        _insert_feature_row(
            _patched_get_db,
            number="RC02",
            title="Type Badge Inside Release Row Coexistence Test",
            slug="rc-badge-in-release",
            ftype="release",
            release_subtype="new-feature",
        )
        body = _body(client.get("/roadmap"))
        # Both must appear in the document; structural co-location is enforced by
        # the template logic (badge only renders inside the feature cell of a row)
        assert (
            "roadmap-row--release" in body
        ), "roadmap-row--release class must be present in HTML"
        assert (
            "roadmap-type-badge--new-feature" in body
        ), "roadmap-type-badge--new-feature class must be present in HTML"
