"""Step 5 — backend connection tests.

Each test points database.db.DB_PATH at a fresh tmp file, runs init_db()
+ seed_db(), and exercises a query helper or the /profile route. The
production spendly.db is never touched.
"""
import importlib
import os

import pytest

import database.db as db_module
import database.queries as queries
from database.db import init_db, seed_db, create_user


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Fresh sqlite file with the demo user (id=1) and 8 seed expenses."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    init_db()
    seed_db()
    yield


@pytest.fixture
def empty_user_db(tmp_path, monkeypatch):
    """Fresh sqlite file with one user but no expenses. Yields the user_id."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    init_db()
    user_id = create_user("Empty User", "empty@spendly.com", "password")
    yield user_id


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by a fresh seeded DB.

    app.py calls init_db() + seed_db() at import time against the real
    DB_PATH, so we re-seed our tmp DB and re-import the module so its
    module-level seed call hits the patched path.
    """
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    init_db()
    seed_db()

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


# ------------------------------------------------------------------ #
# Unit tests — get_user_by_id                                         #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(seeded_db):
    user = queries.get_user_by_id(1)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    # member_since formatted as "Month YYYY"
    assert len(user["member_since"].split()) == 2


def test_get_user_by_id_missing(seeded_db):
    assert queries.get_user_by_id(99999) is None


# ------------------------------------------------------------------ #
# Unit tests — get_summary_stats                                      #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(seeded_db):
    stats = queries.get_summary_stats(1)
    assert stats == {
        "total_spent": "₹345.49",
        "transaction_count": 8,
        "top_category": "Bills",
    }


def test_get_summary_stats_no_expenses(empty_user_db):
    user_id = empty_user_db
    stats = queries.get_summary_stats(user_id)
    assert stats == {
        "total_spent": "₹0.00",
        "transaction_count": 0,
        "top_category": "—",
    }


# ------------------------------------------------------------------ #
# Unit tests — get_recent_transactions                                #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_ordering_and_shape(seeded_db):
    txs = queries.get_recent_transactions(1)
    assert len(txs) == 8
    # Newest first: Apr 12 then Apr 11
    assert txs[0]["date"] == "Apr 12, 2026"
    assert txs[1]["date"] == "Apr 11, 2026"
    for tx in txs:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}
        assert tx["amount"].startswith("₹")


def test_get_recent_transactions_empty(empty_user_db):
    assert queries.get_recent_transactions(empty_user_db) == []


# ------------------------------------------------------------------ #
# Unit tests — get_category_breakdown                                 #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_ordered_and_sums_to_100(seeded_db):
    cats = queries.get_category_breakdown(1)
    assert len(cats) == 7
    # Ordered by amount desc
    amounts = [float(c["amount"].replace("₹", "").replace(",", "")) for c in cats]
    assert amounts == sorted(amounts, reverse=True)
    # First (largest) is Bills
    assert cats[0]["name"] == "Bills"
    # All percentages are ints and sum to 100
    assert all(isinstance(c["pct"], int) for c in cats)
    assert sum(c["pct"] for c in cats) == 100
    for c in cats:
        assert c["amount"].startswith("₹")


def test_get_category_breakdown_empty(empty_user_db):
    assert queries.get_category_breakdown(empty_user_db) == []


# ------------------------------------------------------------------ #
# Route tests — GET /profile                                          #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects_to_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_as_seed_user_renders_real_data(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "₹345.49" in body
    assert "Bills" in body
    # 8 transaction rows: count tx-amount cells
    assert body.count('class="tx-amount"') == 8
    # Newest-first: Apr 12 row appears before Apr 01
    assert body.index("Apr 12, 2026") < body.index("Apr 01, 2026")
    # Category breakdown lists all 7 categories
    for cat in ("Bills", "Shopping", "Health", "Transport", "Food",
                "Entertainment", "Other"):
        assert cat in body


def test_profile_as_brand_new_user_is_empty(client, tmp_path, monkeypatch):
    """A user with no expenses still renders 200 with zero values."""
    new_id = create_user("Newbie User", "new@spendly.com", "password123")
    with client.session_transaction() as sess:
        sess["user_id"] = new_id
        sess["user_name"] = "Newbie User"

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Newbie User" in body
    assert "₹0.00" in body
    assert "—" in body
    # Empty transactions table
    assert body.count('class="tx-amount"') == 0
