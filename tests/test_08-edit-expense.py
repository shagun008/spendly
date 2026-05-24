"""Step 8 — Edit Expense: /expenses/<id>/edit route tests + query helper unit tests.

Strategy: monkeypatch database.db.DB_PATH to a fresh tmp file, seed the demo
user so foreign-key references resolve, reload app so the module-level
init_db/seed_db hits the patched path. Route tests drive Flask's test client;
unit tests call database.queries helpers directly against the same patched DB.

Fixture hierarchy:
  client        — Flask test client backed by a fresh seeded tmp DB
  auth_client   — client with the demo user (id=1) already in session
  demo_user_id  — integer PK of the seeded demo user (always 1 after seed_db)

Seed data:
  seed_db() inserts 8 expense rows for user 1.  Tests that need a known
  expense id query the DB for the first row (lowest id) belonging to user 1.
  Tests requiring a second user insert one directly via sqlite3.
"""

import importlib
import sqlite3

import pytest

import database.db as db_module
from database.db import init_db, seed_db
from database.queries import get_expense_by_id, update_expense

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

# A valid POST payload used as the baseline for most route tests.
VALID_POST_DATA = {
    "amount": "99.99",
    "category": "Transport",
    "date": "2026-05-01",
    "description": "Edited expense",
}


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
    """Integer PK of the seeded demo user. seed_db always inserts one user
    first, so AUTOINCREMENT gives id=1."""
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
    """Fetch the raw DB row for *expense_id*."""
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    conn.close()
    return row


def _insert_second_user(db_path):
    """Insert a second user and one expense for them; return (user_id, expense_id)."""
    conn = _get_conn(db_path)
    from werkzeug.security import generate_password_hash

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


# ------------------------------------------------------------------ #
# 1. Unit tests — get_expense_by_id                                   #
# ------------------------------------------------------------------ #


