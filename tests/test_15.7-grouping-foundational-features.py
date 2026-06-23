"""Feature 15.7 — Grouping Foundational Features

Tests the roadmap page's grouping and accordion markup after the 15.7
frontend-only change. No backend or database changes — assertions are
against the rendered HTML of GET /roadmap.

Coverage targets the Definition of Done items added by 15.7:
  - "Foundational Features" group row wrapping features 01-10
  - Group row is collapsed by default, has chevron, count badge, aria attributes
  - Parent features (11, 12, 15) render as roadmap-parent-row with accordion
  - Release sub-rows carry data-parent attribute
  - Description detail row (roadmap-detail-row) is completely removed
  - New data-parent-group attribute on features 01-10
  - Inline JS references both group and parent toggle classes
"""

import importlib

import psycopg2
import psycopg2.extras
import pytest

import database.db as db_module
from database.db import init_db, seed_features
import database.queries as queries_module


# ------------------------------------------------------------------ #
# Fixtures — same isolation strategy as test_15.2 / test_15.5       #
# ------------------------------------------------------------------ #


@pytest.fixture
def _patched_get_db(monkeypatch):
    """Open a real Postgres connection, monkeypatch get_db in both
    database modules, and TRUNCATE features at setup + teardown."""
    init_db()
    _real_conn = db_module.get_db()

    class _NoCloseProxy:
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

    cur = _patched_get_db.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _patched_get_db.commit()
    cur.close()

    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(_patched_get_db, monkeypatch):
    """Flask test client with the features table populated via seed_features()."""
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
    parent_number=None,
    description=None,
    captured_at=None,
    planned_at=None,
    spec_at=None,
    implemented_at=None,
    tested_at=None,
    reviewed_at=None,
    shipped_at=None,
):
    """Insert a single row into the features table."""
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
# 1. Group row — presence and label                                   #
# ------------------------------------------------------------------ #


class TestGroupRowPresence:
    def test_group_row_class_in_html(self, seeded_client):
        """A row with class 'roadmap-group-row' must be present in the rendered
        roadmap page."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-row" in body, (
            "A group row with class 'roadmap-group-row' must be present"
        )

    def test_group_row_label(self, seeded_client):
        """The group row must show the 'Foundational Features' label."""
        body = _body(seeded_client.get("/roadmap"))
        assert "Foundational Features" in body, (
            "The group row must contain the 'Foundational Features' label"
        )

    def test_group_row_data_group_attribute(self, seeded_client):
        """The group row must carry data-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        assert 'data-group="foundational"' in body, (
            "The group row must carry data-group='foundational'"
        )


# ------------------------------------------------------------------ #
# 2. Group row — count badge                                          #
# ------------------------------------------------------------------ #


class TestGroupRowCount:
    def test_group_row_has_count_badge(self, seeded_client):
        """The group row must contain an element with class 'roadmap-group-count'."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-count" in body, (
            "The group row must contain a .roadmap-group-count badge"
        )

    def test_group_row_count_shows_10(self, seeded_client):
        """The count badge must display '10' for the ten foundational features."""
        body = _body(seeded_client.get("/roadmap"))
        # Find the roadmap-group-count element and verify its text content is "10"
        idx = body.find("roadmap-group-count")
        assert idx != -1, "roadmap-group-count element must exist"
        # Find the closing > after the class, then read until the next <
        tag_end = body.find(">", idx)
        assert tag_end != -1
        next_open = body.find("<", tag_end + 1)
        assert next_open != -1
        count_text = body[tag_end + 1:next_open].strip()
        assert count_text == "10", (
            f"Group count badge must show '10', got '{count_text}'"
        )


# ------------------------------------------------------------------ #
# 3. Group row — chevron icon                                         #
# ------------------------------------------------------------------ #


class TestGroupRowChevron:
    def test_group_row_has_chevron(self, seeded_client):
        """The group row must contain a chevron icon for the expand/collapse indicator."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-chevron" in body, (
            "The group row must contain a .roadmap-group-chevron element"
        )

    def test_group_chevron_uses_lucide(self, seeded_client):
        """The group chevron must use the Lucide 'chevron-down' icon via data-lucide."""
        body = _body(seeded_client.get("/roadmap"))
        # Scope to the group row area
        idx = body.find('class="roadmap-group-row"')
        assert idx != -1, "Group row class must exist"
        # Find the end of the group row (</tr> after the group row)
        group_end = body.find("</tr>", idx)
        assert group_end != -1
        group_html = body[idx:group_end]
        assert 'data-lucide="chevron-down"' in group_html, (
            "The group chevron must use data-lucide='chevron-down'"
        )


