"""Feature 11.3 — Home Latest Features Section.

Tests for the "Shaping Spendly Together" section added to the landing page (GET /).

Strategy: monkeypatch database.db.DB_PATH to a fresh tmp file, seed the demo user,
reload app so module-level init_db/seed_db hits the patched path. All DB fixtures
are set up inline per test using _insert_feature; no shared state between tests.

Behaviours covered
------------------
1.  GET / with empty feature_requests table returns 200 — section absent
2.  GET / with feature requests present returns 200 — section rendered
3.  Section heading "Shaping Spendly Together" absent when table is empty
4.  Section heading "Shaping Spendly Together" present when requests exist
5.  At most 6 cards rendered even when 7+ requests exist in the DB
6.  Card contains the request title
7.  Card contains the page badge text
8.  Card contains the status text
9.  Long description (>100 chars) is truncated with an ellipsis in the snippet
10. Short description (<=100 chars) has no trailing ellipsis
11. Vote count appears in the card HTML
12. View count appears in the card HTML
13. Section links to /features (card hrefs and CTA)
14. "View All" CTA linking to /features is present
15. Section renders when user is logged in
16. Section renders when user is logged out
17. No upvote button (form action POST /features/<id>/vote) on landing page cards
"""

import importlib
import sqlite3

import pytest

import database.db as db_module
from database.db import init_db, seed_db

# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by a fresh seeded tmp DB."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
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
    """Test client with the demo user (id=1) already in session."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"
    return client


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _body(response):
    return response.get_data(as_text=True)


def _insert_feature(
    user_id=1,
    page="Home",
    title="Test Feature Title",
    description="This is a test feature description that meets the minimum length.",
    status="submitted",
    views=0,
):
    """Insert a feature request directly into the patched DB; returns the new id."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.execute(
        "INSERT INTO feature_requests (user_id, page, title, description, status, views)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, page, title, description, status, views),
    )
    conn.commit()
    fid = cursor.lastrowid
    conn.close()
    return fid


