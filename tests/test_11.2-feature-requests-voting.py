"""Feature 11.2 — Feature Requests Voting: /features/<id>/vote route and Trending sort.

Strategy: same monkeypatch + importlib.reload pattern as test_11.1. Each test is
fully independent; all DB state is set up inline using _insert_feature and
_insert_vote helpers that write directly to the patched SQLite file.

Fixture hierarchy (mirrors 11.1):
  client        — Flask test client backed by a fresh seeded tmp DB
  auth_client   — client with the demo user (id=1) already in session
  second_client — separate authenticated client for a second user (id=2+)

Spec behaviours covered (Definition of Done from 11.2 spec)
------------------------------------------------------------
1.  POST /features/<id>/vote returns {"voted": true, "upvotes": N} on first vote
2.  Second POST by same user returns {"voted": false, "upvotes": N-1} (toggle off)
3.  Voting on own request returns 403
4.  Unauthenticated POST returns 401 (not a redirect)
5.  POST on non-existent ID returns 404
6.  Trending sort returns 200 and orders by (votes*5 + views + recency_bonus) DESC
7.  "Trending" option appears in the HTML of GET /features
8.  voted_ids pre-populates fr-vote-btn--voted class for already-voted requests
9.  Modal card data attributes data-voted and data-is-own are present in HTML
10. JSON response contains both "voted" (bool) and "upvotes" (int) keys
11. DB side effect: feature_votes row inserted on first vote
12. DB side effect: feature_votes row removed on toggle-off
13. Upvotes count in JSON matches actual feature_votes row count
14. Two users voting the same request yields upvotes: 2
15. most_upvoted sort: high-vote feature appears before low-vote feature
16. Invalid sort param falls back gracefully (no 500)
"""

import importlib
import json
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


@pytest.fixture
def second_user_id(tmp_path):
    """Insert a second user directly into the patched DB and return their id.

    Must be called after the monkeypatch in the `client` fixture has already
    set DB_PATH.
    """
    from werkzeug.security import generate_password_hash

    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Alice Smith", "alice@example.com", generate_password_hash("alicepass")),
    )
    conn.commit()
    uid = cursor.lastrowid
    conn.close()
    return uid


@pytest.fixture
def second_client(client, second_user_id):
    """A second authenticated test client (different user to the demo user)."""
    with client.session_transaction() as sess:
        sess["user_id"] = second_user_id
        sess["user_name"] = "Alice Smith"
    return client


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _body(response):
    return response.get_data(as_text=True)


def _insert_feature(
    user_id,
    page="Home",
    title="Test Feature",
    description="This is a test feature description that meets the minimum length.",
):
    """Insert a feature request directly into the patched DB; returns the new id."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.execute(
        "INSERT INTO feature_requests (user_id, page, title, description) VALUES (?, ?, ?, ?)",
        (user_id, page, title, description),
    )
    conn.commit()
    fid = cursor.lastrowid
    conn.close()
    return fid


def _insert_feature_with_views(
    user_id,
    views,
    title="Test Feature With Views",
    description="This is a test feature description that meets the minimum length.",
):
    """Insert a feature request with a pre-set views count; returns the new id."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.execute(
        "INSERT INTO feature_requests (user_id, page, title, description, views)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, "Home", title, description, views),
    )
    conn.commit()
    fid = cursor.lastrowid
    conn.close()
    return fid


def _insert_vote(feature_id, user_id):
    """Directly insert a vote into feature_votes for test setup.

    Uses INSERT OR IGNORE so calling it twice for the same pair is safe.
    """
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT OR IGNORE INTO feature_votes (feature_id, user_id) VALUES (?, ?)",
        (feature_id, user_id),
    )
    conn.commit()
    conn.close()


def _count_votes(feature_id):
    """Return the number of vote rows for a feature in the patched DB."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    row = conn.execute(
        "SELECT COUNT(*) FROM feature_votes WHERE feature_id = ?",
        (feature_id,),
    ).fetchone()
    conn.close()
    return row[0]


def _vote_exists(feature_id, user_id):
    """Return True if a specific (feature_id, user_id) pair exists in feature_votes."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    row = conn.execute(
        "SELECT COUNT(*) FROM feature_votes WHERE feature_id = ? AND user_id = ?",
        (feature_id, user_id),
    ).fetchone()
    conn.close()
    return row[0] > 0