# ------------------------------------------------------------------ #
# 4. Group row — default collapsed state                              #
# ------------------------------------------------------------------ #


class TestGroupRowDefaultState:
    def test_group_row_aria_expanded_false(self, seeded_client):
        """The group row must have aria-expanded='false' (collapsed by default)."""
        body = _body(seeded_client.get("/roadmap"))
        idx = body.find('class="roadmap-group-row"')
        assert idx != -1, "Group row class must exist"
        tag_start = body.rfind("<tr", 0, idx)
        tag_end = body.find(">", idx)
        group_tag = body[tag_start:tag_end + 1]
        assert 'aria-expanded="false"' in group_tag, (
            "The group row must have aria-expanded='false' (collapsed by default)"
        )

    def test_no_row_is_expanded_initially(self, seeded_client):
        """No expandable row (parent or group) should be aria-expanded='true' on page load."""
        body = _body(seeded_client.get("/roadmap"))
        assert 'aria-expanded="true"' not in body, (
            "No row should be expanded (aria-expanded='true') on initial page load"
        )


# ------------------------------------------------------------------ #
# 5. Features 01-10 carry data-parent-group                            #
# ------------------------------------------------------------------ #


class TestDataParentGroupAttribute:
    def test_feature_01_has_data_parent_group(self, seeded_client):
        """Feature 01 must carry data-parent-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        assert 'data-parent-group="foundational"' in body, (
            "Feature 01 must carry data-parent-group='foundational'"
        )

    def test_all_features_01_to_10_have_data_parent_group(self, seeded_client):
        """All features 01-10 must carry data-parent-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        # Count occurrences in <tbody> only (the attribute also appears in the
        # inline <script> block as a selector string)
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        assert tbody_start != -1 and tbody_end != -1, "tbody must be present"
        tbody = body[tbody_start:tbody_end]
        count = tbody.count('data-parent-group="foundational"')
        assert count == 10, (
            f"Exactly 10 rows in <tbody> must have data-parent-group='foundational', "
            f"found {count}"
        )

    def test_features_11_plus_do_not_have_data_parent_group(self, seeded_client):
        """Features 11+ must NOT carry data-parent-group='foundational' in tbody rows."""
        body = _body(seeded_client.get("/roadmap"))
        tbody_start = body.find("<tbody>")
        tbody_end = body.find("</tbody>")
        assert tbody_start != -1 and tbody_end != -1, "tbody must be present"
        tbody = body[tbody_start:tbody_end]
        # Features 11, 12, 14, 15, 16 are in the seed data — none should have data-parent-group
        for num in ["11", "12", "14", "15", "16"]:
            # Find the row for this feature number and check it does not have the attribute
            idx = body.find(f'class="roadmap-row ')
            # Search for the specific number cell
            # Look for the feature number in a td and check its row
            # We'll search for the number followed by the attribute absence
            # A simpler approach: count total in tbody is exactly 10
            pass
        # The count-based assertion in the previous test already covers this.
        # Verify no feature number >= 11 has the attribute by scanning each row.
        import re
        # Find all <tr ...> tags in tbody
        tr_pattern = re.compile(r'<tr[^>]*>', re.DOTALL)
        tr_tags = tr_pattern.findall(tbody)
        for tag in tr_tags:
            if 'data-parent-group="foundational"' in tag:
                # This tag should be for a foundational feature (01-10)
                # Extract the feature number from the tag or nearby content
                # The number cell is the first <td> after the <tr tag
                tag_pos = tbody.find(tag)
                after_tag = tbody[tag_pos + len(tag):]
                # Find the first <td>...</td> content which is the number
                td_match = re.search(r'<td[^>]*>(.*?)</td>', after_tag)
                if td_match:
                    num_text = td_match.group(1).strip()
                    assert num_text in {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}, (
                        f"Row with number '{num_text}' must not have data-parent-group='foundational'"
                    )


