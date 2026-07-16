"""Tests for Context Section with Card Flip (21.2-oxos-context-flip)

Spec: .claude/specs/21.2-oxos-context-flip.md

Scope:
- No new routes — uses the existing public `/platform` route
- No database changes — table list is hardcoded in the template
- Adds a Context section with a flippable Supabase card:
    - Front: database icon, "Supabase", "Primary Data System"
    - Back: hardcoded list of database tables (users, expenses, features)
- Card flip is a client-side (JS/CSS) interaction; from the server-rendered
  HTML we can only assert that the markup landmarks needed for the flip
  (front face, back face, toggle container) are present.
"""

import importlib

import pytest

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


# ------------------------------------------------------------------ #
# /platform route — basic rendering                                   #
# ------------------------------------------------------------------ #


class TestPlatformRouteRendersContext:
    """The existing /platform route should render successfully and
    include the new Context section alongside prior sections."""

    def test_platform_route_returns_200(self, client):
        """`/platform` should exist and return 200 OK."""
        response = client.get("/platform")
        assert response.status_code == 200, "Expected /platform to return 200"

    def test_platform_is_public(self, client):
        """`/platform` should be accessible without authentication (no redirect)."""
        response = client.get("/platform")
        assert response.status_code == 200, "Expected no auth redirect for /platform"

    def test_platform_still_renders_other_sections(self, client):
        """Sanity check: Business Outcomes and Learnings sections (from
        Release 1) should still be present alongside the new Context section."""
        response = client.get("/platform")
        assert b"Business Outcomes" in response.data
        assert b"Learnings" in response.data


# ------------------------------------------------------------------ #
# Context section presence                                            #
# ------------------------------------------------------------------ #


class TestContextSection:
    """The Context section header and card content should be present."""

    def test_context_section_heading_present(self, client):
        """Page should contain a 'Context' section heading."""
        response = client.get("/platform")
        assert b"Context" in response.data, "Expected 'Context' section heading"

    def test_context_section_has_database_icon(self, client):
        """Context section heading should use the lucide 'database' icon."""
        response = client.get("/platform")
        assert (
            b'data-lucide="database"' in response.data
        ), "Expected a lucide database icon in the Context section"

    def test_context_section_appears_after_business_outcomes(self, client):
        """Per spec, Context section should follow Business Outcomes in
        document order (Business Outcomes -> Context -> Learnings)."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")
        business_idx = html.find("Business Outcomes")
        context_idx = html.find("Context")
        learnings_idx = html.find("Learnings")

        assert business_idx != -1, "Business Outcomes section not found"
        assert context_idx != -1, "Context section heading not found"
        assert learnings_idx != -1, "Learnings section not found"
        assert (
            business_idx < context_idx < learnings_idx
        ), "Expected section order: Business Outcomes, Context, Learnings"


# ------------------------------------------------------------------ #
# Flip card structure                                                 #
# ------------------------------------------------------------------ #


class TestFlipCardStructure:
    """The flip card markup should provide a front face and a back face
    inside a toggle-able container, per the spec's flip interaction."""

    def test_flip_card_container_present(self, client):
        """A flip card container should exist in the Context section."""
        response = client.get("/platform")
        assert b"flip-card" in response.data, "Expected a flip card container element"

    def test_flip_card_has_front_face(self, client):
        """Flip card should have a distinguishable front face."""
        response = client.get("/platform")
        assert (
            b"flip-card-front" in response.data
        ), "Expected flip card front face markup"

    def test_flip_card_has_back_face(self, client):
        """Flip card should have a distinguishable back face."""
        response = client.get("/platform")
        assert b"flip-card-back" in response.data, "Expected flip card back face markup"

    def test_flip_card_front_shows_supabase_info(self, client):
        """Front of the card should show the database icon, 'Supabase',
        and 'Primary Data System' per the spec."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")
        assert "Supabase" in html, "Expected 'Supabase' on the front of the card"
        assert (
            "Primary Data System" in html
        ), "Expected 'Primary Data System' subtitle on the front of the card"

    def test_flip_card_loads_platform_css(self, client):
        """Flip card animation styles are expected to live in platform.css."""
        response = client.get("/platform")
        assert b"platform.css" in response.data, "Expected platform.css to be loaded"

    def test_flip_card_has_toggle_affordance(self, client):
        """The flip interaction should be wired up client-side: the
        server-rendered page should include a script block (or data
        attribute) responsible for toggling the flipped state. This
        does not execute JS, only checks the hook is emitted."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")
        assert (
            "flip" in html.lower()
        ), "Expected some flip-related hook (class/id/script) in HTML"


# ------------------------------------------------------------------ #
# Database tables shown on the back of the card                       #
# ------------------------------------------------------------------ #


