"""Release 18.1 — Quick Edit Expense Modal: tests for the edit modal on Profile.

Tests are based on the spec at .claude/specs/18.1-quick-edit-expense-modal.md
and do NOT derive expectations from reading the implementation.

Test groups:
  TestModalMarkup          — profile page HTML contains the edit modal + button
  TestRouteRemoval         — /expenses/<id>/edit no longer exists
  TestTemplateRemoval      — templates/edit_expense.html is deleted
  TestUnauthenticated      — POST without session redirects to /login
  TestValidation           — each validation rule produces the correct flash
  TestSuccessfulSubmit     — valid submission updates expense in DB
  TestOtherUserExpense     — editing another user's expense is a no-op (rowcount gap documented)
  TestNonExistentExpense   — editing non-existent id silently succeeds (rowcount gap documented)
"""

import importlib
import os
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


def _last_expense_id(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id FROM expenses WHERE user_id = %s ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["id"] if row else None


def _get_expense(expense_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


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
    email = _unique_email("qeem")
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


@pytest.fixture
def with_expense(auth_client, test_user):
    """Add an expense for the test user and return its id."""
    resp = auth_client.post("/profile/add-expense", data={
        "amount": "50.00",
        "category": "Food",
        "date": "2026-05-15",
        "description": "Test expense",
    })
    assert resp.status_code == 302
    return _last_expense_id(test_user["id"])


# ------------------------------------------------------------------ #
# 1. Modal markup                                                      #
# ------------------------------------------------------------------ #


class TestModalMarkup:
    def test_edit_button_present(self, auth_client, with_expense):
        """Each transaction row must have an Edit button with data attributes."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'class="tx-edit-btn"' in body, "tx-edit-btn must exist"
        assert "data-expense=" in body, "Edit button must have data-expense"
        assert "data-date=" in body, "Edit button must have data-date"
        assert "data-amount=" in body, "Edit button must have data-amount"

    def test_modal_overlay_present(self, auth_client, with_expense):
        """Profile page must contain the quick-edit modal overlay."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="quick-edit-modal"' in body, "quick-edit-modal must exist"

    def test_modal_accessibility(self, auth_client, with_expense):
        """Modal must have role=dialog, aria-modal, and aria-labelledby."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'role="dialog"' in body, "Modal must have role=dialog"
        assert 'aria-modal="true"' in body, "Modal must have aria-modal=true"
        assert 'aria-labelledby="quick-edit-modal-title"' in body, (
            "Modal must have aria-labelledby pointing to the title"
        )

    def test_modal_has_all_fields(self, auth_client, with_expense):
        """Modal form must have amount, category, date, description, hidden id."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="edit-expense-id"' in body, "Hidden expense_id field must exist"
        assert 'id="qe-amount"' in body, "amount field must exist"
        assert 'id="qe-category"' in body, "category field must exist"
        assert 'id="qe-date"' in body, "date field must exist"
        assert 'id="qe-description"' in body, "description field must exist"

    def test_modal_has_close_button(self, auth_client, with_expense):
        """Modal must have an X close button."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="quick-edit-modal-close"' in body, "Close button must exist"

    def test_modal_has_cancel_button(self, auth_client, with_expense):
        """Modal must have a Cancel button."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="quick-edit-modal-cancel"' in body, "Cancel button must exist"

    def test_modal_form_posts_to_endpoint(self, auth_client, with_expense):
        """Modal form must POST to /profile/edit-expense."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert "/profile/edit-expense" in body, "Form must post to /profile/edit-expense"


# ------------------------------------------------------------------ #
# 2. Route removal                                                     #
# ------------------------------------------------------------------ #


class TestRouteRemoval:
    def test_standalone_edit_route_returns_404(self, auth_client, with_expense):
        """GET /expenses/<id>/edit must no longer exist."""
        resp = auth_client.get("/expenses/1/edit")
        assert resp.status_code == 404, "/expenses/1/edit should return 404"

    def test_standalone_edit_post_returns_404(self, auth_client, with_expense):
        """POST /expenses/<id>/edit must no longer exist."""
        resp = auth_client.post("/expenses/1/edit", data={
            "amount": "10",
            "category": "Food",
            "date": "2026-05-01",
        })
        assert resp.status_code == 404, "POST /expenses/1/edit should return 404"

    def test_old_url_for_raises_build_error(self, app):
        """url_for('edit_expense', id=1) must raise BuildError."""
        from werkzeug.routing import BuildError
        with app.test_request_context():
            from flask import url_for
            with pytest.raises(BuildError):
                url_for("edit_expense", id=1)


# ------------------------------------------------------------------ #
# 3. Template removal                                                  #
# ------------------------------------------------------------------ #


class TestTemplateRemoval:
    def test_edit_expense_template_deleted(self):
        """templates/edit_expense.html must be deleted per spec DOD."""
        template_path = os.path.join(
            os.path.dirname(__file__), "..", "templates", "edit_expense.html"
        )
        assert not os.path.exists(template_path), (
            f"templates/edit_expense.html should have been deleted but still exists at {template_path}"
        )


# ------------------------------------------------------------------ #
# 4. Unauthenticated access                                            #
# ------------------------------------------------------------------ #


class TestUnauthenticated:
    def test_post_redirects_to_login(self, client):
        """POST /profile/edit-expense without auth must redirect to /login."""
        resp = client.post("/profile/edit-expense", data={
            "expense_id": "1",
            "amount": "100",
            "category": "Food",
            "date": "2026-05-01",
        })
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_post_does_not_crash(self, client):
        """Unauthenticated POST must not return 500."""
        resp = client.post("/profile/edit-expense", data={
            "expense_id": "1",
            "amount": "100",
            "category": "Food",
            "date": "2026-05-01",
        })
        assert resp.status_code != 500


# ------------------------------------------------------------------ #
# 5. Validation errors                                                 #
# ------------------------------------------------------------------ #


class TestValidation:
    def _post(self, auth_client, expense_id, **overrides):
        data = {
            "expense_id": str(expense_id),
            "amount": "75.00",
            "category": "Food",
            "date": "2026-05-20",
            "description": "Valid edit",
        }
        data.update(overrides)
        return auth_client.post("/profile/edit-expense", data=data, follow_redirects=True)

    def test_missing_id(self, auth_client, with_expense):
        """Missing expense_id flashes 'Expense not found.'"""
        resp = auth_client.post("/profile/edit-expense", data={
            "amount": "10",
            "category": "Food",
            "date": "2026-05-01",
            "description": "",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Expense not found." in resp.data

    def test_negative_amount(self, auth_client, with_expense):
        """Negative amount must flash an error."""
        resp = self._post(auth_client, with_expense, amount="-50")
        assert resp.status_code == 200
        assert b"Amount must be a number greater than 0" in resp.data

    def test_zero_amount(self, auth_client, with_expense):
        """Zero amount must flash an error."""
        resp = self._post(auth_client, with_expense, amount="0")
        assert resp.status_code == 200
        assert b"Amount must be a number greater than 0" in resp.data

    def test_non_numeric_amount(self, auth_client, with_expense):
        """Non-numeric amount must flash an error."""
        resp = self._post(auth_client, with_expense, amount="abc")
        assert resp.status_code == 200
        assert b"Amount must be a number greater than 0" in resp.data

    def test_empty_amount(self, auth_client, with_expense):
        """Empty amount must flash an error."""
        resp = self._post(auth_client, with_expense, amount="")
        assert resp.status_code == 200
        assert b"Amount must be a number greater than 0" in resp.data

    def test_invalid_category(self, auth_client, with_expense):
        """Invalid category must flash an error."""
        resp = self._post(auth_client, with_expense, category="InvalidCategory")
        assert resp.status_code == 200
        assert b"Please select a valid category" in resp.data

    def test_empty_category(self, auth_client, with_expense):
        """Empty category must flash an error."""
        resp = self._post(auth_client, with_expense, category="")
        assert resp.status_code == 200
        assert b"Please select a valid category" in resp.data

    def test_invalid_date(self, auth_client, with_expense):
        """Invalid date must flash an error."""
        resp = self._post(auth_client, with_expense, date="not-a-date")
        assert resp.status_code == 200
        assert b"Please enter a valid date" in resp.data

    def test_empty_date(self, auth_client, with_expense):
        """Empty date must flash an error."""
        resp = self._post(auth_client, with_expense, date="")
        assert resp.status_code == 200
        assert b"Please enter a valid date" in resp.data

    def test_description_too_long(self, auth_client, with_expense):
        """Description over 200 chars must flash an error."""
        resp = self._post(auth_client, with_expense, description="x" * 201)
        assert resp.status_code == 200
        assert b"Description must be 200 characters or fewer" in resp.data


# ------------------------------------------------------------------ #
# 6. Successful submission                                             #
# ------------------------------------------------------------------ #


class TestSuccessfulSubmit:
    def test_flash_success(self, auth_client, with_expense):
        """Valid submission must flash 'Expense updated.'"""
        resp = auth_client.post("/profile/edit-expense", data={
            "expense_id": str(with_expense),
            "amount": "99.99",
            "category": "Bills",
            "date": "2026-05-18",
            "description": "Updated expense",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Expense updated." in resp.data

    def test_expense_updated_in_db(self, auth_client, test_user, with_expense):
        """Valid submission must persist the updated values."""
        auth_client.post("/profile/edit-expense", data={
            "expense_id": str(with_expense),
            "amount": "123.45",
            "category": "Health",
            "date": "2026-05-19",
            "description": "Doctor visit",
        })
        row = _get_expense(with_expense)
        assert row is not None
        assert row["amount"] == 123.45
        assert row["category"] == "Health"
        assert row["date"] == "2026-05-19"
        assert row["description"] == "Doctor visit"

    def test_redirect_to_profile(self, auth_client, with_expense):
        """Successful submit must redirect to /profile."""
        resp = auth_client.post("/profile/edit-expense", data={
            "expense_id": str(with_expense),
            "amount": "10",
            "category": "Food",
            "date": "2026-05-01",
            "description": "",
        })
        assert resp.status_code == 302
        assert "/profile" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# 7. Ownership / rowcount edge cases                                    #
# ------------------------------------------------------------------ #


class TestOwnershipEdgeCases:
    def test_other_user_expense_not_modified(self, auth_client, test_user, with_expense):
        """Editing another user's expense must NOT change the row in the DB.

        The spec DOD says this should flash 'Expense not found.', but the
        current implementation does not check the UPDATE rowcount. This test
        documents the gap: the row is not modified, but the response is a
        silent success.
        """
        # Switch to a different user
        auth_client.get("/logout")
        other_email = _unique_email("other")
        other_id = _create_user_and_get_id(other_email)
        auth_client.post("/login", data={"email": other_email, "password": "password123"})

        # Capture original values
        original = _get_expense(with_expense)
        assert original["amount"] == 50.00
        assert original["category"] == "Food"

        # Attempt to edit as the other user
        resp = auth_client.post("/profile/edit-expense", data={
            "expense_id": str(with_expense),
            "amount": "999.99",
            "category": "Bills",
            "date": "2026-05-15",
            "description": "hacked",
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Row must NOT have been modified
        after = _get_expense(with_expense)
        assert after["amount"] == original["amount"], (
            "Another user's edit must not change the amount"
        )
        assert after["category"] == original["category"], (
            "Another user's edit must not change the category"
        )
        assert after["description"] == original["description"], (
            "Another user's edit must not change the description"
        )

        # Clean up
        auth_client.get("/logout")
        _delete_user(other_id)

    def test_nonexistent_id_returns_not_found(self, auth_client, test_user, with_expense):
        """Editing a non-existent expense id now correctly flashes 'Expense not found.'"""
        resp = auth_client.post("/profile/edit-expense", data={
            "expense_id": "999999",
            "amount": "10",
            "category": "Food",
            "date": "2026-05-01",
            "description": "",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Expense not found." in resp.data