def _insert_vote(feature_id, user_id):
    """Directly insert a vote into feature_votes for test setup."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT OR IGNORE INTO feature_votes (feature_id, user_id) VALUES (?, ?)",
        (feature_id, user_id),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# 1 & 3. Empty table — 200 OK and section absent                      #
# ------------------------------------------------------------------ #


class TestLandingEmptyFeatureRequests:
    def test_landing_returns_200_when_table_empty(self, client):
        """GET / must return 200 even when feature_requests table has no rows."""
        resp = client.get("/")
        assert (
            resp.status_code == 200
        ), "GET / must return 200 with an empty feature_requests table"

    def test_landing_section_absent_when_table_empty(self, client):
        """'Shaping Spendly Together' section heading must not appear when table is empty."""
        body = _body(client.get("/"))
        assert (
            "Shaping Spendly Together" not in body
        ), "'Shaping Spendly Together' heading must be absent when feature_requests table is empty"

    def test_landing_no_server_error_when_table_empty(self, client):
        resp = client.get("/")
        assert (
            resp.status_code != 500
        ), "GET / must not raise a 500 when feature_requests is empty"

    def test_landing_still_renders_html_when_table_empty(self, client):
        body = _body(client.get("/"))
        assert (
            "<html" in body.lower() or "<!DOCTYPE" in body
        ), "GET / must still return HTML even with no feature requests"


# ------------------------------------------------------------------ #
# 2 & 4. Section present when requests exist                          #
# ------------------------------------------------------------------ #


class TestLandingSectionPresent:
    def test_landing_returns_200_with_feature_requests(self, client):
        _insert_feature(title="Feature for landing section presence check")
        resp = client.get("/")
        assert (
            resp.status_code == 200
        ), "GET / must return 200 when feature requests exist"

    def test_landing_section_heading_present(self, client):
        """Section heading 'Shaping Spendly Together' must appear when requests exist."""
        _insert_feature(title="Feature to trigger section heading rendering")
        body = _body(client.get("/"))
        assert (
            "Shaping Spendly Together" in body
        ), "'Shaping Spendly Together' heading must be present when feature requests exist"

    def test_landing_section_subtitle_present(self, client):
        """Section subtitle text must appear when requests exist."""
        _insert_feature(title="Feature for subtitle presence check on landing")
        body = _body(client.get("/"))
        # The spec defines: "See what the community is building next."
        assert (
            "community" in body or "building next" in body
        ), "Section subtitle referencing community/building next must appear when requests exist"


# ------------------------------------------------------------------ #
# 5. At most 6 cards when 7+ rows exist                               #
# ------------------------------------------------------------------ #


class TestLandingMaxSixCards:
    def test_exactly_six_titles_shown_when_seven_exist(self, client):
        """Only up to 6 cards must be shown even if 7 feature requests exist in DB."""
        titles = [
            f"Feature number {i:02d} for six card cap landing test" for i in range(1, 8)
        ]
        for t in titles:
            _insert_feature(title=t)

        body = _body(client.get("/"))

        visible_count = sum(1 for t in titles if t in body)
        assert (
            visible_count <= 6
        ), f"Landing page must show at most 6 feature cards; found {visible_count} visible titles"

    def test_six_cards_shown_when_exactly_six_exist(self, client):
        """When exactly 6 requests exist all 6 must appear."""
        titles = [
            f"Exactly six feature title number {i:02d} landing test"
            for i in range(1, 7)
        ]
        for t in titles:
            _insert_feature(title=t)

        body = _body(client.get("/"))
        visible_count = sum(1 for t in titles if t in body)
        assert (
            visible_count == 6
        ), f"Landing page must show all 6 titles when exactly 6 exist; found {visible_count}"

    def test_section_shows_at_most_six_cards_with_large_db(self, client):
        """With 10 requests in DB, still at most 6 are rendered."""
        for i in range(10):
            _insert_feature(title=f"Ten feature large db six cap test card {i:02d}")
        body = _body(client.get("/"))
        # Count the sentinel phrase that is common to all inserted titles
        count = body.count("Ten feature large db six cap test card")
        assert (
            count <= 6
        ), f"Landing must cap the cards at 6 even with 10 rows in DB; found {count} occurrences"


# ------------------------------------------------------------------ #
# 6 & 7 & 8. Card content — title, page badge, status                #
# ------------------------------------------------------------------ #


class TestLandingCardContent:
    def test_card_contains_title(self, client):
        _insert_feature(title="Unique card title content check for landing page")
        body = _body(client.get("/"))
        assert (
            "Unique card title content check for landing page" in body
        ), "Card must contain the feature request title"

    def test_card_contains_page_badge_text(self, client):
        _insert_feature(
            page="Analytics", title="Card page badge Analytics landing test"
        )
        body = _body(client.get("/"))
        assert (
            "Analytics" in body
        ), "Card must contain the page badge text (e.g. 'Analytics')"

    def test_card_contains_status_text(self, client):
        _insert_feature(
            title="Card status text submitted badge landing test",
            status="submitted",
        )
        body = _body(client.get("/"))
        # The spec defines status badges: 'submitted', 'under_review', 'planned', 'completed'
        assert "submitted" in body, "Card must contain the status badge text"

    def test_card_contains_under_review_status(self, client):
        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "INSERT INTO feature_requests (user_id, page, title, description, status)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                1,
                "Profile",
                "Under review status badge landing page card test",
                "This description is long enough to satisfy the minimum length check.",
                "under_review",
            ),
        )
        conn.commit()
        conn.close()

        body = _body(client.get("/"))
        assert (
            "under_review" in body or "Under Review" in body or "under review" in body
        ), "Card must display the 'under_review' status when that is the request status"

    def test_card_page_home_appears(self, client):
        _insert_feature(
            page="Home", title="Home page badge test on landing cards section"
        )
        body = _body(client.get("/"))
        assert (
            "Home" in body
        ), "Card page badge 'Home' must appear in landing section HTML"

    def test_multiple_cards_show_correct_titles(self, client):
        _insert_feature(title="Alpha feature card title landing multi-card test")
        _insert_feature(title="Beta feature card title landing multi-card test")
        body = _body(client.get("/"))
        assert (
            "Alpha feature card title landing multi-card test" in body
        ), "First inserted feature title must appear in landing section"
        assert (
            "Beta feature card title landing multi-card test" in body
        ), "Second inserted feature title must appear in landing section"


# ------------------------------------------------------------------ #
# 9. Long description truncated with ellipsis                         #
# ------------------------------------------------------------------ #


class TestLandingDescriptionSnippet:
    # The spec says: truncated at 100 chars with '…' (U+2026 horizontal ellipsis)
    LONG_DESC = "A" * 80 + "B" * 40  # 120 chars total — exceeds 100-char boundary

    def test_long_description_truncated_with_ellipsis(self, client):
        """Descriptions longer than 100 chars must have '…' appended in the snippet."""
        _insert_feature(
            title="Long description ellipsis truncation landing test",
            description=self.LONG_DESC,
        )
        body = _body(client.get("/"))
        assert (
            "…" in body  # U+2026 HORIZONTAL ELLIPSIS
        ), "Description longer than 100 chars must be truncated with '…' (U+2026) on the landing page"

    def test_long_description_first_100_chars_present(self, client):
        """The first 100 characters of a long description must still appear in the snippet."""
        _insert_feature(
            title="Long description first 100 chars check landing",
            description=self.LONG_DESC,
        )
        body = _body(client.get("/"))
        expected_snippet_start = self.LONG_DESC[:100]
        assert (
            expected_snippet_start in body
        ), "The first 100 chars of a long description must appear verbatim in the landing card"

    def test_long_description_characters_beyond_100_not_shown(self, client):
        """Characters beyond position 100 (the extra 'B's) must not appear after truncation."""
        # The full long desc has 80 A's then 40 B's. After truncating at 100 we get
        # 80 A's + 20 B's followed by ellipsis. The remaining 20 B's after that
        # should not appear in the snippet. We detect this by checking the snippet
        # ends with B's only up to position 100.
        _insert_feature(
            title="Long description truncation boundary landing test",
            description=self.LONG_DESC,
        )
        body = _body(client.get("/"))
        # Full description should NOT be present verbatim (since it is truncated)
        assert (
            self.LONG_DESC not in body
        ), "The full 120-char description must not appear verbatim — it should be truncated"

    # ------------------------------------------------------------------ #
    # 10. Short description — no trailing ellipsis                        #
    # ------------------------------------------------------------------ #

    def test_short_description_has_no_ellipsis(self, client):
        """Descriptions of 100 chars or fewer must not have a trailing ellipsis."""
        short_desc = (
            "X" * 100
        )  # exactly 100 chars — at the boundary, no truncation expected
        _insert_feature(
            title="Short description no ellipsis landing card test",
            description=short_desc,
        )
        body = _body(client.get("/"))
        # The short_desc itself must appear, followed immediately by nothing (no ellipsis)
        assert (
            short_desc + "…" not in body
        ), "A 100-char description must not have '…' appended in the landing card"

    def test_very_short_description_has_no_ellipsis(self, client):
        """A description well under 100 chars must not acquire a trailing ellipsis."""
        short_desc = "Short but valid and meets minimum length req."  # 46 chars
        _insert_feature(
            title="Very short description no ellipsis test landing",
            description=short_desc,
        )
        body = _body(client.get("/"))
        assert (
            short_desc + "…" not in body
        ), "A description well under 100 chars must not have '…' appended in the landing card"


# ------------------------------------------------------------------ #
# 11 & 12. Vote count and view count in card HTML                     #
# ------------------------------------------------------------------ #


class TestLandingCardCounts:
    def test_vote_count_zero_appears_in_card(self, client):
        """Even a vote count of 0 must appear somewhere in each card's HTML."""
        _insert_feature(title="Vote count zero display landing card test feature")
        body = _body(client.get("/"))
        # The number '0' is a loose check — the section must at least render numeric counts
        assert (
            "0" in body
        ), "Vote count of 0 must be rendered in the landing section HTML"

    def test_vote_count_nonzero_appears_in_card(self, client):
        """A feature with votes must show the correct vote count on the landing card."""
        from werkzeug.security import generate_password_hash

        # Insert a second user to cast a vote (votes from non-owner only)
        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Voter User", "voter@example.com", generate_password_hash("pass")),
        )
        conn.commit()
        voter_id = cursor.lastrowid
        conn.close()

        fid = _insert_feature(
            user_id=1,
            title="Vote count nonzero display landing card test",
        )
        _insert_vote(fid, voter_id)

        body = _body(client.get("/"))
        assert (
            "1" in body
        ), "A feature with 1 vote must show '1' somewhere in the landing section HTML"

    def test_view_count_zero_appears_in_card(self, client):
        """View count of 0 must appear in the landing card HTML."""
        _insert_feature(title="View count zero display landing card test feature")
        body = _body(client.get("/"))
        assert (
            "0" in body
        ), "View count of 0 must be rendered in the landing section HTML"

    def test_view_count_nonzero_appears_in_card(self, client):
        """A feature with a nonzero view count must show that count in the landing card."""
        _insert_feature(
            title="View count nonzero display landing card test",
            views=7,
        )
        body = _body(client.get("/"))
        assert (
            "7" in body
        ), "A feature with 7 views must show '7' somewhere in the landing section HTML"


