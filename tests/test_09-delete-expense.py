"""Step 9 — Delete Expense: POST /expenses/<id>/delete route + delete_expense query helper.

Strategy: monkeypatch database.db.DB_PATH to a fresh tmp file, seed the demo
user so foreign-key references resolve, reload app so its module-level
init_db/seed_db hits the patched path.  Route tests drive Flask's test client;
unit tests call database.queries.delete_expense directly against the same
patched DB.

Fixture hierarchy:
  client        — Flask test client backed by a fresh seeded tmp DB
  auth_client   — client with the demo user (id=1) already in session
  demo_user_id  — integer PK of the seeded demo user (always 1 after seed_db)

Seed data:
  seed_db() inserts 8 expense rows for user 1.  Tests that need a known
  expense id query the DB for the first row (lowest id) belonging to user 1.
  Tests requiring a second user insert one directly via sqlite3.

Spec behaviours covered
-----------------------
1. Auth guard: unauthenticated POST redirects to /login (302)
2. Method guard: GET returns 405
3. Happy path: POST for own expense → 302 to /profile + flash "Expense deleted."
4. DB side effect: row is gone after successful delete
5. Ownership: POST for another user's expense is a silent no-op; row survives
6. Non-existent id: POST is a silent no-op; 302 to /profile, no crash
"""

import importlib
import sqlite3

import pytest

import database.db as db_module
from database.db import init_db, seed_db
from database.queries import delete_expense

# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by a fresh seeded tmp DB.

    Follows the established pattern: patch DB_PATH first, initialise schema,
    seed demo data, then reload app so its module-level init_db/seed_db calls
    hit the tmp DB.
    """
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
def demo_user_id():
    """Integer PK of the seeded demo user (always 1 after seed_db)."""
    return 1


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _body(response):
    return response.get_data(as_text=True)


def _get_conn(db_path):
    """Return an open sqlite3 connection with Row factory and FK enforcement."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _first_expense_id(db_path, user_id):
    """Return the lowest expense id for *user_id* (oldest seeded row)."""
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT id FROM expenses WHERE user_id = ? ORDER BY id ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    assert row is not None, "No expenses found for user — seed_db may have failed"
    return row["id"]


def _get_expense_row(db_path, expense_id):
    """Fetch the raw DB row for *expense_id*, or None if it doesn't exist."""
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    conn.close()
    return row


def _expense_count(db_path, user_id=None):
    """Return the total expense row count.  If user_id given, scope to that user."""
    conn = _get_conn(db_path)
    if user_id is not None:
        count = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    else:
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    return count


def _insert_second_user(db_path):
    """Insert a second user and one expense for them; return (user_id, expense_id)."""
    from werkzeug.security import generate_password_hash

    conn = _get_conn(db_path)
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@spendly.com", generate_password_hash("other123")),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, 55.0, "Bills", "2026-04-15", "Other user expense"),
    )
    conn.commit()
    expense_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return user_id, expense_id


def _make_app_client(tmp_path, db_name, monkeypatch):
    """Helper: patch DB_PATH, init/seed, reload app, return (test_client, db_path)."""
    db_path = str(tmp_path / db_name)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    init_db()
    seed_db()

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    return app_module.app.test_client(), db_path


# ------------------------------------------------------------------ #
# 1. Unit tests — delete_expense query helper                         #
# ------------------------------------------------------------------ #


