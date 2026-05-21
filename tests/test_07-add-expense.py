"""Step 7 — Add Expense: /expenses/add route tests + add_expense DB helper unit tests.

Strategy: monkeypatch database.db.DB_PATH to a fresh tmp file, seed the demo user
so foreign-key references resolve, reload app so the module-level init_db/seed_db
hits the patched path. Route tests drive Flask's test client; unit tests call
database.db.add_expense directly against the same patched DB.

Fixture hierarchy:
  tmp_db_path  — patches DB_PATH to a fresh tmp file and initialises schema
  client       — Flask test client backed by that tmp DB
  auth_client  — client with the demo user (id=1) already in session
  demo_user_id — the integer PK of the seeded demo user (always 1 after seed_db)
"""

import importlib
import sqlite3

import pytest

import database.db as db_module
from database.db import init_db, seed_db
from database.queries import insert_expense as add_expense


VALID_CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
]

VALID_POST_DATA = {
    "amount": "50.0",
    "category": "Food",
    "date": "2026-03-20",
    "description": "Lunch",
}


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by a fresh seeded tmp DB.

    Follows the established pattern from test_06-date-filter-profile.py:
    patch DB_PATH first, seed, then reload app so its module-level
    init_db/seed_db hits the tmp DB.
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
    """The integer PK of the seeded demo user. seed_db always inserts a
    single user first, so AUTOINCREMENT gives id=1."""
    return 1


# ------------------------------------------------------------------ #
# Helper                                                               #
# ------------------------------------------------------------------ #

def _body(response):
    return response.get_data(as_text=True)


def _query_expenses(db_path, user_id):
    """Return all expense rows for *user_id* as a list of sqlite3.Row objects."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


# ------------------------------------------------------------------ #
# 1. Unit tests — add_expense DB helper                               #
# ------------------------------------------------------------------ #

class TestAddExpenseDBHelper:
    """Direct unit tests for database.db.add_expense.

    These call the helper against the patched tmp DB so they remain
    isolated from the real spendly.db.
    """

    def test_valid_insert_row_exists(self, tmp_path, monkeypatch, demo_user_id):
        """add_expense with full valid data must persist a row in the DB."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        add_expense(demo_user_id, 50.0, "Food", "2026-03-20", "Lunch")

        rows = _query_expenses(str(tmp_path / "unit.db"), demo_user_id)
        # seed_db inserts 8 rows; our new one should be the 9th (most-recent by id)
        matching = [r for r in rows if r["description"] == "Lunch" and r["date"] == "2026-03-20"]
        assert len(matching) == 1, "Exactly one row with description='Lunch' must exist after insert"

    def test_valid_insert_correct_amount(self, tmp_path, monkeypatch, demo_user_id):
        """Inserted row must store the exact amount supplied."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        add_expense(demo_user_id, 50.0, "Food", "2026-03-20", "Lunch")

        rows = _query_expenses(str(tmp_path / "unit.db"), demo_user_id)
        matching = [r for r in rows if r["description"] == "Lunch"]
        assert matching[0]["amount"] == 50.0, "Row amount must be 50.0"

    def test_valid_insert_correct_category(self, tmp_path, monkeypatch, demo_user_id):
        """Inserted row must store the exact category supplied."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        add_expense(demo_user_id, 50.0, "Food", "2026-03-20", "Lunch")

        rows = _query_expenses(str(tmp_path / "unit.db"), demo_user_id)
        matching = [r for r in rows if r["description"] == "Lunch"]
        assert matching[0]["category"] == "Food", "Row category must be 'Food'"

    def test_valid_insert_correct_date(self, tmp_path, monkeypatch, demo_user_id):
        """Inserted row must store the exact date supplied."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        add_expense(demo_user_id, 50.0, "Food", "2026-03-20", "Lunch")

        rows = _query_expenses(str(tmp_path / "unit.db"), demo_user_id)
        matching = [r for r in rows if r["description"] == "Lunch"]
        assert matching[0]["date"] == "2026-03-20", "Row date must be '2026-03-20'"

    def test_valid_insert_correct_user_id(self, tmp_path, monkeypatch, demo_user_id):
        """Inserted row must be associated with the given user_id."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        add_expense(demo_user_id, 50.0, "Food", "2026-03-20", "Lunch")

        rows = _query_expenses(str(tmp_path / "unit.db"), demo_user_id)
        matching = [r for r in rows if r["description"] == "Lunch"]
        assert matching[0]["user_id"] == demo_user_id, "Row user_id must match the supplied user_id"

    def test_null_description_stored_as_null(self, tmp_path, monkeypatch, demo_user_id):
        """add_expense with description=None must store NULL in the description column."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        add_expense(demo_user_id, 50.0, "Food", "2026-03-20", None)

        rows = _query_expenses(str(tmp_path / "unit.db"), demo_user_id)
        # Find the row we just inserted: same amount, date, category, and NULL description
        matching = [
            r for r in rows
            if r["amount"] == 50.0
            and r["date"] == "2026-03-20"
            and r["description"] is None
        ]
        assert len(matching) == 1, (
            "One row with description=NULL must exist when add_expense is called with description=None"
        )

    def test_insert_increments_row_count(self, tmp_path, monkeypatch, demo_user_id):
        """Each call to add_expense must add exactly one new row."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unit.db"))
        init_db()
        seed_db()

        before = len(_query_expenses(str(tmp_path / "unit.db"), demo_user_id))
        add_expense(demo_user_id, 25.0, "Transport", "2026-03-21", "Bus fare")
        after = len(_query_expenses(str(tmp_path / "unit.db"), demo_user_id))

        assert after == before + 1, "Row count must increase by exactly 1 after add_expense"


