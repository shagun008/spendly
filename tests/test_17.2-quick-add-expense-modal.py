"""Release 17.2 — Quick Add Expense Modal: POST /profile/add-expense route tests.

Tests run against the real Supabase database (via DATABASE_URL). Each test
creates its own user, logs in, exercises the quick-add expense modal flow,
and tears down its data.

Test classes:
  TestModalMarkup         — profile page HTML contains "+" button and modal
  TestNavRemoval          — Add Expense nav link is gone from base.html
  TestRouteRemoval        — /expenses/add no longer exists
  TestUnauthenticated     — POST without session redirects to /login
  TestValidation          — each validation rule produces the correct flash
  TestSuccessfulSubmit    — valid submission saves expense to DB
  TestCategoryDropdown    — dropdown shows all valid categories
"""

import importlib
import uuid

import pytest
import psycopg2
import psycopg2.extras

import database.db as db_module
from database.db import get_db, create_user


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _unique_email(prefix="user"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.spendly.com"


def _create_user_and_get_id(email, password="password123"):
    name = email.split("@")[0].replace("-", " ").title()
    return create_user(name, email, password)


def _delete_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def _count_expenses(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["cnt"]


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app():
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_user():
    email = _unique_email("qaem")
    password = "password123"
    user_id = _create_user_and_get_id(email, password)
    yield {"id": user_id, "email": email, "password": password}
    _delete_user(user_id)


@pytest.fixture
def auth_client(client, test_user):
    client.post("/login", data={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    return client


# ------------------------------------------------------------------ #
# 1. Modal markup                                                      #
# ------------------------------------------------------------------ #

class TestModalMarkup:
    def test_plus_button_present(self, auth_client):
        """Profile page must contain the quick-add button."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'id="quick-add-btn"' in body, "quick-add-btn must exist"

    def test_modal_overlay_present(self, auth_client):
        """Profile page must contain the quick-add modal overlay."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="quick-add-modal"' in body, "Modal overlay must exist"

    def test_modal_has_amount_field(self, auth_client):
        """Modal form must have an amount input field."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'name="amount"' in body, "amount field must exist in modal"

    def test_modal_has_category_field(self, auth_client):
        """Modal form must have a category select field."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'name="category"' in body, "category field must exist in modal"

    def test_modal_has_date_field(self, auth_client):
        """Modal form must have a date input field."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'name="date"' in body, "date field must exist in modal"

    def test_modal_has_description_field(self, auth_client):
        """Modal form must have a description input field."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'name="description"' in body, "description field must exist in modal"

    def test_modal_accessibility(self, auth_client):
        """Modal must have role=dialog, aria-modal, and aria-labelledby."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'role="dialog"' in body, "Modal must have role=dialog"
        assert 'aria-modal="true"' in body, "Modal must have aria-modal=true"
        assert 'aria-labelledby="quick-add-modal-title"' in body, (
            "Modal must have aria-labelledby pointing to the title"
        )


# ------------------------------------------------------------------ #
# 2. Nav removal                                                       #
# ------------------------------------------------------------------ #

class TestNavRemoval:
    def test_add_expense_not_in_desktop_nav(self, auth_client):
        """The Add Expense nav link must be removed from desktop nav."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The nav link would look like: >Add Expense</a>
        assert ">Add Expense</a>" not in body, (
            "Add Expense nav link must not appear anywhere in the page"
        )

    def test_add_expense_not_in_mobile_nav(self, auth_client):
        """The Add Expense nav link must be removed from mobile nav."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # The mobile menu renders the same nav links — already covered above
        # but verify the mobile menu container exists and doesn't contain it
        assert 'class="nav-mobile-menu"' in body, "Mobile menu must still exist"
        assert ">Add Expense</a>" not in body


# ------------------------------------------------------------------ #
# 3. Route removal                                                     #
# ------------------------------------------------------------------ #

class TestRouteRemoval:
    def test_add_expense_route_returns_404(self, auth_client):
        """The /expenses/add route must no longer exist."""
        resp = auth_client.get("/expenses/add")
        assert resp.status_code == 404, "/expenses/add should return 404"

    def test_add_expense_post_returns_404(self, auth_client):
        """POST /expenses/add must no longer exist."""
        resp = auth_client.post("/expenses/add", data={
            "amount": "100",
            "category": "Food",
            "date": "2026-06-23",
        })
        assert resp.status_code == 404, "POST /expenses/add should return 404"


# ------------------------------------------------------------------ #
# 4. Unauthenticated access                                            #
# ------------------------------------------------------------------ #

class TestUnauthenticated:
    def test_post_redirects_to_login(self, client):
        """POST /profile/add-expense without auth must redirect to /login."""
        resp = client.post("/profile/add-expense", data={
            "amount": "100",
            "category": "Food",
            "date": "2026-06-23",
        })
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_post_does_not_crash(self, client):
        """Unauthenticated POST must not return 500."""
        resp = client.post("/profile/add-expense", data={
            "amount": "100",
            "category": "Food",
            "date": "2026-06-23",
        })
        assert resp.status_code != 500


# ------------------------------------------------------------------ #
# 5. Validation errors                                                 #
# ------------------------------------------------------------------ #

class TestValidation:
    def _post(self, auth_client, **overrides):
        """Helper to POST the quick-add form with default valid data."""
        data = {
            "amount": "100.50",
            "category": "Food",
            "date": "2026-06-23",
            "description": "Test expense",
        }
        data.update(overrides)
        return auth_client.post("/profile/add-expense", data=data, follow_redirects=True)

    def test_negative_amount(self, auth_client):
        """Negative amount must flash an error."""
        resp = self._post(auth_client, amount="-50")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Amount must be a number greater than 0" in body

    def test_zero_amount(self, auth_client):
        """Zero amount must flash an error."""
        resp = self._post(auth_client, amount="0")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Amount must be a number greater than 0" in body

    def test_non_numeric_amount(self, auth_client):
        """Non-numeric amount must flash an error."""
        resp = self._post(auth_client, amount="abc")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Amount must be a number greater than 0" in body

    def test_empty_amount(self, auth_client):
        """Empty amount must flash an error."""
        resp = self._post(auth_client, amount="")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Amount must be a number greater than 0" in body

    def test_invalid_category(self, auth_client):
        """Invalid category must flash an error."""
        resp = self._post(auth_client, category="InvalidCategory")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Please select a valid category" in body

    def test_empty_category(self, auth_client):
        """Empty category must flash an error."""
        resp = self._post(auth_client, category="")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Please select a valid category" in body

    def test_invalid_date(self, auth_client):
        """Invalid date must flash an error."""
        resp = self._post(auth_client, date="not-a-date")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Please enter a valid date" in body

    def test_empty_date(self, auth_client):
        """Empty date must flash an error."""
        resp = self._post(auth_client, date="")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Please enter a valid date" in body

    def test_description_too_long(self, auth_client):
        """Description over 200 chars must flash an error."""
        resp = self._post(auth_client, description="x" * 201)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Description must be 200 characters or fewer" in body


# ------------------------------------------------------------------ #
# 6. Successful submission                                             #
# ------------------------------------------------------------------ #

class TestSuccessfulSubmit:
    def test_flash_success(self, auth_client, test_user):
        """Valid submission must flash 'Expense added.' with success."""
        resp = auth_client.post("/profile/add-expense", data={
            "amount": "250.00",
            "category": "Transport",
            "date": "2026-06-23",
            "description": "Bus fare",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Expense added" in body

    def test_expense_saved_to_db(self, auth_client, test_user):
        """Valid submission must persist a row in the expenses table."""
        before = _count_expenses(test_user["id"])
        auth_client.post("/profile/add-expense", data={
            "amount": "350.00",
            "category": "Bills",
            "date": "2026-06-23",
            "description": "Electricity bill",
        })
        after = _count_expenses(test_user["id"])
        assert after == before + 1, "Exactly one new expense row must be inserted"

    def test_redirect_to_profile(self, auth_client, test_user):
        """Successful submit must redirect to /profile."""
        resp = auth_client.post("/profile/add-expense", data={
            "amount": "100",
            "category": "Food",
            "date": "2026-06-23",
        })
        assert resp.status_code == 302
        assert "/profile" in resp.headers["Location"]

    def test_multiple_expenses(self, auth_client, test_user):
        """Submitting multiple expenses in sequence must save all of them."""
        before = _count_expenses(test_user["id"])
        for i in range(3):
            auth_client.post("/profile/add-expense", data={
                "amount": str(100 * (i + 1)),
                "category": "Food",
                "date": "2026-06-23",
                "description": f"Expense {i + 1}",
            })
        after = _count_expenses(test_user["id"])
        assert after == before + 3, "All three expenses must be saved"


# ------------------------------------------------------------------ #
# 7. Category dropdown                                                  #
# ------------------------------------------------------------------ #

class TestCategoryDropdown:
    VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

    def test_all_categories_in_dropdown(self, auth_client):
        """The category dropdown must contain all valid categories."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        for cat in self.VALID_CATEGORIES:
            assert f'value="{cat}"' in body, f"Category '{cat}' must be in the dropdown"

    def test_no_spending_breakdown_values(self, auth_client):
        """The dropdown must not be populated from spending breakdown data.

        If the dropdown were using the spending breakdown, categories with no
        expenses would be missing. Verify all 7 are present regardless of
        whether the user has expenses.
        """
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        # Count how many valid categories appear as option values
        found = sum(1 for cat in self.VALID_CATEGORIES if f'value="{cat}"' in body)
        assert found == 7, f"All 7 categories must be present, found only {found}"