class TestDeleteExpenseQueryHelper:
    """Direct unit tests for database.queries.delete_expense."""

    def test_correct_user_id_removes_row_from_db(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """delete_expense with the correct user_id must delete the row from the DB."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_del.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit_del.db"), demo_user_id)

        delete_expense(expense_id, demo_user_id)

        row = _get_expense_row(str(tmp_path / "unit_del.db"), expense_id)
        assert (
            row is None
        ), "delete_expense with correct user_id must remove the row from the DB"

    def test_correct_user_id_decrements_row_count(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """delete_expense with the correct user_id must reduce the total row count by 1."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_cnt.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit_cnt.db"), demo_user_id)
        before = _expense_count(str(tmp_path / "unit_cnt.db"), demo_user_id)

        delete_expense(expense_id, demo_user_id)

        after = _expense_count(str(tmp_path / "unit_cnt.db"), demo_user_id)
        assert (
            after == before - 1
        ), "delete_expense with correct user_id must reduce the expense count by exactly 1"

    def test_wrong_user_id_leaves_row_in_db(self, tmp_path, monkeypatch, demo_user_id):
        """delete_expense with a wrong user_id must leave the target row untouched."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_wrong.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit_wrong.db"), demo_user_id)
        wrong_user_id = demo_user_id + 999

        delete_expense(expense_id, wrong_user_id)

        row = _get_expense_row(str(tmp_path / "unit_wrong.db"), expense_id)
        assert (
            row is not None
        ), "delete_expense with wrong user_id must NOT delete the row from the DB"

    def test_wrong_user_id_leaves_row_count_unchanged(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """delete_expense with a wrong user_id must not change the total row count."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_wrcnt.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit_wrcnt.db"), demo_user_id)
        wrong_user_id = demo_user_id + 999
        before = _expense_count(str(tmp_path / "unit_wrcnt.db"))

        delete_expense(expense_id, wrong_user_id)

        after = _expense_count(str(tmp_path / "unit_wrcnt.db"))
        assert (
            after == before
        ), "delete_expense with wrong user_id must not change the total expense row count"

    def test_wrong_user_id_does_not_raise(self, tmp_path, monkeypatch, demo_user_id):
        """delete_expense with a wrong user_id must be a silent no-op — no exception raised."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_noraise.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit_noraise.db"), demo_user_id)
        wrong_user_id = demo_user_id + 999

        try:
            delete_expense(expense_id, wrong_user_id)
        except Exception as exc:
            pytest.fail(
                f"delete_expense with wrong user_id raised an unexpected exception: {exc}"
            )

    def test_nonexistent_expense_id_does_not_raise(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """delete_expense for a non-existent expense_id must not raise any exception."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_noexp.db"))
        init_db()
        seed_db()

        try:
            delete_expense(99999, demo_user_id)
        except Exception as exc:
            pytest.fail(
                f"delete_expense with non-existent expense_id raised an unexpected exception: {exc}"
            )

    def test_nonexistent_expense_id_leaves_row_count_unchanged(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """delete_expense for a non-existent id must not alter the DB row count."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit_noexp_cnt.db"))
        init_db()
        seed_db()

        before = _expense_count(str(tmp_path / "unit_noexp_cnt.db"))
        delete_expense(99999, demo_user_id)
        after = _expense_count(str(tmp_path / "unit_noexp_cnt.db"))

        assert (
            after == before
        ), "delete_expense for a non-existent id must not change the expense row count"


# ------------------------------------------------------------------ #
# 2. Auth guard — unauthenticated POST                                #
# ------------------------------------------------------------------ #


class TestDeleteExpenseUnauthenticated:
    """POST /expenses/<id>/delete without a session must redirect to /login."""

    def test_unauthenticated_post_returns_302(self, client):
        resp = client.post("/expenses/1/delete")
        assert (
            resp.status_code == 302
        ), "POST /expenses/<id>/delete without auth must redirect (302)"

    def test_unauthenticated_post_redirects_to_login(self, client):
        resp = client.post("/expenses/1/delete")
        assert (
            "/login" in resp.headers["Location"]
        ), "Unauthenticated POST /expenses/<id>/delete must redirect to /login"

    def test_unauthenticated_post_following_redirect_shows_login_page(self, client):
        resp = client.post("/expenses/1/delete", follow_redirects=True)
        assert (
            resp.status_code == 200
        ), "Following unauthenticated redirect must yield 200"
        body = _body(resp)
        assert (
            "login" in body.lower()
        ), "Unauthenticated redirect must land on the login page"


# ------------------------------------------------------------------ #
# 3. Method guard — GET returns 405                                   #
# ------------------------------------------------------------------ #


class TestDeleteExpenseMethodNotAllowed:
    """The route only accepts POST; a GET must return 405."""

    def test_get_returns_405_unauthenticated(self, client):
        resp = client.get("/expenses/1/delete")
        assert (
            resp.status_code == 405
        ), "GET /expenses/<id>/delete must return 405 Method Not Allowed"

    def test_get_returns_405_authenticated(self, tmp_path, monkeypatch, demo_user_id):
        """Even when logged in, a GET to the delete route must be 405."""
        c, db_path = _make_app_client(tmp_path, "get_405.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.get(f"/expenses/{expense_id}/delete")

        assert (
            resp.status_code == 405
        ), "Authenticated GET /expenses/<id>/delete must return 405"

    def test_get_does_not_delete_row(self, tmp_path, monkeypatch, demo_user_id):
        """A GET request must not trigger any deletion — row count must stay the same."""
        c, db_path = _make_app_client(tmp_path, "get_nodelete.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)
        before = _expense_count(db_path)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.get(f"/expenses/{expense_id}/delete")

        after = _expense_count(db_path)
        assert (
            after == before
        ), "A GET request to the delete route must not remove any rows from the DB"


# ------------------------------------------------------------------ #
# 4. Happy path — authenticated, own expense                          #
# ------------------------------------------------------------------ #


class TestDeleteExpenseHappyPath:
    """POST /expenses/<id>/delete for a valid owned expense."""

    def test_returns_302(self, tmp_path, monkeypatch, demo_user_id):
        c, db_path = _make_app_client(tmp_path, "happy_302.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{expense_id}/delete")

        assert (
            resp.status_code == 302
        ), "Successful POST /expenses/<id>/delete must redirect (302)"

    def test_redirects_to_profile(self, tmp_path, monkeypatch, demo_user_id):
        c, db_path = _make_app_client(tmp_path, "happy_redir.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{expense_id}/delete")

        assert (
            "/profile" in resp.headers["Location"]
        ), "Successful delete must redirect to /profile"

    def test_following_redirect_lands_on_profile_200(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        c, db_path = _make_app_client(tmp_path, "happy_follow.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)

        assert resp.status_code == 200, "Following redirect after delete must yield 200"

    def test_flash_message_expense_deleted_appears(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The flash message 'Expense deleted.' must appear on the redirected page."""
        c, db_path = _make_app_client(tmp_path, "happy_flash.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)

        body = _body(resp)
        assert (
            "Expense deleted" in body
        ), "Flash message 'Expense deleted.' must appear on the profile page after deletion"

    def test_db_row_no_longer_exists_after_delete(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The deleted expense row must not exist in the DB after a successful POST."""
        c, db_path = _make_app_client(tmp_path, "happy_db_gone.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{expense_id}/delete")

        row = _get_expense_row(db_path, expense_id)
        assert (
            row is None
        ), "The deleted expense row must not exist in the DB after a successful delete"

    def test_db_row_count_decreases_by_one(self, tmp_path, monkeypatch, demo_user_id):
        """The total expense count for the user must drop by exactly 1."""
        c, db_path = _make_app_client(tmp_path, "happy_cnt.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)
        before = _expense_count(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{expense_id}/delete")

        after = _expense_count(db_path, demo_user_id)
        assert (
            after == before - 1
        ), "Successful delete must reduce the user's expense count by exactly 1"

    def test_other_rows_unaffected(self, tmp_path, monkeypatch, demo_user_id):
        """Only the targeted row must be deleted; all other rows must remain."""
        c, db_path = _make_app_client(tmp_path, "happy_others.db", monkeypatch)

        # collect ALL expense ids for demo user
        conn = _get_conn(db_path)
        all_ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM expenses WHERE user_id = ? ORDER BY id",
                (demo_user_id,),
            ).fetchall()
        ]
        conn.close()

        # delete only the first one
        target_id = all_ids[0]
        remaining_ids = all_ids[1:]

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{target_id}/delete")

        for eid in remaining_ids:
            row = _get_expense_row(db_path, eid)
            assert (
                row is not None
            ), f"Expense id={eid} must still exist in the DB after deleting id={target_id}"


# ------------------------------------------------------------------ #
# 5. Ownership enforcement — another user's expense                   #
# ------------------------------------------------------------------ #


class TestDeleteExpenseOwnershipEnforcement:
    """POST /expenses/<other_id>/delete must be a silent no-op for the current user."""

    def test_returns_302_for_other_users_expense(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The response must still be a redirect — no error page, no 403."""
        c, db_path = _make_app_client(tmp_path, "own_302.db", monkeypatch)
        _, other_expense_id = _insert_second_user(db_path)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{other_expense_id}/delete")

        assert (
            resp.status_code == 302
        ), "POST for another user's expense must still return 302 (silent no-op)"

    def test_redirects_to_profile_for_other_users_expense(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        c, db_path = _make_app_client(tmp_path, "own_redir.db", monkeypatch)
        _, other_expense_id = _insert_second_user(db_path)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{other_expense_id}/delete")

        assert (
            "/profile" in resp.headers["Location"]
        ), "POST for another user's expense must redirect to /profile"

    def test_other_users_row_still_exists_in_db(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The other user's expense row must NOT be deleted."""
        c, db_path = _make_app_client(tmp_path, "own_rowexists.db", monkeypatch)
        _, other_expense_id = _insert_second_user(db_path)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{other_expense_id}/delete")

        row = _get_expense_row(db_path, other_expense_id)
        assert (
            row is not None
        ), "Posting to delete another user's expense must leave that row intact in the DB"

    def test_total_count_unchanged_after_ownership_block(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """No rows at all must be deleted when the ownership check blocks the operation."""
        c, db_path = _make_app_client(tmp_path, "own_totalcnt.db", monkeypatch)
        _insert_second_user(db_path)
        before = _expense_count(db_path)

        # demo user tries to delete some high id that belongs to the other user
        conn = _get_conn(db_path)
        other_row = conn.execute(
            "SELECT id FROM expenses WHERE user_id != ? LIMIT 1",
            (demo_user_id,),
        ).fetchone()
        conn.close()
        other_expense_id = other_row["id"]

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{other_expense_id}/delete")

        after = _expense_count(db_path)
        assert (
            after == before
        ), "Total expense count must be unchanged when ownership enforcement blocks deletion"

    def test_own_rows_also_unaffected_by_ownership_block(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The demo user's own rows must also remain untouched after a blocked delete."""
        c, db_path = _make_app_client(tmp_path, "own_ownrows.db", monkeypatch)
        _, other_expense_id = _insert_second_user(db_path)
        own_count_before = _expense_count(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{other_expense_id}/delete")

        own_count_after = _expense_count(db_path, demo_user_id)
        assert (
            own_count_after == own_count_before
        ), "The logged-in user's own expense count must be unchanged after a blocked delete"


# ------------------------------------------------------------------ #
# 6. Non-existent expense id                                          #
# ------------------------------------------------------------------ #


class TestDeleteExpenseNonExistent:
    """POST for an id that doesn't exist must be a silent no-op."""

    def test_nonexistent_id_returns_302(self, auth_client):
        resp = auth_client.post("/expenses/99999/delete")
        assert (
            resp.status_code == 302
        ), "POST /expenses/99999/delete for a non-existent id must redirect (302)"

    def test_nonexistent_id_redirects_to_profile(self, auth_client):
        resp = auth_client.post("/expenses/99999/delete")
        assert (
            "/profile" in resp.headers["Location"]
        ), "POST for a non-existent expense id must redirect to /profile"

    def test_nonexistent_id_does_not_return_500(self, auth_client):
        resp = auth_client.post("/expenses/99999/delete")
        assert (
            resp.status_code != 500
        ), "POST for a non-existent expense id must not return a 500 error"

    def test_nonexistent_id_does_not_crash_app(self, auth_client):
        """Following the redirect must still yield a 200 from the profile page."""
        resp = auth_client.post("/expenses/99999/delete", follow_redirects=True)
        assert (
            resp.status_code == 200
        ), "App must continue serving requests normally after a delete of a non-existent id"

    def test_nonexistent_id_leaves_row_count_unchanged(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        c, db_path = _make_app_client(tmp_path, "noexp_cnt.db", monkeypatch)
        before = _expense_count(db_path)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post("/expenses/99999/delete")

        after = _expense_count(db_path)
        assert (
            after == before
        ), "Deleting a non-existent expense must not change the DB row count"

    def test_very_large_nonexistent_id_is_handled(self, auth_client):
        """A very large integer id that doesn't exist must also be a silent no-op."""
        resp = auth_client.post("/expenses/2147483647/delete")
        assert resp.status_code in (
            302,
            404,
        ), "A very large non-existent expense id must not crash the server"
        assert (
            resp.status_code != 500
        ), "Very large non-existent id must not produce a 500 error"


# ------------------------------------------------------------------ #
# 7. Profile page — delete button presence                            #
# ------------------------------------------------------------------ #


class TestDeleteButtonOnProfilePage:
    """The profile page must render a Delete form button for each transaction row."""

    def test_delete_form_present_on_profile(self, tmp_path, monkeypatch, demo_user_id):
        """The profile page must contain at least one POST form pointing to .../delete."""
        c, db_path = _make_app_client(tmp_path, "btn_form.db", monkeypatch)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(client.get("/profile"))

        assert (
            "delete" in body.lower()
        ), "Profile page must contain a delete action for expenses"

    def test_delete_form_uses_post_method(self, tmp_path, monkeypatch, demo_user_id):
        """The delete trigger on the profile page must be a POST form, not a plain link."""
        c, db_path = _make_app_client(tmp_path, "btn_post.db", monkeypatch)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(client.get("/profile"))

        # The page must have a <form ... method="POST"> that points to a delete URL.
        # Both "method=\"POST\"" and "method='POST'" (case-insensitive) are acceptable.
        assert (
            "method" in body.lower() and "post" in body.lower()
        ), "Profile page must include a form with method=POST for the delete action"
        assert (
            "/delete" in body
        ), "Profile page must include a form action pointing to a /delete route"

    def test_delete_route_url_in_profile_body(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Each transaction row's delete URL must appear in the profile HTML."""
        c, db_path = _make_app_client(tmp_path, "btn_url.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(client.get("/profile"))

        assert (
            f"/expenses/{expense_id}/delete" in body
        ), f"Profile page must contain the delete URL /expenses/{expense_id}/delete"


# ------------------------------------------------------------------ #
# 8. Edge cases                                                        #
# ------------------------------------------------------------------ #


class TestDeleteExpenseEdgeCases:
    """Miscellaneous robustness checks."""

    def test_delete_does_not_return_500_for_own_expense(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        c, db_path = _make_app_client(tmp_path, "edge_no500.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = client.post(f"/expenses/{expense_id}/delete")

        assert (
            resp.status_code != 500
        ), "Successful delete must not trigger an internal server error"

    def test_double_delete_is_safe(self, tmp_path, monkeypatch, demo_user_id):
        """Deleting the same expense twice must not crash the server."""
        c, db_path = _make_app_client(tmp_path, "edge_double.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            first = client.post(f"/expenses/{expense_id}/delete")
            second = client.post(f"/expenses/{expense_id}/delete")

        assert first.status_code == 302, "First delete must redirect (302)"
        assert second.status_code in (
            302,
            404,
        ), "Second delete of an already-deleted expense must not crash (302 or 404)"
        assert second.status_code != 500, "Double-delete must not produce a 500 error"

    def test_delete_only_own_expense_not_all_expenses(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Deleting one expense must not wipe out all expenses for the user."""
        c, db_path = _make_app_client(tmp_path, "edge_oneonly.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)
        total_before = _expense_count(db_path, demo_user_id)

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{expense_id}/delete")

        total_after = _expense_count(db_path, demo_user_id)
        # seed_db inserts 8 rows; after one delete 7 must remain
        assert (
            total_after == total_before - 1
        ), "Deleting one expense must remove exactly one row, not all expenses"
        assert total_after > 0, "Other expenses must still exist after a single delete"

    def test_delete_does_not_affect_users_table(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Deleting an expense must not alter the users table row count."""
        c, db_path = _make_app_client(tmp_path, "edge_users.db", monkeypatch)
        expense_id = _first_expense_id(db_path, demo_user_id)

        conn = _get_conn(db_path)
        users_before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        with c as client:
            with client.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            client.post(f"/expenses/{expense_id}/delete")

        conn = _get_conn(db_path)
        users_after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        assert (
            users_after == users_before
        ), "Deleting an expense must not change the users table row count"

    @pytest.mark.parametrize("bad_id", [99999, 0, 2147483647])
    def test_parametrized_nonexistent_ids_return_302_or_404(self, bad_id, auth_client):
        """Various non-existent ids must all result in a non-500 redirect."""
        resp = auth_client.post(f"/expenses/{bad_id}/delete")
        assert (
            resp.status_code != 500
        ), f"Non-existent expense id={bad_id} must not produce a 500 error"
        assert resp.status_code in (
            302,
            404,
        ), f"Non-existent expense id={bad_id} must return 302 or 404, not {resp.status_code}"