class TestGetExpenseById:
    """Direct unit tests for database.queries.get_expense_by_id."""

    def test_correct_user_id_returns_matching_dict(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """get_expense_by_id with correct expense_id and correct user_id must
        return a dict-like object whose fields match the seeded row."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        result = get_expense_by_id(expense_id, demo_user_id)

        assert (
            result is not None
        ), "get_expense_by_id must return a dict for a valid expense_id owned by the user"
        assert result["id"] == expense_id, "Returned dict must have the correct id"

    def test_correct_user_id_returns_correct_amount(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Returned dict must include the correct amount."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        raw = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        result = get_expense_by_id(expense_id, demo_user_id)

        assert (
            result["amount"] == raw["amount"]
        ), "Returned amount must match the DB row"

    def test_correct_user_id_returns_correct_category(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Returned dict must include the correct category."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        raw = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        result = get_expense_by_id(expense_id, demo_user_id)

        assert (
            result["category"] == raw["category"]
        ), "Returned category must match the DB row"

    def test_correct_user_id_returns_correct_date(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Returned dict must include the correct date."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        raw = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        result = get_expense_by_id(expense_id, demo_user_id)

        assert result["date"] == raw["date"], "Returned date must match the DB row"

    def test_wrong_user_id_returns_none(self, tmp_path, monkeypatch, demo_user_id):
        """get_expense_by_id with wrong user_id must return None."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        wrong_user_id = demo_user_id + 999

        result = get_expense_by_id(expense_id, wrong_user_id)

        assert (
            result is None
        ), "get_expense_by_id must return None when user_id does not own the expense"

    def test_nonexistent_expense_id_returns_none(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """get_expense_by_id with a non-existent expense_id must return None."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        result = get_expense_by_id(99999, demo_user_id)

        assert (
            result is None
        ), "get_expense_by_id must return None for a non-existent expense_id"


# ------------------------------------------------------------------ #
# 2. Unit tests — update_expense                                       #
# ------------------------------------------------------------------ #


class TestUpdateExpense:
    """Direct unit tests for database.queries.update_expense."""

    def test_correct_user_id_updates_amount(self, tmp_path, monkeypatch, demo_user_id):
        """update_expense with correct user_id and new amount=99.0 must persist
        the updated amount in the DB row."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        update_expense(expense_id, demo_user_id, 99.0, "Food", "2026-04-01", "Updated")

        row = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        assert (
            row["amount"] == 99.0
        ), "DB row amount must be 99.0 after update_expense with correct user_id"

    def test_correct_user_id_updates_category(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """update_expense must persist the new category."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        update_expense(
            expense_id, demo_user_id, 99.0, "Health", "2026-04-01", "Updated"
        )

        row = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        assert (
            row["category"] == "Health"
        ), "DB row category must be 'Health' after update_expense with correct user_id"

    def test_correct_user_id_updates_date(self, tmp_path, monkeypatch, demo_user_id):
        """update_expense must persist the new date."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        update_expense(expense_id, demo_user_id, 99.0, "Food", "2026-05-10", "Updated")

        row = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        assert (
            row["date"] == "2026-05-10"
        ), "DB row date must be '2026-05-10' after update_expense with correct user_id"

    def test_correct_user_id_updates_description(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """update_expense must persist the new description."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        update_expense(expense_id, demo_user_id, 99.0, "Food", "2026-04-01", "New note")

        row = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        assert (
            row["description"] == "New note"
        ), "DB row description must be 'New note' after update_expense with correct user_id"

    def test_wrong_user_id_leaves_row_unchanged(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """update_expense with wrong user_id must not modify the DB row."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        original_row = _get_expense_row(str(tmp_path / "unit.db"), expense_id)

        wrong_user_id = demo_user_id + 999
        update_expense(
            expense_id, wrong_user_id, 99.0, "Health", "2026-05-10", "Attempted"
        )

        row_after = _get_expense_row(str(tmp_path / "unit.db"), expense_id)
        assert (
            row_after["amount"] == original_row["amount"]
        ), "DB row amount must be unchanged when update_expense is called with wrong user_id"
        assert (
            row_after["category"] == original_row["category"]
        ), "DB row category must be unchanged when update_expense is called with wrong user_id"
        assert (
            row_after["date"] == original_row["date"]
        ), "DB row date must be unchanged when update_expense is called with wrong user_id"

    def test_wrong_user_id_does_not_raise(self, tmp_path, monkeypatch, demo_user_id):
        """update_expense with wrong user_id must not raise any exception."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        expense_id = _first_expense_id(str(tmp_path / "unit.db"), demo_user_id)
        wrong_user_id = demo_user_id + 999

        try:
            update_expense(
                expense_id, wrong_user_id, 99.0, "Health", "2026-05-10", "Attempted"
            )
        except Exception as exc:
            pytest.fail(
                f"update_expense with wrong user_id raised an unexpected exception: {exc}"
            )


# ------------------------------------------------------------------ #
# 3. GET /expenses/<id>/edit — unauthenticated                        #
# ------------------------------------------------------------------ #


class TestGetEditExpenseUnauthenticated:
    def test_redirects_302(self, client):
        resp = client.get("/expenses/1/edit")
        assert (
            resp.status_code == 302
        ), "GET /expenses/<id>/edit without auth must redirect (302)"

    def test_redirect_target_is_login(self, client):
        resp = client.get("/expenses/1/edit")
        assert (
            "/login" in resp.headers["Location"]
        ), "Unauthenticated GET /expenses/<id>/edit must redirect to /login"

    def test_following_redirect_shows_login_page(self, client):
        resp = client.get("/expenses/1/edit", follow_redirects=True)
        assert resp.status_code == 200, "Following redirect must yield 200"
        body = _body(resp)
        assert (
            "login" in body.lower()
        ), "Unauthenticated redirect must land on the login page"


# ------------------------------------------------------------------ #
# 4. GET /expenses/<id>/edit — authenticated, own expense             #
# ------------------------------------------------------------------ #


class TestGetEditExpenseAuthenticated:
    def test_returns_200_for_own_expense(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_own.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_own.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.get(f"/expenses/{expense_id}/edit")

        assert (
            resp.status_code == 200
        ), "Authenticated GET for own expense must return 200"

    def test_form_contains_amount_field(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_form.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_form.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        assert (
            'name="amount"' in body or "name='amount'" in body
        ), "Edit form must contain an input named 'amount'"

    def test_form_prefilled_with_existing_amount(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The amount input must be pre-filled with the expense's current amount."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_prefill.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_prefill.db"), demo_user_id)
        raw = _get_expense_row(str(tmp_path / "get_prefill.db"), expense_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        # The amount value (e.g. "12.5") must appear somewhere in the rendered form.
        assert (
            str(raw["amount"]) in body or f"{raw['amount']:.2f}" in body
        ), "Edit form must be pre-filled with the current amount value"

    def test_form_prefilled_with_existing_date(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The date input must be pre-filled with the expense's current date."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_date.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_date.db"), demo_user_id)
        raw = _get_expense_row(str(tmp_path / "get_date.db"), expense_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        assert (
            raw["date"] in body
        ), "Edit form must be pre-filled with the current date value"

    def test_form_contains_category_select(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_cat.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_cat.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        assert (
            "<select" in body.lower()
        ), "Edit form must contain a <select> element for category"

    def test_correct_category_preselected(self, tmp_path, monkeypatch, demo_user_id):
        """The category matching the expense must be pre-selected in the dropdown."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_presel.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_presel.db"), demo_user_id)
        raw = _get_expense_row(str(tmp_path / "get_presel.db"), expense_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        # The current category must appear, and 'selected' must appear near it.
        assert (
            raw["category"] in body
        ), f"Current category '{raw['category']}' must appear in the edit form"
        assert (
            "selected" in body
        ), "A category option must carry the 'selected' attribute in the edit form"

    def test_all_seven_categories_present(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_allcat.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_allcat.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        for cat in VALID_CATEGORIES:
            assert (
                cat in body
            ), f"Category '{cat}' must appear as an option in the edit form"

    def test_cancel_link_to_profile_present(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_cancel.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_cancel.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        assert (
            "/profile" in body
        ), "Edit form page must contain a cancel/back link pointing to /profile"

    def test_form_uses_post_method(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_method.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_method.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.get(f"/expenses/{expense_id}/edit"))

        assert "<form" in body.lower(), "Response must contain a <form> element"
        assert "post" in body.lower(), "Form must specify POST method"


# ------------------------------------------------------------------ #
# 5. GET /expenses/<id>/edit — authenticated, other user's expense    #
# ------------------------------------------------------------------ #


class TestGetEditExpenseOtherUser:
    def test_other_users_expense_returns_404(self, tmp_path, monkeypatch, demo_user_id):
        """Attempting to GET the edit form for another user's expense must return 404."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_other.db"))
        init_db()
        seed_db()

        _, other_expense_id = _insert_second_user(str(tmp_path / "get_other.db"))

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.get(f"/expenses/{other_expense_id}/edit")

        assert (
            resp.status_code == 404
        ), "GET edit for another user's expense must return 404"


# ------------------------------------------------------------------ #
# 6. GET /expenses/<id>/edit — authenticated, non-existent id         #
# ------------------------------------------------------------------ #


class TestGetEditExpenseNonExistent:
    def test_nonexistent_expense_returns_404(self, auth_client):
        resp = auth_client.get("/expenses/99999/edit")
        assert (
            resp.status_code == 404
        ), "GET edit for a non-existent expense_id must return 404"


# ------------------------------------------------------------------ #
# 7. POST /expenses/<id>/edit — unauthenticated                       #
# ------------------------------------------------------------------ #


class TestPostEditExpenseUnauthenticated:
    def test_redirects_302(self, client):
        resp = client.post("/expenses/1/edit", data=VALID_POST_DATA)
        assert (
            resp.status_code == 302
        ), "POST /expenses/<id>/edit without auth must redirect (302)"

    def test_redirect_target_is_login(self, client):
        resp = client.post("/expenses/1/edit", data=VALID_POST_DATA)
        assert (
            "/login" in resp.headers["Location"]
        ), "Unauthenticated POST /expenses/<id>/edit must redirect to /login"


# ------------------------------------------------------------------ #
# 8. POST /expenses/<id>/edit — authenticated, valid data             #
# ------------------------------------------------------------------ #


class TestPostEditExpenseValidData:
    def test_redirects_to_profile(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "post_valid.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "post_valid.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(f"/expenses/{expense_id}/edit", data=VALID_POST_DATA)

        assert resp.status_code == 302, "Valid POST must redirect (302)"
        assert (
            "/profile" in resp.headers["Location"]
        ), "Successful POST /expenses/<id>/edit must redirect to /profile"

    def test_db_row_updated_after_valid_post(self, tmp_path, monkeypatch, demo_user_id):
        """After a valid POST the DB row must reflect all submitted values."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "post_db.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "post_db.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(f"/expenses/{expense_id}/edit", data=VALID_POST_DATA)

        row = _get_expense_row(str(tmp_path / "post_db.db"), expense_id)
        assert row["amount"] == float(
            VALID_POST_DATA["amount"]
        ), "DB row amount must match the submitted value after update"
        assert (
            row["category"] == VALID_POST_DATA["category"]
        ), "DB row category must match the submitted value after update"
        assert (
            row["date"] == VALID_POST_DATA["date"]
        ), "DB row date must match the submitted value after update"
        assert (
            row["description"] == VALID_POST_DATA["description"]
        ), "DB row description must match the submitted value after update"

    def test_row_count_unchanged_after_valid_post(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """A valid update must not create or delete rows — only modify the target row."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "post_count.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "post_count.db"), demo_user_id)

        conn = _get_conn(str(tmp_path / "post_count.db"))
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(f"/expenses/{expense_id}/edit", data=VALID_POST_DATA)

        conn = _get_conn(str(tmp_path / "post_count.db"))
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        assert (
            after == before
        ), "Row count must be unchanged after a valid expense update"


# ------------------------------------------------------------------ #
# 9. POST /expenses/<id>/edit — authenticated, other user's expense   #
# ------------------------------------------------------------------ #


class TestPostEditExpenseOtherUser:
    def test_other_users_expense_returns_404(self, tmp_path, monkeypatch, demo_user_id):
        """Attempting to POST to another user's expense edit endpoint must return 404."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "post_other.db"))
        init_db()
        seed_db()

        _, other_expense_id = _insert_second_user(str(tmp_path / "post_other.db"))

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(f"/expenses/{other_expense_id}/edit", data=VALID_POST_DATA)

        assert (
            resp.status_code == 404
        ), "POST edit for another user's expense must return 404"

    def test_other_users_expense_db_row_unchanged(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """A 404 response must leave the other user's DB row untouched."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "post_other_db.db"))
        init_db()
        seed_db()

        _, other_expense_id = _insert_second_user(str(tmp_path / "post_other_db.db"))
        original_row = _get_expense_row(
            str(tmp_path / "post_other_db.db"), other_expense_id
        )

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(f"/expenses/{other_expense_id}/edit", data=VALID_POST_DATA)

        row_after = _get_expense_row(
            str(tmp_path / "post_other_db.db"), other_expense_id
        )
        assert (
            row_after["amount"] == original_row["amount"]
        ), "Other user's row amount must be unchanged after a rejected POST"


# ------------------------------------------------------------------ #
# 10. POST /expenses/<id>/edit — amount validation failures           #
# ------------------------------------------------------------------ #


class TestPostEditExpenseAmountValidation:

    def test_missing_amount_returns_200(
        self, auth_client, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_miss.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_miss.db"), demo_user_id)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "amount"}

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(f"/expenses/{expense_id}/edit", data=data)

        assert resp.status_code == 200, "Missing amount must re-render form (200)"

    def test_missing_amount_shows_error(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_miss_err.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_miss_err.db"), demo_user_id)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "amount"}

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(c.post(f"/expenses/{expense_id}/edit", data=data))

        assert (
            "error" in body.lower() or "amount" in body.lower()
        ), "Missing amount must surface an error message in the re-rendered form"

    def test_zero_amount_returns_200(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_zero.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_zero.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, amount="0"),
            )

        assert resp.status_code == 200, "Amount=0 must re-render form (200)"

    def test_zero_amount_shows_error(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_zero_err.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_zero_err.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, amount="0"),
                )
            )

        assert (
            "error" in body.lower() or "amount" in body.lower()
        ), "Amount=0 must surface an error message"

    def test_zero_amount_does_not_update_db(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_zero_db.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_zero_db.db"), demo_user_id)
        original_amount = _get_expense_row(
            str(tmp_path / "amt_zero_db.db"), expense_id
        )["amount"]

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, amount="0"),
            )

        row = _get_expense_row(str(tmp_path / "amt_zero_db.db"), expense_id)
        assert (
            row["amount"] == original_amount
        ), "DB row amount must be unchanged when amount=0 is submitted"

    def test_non_numeric_amount_returns_200(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_str.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_str.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, amount="abc"),
            )

        assert resp.status_code == 200, "Non-numeric amount must re-render form (200)"

    def test_non_numeric_amount_shows_error(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "amt_str_err.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "amt_str_err.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, amount="abc"),
                )
            )

        assert (
            "error" in body.lower() or "amount" in body.lower()
        ), "Non-numeric amount must surface an error message"

    @pytest.mark.parametrize(
        "bad_amount", ["", "0", "-1", "-0.01", "abc", "None", "null"]
    )
    def test_parametrized_invalid_amounts_return_200(
        self, bad_amount, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(
            db_module, "DB_PATH", str(tmp_path / f"amt_param_{bad_amount}.db")
        )
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(
            str(tmp_path / f"amt_param_{bad_amount}.db"), demo_user_id
        )

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, amount=bad_amount),
            )

        assert (
            resp.status_code == 200
        ), f"Invalid amount '{bad_amount}' must re-render form (200), not redirect"


# ------------------------------------------------------------------ #
# 11. POST /expenses/<id>/edit — category validation failures         #
# ------------------------------------------------------------------ #


class TestPostEditExpenseCategoryValidation:

    def test_invalid_category_returns_200(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "cat_inv.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "cat_inv.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, category="Groceries"),
            )

        assert resp.status_code == 200, "Invalid category must re-render form (200)"

    def test_invalid_category_shows_error(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "cat_err.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "cat_err.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, category="Groceries"),
                )
            )

        assert (
            "error" in body.lower() or "category" in body.lower()
        ), "Invalid category must surface an error message"

    def test_invalid_category_does_not_redirect(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "cat_noredir.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "cat_noredir.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, category="Groceries"),
            )

        assert resp.status_code != 302, "Invalid category must not redirect"

    @pytest.mark.parametrize(
        "bad_category",
        [
            "Groceries",
            "food",
            "FOOD",
            "travel",
            "utilities",
            "",
            "'; DROP TABLE expenses; --",
        ],
    )
    def test_parametrized_invalid_categories_return_200(
        self, bad_category, tmp_path, monkeypatch, demo_user_id
    ):
        safe_name = (
            bad_category.replace(" ", "_").replace(";", "").replace("'", "")[:20]
        )
        monkeypatch.setattr(
            db_module, "DB_PATH", str(tmp_path / f"cat_p_{safe_name}.db")
        )
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(
            str(tmp_path / f"cat_p_{safe_name}.db"), demo_user_id
        )

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, category=bad_category),
            )

        assert (
            resp.status_code == 200
        ), f"Invalid category '{bad_category}' must re-render form (200), not redirect"


# ------------------------------------------------------------------ #
# 12. POST /expenses/<id>/edit — date validation failures             #
# ------------------------------------------------------------------ #


class TestPostEditExpenseDateValidation:

    def test_invalid_date_string_returns_200(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "date_inv.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "date_inv.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, date="not-a-date"),
            )

        assert resp.status_code == 200, "Invalid date must re-render form (200)"

    def test_invalid_date_string_shows_error(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "date_err.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "date_err.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, date="not-a-date"),
                )
            )

        assert (
            "error" in body.lower() or "date" in body.lower()
        ), "Invalid date must surface an error message"

    def test_invalid_date_does_not_redirect(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "date_noredir.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "date_noredir.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, date="not-a-date"),
            )

        assert resp.status_code != 302, "Invalid date must not redirect"

    def test_missing_date_returns_200(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "date_miss.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "date_miss.db"), demo_user_id)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "date"}

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(f"/expenses/{expense_id}/edit", data=data)

        assert resp.status_code == 200, "Missing date must re-render form (200)"

    def test_invalid_date_does_not_update_db(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "date_db.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "date_db.db"), demo_user_id)
        original_row = _get_expense_row(str(tmp_path / "date_db.db"), expense_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, date="not-a-date"),
            )

        row = _get_expense_row(str(tmp_path / "date_db.db"), expense_id)
        assert (
            row["date"] == original_row["date"]
        ), "DB row date must be unchanged when an invalid date is submitted"

    @pytest.mark.parametrize(
        "bad_date",
        [
            "not-a-date",
            "20260501",
            "05-01-2026",
            "2026/05/01",
            "2026-13-01",
            "2026-04-99",
            "",
            "yesterday",
        ],
    )
    def test_parametrized_invalid_dates_return_200(
        self, bad_date, tmp_path, monkeypatch, demo_user_id
    ):
        safe_name = bad_date.replace("/", "_").replace("-", "_")[:20]
        monkeypatch.setattr(
            db_module, "DB_PATH", str(tmp_path / f"date_p_{safe_name}.db")
        )
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(
            str(tmp_path / f"date_p_{safe_name}.db"), demo_user_id
        )

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, date=bad_date),
            )

        assert (
            resp.status_code == 200
        ), f"Invalid date '{bad_date}' must re-render form (200), not redirect"


# ------------------------------------------------------------------ #
# 13. POST /expenses/<id>/edit — no description (optional field)      #
# ------------------------------------------------------------------ #


class TestPostEditExpenseNoDescription:

    def test_no_description_redirects_to_profile(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Omitting description must still succeed and redirect to /profile."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "nodesc_redir.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "nodesc_redir.db"), demo_user_id)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(f"/expenses/{expense_id}/edit", data=data)

        assert resp.status_code == 302, "POST without description must redirect (302)"
        assert (
            "/profile" in resp.headers["Location"]
        ), "POST without description must redirect to /profile"

    def test_no_description_stores_null(self, tmp_path, monkeypatch, demo_user_id):
        """Row updated without description must have NULL in the description column."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "nodesc_null.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "nodesc_null.db"), demo_user_id)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(f"/expenses/{expense_id}/edit", data=data)

        row = _get_expense_row(str(tmp_path / "nodesc_null.db"), expense_id)
        assert (
            row["description"] is None
        ), "Row updated without description must have description=NULL in the DB"

    def test_empty_string_description_stores_null(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """An explicitly empty description string must also be stored as NULL."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "emptydesc_null.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(
            str(tmp_path / "emptydesc_null.db"), demo_user_id
        )

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, description=""),
            )

        row = _get_expense_row(str(tmp_path / "emptydesc_null.db"), expense_id)
        assert (
            row["description"] is None
        ), "Row updated with empty description string must have description=NULL in the DB"

    def test_whitespace_only_description_stores_null(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """A whitespace-only description must be stripped and stored as NULL."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "wsdesc_null.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "wsdesc_null.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, description="   "),
            )

        row = _get_expense_row(str(tmp_path / "wsdesc_null.db"), expense_id)
        assert (
            row["description"] is None
        ), "Whitespace-only description must be stored as NULL after strip"


# ------------------------------------------------------------------ #
# 14. Form re-population on validation failure                        #
# ------------------------------------------------------------------ #


class TestEditFormRepopulationOnError:
    """On validation failure the submitted values must be retained in
    the re-rendered form so the user does not lose work."""

    def test_submitted_category_retained_on_invalid_amount(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "repop_cat.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "repop_cat.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, amount="abc", category="Health"),
                )
            )

        assert (
            "Health" in body
        ), "Submitted category must be retained in the re-rendered form after an amount error"

    def test_submitted_date_retained_on_invalid_amount(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "repop_date.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "repop_date.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, amount="abc", date="2026-05-01"),
                )
            )

        assert (
            "2026-05-01" in body
        ), "Submitted date must be retained in the re-rendered form after an amount error"

    def test_submitted_description_retained_on_invalid_amount(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "repop_desc.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "repop_desc.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(
                        VALID_POST_DATA, amount="abc", description="My edited note"
                    ),
                )
            )

        assert (
            "My edited note" in body
        ), "Submitted description must be retained in the re-rendered form after an amount error"

    def test_category_select_still_present_on_error(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "repop_sel.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "repop_sel.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, amount="abc"),
                )
            )

        assert (
            "<select" in body.lower()
        ), "Category <select> must still be present in the re-rendered form after a validation error"

    def test_all_categories_still_present_on_error(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "repop_allcat.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "repop_allcat.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            body = _body(
                c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, amount="abc"),
                )
            )

        for cat in VALID_CATEGORIES:
            assert (
                cat in body
            ), f"Category '{cat}' must still be present in the re-rendered form after a validation error"