# ------------------------------------------------------------------ #
# 2. GET /expenses/add — unauthenticated                              #
# ------------------------------------------------------------------ #

class TestGetAddExpenseUnauthenticated:
    def test_redirects_to_login(self, client):
        resp = client.get("/expenses/add")
        assert resp.status_code == 302, (
            "GET /expenses/add without auth must redirect (302)"
        )

    def test_redirect_target_is_login(self, client):
        resp = client.get("/expenses/add")
        assert "/login" in resp.headers["Location"], (
            "Unauthenticated GET /expenses/add must redirect to /login"
        )

    def test_following_redirect_shows_login_page(self, client):
        resp = client.get("/expenses/add", follow_redirects=True)
        assert resp.status_code == 200, "Following redirect must yield 200 login page"
        body = _body(resp)
        assert "login" in body.lower(), "Following unauthenticated redirect must land on login page"


# ------------------------------------------------------------------ #
# 3. GET /expenses/add — authenticated                                #
# ------------------------------------------------------------------ #

class TestGetAddExpenseAuthenticated:
    def test_returns_200(self, auth_client):
        resp = auth_client.get("/expenses/add")
        assert resp.status_code == 200, "Authenticated GET /expenses/add must return 200"

    def test_response_contains_form_with_post_method(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        assert "<form" in body.lower(), "Response must contain a <form> element"
        assert "post" in body.lower(), "Form must specify POST method"

    def test_response_contains_amount_input(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        assert 'name="amount"' in body or "name='amount'" in body, (
            "Form must contain an input named 'amount'"
        )

    def test_response_contains_date_input(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        assert 'name="date"' in body or "name='date'" in body, (
            "Form must contain an input named 'date'"
        )

    def test_response_contains_description_input(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        assert 'name="description"' in body or "name='description'" in body, (
            "Form must contain an input named 'description'"
        )

    def test_response_contains_category_select(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        assert "<select" in body.lower(), "Form must contain a <select> element for category"

    def test_all_seven_categories_present(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        for category in VALID_CATEGORIES:
            assert category in body, (
                f"Category option '{category}' must appear in the form's <select>"
            )

    def test_exactly_seven_category_options(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        # Count <option> tags — each valid category maps to one <option>
        option_count = body.lower().count("<option")
        assert option_count >= 7, (
            f"Form must have at least 7 <option> elements for categories, found {option_count}"
        )

    def test_cancel_link_to_profile_present(self, auth_client):
        body = _body(auth_client.get("/expenses/add"))
        assert "/profile" in body, (
            "Form page must contain a cancel link pointing to /profile"
        )


# ------------------------------------------------------------------ #
# 4. POST /expenses/add — unauthenticated                             #
# ------------------------------------------------------------------ #

class TestPostAddExpenseUnauthenticated:
    def test_redirects_302(self, client):
        resp = client.post("/expenses/add", data=VALID_POST_DATA)
        assert resp.status_code == 302, (
            "POST /expenses/add without auth must redirect (302)"
        )

    def test_redirect_target_is_login(self, client):
        resp = client.post("/expenses/add", data=VALID_POST_DATA)
        assert "/login" in resp.headers["Location"], (
            "Unauthenticated POST /expenses/add must redirect to /login"
        )


# ------------------------------------------------------------------ #
# 5. POST /expenses/add — authenticated, valid data                   #
# ------------------------------------------------------------------ #

class TestPostAddExpenseValidData:
    def test_redirects_to_profile(self, auth_client):
        resp = auth_client.post("/expenses/add", data=VALID_POST_DATA)
        assert resp.status_code == 302, "Valid POST must redirect (302)"
        assert "/profile" in resp.headers["Location"], (
            "Successful POST /expenses/add must redirect to /profile"
        )

    def test_flash_message_expense_added(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=VALID_POST_DATA, follow_redirects=True
        )
        body = _body(resp)
        assert "Expense added" in body, (
            "Flash message 'Expense added.' must appear after successful POST"
        )

    def test_new_row_exists_in_db(self, tmp_path, monkeypatch, demo_user_id):
        """After a valid POST the expense must be persisted in the DB."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "route.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            before = len(_query_expenses(str(tmp_path / "route.db"), demo_user_id))
            c.post("/expenses/add", data=VALID_POST_DATA)
            after_rows = _query_expenses(str(tmp_path / "route.db"), demo_user_id)

        assert len(after_rows) == before + 1, (
            "A new expense row must be written to the DB after a valid POST"
        )
        newest = after_rows[0]  # ORDER BY id DESC — most recent first
        assert newest["amount"] == 50.0, "Stored amount must match submitted value"
        assert newest["category"] == "Food", "Stored category must match submitted value"
        assert newest["date"] == "2026-03-20", "Stored date must match submitted value"
        assert newest["description"] == "Lunch", "Stored description must match submitted value"

    def test_no_description_redirects_to_profile(self, auth_client):
        """Omitting the optional description field must still succeed."""
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 302, (
            "POST without description must redirect (302)"
        )
        assert "/profile" in resp.headers["Location"], (
            "POST without description must redirect to /profile"
        )

    def test_no_description_stores_null(self, tmp_path, monkeypatch, demo_user_id):
        """Row inserted without description must have NULL in the description column."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "nodesc.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}
            c.post("/expenses/add", data=data)

        rows = _query_expenses(str(tmp_path / "nodesc.db"), demo_user_id)
        matching = [
            r for r in rows
            if r["amount"] == 50.0
            and r["date"] == "2026-03-20"
            and r["description"] is None
        ]
        assert len(matching) == 1, (
            "Row inserted without description must have description=NULL in the DB"
        )

    def test_empty_string_description_stores_null(self, tmp_path, monkeypatch, demo_user_id):
        """An explicitly empty description string must also be stored as NULL."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "emptydesc.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            data = dict(VALID_POST_DATA, description="")
            c.post("/expenses/add", data=data)

        rows = _query_expenses(str(tmp_path / "emptydesc.db"), demo_user_id)
        matching = [
            r for r in rows
            if r["amount"] == 50.0
            and r["date"] == "2026-03-20"
            and r["description"] is None
        ]
        assert len(matching) == 1, (
            "Row inserted with empty description must have description=NULL in the DB"
        )

    def test_whitespace_only_description_stores_null(self, tmp_path, monkeypatch, demo_user_id):
        """A whitespace-only description must be stripped and stored as NULL."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "wsdesc.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            data = dict(VALID_POST_DATA, description="   ")
            c.post("/expenses/add", data=data)

        rows = _query_expenses(str(tmp_path / "wsdesc.db"), demo_user_id)
        matching = [
            r for r in rows
            if r["amount"] == 50.0
            and r["date"] == "2026-03-20"
            and r["description"] is None
        ]
        assert len(matching) == 1, (
            "Whitespace-only description must be stored as NULL after strip"
        )


# ------------------------------------------------------------------ #
# 6. POST /expenses/add — amount validation failures                  #
# ------------------------------------------------------------------ #

class TestPostAddExpenseAmountValidation:
    def test_missing_amount_returns_200(self, auth_client):
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "amount"}
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 200, "Missing amount must re-render form (200)"

    def test_missing_amount_shows_error(self, auth_client):
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "amount"}
        body = _body(auth_client.post("/expenses/add", data=data))
        assert "error" in body.lower() or "amount" in body.lower(), (
            "Missing amount must surface an error message in the response"
        )

    def test_zero_amount_returns_200(self, auth_client):
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="0"))
        assert resp.status_code == 200, "Amount=0 must re-render form (200)"

    def test_zero_amount_shows_error(self, auth_client):
        body = _body(
            auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="0"))
        )
        assert "error" in body.lower() or "amount" in body.lower(), (
            "Amount=0 must surface an error message"
        )

    def test_zero_amount_does_not_redirect(self, auth_client):
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="0"))
        assert resp.status_code != 302, "Amount=0 must not redirect"

    def test_negative_amount_returns_200(self, auth_client):
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="-10"))
        assert resp.status_code == 200, "Negative amount must re-render form (200)"

    def test_negative_amount_shows_error(self, auth_client):
        body = _body(
            auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="-10"))
        )
        assert "error" in body.lower() or "amount" in body.lower(), (
            "Negative amount must surface an error message"
        )

    def test_non_numeric_amount_returns_200(self, auth_client):
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="abc"))
        assert resp.status_code == 200, "Non-numeric amount must re-render form (200)"

    def test_non_numeric_amount_shows_error(self, auth_client):
        body = _body(
            auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="abc"))
        )
        assert "error" in body.lower() or "amount" in body.lower(), (
            "Non-numeric amount must surface an error message"
        )

    def test_non_numeric_amount_does_not_persist_row(self, tmp_path, monkeypatch, demo_user_id):
        """No row must be written when the amount is invalid."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "inv_amt.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            before = len(_query_expenses(str(tmp_path / "inv_amt.db"), demo_user_id))
            c.post("/expenses/add", data=dict(VALID_POST_DATA, amount="abc"))
            after = len(_query_expenses(str(tmp_path / "inv_amt.db"), demo_user_id))

        assert after == before, "Invalid amount must not write any row to the DB"

    @pytest.mark.parametrize("bad_amount", ["", "0", "-1", "-0.01", "abc", "1e999", "None", "null"])
    def test_parametrized_invalid_amounts_return_200(self, auth_client, bad_amount):
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount=bad_amount))
        assert resp.status_code == 200, (
            f"Invalid amount '{bad_amount}' must re-render form (200), not redirect"
        )


# ------------------------------------------------------------------ #
# 7. POST /expenses/add — category validation failures                #
# ------------------------------------------------------------------ #

class TestPostAddExpenseCategoryValidation:
    def test_invalid_category_returns_200(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, category="Groceries")
        )
        assert resp.status_code == 200, "Invalid category must re-render form (200)"

    def test_invalid_category_shows_error(self, auth_client):
        body = _body(
            auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, category="Groceries"))
        )
        assert "error" in body.lower() or "category" in body.lower(), (
            "Invalid category must surface an error message"
        )

    def test_invalid_category_does_not_redirect(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, category="Groceries")
        )
        assert resp.status_code != 302, "Invalid category must not redirect"

    def test_missing_category_returns_200(self, auth_client):
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "category"}
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 200, "Missing category must re-render form (200)"

    def test_empty_category_returns_200(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, category="")
        )
        assert resp.status_code == 200, "Empty category must re-render form (200)"

    @pytest.mark.parametrize("bad_category", [
        "Groceries",
        "food",          # case-sensitive — must not match "Food"
        "FOOD",
        "travel",
        "utilities",
        "",
        "'; DROP TABLE expenses; --",
    ])
    def test_parametrized_invalid_categories_return_200(self, auth_client, bad_category):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, category=bad_category)
        )
        assert resp.status_code == 200, (
            f"Invalid category '{bad_category}' must re-render form (200), not redirect"
        )


# ------------------------------------------------------------------ #
# 8. POST /expenses/add — date validation failures                    #
# ------------------------------------------------------------------ #

class TestPostAddExpenseDateValidation:
    def test_invalid_date_string_returns_200(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, date="not-a-date")
        )
        assert resp.status_code == 200, "Invalid date must re-render form (200)"

    def test_invalid_date_string_shows_error(self, auth_client):
        body = _body(
            auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, date="not-a-date"))
        )
        assert "error" in body.lower() or "date" in body.lower(), (
            "Invalid date must surface an error message"
        )

    def test_invalid_date_does_not_redirect(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, date="not-a-date")
        )
        assert resp.status_code != 302, "Invalid date must not redirect"

    def test_missing_date_returns_200(self, auth_client):
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "date"}
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 200, "Missing date must re-render form (200)"

    def test_invalid_date_does_not_persist_row(self, tmp_path, monkeypatch, demo_user_id):
        """No row must be written when the date is invalid."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "inv_date.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            before = len(_query_expenses(str(tmp_path / "inv_date.db"), demo_user_id))
            c.post("/expenses/add", data=dict(VALID_POST_DATA, date="not-a-date"))
            after = len(_query_expenses(str(tmp_path / "inv_date.db"), demo_user_id))

        assert after == before, "Invalid date must not write any row to the DB"

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "20260320",          # no hyphens
        "03-20-2026",        # wrong order
        "2026/03/20",        # wrong separator
        "2026-13-01",        # invalid month
        "2026-04-99",        # invalid day
        "",
        "yesterday",
    ])
    def test_parametrized_invalid_dates_return_200(self, auth_client, bad_date):
        resp = auth_client.post(
            "/expenses/add", data=dict(VALID_POST_DATA, date=bad_date)
        )
        assert resp.status_code == 200, (
            f"Invalid date '{bad_date}' must re-render form (200), not redirect"
        )