# ------------------------------------------------------------------ #
# 1. POST /features/<id>/vote — first vote (happy path)               #
# ------------------------------------------------------------------ #


class TestVoteFirstTime:
    def test_first_vote_returns_200(self, auth_client, second_user_id):
        """Voting on another user's request must return 200."""
        fid = _insert_feature(
            second_user_id, title="Feature owned by Alice for first vote"
        )
        resp = auth_client.post(f"/features/{fid}/vote")
        assert (
            resp.status_code == 200
        ), "POST /features/<id>/vote must return 200 on first vote"

    def test_first_vote_returns_json_content_type(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for JSON content type check vote"
        )
        resp = auth_client.post(f"/features/{fid}/vote")
        assert (
            "application/json" in resp.content_type
        ), "POST /features/<id>/vote must return Content-Type: application/json"

    def test_first_vote_json_voted_is_true(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for voted=true JSON key check"
        )
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert data["voted"] is True, "First vote must return {'voted': true, ...}"

    def test_first_vote_json_upvotes_is_1(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for upvotes=1 JSON value check"
        )
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert (
            data["upvotes"] == 1
        ), "First vote must return {'upvotes': 1} when starting from 0"

    def test_first_vote_json_has_both_keys(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for JSON key presence check"
        )
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert "voted" in data, "JSON response must contain 'voted' key"
        assert "upvotes" in data, "JSON response must contain 'upvotes' key"

    def test_first_vote_inserts_row_in_feature_votes(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for DB row insert on vote check"
        )
        assert not _vote_exists(fid, 1), "No vote row must exist before voting"
        auth_client.post(f"/features/{fid}/vote")
        assert _vote_exists(
            fid, 1
        ), "POST /features/<id>/vote must insert a row into feature_votes"

    def test_first_vote_upvotes_matches_db_count(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for upvotes vs DB count accuracy"
        )
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        db_count = _count_votes(fid)
        assert (
            data["upvotes"] == db_count
        ), "JSON 'upvotes' must equal the actual row count in feature_votes"


# ------------------------------------------------------------------ #
# 2. POST /features/<id>/vote — second vote (toggle off)              #
# ------------------------------------------------------------------ #


class TestVoteToggleOff:
    def test_second_vote_returns_200(self, auth_client, second_user_id):
        fid = _insert_feature(second_user_id, title="Feature for toggle off 200 status")
        auth_client.post(f"/features/{fid}/vote")
        resp = auth_client.post(f"/features/{fid}/vote")
        assert resp.status_code == 200, "Toggle-off POST must return 200"

    def test_second_vote_json_voted_is_false(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for toggle off voted=false"
        )
        auth_client.post(f"/features/{fid}/vote")
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert data["voted"] is False, "Second vote must return {'voted': false, ...}"

    def test_second_vote_json_upvotes_decrements(self, auth_client, second_user_id):
        fid = _insert_feature(
            second_user_id, title="Feature for toggle off upvotes decrement"
        )
        first = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        second = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert (
            second["upvotes"] == first["upvotes"] - 1
        ), "Toggle-off must decrement upvotes by 1"

    def test_second_vote_upvotes_is_zero_when_only_voter(
        self, auth_client, second_user_id
    ):
        fid = _insert_feature(
            second_user_id, title="Feature for toggle off returns zero count"
        )
        auth_client.post(f"/features/{fid}/vote")
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert (
            data["upvotes"] == 0
        ), "Toggle-off as the only voter must return upvotes: 0"

    def test_second_vote_removes_row_from_feature_votes(
        self, auth_client, second_user_id
    ):
        fid = _insert_feature(
            second_user_id, title="Feature for DB row removal on toggle off"
        )
        auth_client.post(f"/features/{fid}/vote")
        assert _vote_exists(fid, 1), "Vote row must exist after first vote"
        auth_client.post(f"/features/{fid}/vote")
        assert not _vote_exists(
            fid, 1
        ), "Toggle-off must remove the feature_votes row for this user"

    def test_third_vote_re_adds_vote(self, auth_client, second_user_id):
        """A third POST must re-cast the vote (voted=True again)."""
        fid = _insert_feature(
            second_user_id, title="Feature for re-vote on third POST check"
        )
        auth_client.post(f"/features/{fid}/vote")
        auth_client.post(f"/features/{fid}/vote")
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert (
            data["voted"] is True
        ), "Third vote must re-toggle the vote on (voted=true)"
        assert data["upvotes"] == 1, "Third vote must bring upvotes back to 1"