# ------------------------------------------------------------------ #
# 15. Edge cases                                                       #
# ------------------------------------------------------------------ #


class TestEditExpenseEdgeCases:

    def test_sql_injection_in_description_does_not_crash(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Parameterised queries must handle SQL injection in description safely."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "sqli.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "sqli.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, description="'; DROP TABLE expenses; --"),
            )

        assert resp.status_code in (
            200,
            302,
        ), "SQL injection in description must not crash the app (no 500)"

    def test_sql_injection_in_description_stored_literally(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """The injected string must be stored as a literal value, not executed as SQL."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "sqli_db.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "sqli_db.db"), demo_user_id)
        injection = "'; DROP TABLE expenses; --"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            c.post(
                f"/expenses/{expense_id}/edit",
                data=dict(VALID_POST_DATA, description=injection),
            )

        row = _get_expense_row(str(tmp_path / "sqli_db.db"), expense_id)
        assert (
            row is not None
        ), "expenses table must still exist after SQL injection attempt"
        assert (
            row["description"] == injection
        ), "SQL injection string must be stored as a literal value"

    def test_valid_post_does_not_return_500(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "no500.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "no500.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.post(f"/expenses/{expense_id}/edit", data=VALID_POST_DATA)

        assert (
            resp.status_code != 500
        ), "Valid POST must not trigger an internal server error"

    def test_get_does_not_return_500(self, tmp_path, monkeypatch, demo_user_id):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "get_no500.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "get_no500.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            resp = c.get(f"/expenses/{expense_id}/edit")

        assert (
            resp.status_code != 500
        ), "GET /expenses/<id>/edit must not trigger an internal server error"

    def test_all_valid_categories_accepted_on_edit(
        self, tmp_path, monkeypatch, demo_user_id
    ):
        """Every category in the fixed list must be accepted as a valid edit."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "allcats.db"))
        init_db()
        seed_db()

        import app as app_module

        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        expense_id = _first_expense_id(str(tmp_path / "allcats.db"), demo_user_id)

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"
            for cat in VALID_CATEGORIES:
                resp = c.post(
                    f"/expenses/{expense_id}/edit",
                    data=dict(VALID_POST_DATA, category=cat),
                )
                assert (
                    resp.status_code == 302
                ), f"Category '{cat}' must be accepted on edit (redirect 302)"