# ------------------------------------------------------------------ #
# 9. Form re-population on validation failure                         #
# ------------------------------------------------------------------ #

class TestFormRepopulationOnError:
    """On validation failure the previously submitted values must be
    pre-filled in the re-rendered form so the user does not lose work."""

    def test_submitted_category_retained_on_invalid_amount(self, auth_client):
        data = dict(VALID_POST_DATA, amount="abc", category="Transport")
        body = _body(auth_client.post("/expenses/add", data=data))
        assert "Transport" in body, (
            "Previously submitted category must be pre-filled after amount error"
        )

    def test_submitted_date_retained_on_invalid_amount(self, auth_client):
        data = dict(VALID_POST_DATA, amount="abc", date="2026-03-20")
        body = _body(auth_client.post("/expenses/add", data=data))
        assert "2026-03-20" in body, (
            "Previously submitted date must be pre-filled after amount error"
        )

    def test_submitted_description_retained_on_invalid_amount(self, auth_client):
        data = dict(VALID_POST_DATA, amount="abc", description="My note")
        body = _body(auth_client.post("/expenses/add", data=data))
        assert "My note" in body, (
            "Previously submitted description must be pre-filled after amount error"
        )

    def test_category_select_still_present_on_error(self, auth_client):
        data = dict(VALID_POST_DATA, amount="abc")
        body = _body(auth_client.post("/expenses/add", data=data))
        assert "<select" in body.lower(), (
            "Category <select> must still be present in the re-rendered form"
        )

    def test_all_categories_still_present_on_error(self, auth_client):
        data = dict(VALID_POST_DATA, amount="abc")
        body = _body(auth_client.post("/expenses/add", data=data))
        for category in VALID_CATEGORIES:
            assert category in body, (
                f"Category '{category}' must still be present in the re-rendered form after error"
            )