# ------------------------------------------------------------------ #
# 3. POST /features/<id>/vote — own request returns 403               #
# ------------------------------------------------------------------ #


class TestVoteOwnRequest:
    def test_vote_own_request_returns_403(self, auth_client):
        """The demo user (id=1) voting on their own request must be blocked."""
        fid = _insert_feature(1, title="Demo user owns this feature for self vote test")
        resp = auth_client.post(f"/features/{fid}/vote")
        assert (
            resp.status_code == 403
        ), "POST /features/<id>/vote on own request must return 403"

    def test_vote_own_request_does_not_insert_vote(self, auth_client):
        fid = _insert_feature(
            1, title="Own request DB guard test for self vote attempt"
        )
        auth_client.post(f"/features/{fid}/vote")
        assert not _vote_exists(
            fid, 1
        ), "Self-vote attempt must not insert a row into feature_votes"

    def test_vote_own_request_vote_count_stays_zero(self, auth_client):
        fid = _insert_feature(1, title="Own request vote count must remain zero test")
        auth_client.post(f"/features/{fid}/vote")
        assert (
            _count_votes(fid) == 0
        ), "Self-vote attempt must not change vote count from 0"


# ------------------------------------------------------------------ #
# 4. POST /features/<id>/vote — unauthenticated returns 401           #
# ------------------------------------------------------------------ #


class TestVoteUnauthenticated:
    def test_vote_without_session_returns_401(self, client):
        """Unauthenticated POST /features/<id>/vote must return 401, not redirect."""
        fid = _insert_feature(1, title="Feature for unauthenticated vote 401 test")
        resp = client.post(f"/features/{fid}/vote")
        assert (
            resp.status_code == 401
        ), "POST /features/<id>/vote without auth must return 401"

    def test_vote_without_session_is_not_302(self, client):
        """The 401 must not be a redirect — this is an AJAX endpoint."""
        fid = _insert_feature(
            1, title="Feature for unauthenticated vote not redirect test"
        )
        resp = client.post(f"/features/{fid}/vote")
        assert (
            resp.status_code != 302
        ), "Unauthenticated POST /features/<id>/vote must not redirect (401 not 302)"

    def test_vote_without_session_does_not_insert_row(self, client):
        fid = _insert_feature(
            1, title="Feature for unauthenticated vote no DB insert test"
        )
        client.post(f"/features/{fid}/vote")
        assert (
            _count_votes(fid) == 0
        ), "Unauthenticated vote attempt must not insert into feature_votes"


# ------------------------------------------------------------------ #
# 5. POST /features/<id>/vote — non-existent ID returns 404           #
# ------------------------------------------------------------------ #


class TestVoteNonExistentFeature:
    def test_vote_nonexistent_id_returns_404(self, auth_client):
        resp = auth_client.post("/features/99999/vote")
        assert (
            resp.status_code == 404
        ), "POST /features/99999/vote must return 404 for a non-existent feature"

    def test_vote_nonexistent_id_does_not_insert_row(self, auth_client):
        auth_client.post("/features/99999/vote")
        conn = sqlite3.connect(db_module.DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM feature_votes WHERE feature_id = ?", (99999,)
        ).fetchone()[0]
        conn.close()
        assert (
            count == 0
        ), "Vote attempt on non-existent ID must not insert any feature_votes row"


# ------------------------------------------------------------------ #
# 6. Multiple users voting — upvote count accumulates correctly       #
# ------------------------------------------------------------------ #


class TestMultipleUserVotes:
    def test_two_users_voting_gives_upvotes_2(self, client, second_user_id):
        """Two different users each casting one vote must produce upvotes=2."""
        fid = _insert_feature(
            1, title="Feature for multi-user vote count accuracy test"
        )

        # Vote as second user (not the owner)
        with client.session_transaction() as sess:
            sess["user_id"] = second_user_id
            sess["user_name"] = "Alice Smith"
        data_alice = json.loads(_body(client.post(f"/features/{fid}/vote")))
        assert data_alice["upvotes"] == 1, "After Alice votes, upvotes must be 1"

        # Add a third user who also votes
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Bob Jones", "bob@example.com", generate_password_hash("bobpass")),
        )
        conn.commit()
        bob_id = cursor.lastrowid
        conn.close()

        _insert_vote(fid, bob_id)
        db_count = _count_votes(fid)
        assert (
            db_count == 2
        ), "Two different users voting on the same request must yield 2 rows in feature_votes"

    def test_vote_count_unaffected_by_other_features(self, auth_client, second_user_id):
        """Votes on feature A must not bleed into the count for feature B."""
        fid_a = _insert_feature(
            second_user_id, title="Feature A for vote isolation test here"
        )
        fid_b = _insert_feature(
            second_user_id, title="Feature B for vote isolation test here"
        )

        auth_client.post(f"/features/{fid_a}/vote")

        data_b = json.loads(_body(auth_client.post(f"/features/{fid_b}/vote")))
        # fid_b starts at 0; after auth user votes it should be exactly 1, not 2
        assert (
            data_b["upvotes"] == 1
        ), "Voting on feature A must not affect the upvote count of feature B"