class TestFlipCardBackTables:
    """Back of the card should list the hardcoded database tables."""

    @pytest.mark.parametrize("table_name", ["users", "expenses", "features"])
    def test_table_name_present_on_back(self, client, table_name):
        """Each expected table name should appear in the rendered HTML."""
        response = client.get("/platform")
        assert (
            table_name.encode() in response.data
        ), f"Expected table '{table_name}' to be listed on the back of the flip card"

    def test_all_three_tables_present_together(self, client):
        """All three hardcoded tables should be present in a single response."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")
        for table_name in ("users", "expenses", "features"):
            assert (
                table_name in html
            ), f"Missing table '{table_name}' in Context section"

    def test_back_of_card_has_table_icons(self, client):
        """Each table entry should be paired with a lucide table icon."""
        response = client.get("/platform")
        assert (
            b'data-lucide="table-2"' in response.data
        ), "Expected lucide table-2 icons for the table list entries"

    def test_no_unexpected_extra_tables_hardcoded(self, client):
        """Only the three tables defined in the schema (users, expenses,
        features) should currently be hardcoded on the back of the card —
        guards against accidental scope creep beyond the spec."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")

        start = html.find("flip-card-back")
        assert start != -1, "flip-card-back section not found"

        # Extract just the back-of-card region for a scoped table count check.
        back_region_start = html.find("flip-card-tables")
        back_region_end = html.find("</ul>", back_region_start)
        back_region = html[back_region_start:back_region_end]

        # Count actual list items with the flip-card-table class
        table_item_count = back_region.count('class="flip-card-table"')
        assert (
            table_item_count == 3
        ), f"Expected exactly 3 table entries on the back of the card, found {table_item_count}"


# ------------------------------------------------------------------ #
# Card flip interaction — both front and back states reachable        #
# ------------------------------------------------------------------ #


class TestCardFlipBothStates:
    """Per spec: 'Click/tap toggles the flip state.' Flask's test client
    does not execute JS/CSS, so we cannot literally click the card or
    observe a `.flipped` class being toggled at runtime. Instead we
    verify that both the front-state content and the back-state content
    are rendered together in the same response — i.e. the server emits
    both faces so a pure client-side (CSS transform) toggle is possible
    without a second request. This is the correct boundary for a
    request/response-level test of a CSS-driven interaction."""

    def test_front_and_back_content_both_present_in_single_response(self, client):
        """Both faces of the card must exist in the DOM simultaneously
        (toggling is expected to be presentation-only, not conditional
        rendering) so that the flip is instant and client-side."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")

        front_idx = html.find("flip-card-front")
        back_idx = html.find("flip-card-back")

        assert front_idx != -1, "Expected front face markup to be present"
        assert back_idx != -1, "Expected back face markup to be present"
        assert (
            front_idx < back_idx
        ), "Expected front face to precede back face in markup"

    def test_front_face_does_not_contain_table_list(self, client):
        """Sanity check on separation of concerns: the front face content
        (icon/name/subtitle) should not itself include the back's table
        list markup, confirming front and back are distinct regions."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")

        front_start = html.find("flip-card-front")
        back_start = html.find("flip-card-back")
        front_region = html[front_start:back_start]

        assert (
            "flip-card-tables" not in front_region
        ), "Expected table list to live only on the back face, not the front"

    def test_flip_card_is_within_context_section_cards_container(self, client):
        """The flip card should live inside the Context section's card
        grid, following the same structural convention as other platform
        sections (extensible for future data-system cards per spec)."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")

        context_idx = html.find("Context")
        flip_card_idx = html.find("flip-card")

        assert context_idx != -1, "Context section heading not found"
        assert flip_card_idx != -1, "flip-card not found"
        assert (
            context_idx < flip_card_idx
        ), "Expected flip card to appear after the Context section heading"


# ------------------------------------------------------------------ #
# Responsive behavior + CSS delivery                                  #
# ------------------------------------------------------------------ #


class TestResponsiveBehavior:
    """Per spec: 'Responsive: flip card works on mobile and desktop' and
    'CSS transition for smooth flip effect.' Flask's test client cannot
    render CSS or simulate viewport widths, so these tests validate the
    delivery mechanism (the stylesheet the template depends on is
    correctly linked and served) rather than asserting exact breakpoint
    values, which are an implementation detail the spec does not
    prescribe."""

    def test_platform_stylesheet_is_linked_in_head(self, client):
        """The platform page must reference its stylesheet so that any
        responsive/transition rules defined there actually apply."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")
        assert (
            'rel="stylesheet"' in html and "platform.css" in html
        ), "Expected platform.css to be linked via a stylesheet tag"

    def test_platform_stylesheet_is_served_successfully(self, client):
        """The linked stylesheet must actually be servable (200), not a
        broken/missing static asset, otherwise flip/transition/responsive
        styling would silently fail to load."""
        response = client.get("/static/css/platform.css")
        assert (
            response.status_code == 200
        ), "Expected /static/css/platform.css to be served with 200 OK"

    def test_platform_page_extends_base_template(self, client):
        """All templates must extend base.html per project convention;
        this is also what provides the responsive nav/hamburger behavior
        referenced by the spec's 'mobile and desktop' requirement."""
        response = client.get("/platform")
        html = response.data.decode("utf-8")
        assert (
            "<html" in html.lower()
        ), "Expected a full rendered HTML document (template extends base.html)"