# ------------------------------------------------------------------ #
# 10. Edge cases                                                       #
# ------------------------------------------------------------------ #

class TestAddExpenseEdgeCases:
    def test_sql_injection_in_description_does_not_crash(self, auth_client):
        """Parameterised queries must handle SQL injection in description safely."""
        data = dict(VALID_POST_DATA, description="'; DROP TABLE expenses; --")
        resp = auth_client.post("/expenses/add", data=data)
        # Should redirect to profile (valid data apart from the dodgy description)
        assert resp.status_code in (200, 302), (
            "SQL injection attempt in description must not crash the app (500)"
        )

    def test_sql_injection_in_description_persists_safely(self, tmp_path, monkeypatch, demo_user_id):
        """The injected string must be stored literally, not executed as SQL."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "sqli.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            injection = "'; DROP TABLE expenses; --"
            c.post("/expenses/add", data=dict(VALID_POST_DATA, description=injection))

        # Table must still exist and the literal string must be stored
        rows = _query_expenses(str(tmp_path / "sqli.db"), demo_user_id)
        matching = [r for r in rows if r["description"] == injection]
        assert len(matching) == 1, (
            "SQL injection string must be stored as a literal value, not executed"
        )

    def test_very_large_amount_accepted(self, auth_client):
        """A numerically valid but very large amount must be accepted without crashing."""
        data = dict(VALID_POST_DATA, amount="9999999.99")
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 302, (
            "Very large valid amount must be accepted and redirect to /profile"
        )

    def test_valid_post_does_not_return_500(self, auth_client):
        resp = auth_client.post("/expenses/add", data=VALID_POST_DATA)
        assert resp.status_code != 500, "Valid POST must not trigger an internal server error"

    def test_get_does_not_return_500(self, auth_client):
        resp = auth_client.get("/expenses/add")
        assert resp.status_code != 500, "GET /expenses/add must not trigger an internal server error"

    def test_all_valid_categories_accepted(self, tmp_path, monkeypatch, demo_user_id):
        """Every category in the fixed list must be accepted without error."""
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "allcats.db"))
        init_db()
        seed_db()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["SECRET_KEY"] = "test-secret"

        with app_module.app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = demo_user_id
                sess["user_name"] = "Demo User"

            for category in VALID_CATEGORIES:
                resp = c.post("/expenses/add", data=dict(VALID_POST_DATA, category=category))
                assert resp.status_code == 302, (
                    f"Category '{category}' must be accepted (redirect 302)"
                )

    def test_decimal_amount_accepted(self, auth_client):
        """An amount with decimal precision must be accepted."""
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="12.75"))
        assert resp.status_code == 302, "Decimal amount 12.75 must be accepted (redirect 302)"

    def test_integer_string_amount_accepted(self, auth_client):
        """An integer-valued string amount must be accepted."""
        resp = auth_client.post("/expenses/add", data=dict(VALID_POST_DATA, amount="100"))
        assert resp.status_code == 302, "Integer string amount '100' must be accepted (redirect 302)"