# ------------------------------------------------------------------ #
# 7. Trending sort — GET /features?sort=trending                      #
# ------------------------------------------------------------------ #


class TestTrendingSort:
    def test_trending_sort_returns_200(self, client):
        resp = client.get("/features?sort=trending")
        assert resp.status_code == 200, "GET /features?sort=trending must return 200"

    def test_trending_option_in_html(self, client):
        """The sort dropdown must include a 'Trending' option."""
        body = _body(client.get("/features"))
        assert (
            "Trending" in body
        ), "'Trending' option must appear in the sort controls HTML of GET /features"

    def test_trending_sort_value_in_html(self, client):
        """The HTML must include the sort value 'trending' in a select or link."""
        body = _body(client.get("/features"))
        assert "trending" in body, (
            "The string 'trending' must appear in the GET /features HTML "
            "(sort option value or href)"
        )

    def test_trending_sort_high_voted_new_ranks_above_low_voted_old(
        self, client, second_user_id
    ):
        """High-voted new request must rank above a low-voted old one.

        Score formula: (vote_count * 5) + views + MAX(0, 7 - days_since_created)

        Both requests are created 'now' (days_since_created ~ 0), so recency bonus
        is ~7 for each. The difference is in vote counts:
          - 'Trending High' gets 2 votes  -> score = (2*5) + 0 + ~7 = ~17
          - 'Trending Low'  gets 0 votes  -> score = (0*5) + 0 + ~7 = ~7
        """
        fid_low = _insert_feature(
            second_user_id, title="Trending Low vote feature sort test"
        )
        fid_high = _insert_feature(
            second_user_id, title="Trending High vote feature sort test"
        )

        # Give fid_high 2 votes using the helper (bypass route to avoid ownership rule)
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Voter One", "voter1@example.com", generate_password_hash("pass")),
        )
        conn.commit()
        voter1 = cursor.lastrowid
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Voter Two", "voter2@example.com", generate_password_hash("pass")),
        )
        conn.commit()
        voter2 = cursor.lastrowid
        conn.close()

        _insert_vote(fid_high, voter1)
        _insert_vote(fid_high, voter2)

        resp = client.get("/features?sort=trending")
        body = _body(resp)
        assert resp.status_code == 200, "sort=trending must return 200"

        pos_high = body.find("Trending High vote feature sort test")
        pos_low = body.find("Trending Low vote feature sort test")

        assert pos_high != -1, "High-voted feature must appear in trending listing"
        assert pos_low != -1, "Low-voted feature must appear in trending listing"
        assert (
            pos_high < pos_low
        ), "sort=trending: the high-voted request must appear before the low-voted request"

    def test_trending_sort_does_not_raise_500(self, client):
        fid = _insert_feature(1, title="Trending sort no server error test feature")
        resp = client.get("/features?sort=trending")
        assert resp.status_code != 500, "sort=trending must not produce a 500 error"

    def test_invalid_sort_falls_back_to_latest(self, client):
        """An unrecognised sort param must not crash the server (falls back to latest)."""
        resp = client.get("/features?sort=bogus_sort_value")
        assert (
            resp.status_code == 200
        ), "Invalid sort param must return 200 (fallback to latest)"
        assert (
            resp.status_code != 500
        ), "Invalid sort param must not produce a 500 error"


# ------------------------------------------------------------------ #
# 8. most_upvoted sort — high-vote feature appears first              #
# ------------------------------------------------------------------ #