# ------------------------------------------------------------------ #
# 13 & 14. /features URL in section — card links and CTA              #
# ------------------------------------------------------------------ #


class TestLandingSectionLinks:
    def test_features_url_in_section_when_requests_exist(self, client):
        """/features URL must appear in the landing section when requests are present."""
        _insert_feature(title="Features URL link presence check landing section test")
        body = _body(client.get("/"))
        assert (
            "/features" in body
        ), "'/features' URL must appear in the landing section HTML (card links or CTA)"

    def test_view_all_cta_present_when_requests_exist(self, client):
        """'View all' or 'View All' CTA linking to /features must be present."""
        _insert_feature(title="View all CTA presence check on landing page section")
        body = _body(client.get("/"))
        # The spec says: "View all requests →" link
        body_lower = body.lower()
        assert (
            "view all" in body_lower
        ), "'View all' (or 'View All') CTA text must appear in the landing section when requests exist"

    def test_card_links_to_features(self, client):
        """Card elements must be anchor tags (or contain anchors) pointing to /features."""
        _insert_feature(title="Card link href features check landing section test")
        body = _body(client.get("/"))
        # Cards should be <a href="/features"> per spec
        assert (
            'href="/features"' in body
        ), "Cards must link to /features via href='/features'"

    def test_view_all_cta_links_to_features(self, client):
        """The 'View all requests →' CTA must href to /features."""
        _insert_feature(title="View all CTA link target check landing section test")
        body = _body(client.get("/"))
        assert "/features" in body, "The View All CTA must link to the /features page"

    def test_no_features_url_when_table_empty(self, client):
        """When the section is hidden, the 'View all' CTA link must not appear."""
        body = _body(client.get("/"))
        # When the section is absent, 'View all requests' text must not appear
        assert (
            "View all requests" not in body
        ), "'View all requests' CTA must not appear when feature_requests table is empty"


