"""Release 17.1 — Change Password: POST /profile/change-password route tests.

Tests run against the real Supabase database (via DATABASE_URL). Each test
creates its own user, logs in, exercises the change-password flow, and
tears down its data. The database.db module is reloaded so the module-level
init_db/seed_features run once at import time.

Test classes:
  TestProfileButtonEnabled       — profile page HTML contains an enabled button
  TestChangePasswordUnauthenticated — POST without session redirects to /login
  TestChangePasswordValidation    — each validation rule produces the correct flash
  TestChangePasswordSuccess       — valid submission updates the hash in the DB
"""

import importlib

import pytest
import psycopg2
import psycopg2.extras

import database.db as db_module
from database.db import get_db, create_user, init_db, seed_features
from werkzeug.security import generate_password_hash, check_password_hash


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _unique_email(prefix="user"):
    """Return a unique email so tests don't collide in the shared DB."""
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.spendly.com"


def _create_user_and_get_id(email, password="password123"):
    """Create a user in the DB and return the user id."""
    name = email.split("@")[0].replace("-", " ").title()
    return create_user(name, email, password)


def _get_password_hash(user_id):
    """Fetch the raw password_hash for a user from the DB."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["password_hash"] if row else None


def _delete_user(user_id):
    """Remove a user and their expenses (cascade) from the DB."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app():
    """Ensure the app module is initialised (module-level init_db runs once)."""
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    return app_module.app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def test_user():
    """Create a test user and yield (user_id, email, password). Cleans up after."""
    email = _unique_email("cpw")
    password = "oldpassword123"
    user_id = _create_user_and_get_id(email, password)
    yield {"id": user_id, "email": email, "password": password}
    _delete_user(user_id)


@pytest.fixture
def auth_client(client, test_user):
    """Test client with the test user logged in."""
    client.post("/login", data={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    return client


# ------------------------------------------------------------------ #
# 1. Profile button is enabled                                        #
# ------------------------------------------------------------------ #

class TestProfileButtonEnabled:
    def test_button_not_disabled(self, auth_client):
        """The Change Password button must not have the btn-disabled class."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "change-password-btn" in body, "Button with id change-password-btn must exist"
        assert "btn-disabled" not in body, "btn-disabled class must not appear anywhere on the page"

    def test_modal_markup_present(self, auth_client):
        """The profile page must contain the change-password modal with three fields."""
        resp = auth_client.get("/profile")
        body = resp.get_data(as_text=True)
        assert 'id="change-password-modal"' in body, "Modal overlay must exist"
        assert 'name="current_password"' in body, "current_password field must exist"
        assert 'name="new_password"' in body, "new_password field must exist"
        assert 'name="confirm_password"' in body, "confirm_password field must exist"


# ------------------------------------------------------------------ #
# 2. Unauthenticated access                                            #
# ------------------------------------------------------------------ #

class TestChangePasswordUnauthenticated:
    def test_post_redirects_to_login(self, client):
        """POST /profile/change-password without auth must redirect to /login."""
        resp = client.post("/profile/change-password", data={
            "current_password": "anything",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        })
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_post_does_not_crash(self, client):
        """Unauthenticated POST must not return 500."""
        resp = client.post("/profile/change-password", data={
            "current_password": "anything",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        })
        assert resp.status_code != 500


# ------------------------------------------------------------------ #
# 3. Validation errors                                                 #
# ------------------------------------------------------------------ #

class TestChangePasswordValidation:
    def test_missing_current_password(self, auth_client):
        """Empty current password must flash 'Current password is required.'"""
        resp = auth_client.post("/profile/change-password", data={
            "current_password": "",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Current password is required" in body

    def test_wrong_current_password(self, auth_client, test_user):
        """Wrong current password must flash 'Current password is incorrect.'"""
        resp = auth_client.post("/profile/change-password", data={
            "current_password": "definitely-wrong-password",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Current password is incorrect" in body

    def test_short_new_password(self, auth_client, test_user):
        """New password under 8 chars must flash 'New password must be at least 8 characters.'"""
        resp = auth_client.post("/profile/change-password", data={
            "current_password": test_user["password"],
            "new_password": "short",
            "confirm_password": "short",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "New password must be at least 8 characters" in body

    def test_mismatched_passwords(self, auth_client, test_user):
        """Mismatched new/confirm must flash 'New passwords do not match.'"""
        resp = auth_client.post("/profile/change-password", data={
            "current_password": test_user["password"],
            "new_password": "newpassword123",
            "confirm_password": "differentpassword",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "New passwords do not match" in body


# ------------------------------------------------------------------ #
# 4. Successful password change                                        #
# ------------------------------------------------------------------ #

class TestChangePasswordSuccess:
    def test_flash_success_message(self, auth_client, test_user):
        """Valid submission must flash 'Password changed.' with success category."""
        resp = auth_client.post("/profile/change-password", data={
            "current_password": test_user["password"],
            "new_password": "newpassword456",
            "confirm_password": "newpassword456",
        }, follow_redirects=True)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Password changed" in body

    def test_password_hash_updated(self, auth_client, test_user):
        """After a successful change the stored hash must verify the new password."""
        new_password = "newpassword456"
        auth_client.post("/profile/change-password", data={
            "current_password": test_user["password"],
            "new_password": new_password,
            "confirm_password": new_password,
        })

        # Fetch the hash directly from the DB
        new_hash = _get_password_hash(test_user["id"])
        assert new_hash is not None, "User must still exist after password change"
        assert check_password_hash(new_hash, new_password), (
            "Stored hash must verify the new password"
        )
        assert not check_password_hash(new_hash, test_user["password"]), (
            "Stored hash must NOT verify the old password"
        )

    def test_old_password_no_longer_works(self, client, test_user):
        """After changing, the old password must not authenticate."""
        new_password = "newsecurepwd789"
        # Log in, change password
        client.post("/login", data={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        client.post("/profile/change-password", data={
            "current_password": test_user["password"],
            "new_password": new_password,
            "confirm_password": new_password,
        })

        # Log out
        client.get("/logout")

        # Try logging in with the old password — must fail
        resp = client.post("/login", data={
            "email": test_user["email"],
            "password": test_user["password"],
        }, follow_redirects=True)
        body = resp.get_data(as_text=True)
        assert "Invalid email or password" in body, (
            "Old password must not authenticate after a successful change"
        )

    def test_new_password_works_for_login(self, client, test_user):
        """After changing, the new password must authenticate."""
        new_password = "newsecurepwd789"
        # Log in, change password
        client.post("/login", data={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        client.post("/profile/change-password", data={
            "current_password": test_user["password"],
            "new_password": new_password,
            "confirm_password": new_password,
        })

        # Log out
        client.get("/logout")

        # Log in with the new password — must succeed
        resp = client.post("/login", data={
            "email": test_user["email"],
            "password": new_password,
        })
        assert resp.status_code == 302
        assert "/profile" in resp.headers["Location"]