class TestMostUpvotedSort:
    def test_most_upvoted_returns_200(self, client):
        resp = client.get("/features?sort=most_upvoted")
        assert (
            resp.status_code == 200
        ), "GET /features?sort=most_upvoted must return 200"

    def test_most_upvoted_orders_by_vote_count_desc(self, client, second_user_id):
        """Feature with more votes must appear before feature with fewer votes."""
        fid_low = _insert_feature(
            second_user_id, title="Most upvoted low vote count sort test"
        )
        fid_high = _insert_feature(
            second_user_id, title="Most upvoted high vote count sort test"
        )

        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Upvoter", "upvoter@example.com", generate_password_hash("pass")),
        )
        conn.commit()
        upvoter_id = cursor.lastrowid
        conn.close()

        _insert_vote(fid_high, upvoter_id)

        resp = client.get("/features?sort=most_upvoted")
        body = _body(resp)

        pos_high = body.find("Most upvoted high vote count sort test")
        pos_low = body.find("Most upvoted low vote count sort test")

        assert pos_high != -1, "High-vote feature must appear in the listing"
        assert pos_low != -1, "Low-vote feature must appear in the listing"
        assert (
            pos_high < pos_low
        ), "sort=most_upvoted: feature with more votes must appear before feature with fewer votes"


# ------------------------------------------------------------------ #
# 9. voted_ids pre-populates button state (fr-vote-btn--voted class)  #
# ------------------------------------------------------------------ #


class TestVotedIdsButtonState:
    def test_voted_request_has_voted_class_in_html(self, auth_client, second_user_id):
        """GET /features as a user who voted must include fr-vote-btn--voted on that card."""
        fid = _insert_feature(
            second_user_id, title="Feature to check voted button class HTML"
        )
        _insert_vote(fid, 1)  # demo user (id=1) has voted

        body = _body(auth_client.get("/features"))
        assert "fr-vote-btn--voted" in body, (
            "GET /features must include 'fr-vote-btn--voted' CSS class for cards the "
            "logged-in user has already voted on"
        )

    def test_unvoted_request_does_not_have_voted_class(
        self, auth_client, second_user_id
    ):
        """An unvoted request must not show the fr-vote-btn--voted class."""
        _insert_feature(second_user_id, title="Feature to check absence of voted class")
        # demo user has NOT voted on this feature

        body = _body(auth_client.get("/features"))
        # Check that no button element has the voted class as an HTML attribute.
        # We match the attribute form to avoid false positives from the JS source string.
        assert (
            'class="fr-vote-btn fr-vote-btn--voted"' not in body
        ), "GET /features must NOT include 'fr-vote-btn--voted' when the user has not voted"

    def test_voted_ids_not_populated_when_logged_out(self, client, second_user_id):
        """Logged-out users must never see the voted button state."""
        fid = _insert_feature(
            second_user_id, title="Feature to verify no voted class logged out"
        )
        # Simulate a vote that exists in DB but the visitor is not logged in
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Ghost", "ghost@example.com", generate_password_hash("pass")),
        )
        conn.commit()
        ghost_id = cursor.lastrowid
        conn.close()
        _insert_vote(fid, ghost_id)

        body = _body(client.get("/features"))
        # Check the HTML attribute form to avoid matching the JS source string literal.
        assert (
            'class="fr-vote-btn fr-vote-btn--voted"' not in body
        ), "Logged-out visitors must never see the fr-vote-btn--voted class"


# ------------------------------------------------------------------ #
# 10. data-voted and data-is-own attributes on card HTML              #
# ------------------------------------------------------------------ #


class TestCardDataAttributes:
    def test_data_voted_true_for_voted_request(self, auth_client, second_user_id):
        """A card the auth user has voted on must include data-voted='true' or data-voted='1'."""
        fid = _insert_feature(
            second_user_id, title="Feature for data-voted true attribute test"
        )
        _insert_vote(fid, 1)  # demo user has voted

        body = _body(auth_client.get("/features"))
        assert (
            'data-voted="true"' in body or 'data-voted="1"' in body
        ), "Card for a voted feature must include data-voted='true' (or '1') attribute"

    def test_data_is_own_true_for_own_request(self, auth_client):
        """The auth user's own request card must include data-is-own='true' or data-is-own='1'."""
        _insert_feature(1, title="Own request for data-is-own attribute test check")

        body = _body(auth_client.get("/features"))
        assert (
            'data-is-own="true"' in body or 'data-is-own="1"' in body
        ), "Own request card must include data-is-own='true' (or '1') attribute"

    def test_data_is_own_false_for_others_request(self, auth_client, second_user_id):
        """A card belonging to another user must have data-is-own='false' or '0'."""
        _insert_feature(
            second_user_id, title="Alice card for data-is-own false attribute test"
        )

        body = _body(auth_client.get("/features"))
        assert (
            'data-is-own="false"' in body or 'data-is-own="0"' in body
        ), "Another user's card must include data-is-own='false' (or '0') attribute"

    def test_data_voted_false_for_unvoted_request(self, auth_client, second_user_id):
        """An unvoted card must include data-voted='false' or data-voted='0'."""
        _insert_feature(
            second_user_id, title="Unvoted feature for data-voted false attribute"
        )

        body = _body(auth_client.get("/features"))
        assert (
            'data-voted="false"' in body or 'data-voted="0"' in body
        ), "Unvoted card must include data-voted='false' (or '0') attribute"


