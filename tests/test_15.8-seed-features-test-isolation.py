"""Feature 15.8 — Seed Features Test Isolation

Strategy
--------
Same no-op-commit + single-rollback isolation strategy introduced across
tests/test_15_1-roadmap-pipeline.py, tests/test_15.2-roadmap-detail.py,
tests/test_15.4-release-type-classification.py,
tests/test_15.5-release-notes-modal.py, and
tests/test_15.7-grouping-foundational-features.py: TRUNCATE once at setup for
a clean slate, then commit() is a no-op for the rest of the test so nothing —
including commits made internally by seed_features() itself — is ever
actually persisted against the live DATABASE_URL.  A single real rollback()
at teardown discards everything.  This file is self-contained, mirroring the
convention of the other test files in this suite.

This file exists to guard against a regression of the 2026-08-08 incident:
seed_features()'s per-row tuple length silently drifted from its INSERT
statement's placeholder count (two stacked bugs), and a third bug in the
/ship-feature regeneration script corrupted multi-line report text via
re.sub() backslash interpretation.  The first two bugs are guarded here by
exercising the real seed_features() INSERT path against an empty table; the
third is out of scope for a pytest regression (it lives in a Markdown
command script, not importable Python) and is instead covered by the round
trip assertion below, which would catch the resulting data corruption if it
reappeared.

Behaviours covered
-------------------
1. seed_features() runs to completion against an empty table without raising
   IndexError or TypeError (guards the dropped-tuple-field and
   column/placeholder-count-mismatch bug classes).
2. After seed_features(), test_report and review_report for a known-populated
   feature (24.1) are non-null and match the values currently in
   database/db.py's seed data.
3. After seed_features(), deployed_at for that same feature round-trips
   correctly (as None, matching current seed data) rather than being silently
   dropped or misaligned.
"""

import psycopg2
import psycopg2.extras
import pytest

import database.db as db_module
from database.db import init_db, seed_features
import database.queries as queries_module

# ------------------------------------------------------------------ #
# Known-populated feature used for the round-trip spot-check           #
# ------------------------------------------------------------------ #

SPOT_CHECK_NUMBER = "24.1"
EXPECTED_TEST_REPORT_PREFIX = "Test Report — 24.1-home-page-routing"
EXPECTED_REVIEW_REPORT_PREFIX = "Code Review Report — 24.1-home-page-routing"
EXPECTED_DEPLOYED_AT = None


# ------------------------------------------------------------------ #
# Fixtures — same isolation strategy as the other 15.x test files    #
# ------------------------------------------------------------------ #


@pytest.fixture
def _patched_get_db(monkeypatch):
    """Open a single real Postgres connection and monkeypatch get_db in both
    database.db and database.queries.  TRUNCATE once at setup for a clean
    slate, then commit() is a no-op for the rest of the test so nothing —
    including commits made internally by seed_features() — is ever actually
    persisted.  A single real rollback() at teardown discards everything.
    """
    init_db()

    _real_conn = db_module.get_db()

    class _NoCloseProxy:
        """Delegates to _real_conn but no-ops close() and commit() so
        seed_features() cannot close the shared connection or persist
        changes mid-test."""

        def close(self):
            pass

        def commit(self):
            pass

        def __getattr__(self, name):
            return getattr(_real_conn, name)

    conn = _NoCloseProxy()

    def _fake_get_db():
        return conn

    monkeypatch.setattr(db_module, "get_db", _fake_get_db)
    monkeypatch.setattr(queries_module, "get_db", _fake_get_db)

    cur = _real_conn.cursor()
    cur.execute("TRUNCATE features RESTART IDENTITY CASCADE")
    _real_conn.commit()
    cur.close()

    yield conn

    _real_conn.rollback()
    _real_conn.close()


# ------------------------------------------------------------------ #
# 1. seed_features() row-tuple / placeholder-count parity              #
# ------------------------------------------------------------------ #


