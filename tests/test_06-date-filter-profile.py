"""Step 6 — date-filter on /profile tests.

Strategy: monkeypatch database.db.DB_PATH to a fresh tmp file, seed it with
the canonical demo data, then reload app so the module-level init_db()/seed_db()
hits the patched path. All tests go through Flask's test client; sessions are
injected directly to avoid depending on the login route's form behaviour.

Seed data (from database/db.py seed_db):
  | date       | description      | category      | amount |
  |------------|------------------|---------------|--------|
  | 2026-04-01 | Lunch at cafe    | Food          |  12.50 |
  | 2026-04-02 | Monthly bus pass | Transport     |  35.00 |
  | 2026-04-03 | Electricity bill | Bills         | 120.00 |
  | 2026-04-05 | Pharmacy         | Health        |  45.00 |
  | 2026-04-07 | Movie ticket     | Entertainment |  20.00 |
  | 2026-04-09 | New shirt        | Shopping      |  89.99 |
  | 2026-04-11 | Coffee and snack | Food          |   8.00 |
  | 2026-04-12 | Miscellaneous    | Other         |  15.00 |
  Total: 345.49
"""
import importlib

import pytest

import database.db as db_module
from database.db import init_db, seed_db


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by a fresh seeded tmp DB.

    Mirrors the pattern from test_backend_connection.py: patch DB_PATH first,
    seed, then reload app so its module-level init_db/seed_db hits the tmp DB.
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


# ------------------------------------------------------------------ #
# Helper                                                               #
# ------------------------------------------------------------------ #

def _body(response):
    return response.get_data(as_text=True)


# ------------------------------------------------------------------ #
# 1. Unauthenticated access                                           #
# ------------------------------------------------------------------ #