# ------------------------------------------------------------------ #
# 11. Cross-feature state isolation — voting A must not affect B     #
# ------------------------------------------------------------------ #


class TestCrossFeatureIsolation:
    def test_data_voted_false_on_feature_b_after_voting_feature_a(
        self, auth_client, second_user_id
    ):
        """Voting on feature A must not set data-voted='true' on feature B's card.

        This is the server-side invariant that guards the modal bug: when the page
        is loaded fresh after voting, each card's data-voted must only reflect
        whether the current user voted on *that* feature, not any other.
        """
        fid_a = _insert_feature(
            second_user_id, title="Cross isolation voted feature A card test"
        )
        fid_b = _insert_feature(
            second_user_id, title="Cross isolation unvoted feature B card test"
        )
        _insert_vote(fid_a, 1)  # demo user voted on A only

        body = _body(auth_client.get("/features"))

        # Find positions of the two card titles and their nearby data-voted values
        import re

        # Extract all data-voted values paired with their feature id from data-id attribute
        cards = re.findall(
            r'data-id="(\d+)"[^>]*data-voted="(true|false)"'
            r'|data-id="(\d+)"[^>]*>.*?data-voted="(true|false)"',
            body,
        )
        # Simpler: just check that data-voted="true" appears exactly once
        # (only for fid_a) and data-voted="false" appears for fid_b
        true_count = body.count('data-voted="true"')
        assert true_count == 1, (
            "Exactly one card must have data-voted='true' when only one feature was voted on; "
            f"found {true_count}"
        )

    def test_vote_json_upvotes_is_per_feature(self, auth_client, second_user_id):
        """Voting on feature A then feature B must return independent upvote counts.

        The JSON for feature B's vote must return upvotes=1, not 2. This directly
        tests the query that guards against cross-feature vote count contamination.
        """
        fid_a = _insert_feature(
            second_user_id, title="Cross isolation vote count feature A test"
        )
        fid_b = _insert_feature(
            second_user_id, title="Cross isolation vote count feature B test"
        )
        auth_client.post(f"/features/{fid_a}/vote")  # vote on A first
        data_b = json.loads(_body(auth_client.post(f"/features/{fid_b}/vote")))
        assert data_b["upvotes"] == 1, (
            "Voting on feature B after voting on feature A must return upvotes=1 for B, "
            f"not the combined total; got {data_b['upvotes']}"
        )

    def test_data_vote_count_attribute_matches_actual_vote_count(
        self, auth_client, second_user_id
    ):
        """The data-vote-count attribute on each card must equal the real vote count.

        This is the attribute read by openModal to populate the modal's vote count.
        If it is wrong, the modal displays a stale count even before any JS interaction.
        """
        fid = _insert_feature(
            second_user_id, title="Vote count attribute accuracy test feature"
        )
        # Give it 2 pre-seeded votes from two extra users
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        for name, email in [("V1", "v1@x.com"), ("V2", "v2@x.com")]:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash("pass")),
            )
            conn.commit()
            _insert_vote(fid, cursor.lastrowid)
        conn.close()

        body = _body(auth_client.get("/features"))
        assert f'data-vote-count="2"' in body, (
            "Card with 2 votes must render data-vote-count='2'; "
            "modal reads this attribute to display the initial vote count"
        )

    def test_data_voted_only_true_for_voted_feature_not_unvoted_neighbour(
        self, auth_client, second_user_id
    ):
        """An unvoted card must have data-voted='false' even when an adjacent voted
        card exists on the same page.

        Simulates the exact UAT scenario: vote on feature A, then open the modal
        for feature B — B's modal must show unvoted state. The server must render
        B's card with data-voted='false' so openModal reads the correct initial state.
        """
        import re

        fid_a = _insert_feature(
            second_user_id, title="Adjacent voted neighbour test feature A"
        )
        fid_b = _insert_feature(
            second_user_id, title="Adjacent unvoted neighbour test feature B"
        )
        _insert_vote(fid_a, 1)  # only voted on A

        body = _body(auth_client.get("/features"))

        # Extract the data-voted value from the card whose data-id matches fid_b.
        # Each card opens with <div class="fr-card" data-id="N" ... data-voted="X" ...>
        # We find the opening tag for fid_b and read its data-voted attribute.
        pattern = rf'data-id="{fid_b}"[^>]*data-voted="(true|false)"'
        match = re.search(pattern, body)
        assert match is not None, (
            f"Could not find a card with data-id='{fid_b}' and a data-voted attribute. "
            "The card may not be rendering the data-voted attribute at all."
        )
        assert match.group(1) == "false", (
            f"Feature B's card must have data-voted='false' even though adjacent "
            f"feature A was voted on; found data-voted='{match.group(1)}'"
        )