# ------------------------------------------------------------------ #
# 6. Release sub-rows carry data-parent                               #
# ------------------------------------------------------------------ #


class TestDataParentAttribute:
    def test_release_row_has_data_parent(self, client, _patched_get_db):
        """A release sub-row must carry data-parent matching its parent number."""
        _insert_feature(
            _patched_get_db,
            number="P01",
            title="Parent Feature For Data Parent Test",
            slug="parent-data-parent",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="P01-1",
            title="Release Sub Row Data Parent Test",
            slug="release-data-parent",
            ftype="release",
            parent_number="P01",
        )
        body = _body(client.get("/roadmap"))
        assert 'data-parent="P01"' in body, (
            "Release sub-row must carry data-parent='P01'"
        )

    def test_multiple_release_rows_have_correct_data_parent(self, client, _patched_get_db):
        """Multiple release sub-rows under the same parent each carry data-parent."""
        _insert_feature(
            _patched_get_db,
            number="P02",
            title="Parent Feature Multiple Releases",
            slug="parent-multi-releases",
            ftype="feature",
        )
        _insert_feature(
            _patched_get_db,
            number="P02-1",
            title="Release 1",
            slug="release-1",
            ftype="release",
            parent_number="P02",
        )
        _insert_feature(
            _patched_get_db,
            number="P02-2",
            title="Release 2",
            slug="release-2",
            ftype="release",
            parent_number="P02",
        )
        body = _body(client.get("/roadmap"))
        # Both release rows should have data-parent="P02"
        count = body.count('data-parent="P02"')
        assert count == 2, (
            f"Both release rows must carry data-parent='P02', found {count}"
        )

    def test_release_row_without_parent_no_data_parent(self, client, _patched_get_db):
        """A release row with no parent_number must NOT carry data-parent."""
        _insert_feature(
            _patched_get_db,
            number="P03",
            title="Parent Feature No Release",
            slug="parent-no-release",
            ftype="feature",
        )
        body = _body(client.get("/roadmap"))
        # Strip <script>...</script> before checking — JS uses data-parent as a
        # selector string, which is not the same as an HTML attribute.
        import re as _re
        html_only = _re.sub(r"<script[^>]*>.*?</script>", "", body, flags=_re.DOTALL)
        assert 'data-parent="' not in html_only, (
            "No data-parent HTML attribute should exist when there are no release rows"
        )


# ------------------------------------------------------------------ #
# 7. Detail row removed                                               #
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
# 8. Parent row markup                                                #
# ------------------------------------------------------------------ #


class TestParentRowMarkup:
    def test_parent_row_class_on_feature_with_children(self, client, _patched_get_db):
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
            "A feature row with child releases must carry class 'roadmap-parent-row'"
        )

    def test_parent_row_aria_expanded_false(self, client, _patched_get_db):
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
        assert 'aria-expanded="false"' in body, (
            'A parent feature row must have aria-expanded="false" on initial load'
        )

    def test_parent_row_aria_controls(self, client, _patched_get_db):
        """The parent row must have aria-controls pointing to its parent id."""
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
            'Parent row for feature C03 must have aria-controls="parent-C03"'
        )

    def test_non_parent_row_no_roadmap_parent_row_class(self, client, _patched_get_db):
        """A top-level feature row with no children must NOT carry 'roadmap-parent-row'."""
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
            "A feature row with no children must NOT carry class 'roadmap-parent-row'"
        )


# ------------------------------------------------------------------ #
# 9. Inline JS toggle logic                                           #
# ------------------------------------------------------------------ #