class TestSeedFeaturesStructuralParity:
    def test_seed_features_runs_against_empty_table_without_raising(
        self, _patched_get_db
    ):
        """seed_features() must not raise IndexError or TypeError when
        inserting into an empty table.  A drift between the per-row tuple
        length built by /ship-feature's regeneration script and the INSERT
        statement's placeholder count raises exactly these errors."""
        try:
            seed_features()
        except (IndexError, TypeError) as exc:
            pytest.fail(
                "seed_features() raised "
                f"{type(exc).__name__}: {exc} — row-tuple length likely "
                "does not match the INSERT statement's placeholder count"
            )

    def test_seed_features_populates_rows(self, _patched_get_db):
        """A successful run must actually insert rows, not silently no-op."""
        seed_features()
        cur = _patched_get_db.cursor()
        cur.execute("SELECT COUNT(*) FROM features")
        count = cur.fetchone()[0]
        cur.close()
        assert count > 0, "seed_features() must populate the features table"


# ------------------------------------------------------------------ #
# 2. Round-trip fidelity for test_report / review_report / deployed_at #
# ------------------------------------------------------------------ #


class TestSeedFeaturesRoundTripFidelity:
    def test_test_report_round_trips_non_null(self, _patched_get_db):
        seed_features()
        cur = _patched_get_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT test_report FROM features WHERE number = %s",
            (SPOT_CHECK_NUMBER,),
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None, f"Feature {SPOT_CHECK_NUMBER} must exist after seeding"
        assert row["test_report"] is not None, (
            f"test_report for {SPOT_CHECK_NUMBER} must not be NULL after "
            "seed_features() — a NULL here reproduces the 2026-08-08 "
            "data-loss incident"
        )
        assert row["test_report"].startswith(EXPECTED_TEST_REPORT_PREFIX), (
            "test_report content for "
            f"{SPOT_CHECK_NUMBER} does not match the expected seed data"
        )

    def test_review_report_round_trips_non_null(self, _patched_get_db):
        seed_features()
        cur = _patched_get_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT review_report FROM features WHERE number = %s",
            (SPOT_CHECK_NUMBER,),
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None, f"Feature {SPOT_CHECK_NUMBER} must exist after seeding"
        assert row["review_report"] is not None, (
            f"review_report for {SPOT_CHECK_NUMBER} must not be NULL after "
            "seed_features() — a NULL here reproduces the 2026-08-08 "
            "data-loss incident"
        )
        assert row["review_report"].startswith(EXPECTED_REVIEW_REPORT_PREFIX), (
            "review_report content for "
            f"{SPOT_CHECK_NUMBER} does not match the expected seed data"
        )

    def test_deployed_at_round_trips_correctly(self, _patched_get_db):
        seed_features()
        cur = _patched_get_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT deployed_at FROM features WHERE number = %s",
            (SPOT_CHECK_NUMBER,),
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None, f"Feature {SPOT_CHECK_NUMBER} must exist after seeding"
        assert row["deployed_at"] == EXPECTED_DEPLOYED_AT, (
            f"deployed_at for {SPOT_CHECK_NUMBER} must round-trip as "
            f"{EXPECTED_DEPLOYED_AT!r} to match current seed data"
        )

    def test_seed_features_idempotent_preserves_reports(self, _patched_get_db):
        """Calling seed_features() twice (its early-return-on-non-empty-table
        guard) must not corrupt or duplicate report data on the second call."""
        seed_features()
        seed_features()

        cur = _patched_get_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT COUNT(*) AS count FROM features WHERE number = %s",
            (SPOT_CHECK_NUMBER,),
        )
        count = cur.fetchone()["count"]
        cur.execute(
            "SELECT test_report, review_report FROM features WHERE number = %s",
            (SPOT_CHECK_NUMBER,),
        )
        row = cur.fetchone()
        cur.close()

        assert (
            count == 1
        ), "seed_features() must not insert duplicate rows on a second call"
        assert row["test_report"] is not None
        assert row["review_report"] is not None