# ------------------------------------------------------------------ #
# 12. _insert_vote helper correctness (unit-level)                    #
# ------------------------------------------------------------------ #


class TestInsertVoteHelper:
    def test_insert_vote_creates_row(self):
        """_insert_vote must write exactly one row per unique (feature_id, user_id) pair."""
        # Bootstrap a minimal DB in a throw-away tmp path
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp:
            old_path = db_module.DB_PATH
            db_module.DB_PATH = os.path.join(tmp, "helper_test.db")
            try:
                init_db()
                seed_db()
                fid = _insert_feature(
                    1, title="Helper test feature for insert vote unit test"
                )
                assert _count_votes(fid) == 0, "No votes before _insert_vote"
                _insert_vote(fid, 1)
                assert (
                    _count_votes(fid) == 1
                ), "_insert_vote must create exactly one row"
            finally:
                db_module.DB_PATH = old_path

    def test_insert_vote_idempotent(self):
        """Calling _insert_vote twice for the same pair must not raise or double-insert."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp:
            old_path = db_module.DB_PATH
            db_module.DB_PATH = os.path.join(tmp, "helper_idempotent.db")
            try:
                init_db()
                seed_db()
                fid = _insert_feature(
                    1, title="Helper idempotent feature for insert vote test"
                )
                _insert_vote(fid, 1)
                _insert_vote(fid, 1)  # second call must be a no-op
                assert (
                    _count_votes(fid) == 1
                ), "_insert_vote called twice must not create duplicate rows (UNIQUE constraint)"
            finally:
                db_module.DB_PATH = old_path


# ------------------------------------------------------------------ #
# 12. Vote count accuracy — upvotes vs DB after pre-seeded votes      #
# ------------------------------------------------------------------ #


class TestVoteCountAccuracy:
    def test_vote_count_reflects_pre_seeded_votes(self, auth_client, second_user_id):
        """If a vote is already in the DB via _insert_vote, the route must count it."""
        fid = _insert_feature(
            second_user_id, title="Pre-seeded vote count accuracy test"
        )

        # Pre-seed one vote from a third user so the DB already has 1 vote
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Pre Voter", "prevote@example.com", generate_password_hash("pass")),
        )
        conn.commit()
        pre_voter_id = cursor.lastrowid
        conn.close()
        _insert_vote(fid, pre_voter_id)

        # auth user (id=1) now votes — should bump to 2
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))
        assert (
            data["upvotes"] == 2
        ), "upvotes in JSON must count all votes including pre-seeded ones"
        assert (
            data["voted"] is True
        ), "voted must be True for the current user's first vote"

    def test_toggle_off_preserves_other_users_votes(self, auth_client, second_user_id):
        """Toggling off auth user's vote must not affect other users' votes."""
        fid = _insert_feature(
            second_user_id, title="Toggle off preserves other votes test"
        )
        _insert_vote(fid, second_user_id)  # second user has voted on this

        # auth user votes then un-votes
        auth_client.post(f"/features/{fid}/vote")
        data = json.loads(_body(auth_client.post(f"/features/{fid}/vote")))

        assert (
            data["upvotes"] == 1
        ), "Toggle-off must only remove auth user's vote; other users' votes must remain counted"
        assert (
            data["voted"] is False
        ), "voted must be False after auth user's toggle-off"
