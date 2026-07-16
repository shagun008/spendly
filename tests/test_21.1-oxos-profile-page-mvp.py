"""Tests for Oxos Platform Page (21.1-oxos-profile-page-mvp)"""

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
# Tests for the / route (Oxos Platform page)                            #
# ------------------------------------------------------------------ #


class TestPlatformRoute:
    """Tests for the / route (Oxos Platform page)"""

    def test_root_route_exists(self, client):
        """Route `/` should exist and return 200"""
        response = client.get("/")
        assert response.status_code == 200

    def test_platform_is_public(self, client):
        """Route `/` should be accessible without authentication"""
        response = client.get("/")
        # Should not redirect to login since public
        assert response.status_code == 200

    def test_platform_extends_base(self, client):
        """Platform page should extend base.html (check for navbar)"""
        response = client.get("/")
        assert b"nav-brand" in response.data
        assert b"Oxos" in response.data

    def test_platform_has_business_outcomes(self, client):
        """Platform page should have Business Outcomes section"""
        response = client.get("/")
        assert b"Business Outcomes" in response.data
        assert b"Reports" in response.data
        assert b"Business Applications" in response.data

    def test_platform_has_learnings(self, client):
        """Platform page should have Learnings section with 5 items"""
        response = client.get("/")
        assert b"Learnings" in response.data
        assert b"No ORMs, raw SQL only" in response.data
        assert b"Passwords hashed with werkzeug" in response.data
        assert b"Use CSS variables" in response.data
        assert b"All templates extend base.html" in response.data
        assert b"Auth guard on protected routes" in response.data

    def test_expense_card_links_to_expense_home(self, client):
        """Expense card should link to /expense-home"""
        response = client.get("/")
        assert (
            b'href="/expense-home"' in response.data or b"expense_home" in response.data
        )


# ------------------------------------------------------------------ #
# Tests for the /expense-home route                                   #
# ------------------------------------------------------------------ #


class TestExpenseHomeRoute:
    """Tests for the /expense-home route"""

    def test_expense_home_route_exists(self, client):
        """Route `/expense-home` should exist and return 200"""
        response = client.get("/expense-home")
        assert response.status_code == 200

    def test_expense_home_is_public(self, client):
        """Route `/expense-home` should be public"""
        response = client.get("/expense-home")
        assert response.status_code == 200


# ------------------------------------------------------------------ #
# Template structure tests                                            #
# ------------------------------------------------------------------ #


class TestPlatformTemplate:
    """Template structure tests"""

    def test_platform_has_css(self, client):
        """Platform page should load its CSS file"""
        response = client.get("/")
        assert b"platform.css" in response.data

    def test_platform_has_lucide_icons(self, client):
        """Platform page should load Lucide icons"""
        response = client.get("/")
        assert b"lucide" in response.data

    def test_platform_footer_has_oxos(self, client):
        """Platform page footer should show Oxos"""
        response = client.get("/")
        # Check footer contains Oxos (not Spendly)
        assert b"Oxos" in response.data