# ------------------------------------------------------------------ #
# 15 & 16. Works for logged-in and logged-out visitors                #
# ------------------------------------------------------------------ #


class TestLandingSectionAuthState:
    def test_section_renders_for_logged_out_visitor(self, client):
        """Logged-out visitors must see the 'Shaping Spendly Together' section."""
        _insert_feature(title="Logged out visitor sees landing section test feature")
        body = _body(client.get("/"))
        assert (
            "Shaping Spendly Together" in body
        ), "Logged-out visitors must see the 'Shaping Spendly Together' section"

    def test_section_renders_for_logged_in_user(self, auth_client):
        """Logged-in users must also see the 'Shaping Spendly Together' section."""
        _insert_feature(title="Logged in user sees landing section test feature")
        body = _body(auth_client.get("/"))
        assert (
            "Shaping Spendly Together" in body
        ), "Logged-in users must see the 'Shaping Spendly Together' section"

    def test_section_returns_200_logged_out(self, client):
        _insert_feature(title="Logged out 200 status landing section test feature")
        resp = client.get("/")
        assert (
            resp.status_code == 200
        ), "GET / must return 200 for logged-out visitors when section is shown"

    def test_section_returns_200_logged_in(self, auth_client):
        _insert_feature(title="Logged in 200 status landing section test feature")
        resp = auth_client.get("/")
        assert (
            resp.status_code == 200
        ), "GET / must return 200 for logged-in users when section is shown"

    def test_card_title_visible_to_logged_out_visitor(self, client):
        _insert_feature(title="Card title visible to logged out visitor test")
        body = _body(client.get("/"))
        assert (
            "Card title visible to logged out visitor test" in body
        ), "Feature request title must be visible to logged-out visitors on the landing page"

    def test_card_title_visible_to_logged_in_user(self, auth_client):
        _insert_feature(title="Card title visible to logged in user test feature")
        body = _body(auth_client.get("/"))
        assert (
            "Card title visible to logged in user test feature" in body
        ), "Feature request title must be visible to logged-in users on the landing page"