class TestUnauthenticatedAccess:
    def test_get_profile_without_session_redirects(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "Expected redirect for unauthenticated request"
        assert "/login" in resp.headers["Location"], (
            "Redirect target should be /login"
        )

    def test_get_profile_with_filter_params_unauthenticated_redirects(self, client):
        resp = client.get("/profile?date_from=2026-04-01&date_to=2026-04-07")
        assert resp.status_code == 302, (
            "Filter params must not bypass auth guard"
        )
        assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# 2. Unfiltered profile (all-time)                                    #
# ------------------------------------------------------------------ #

class TestUnfilteredProfile:
    def test_returns_200(self, auth_client):
        resp = auth_client.get("/profile")
        assert resp.status_code == 200

    def test_shows_user_name(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert "Demo User" in body, "Profile page must show the user's name"

    def test_shows_all_time_total(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert "₹345.49" in body, "Unfiltered total must be ₹345.49"

    def test_shows_all_eight_transactions(self, auth_client):
        body = _body(auth_client.get("/profile"))
        # Each transaction row renders an amount cell with class "tx-amount"
        assert body.count('class="tx-amount"') == 8, (
            "All 8 seed transactions must appear unfiltered"
        )

    def test_rupee_symbol_present(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert "₹" in body, "Currency symbol ₹ must appear on unfiltered page"


# ------------------------------------------------------------------ #
# 3. Custom date range — both bounds                                   #
# ------------------------------------------------------------------ #

class TestBothDateBounds:
    """date_from=2026-04-01 & date_to=2026-04-07 → Apr01,02,03,05,07 = 5 txns"""

    def test_returns_200(self, auth_client):
        resp = auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07")
        assert resp.status_code == 200

    def test_total_is_correct(self, auth_client):
        # 12.50 + 35.00 + 120.00 + 45.00 + 20.00 = 232.50
        body = _body(auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07"))
        assert "₹232.50" in body, "Filtered total must be ₹232.50"

    def test_transaction_count_is_five(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07"))
        assert body.count('class="tx-amount"') == 5, (
            "Only 5 transactions fall in 2026-04-01..2026-04-07"
        )

    def test_lower_bound_is_inclusive(self, auth_client):
        # Apr 01 entry "Lunch at cafe" must appear
        body = _body(auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07"))
        assert "Lunch at cafe" in body, "date_from bound must be inclusive"

    def test_upper_bound_is_inclusive(self, auth_client):
        # Apr 07 entry "Movie ticket" must appear
        body = _body(auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07"))
        assert "Movie ticket" in body, "date_to bound must be inclusive"

    def test_out_of_range_expense_excluded(self, auth_client):
        # Apr 09 "New shirt" must NOT appear
        body = _body(auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07"))
        assert "New shirt" not in body, "Expense outside the range must be excluded"

    def test_rupee_symbol_still_present(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=2026-04-01&date_to=2026-04-07"))
        assert "₹" in body, "₹ symbol must appear on filtered page"


# ------------------------------------------------------------------ #
# 4. Only date_from provided                                          #
# ------------------------------------------------------------------ #

class TestOnlyDateFrom:
    """date_from=2026-04-09 → Apr09,11,12 = 3 txns, ₹112.99"""

    def test_returns_200(self, auth_client):
        resp = auth_client.get("/profile?date_from=2026-04-09")
        assert resp.status_code == 200

    def test_total_is_correct(self, auth_client):
        # 89.99 + 8.00 + 15.00 = 112.99
        body = _body(auth_client.get("/profile?date_from=2026-04-09"))
        assert "₹112.99" in body, "date_from-only total must be ₹112.99"

    def test_transaction_count_is_three(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=2026-04-09"))
        assert body.count('class="tx-amount"') == 3, (
            "3 transactions on or after 2026-04-09"
        )

    def test_date_from_bound_is_inclusive(self, auth_client):
        # Apr 09 "New shirt" must appear
        body = _body(auth_client.get("/profile?date_from=2026-04-09"))
        assert "New shirt" in body, "date_from bound must be inclusive"

    def test_earlier_expenses_excluded(self, auth_client):
        # Apr 07 "Movie ticket" is before date_from and must be excluded
        body = _body(auth_client.get("/profile?date_from=2026-04-09"))
        assert "Movie ticket" not in body, "Expenses before date_from must be excluded"


# ------------------------------------------------------------------ #
# 5. Only date_to provided                                            #
# ------------------------------------------------------------------ #

class TestOnlyDateTo:
    """date_to=2026-04-03 → Apr01,02,03 = 3 txns, ₹167.50"""

    def test_returns_200(self, auth_client):
        resp = auth_client.get("/profile?date_to=2026-04-03")
        assert resp.status_code == 200

    def test_total_is_correct(self, auth_client):
        # 12.50 + 35.00 + 120.00 = 167.50
        body = _body(auth_client.get("/profile?date_to=2026-04-03"))
        assert "₹167.50" in body, "date_to-only total must be ₹167.50"

    def test_transaction_count_is_three(self, auth_client):
        body = _body(auth_client.get("/profile?date_to=2026-04-03"))
        assert body.count('class="tx-amount"') == 3, (
            "3 transactions on or before 2026-04-03"
        )

    def test_date_to_bound_is_inclusive(self, auth_client):
        # Apr 03 "Electricity bill" must appear
        body = _body(auth_client.get("/profile?date_to=2026-04-03"))
        assert "Electricity bill" in body, "date_to bound must be inclusive"

    def test_later_expenses_excluded(self, auth_client):
        # Apr 05 "Pharmacy" is after date_to and must be excluded
        body = _body(auth_client.get("/profile?date_to=2026-04-03"))
        assert "Pharmacy" not in body, "Expenses after date_to must be excluded"


# ------------------------------------------------------------------ #
# 6. Reversed dates (date_from > date_to)                             #
# ------------------------------------------------------------------ #

class TestReversedDates:
    URL = "/profile?date_from=2026-04-30&date_to=2026-04-01"

    def test_returns_200(self, auth_client):
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200

    def test_flash_error_present(self, auth_client):
        body = _body(auth_client.get(self.URL))
        assert "Start date must be before end date." in body, (
            "Flash error must appear when date_from > date_to"
        )

    def test_falls_back_to_unfiltered_total(self, auth_client):
        body = _body(auth_client.get(self.URL))
        assert "₹345.49" in body, (
            "Reversed-date fallback must show all-time total ₹345.49"
        )

    def test_falls_back_to_all_eight_transactions(self, auth_client):
        body = _body(auth_client.get(self.URL))
        assert body.count('class="tx-amount"') == 8, (
            "Reversed-date fallback must show all 8 transactions"
        )


# ------------------------------------------------------------------ #
# 7. Malformed date_from                                              #
# ------------------------------------------------------------------ #

class TestMalformedDateFrom:
    def test_returns_200_not_500(self, auth_client):
        resp = auth_client.get("/profile?date_from=not-a-date")
        assert resp.status_code == 200, "Malformed date must not crash the app"

    def test_falls_back_to_unfiltered_total(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=not-a-date"))
        assert "₹345.49" in body, (
            "Malformed date_from must fall back to all-time total"
        )

    def test_falls_back_to_all_eight_transactions(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=not-a-date"))
        assert body.count('class="tx-amount"') == 8, (
            "Malformed date_from must fall back to all 8 transactions"
        )


@pytest.mark.parametrize("params", [
    "date_from=not-a-date",
    "date_to=not-a-date",
    "date_from=not-a-date&date_to=also-bad",
    "date_from=20260401",          # wrong format (no hyphens)
    "date_from=2026-13-01",        # invalid month
    "date_from=2026-04-99",        # invalid day
    "date_from=abc&date_to=xyz",
])
def test_malformed_date_params_do_not_crash(auth_client, params):
    """All malformed date inputs must silently fall back to unfiltered view."""
    resp = auth_client.get(f"/profile?{params}")
    assert resp.status_code == 200, (
        f"Malformed params '{params}' must return 200, not crash"
    )
    body = _body(resp)
    assert "₹345.49" in body, (
        f"Malformed params '{params}' must fall back to all-time total ₹345.49"
    )


# ------------------------------------------------------------------ #
# 8. Empty range (no expenses match the filter)                       #
# ------------------------------------------------------------------ #

class TestEmptyRange:
    URL = "/profile?date_from=2025-01-01&date_to=2025-01-31"

    def test_returns_200(self, auth_client):
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200, "Empty-range filter must return 200"

    def test_total_is_zero(self, auth_client):
        body = _body(auth_client.get(self.URL))
        assert "₹0.00" in body, "Empty range must show ₹0.00 total"

    def test_zero_transactions(self, auth_client):
        body = _body(auth_client.get(self.URL))
        assert body.count('class="tx-amount"') == 0, (
            "Empty range must show 0 transaction rows"
        )

    def test_no_server_error_in_body(self, auth_client):
        body = _body(auth_client.get(self.URL))
        # A 200 with no traceback text means no internal error surfaced
        assert "Internal Server Error" not in body
        assert "Traceback" not in body


# ------------------------------------------------------------------ #
# 9. Filter form is present in the HTML                               #
# ------------------------------------------------------------------ #

class TestFilterFormPresent:
    def test_form_with_method_get_exists(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert 'method="get"' in body.lower() or "method='get'" in body.lower(), (
            "Profile page must contain a form with method=get for the date filter"
        )

    def test_date_from_input_present(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert 'name="date_from"' in body or "name='date_from'" in body, (
            "Filter form must have an input named date_from"
        )

    def test_date_to_input_present(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert 'name="date_to"' in body or "name='date_to'" in body, (
            "Filter form must have an input named date_to"
        )

    def test_preset_links_present(self, auth_client):
        body = _body(auth_client.get("/profile"))
        # All four preset labels must appear in the filter bar
        for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
            assert label in body, f"Preset link '{label}' must appear on profile page"


# ------------------------------------------------------------------ #
# 10. Filter notice shown when date_from is provided                  #
# ------------------------------------------------------------------ #

class TestFilterNoticeShown:
    def test_showing_results_present_with_date_from(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=2026-04-09"))
        assert "Showing results" in body, (
            "'Showing results' notice must appear when date_from is active"
        )

    def test_showing_results_present_with_date_to(self, auth_client):
        body = _body(auth_client.get("/profile?date_to=2026-04-03"))
        assert "Showing results" in body, (
            "'Showing results' notice must appear when date_to is active"
        )

    def test_showing_results_present_with_both_bounds(self, auth_client):
        body = _body(auth_client.get(
            "/profile?date_from=2026-04-01&date_to=2026-04-07"
        ))
        assert "Showing results" in body, (
            "'Showing results' notice must appear when both date bounds are active"
        )


# ------------------------------------------------------------------ #
# 11. Filter notice absent when no filter params                      #
# ------------------------------------------------------------------ #

class TestFilterNoticeAbsent:
    def test_showing_results_absent_on_unfiltered_page(self, auth_client):
        body = _body(auth_client.get("/profile"))
        assert "Showing results" not in body, (
            "'Showing results' must NOT appear when no filter is active"
        )

    def test_showing_results_absent_after_reversed_date_fallback(self, auth_client):
        # Reversed dates cause fallback to unfiltered — notice must not show
        body = _body(
            auth_client.get("/profile?date_from=2026-04-30&date_to=2026-04-01")
        )
        assert "Showing results" not in body, (
            "'Showing results' must NOT appear on reversed-date fallback"
        )


# ------------------------------------------------------------------ #
# 12. All amounts use ₹ on filtered responses                         #
# ------------------------------------------------------------------ #

class TestRupeeSymbolOnFilteredResponses:
    def test_rupee_present_with_both_date_bounds(self, auth_client):
        body = _body(auth_client.get(
            "/profile?date_from=2026-04-01&date_to=2026-04-07"
        ))
        assert "₹" in body, "₹ symbol must appear on filtered (both bounds) page"

    def test_rupee_present_with_only_date_from(self, auth_client):
        body = _body(auth_client.get("/profile?date_from=2026-04-09"))
        assert "₹" in body, "₹ symbol must appear on date_from-only filtered page"

    def test_rupee_present_with_only_date_to(self, auth_client):
        body = _body(auth_client.get("/profile?date_to=2026-04-03"))
        assert "₹" in body, "₹ symbol must appear on date_to-only filtered page"

    def test_rupee_present_on_empty_range(self, auth_client):
        body = _body(auth_client.get(
            "/profile?date_from=2025-01-01&date_to=2025-01-31"
        ))
        assert "₹0.00" in body, "₹ symbol must appear even when the range is empty"


# ------------------------------------------------------------------ #
# Edge cases / boundary precision                                      #
# ------------------------------------------------------------------ #

class TestEdgeCases:
    def test_single_day_range_exact_match(self, auth_client):
        """A range of exactly one day returns only that day's expense."""
        # Apr 03 only → Electricity bill = 120.00
        body = _body(auth_client.get(
            "/profile?date_from=2026-04-03&date_to=2026-04-03"
        ))
        assert "₹120.00" in body, "Single-day range must return that day's total"
        assert body.count('class="tx-amount"') == 1

    def test_single_day_range_expense_description_present(self, auth_client):
        body = _body(auth_client.get(
            "/profile?date_from=2026-04-03&date_to=2026-04-03"
        ))
        assert "Electricity bill" in body

    def test_future_date_range_empty(self, auth_client):
        """A range entirely in the future returns no transactions."""
        resp = auth_client.get("/profile?date_from=2099-01-01&date_to=2099-12-31")
        assert resp.status_code == 200, "Future date range must return 200, not crash"
        body = _body(resp)
        assert "₹0.00" in body, "Future date range must show ₹0.00 total"
        assert body.count('class="tx-amount"') == 0, (
            "Future date range must show 0 transactions"
        )

    def test_malformed_date_to_with_valid_date_from_falls_back(self, auth_client):
        """If date_to is malformed but date_from is valid, only date_from is applied."""
        # The spec says a malformed param is silently ignored (treated as absent).
        # date_from=2026-04-09 is valid; date_to=bad-date is dropped.
        # Effective filter: date_from=2026-04-09 only → 3 transactions (Apr09,11,12).
        resp = auth_client.get("/profile?date_from=2026-04-09&date_to=bad-date")
        assert resp.status_code == 200, "Valid date_from + malformed date_to must return 200"
        body = _body(resp)
        assert body.count('class="tx-amount"') == 3, (
            "Valid date_from + malformed date_to should apply only the date_from filter"
        )

    def test_sql_injection_attempt_in_date_from_does_not_crash(self, auth_client):
        """Parameterised queries must safely handle injection attempts in date fields."""
        resp = auth_client.get(
            "/profile?date_from=2026-04-01' OR '1'%3D'1"
        )
        # The value won't parse as YYYY-MM-DD so it is silently ignored
        assert resp.status_code == 200, "SQL injection attempt must return 200"
        body = _body(resp)
        assert "₹345.49" in body, (
            "SQL injection in date_from must fall back to unfiltered view"
        )