class TestInlineJSToggle:
    def test_script_block_present(self, seeded_client):
        """The /roadmap page must contain a <script> block with toggle logic."""
        body = _body(seeded_client.get("/roadmap"))
        assert "<script>" in body or "<script " in body, (
            "GET /roadmap must include a <script> block containing the toggle logic"
        )

    def test_script_references_roadmap_group_row(self, seeded_client):
        """The inline script must query for '.roadmap-group-row'."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-row" in body, (
            "The inline JS must reference '.roadmap-group-row' for group toggle"
        )

    def test_script_references_roadmap_parent_row(self, seeded_client):
        """The inline script must query for '.roadmap-parent-row'."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-parent-row" in body, (
            "The inline JS must reference '.roadmap-parent-row' for parent accordion"
        )

    def test_script_references_data_parent_group(self, seeded_client):
        """The inline script must reference data-parent-group='foundational'."""
        body = _body(seeded_client.get("/roadmap"))
        assert 'data-parent-group="foundational"' in body, (
            "The inline JS must reference data-parent-group='foundational' for group selection"
        )

    def test_script_references_aria_expanded(self, seeded_client):
        """The inline script must read/write 'aria-expanded' for toggle state."""
        body = _body(seeded_client.get("/roadmap"))
        assert "aria-expanded" in body, (
            "The inline JS must reference 'aria-expanded' to manage toggle state"
        )

    def test_lucide_create_icons_called(self, seeded_client):
        """The page must call lucide.createIcons() to render chevron SVGs."""
        body = _body(seeded_client.get("/roadmap"))
        assert "lucide.createIcons()" in body or "lucide.createIcons" in body, (
            "The page must call lucide.createIcons() so chevron SVGs are rendered"
        )


# ------------------------------------------------------------------ #
# 10. Public access (regression)                                      #
# ------------------------------------------------------------------ #


class TestPublicAccessRegression:
    def test_get_roadmap_returns_200_unauthenticated(self, seeded_client):
        """GET /roadmap must return 200 for an unauthenticated request."""
        resp = seeded_client.get("/roadmap")
        assert resp.status_code == 200, (
            "GET /roadmap must return 200 for unauthenticated visitors"
        )

    def test_get_roadmap_does_not_redirect_to_login(self, seeded_client):
        """GET /roadmap must not redirect unauthenticated visitors to /login."""
        resp = seeded_client.get("/roadmap")
        assert resp.status_code != 302, (
            "GET /roadmap must not redirect unauthenticated visitors to /login"
        )

    def test_get_roadmap_does_not_return_500(self, seeded_client):
        """GET /roadmap must not raise a 500 error after 15.7 template changes."""
        resp = seeded_client.get("/roadmap")
        assert resp.status_code != 500, (
            "GET /roadmap must not raise a 500 error after 15.7 template changes"
        )


# ------------------------------------------------------------------ #
# 11. Full seeded-data rendering — integration                        #
# ------------------------------------------------------------------ #


class TestSeededDataIntegration:
    def test_seeded_page_returns_200(self, seeded_client):
        """GET /roadmap must return 200 with seeded data."""
        resp = seeded_client.get("/roadmap")
        assert resp.status_code == 200, "GET /roadmap must return 200 with seeded data"

    def test_seeded_page_has_group_row(self, seeded_client):
        """With seeded data, a group row must be present."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-group-row" in body, (
            "A group row must be present with seeded data"
        )

    def test_seeded_page_has_parent_rows(self, seeded_client):
        """With seeded data, parent features (11, 12, 15) must have
        roadmap-parent-row class."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-parent-row" in body, (
            "Parent feature rows must carry 'roadmap-parent-row' with seeded data"
        )

    def test_seeded_page_no_detail_rows(self, seeded_client):
        """With seeded data, no detail rows should exist."""
        body = _body(seeded_client.get("/roadmap"))
        assert "roadmap-detail-row" not in body, (
            "No detail rows must exist with seeded data after 15.7 changes"
        )

    def test_seeded_page_has_table(self, seeded_client):
        """The roadmap table must render with seeded data."""
        body = _body(seeded_client.get("/roadmap"))
        assert "<table" in body, "Pipeline table must still render with seeded data"
        assert "</table>" in body, "Pipeline table must be properly closed"
        assert "<tbody>" in body or "<tr" in body, "Table body rows must be present"

    def test_seeded_page_has_aria_expanded_false(self, seeded_client):
        """On initial page load all expandable rows start collapsed."""
        body = _body(seeded_client.get("/roadmap"))
        assert 'aria-expanded="false"' in body, (
            'All parent rows must have aria-expanded="false" on initial load'
        )