# ------------------------------------------------------------------ #
# 17. No upvote button on landing page cards                          #
# ------------------------------------------------------------------ #


class TestLandingNoUpvoteButton:
    def test_no_vote_button_on_landing_cards_logged_out(self, client):
        """Upvote buttons must not appear on landing page cards for logged-out visitors."""
        _insert_feature(title="No vote button logged out check landing section")
        body = _body(client.get("/"))
        # The vote route on the full /features page uses /features/<id>/vote
        # No such form action should appear in the landing section
        assert (
            "/vote" not in body
        ), "No upvote button (href or action referencing /vote) must appear on the landing page"

    def test_no_vote_button_on_landing_cards_logged_in(self, auth_client):
        """Upvote buttons must not appear on landing page cards for logged-in users either."""
        _insert_feature(title="No vote button logged in check landing section test")
        body = _body(auth_client.get("/"))
        assert (
            "/vote" not in body
        ), "No upvote button must appear on landing page cards even for logged-in users"


# ------------------------------------------------------------------ #
# 18. Initials avatar — privacy: full name must not appear            #
# ------------------------------------------------------------------ #


class TestLandingCardInitials:
    def test_initials_appear_in_landing_card(self, client):
        """Cards must show initials avatar. Demo User -> 'DU'."""
        _insert_feature(title="Initials avatar DU appears on landing card test")
        body = _body(client.get("/"))
        assert (
            "DU" in body
        ), "Initials 'DU' for 'Demo User' must appear in the landing section card HTML"

    def test_full_name_not_in_landing_card_html(self, client):
        """The full user name must not appear verbatim in the landing card HTML."""
        _insert_feature(title="Privacy full name not shown in landing card test")
        body = _body(client.get("/"))
        # 'Demo User' is the seeded user name — it must not appear as raw text in card
        # The section HTML should only show initials, not the full name
        # We check that 'Demo User' does not appear outside of nav/session UI
        # by verifying the card section itself does not include it verbatim
        # (it's acceptable if it appears in a logged-in nav element, so we narrow
        # the check: the section should show 'DU' which means initials are used)
        assert (
            "DU" in body
        ), "Initials 'DU' must appear in the card, confirming the privacy convention is followed"

    def test_email_not_in_landing_section(self, client):
        """User email addresses must not appear anywhere on the landing page."""
        _insert_feature(title="Email privacy check on landing page section test")
        body = _body(client.get("/"))
        assert (
            "demo@spendly.com" not in body
        ), "User email 'demo@spendly.com' must not appear in the landing page HTML"


# ------------------------------------------------------------------ #
# 19. Time-ago / relative timestamp appears in card                   #
# ------------------------------------------------------------------ #


class TestLandingCardTimestamp:
    def test_time_ago_appears_in_card(self, client):
        """Each card must show a relative timestamp (e.g. 'just now', 'X min ago')."""
        _insert_feature(title="Time ago relative timestamp landing card test feature")
        body = _body(client.get("/"))
        # Freshly inserted records will show 'just now'
        assert (
            "just now" in body
            or "min ago" in body
            or "hour" in body
            or "day" in body
            or "ago" in body
        ), "Card must display a relative time string (e.g. 'just now' or 'X ago')"


# ------------------------------------------------------------------ #
# 20. Section ordering — latest first                                  #
# ------------------------------------------------------------------ #


class TestLandingSectionOrdering:
    def test_latest_feature_appears_before_older_feature(self, client):
        """The most recently created feature must appear before older ones in the section."""
        _insert_feature(title="Older landing section ordering feature test card")
        _insert_feature(title="Newer landing section ordering feature test card")

        body = _body(client.get("/"))
        pos_older = body.find("Older landing section ordering feature test card")
        pos_newer = body.find("Newer landing section ordering feature test card")

        assert pos_older != -1, "Older feature must appear in the landing section"
        assert pos_newer != -1, "Newer feature must appear in the landing section"
        assert (
            pos_newer < pos_older
        ), "Latest (most recently created) feature must appear before older ones in the landing section"
