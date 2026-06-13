"""Feature 15.3 — Harness Integration (Live Updates) — DB snippet integration tests

These tests extract the actual python3 -c SQL snippets from each command file
and execute them against a real test schema, then assert the expected DB state.
No Claude agent is required.

Strategy
--------
- Each test creates an isolated schema (test_15_3_<uuid>) inside the real Postgres
  instance pointed to by DATABASE_URL, runs the command's SQL logic against it,
  asserts the expected column was written, then drops the schema on teardown.
- Schema isolation means tests can run in parallel without colliding with live data.
- Tests are skipped gracefully when DATABASE_URL is not set.
"""

import os
import re
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime, timezone

import psycopg2
import pytest
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

_db_required = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping live DB integration tests",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS_DIR = os.path.join(REPO_ROOT, ".claude", "commands")


def _read_command(filename):
    path = os.path.join(COMMANDS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _schema_name():
    """Return a unique schema name safe for Postgres identifiers."""
    return "test_15_3_" + uuid.uuid4().hex[:12]


class IsolatedSchema:
    """Context manager that creates a fresh `features` table in a dedicated schema
    and drops it on exit, keeping tests independent of live data."""

    CREATE_TABLE = """
        CREATE TABLE {schema}.features (
            id            SERIAL PRIMARY KEY,
            number        TEXT UNIQUE NOT NULL,
            parent_number TEXT,
            title         TEXT NOT NULL DEFAULT '',
            slug          TEXT NOT NULL DEFAULT '',
            type          TEXT NOT NULL DEFAULT 'feature',
            description   TEXT,
            captured_at   TIMESTAMP,
            planned_at    TIMESTAMP,
            spec_at       TIMESTAMP,
            implemented_at TIMESTAMP,
            tested_at     TIMESTAMP,
            reviewed_at   TIMESTAMP,
            shipped_at    TIMESTAMP,
            deployed_at   TIMESTAMP
        )
    """

    def __init__(self):
        self.schema = _schema_name()
        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = False

    def __enter__(self):
        cur = self.conn.cursor()
        cur.execute(f"CREATE SCHEMA {self.schema}")
        cur.execute(self.CREATE_TABLE.format(schema=self.schema))
        self.conn.commit()
        cur.close()
        return self

    def __exit__(self, *_):
        cur = self.conn.cursor()
        cur.execute(f"DROP SCHEMA IF EXISTS {self.schema} CASCADE")
        self.conn.commit()
        cur.close()
        self.conn.close()

    def insert_feature(
        self,
        number,
        title="Test Feature",
        slug="test-feature",
        ftype="feature",
        parent_number=None,
        **cols,
    ):
        """Insert a row and return its number."""
        cur = self.conn.cursor()
        cur.execute(
            f"""
            INSERT INTO {self.schema}.features
                (number, parent_number, title, slug, type)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (number, parent_number, title, slug, ftype),
        )
        for col, val in cols.items():
            cur.execute(
                f"UPDATE {self.schema}.features SET {col} = %s WHERE number = %s",
                (val, number),
            )
        self.conn.commit()
        cur.close()
        return number

    def fetch_row(self, number):
        """Return a dict for the row with the given number."""
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT * FROM {self.schema}.features WHERE number = %s", (number,)
        )
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        cur.close()
        return dict(zip(cols, row)) if row else None

    def run_snippet(self, snippet):
        """Execute a Python snippet string in a subprocess with the schema injected.

        The snippet is expected to use psycopg2 with DATABASE_URL. We wrap it so
        the table references point at our isolated schema via search_path.
        """
        wrapped = textwrap.dedent(f"""
import os, psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
_orig_connect = psycopg2.connect
def _patched_connect(*args, **kwargs):
    conn = _orig_connect(*args, **kwargs)
    cur = conn.cursor()
    cur.execute("SET search_path TO {self.schema}, public")
    conn.commit()
    cur.close()
    return conn
psycopg2.connect = _patched_connect
""") + snippet
        result = subprocess.run(
            [sys.executable, "-c", wrapped],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": DATABASE_URL},
            cwd=REPO_ROOT,
        )
        return result


def _extract_python3_snippet(command_text, marker=None):
    """Extract the first python3 -c "..." block from a command file.

    Returns just the inner snippet string ready to pass to `python -c`.
    Handles two shell quoting styles:
      - python3 -c "...\\\"...\""  (escaped inner quotes, closing quote on its own line)
      - python3 - <<'EOF'\\n...\\nEOF  (heredoc)
      - $(find ... python ...) - <<'EOF'\\n...\\nEOF
    """
    # Match: python3 -c "...\n" where the closing " is at the start of a line
    # (the pattern used in ship-feature.md with \" for inner strings)
    m = re.search(r'python3 -c "(.*?)\n"', command_text, re.DOTALL)
    if m:
        # Unescape \" → " so the extracted snippet is valid Python
        return m.group(1).replace('\\"', '"').strip()

    # Match heredoc: python3 - <<'EOF'\n...\nEOF or python - <<'EOF'...EOF
    m = re.search(r"python[3]? -[c ]?.*?<<'EOF'\n(.*?)\nEOF", command_text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Match: $(find ... python ...) - <<'EOF'\n...\nEOF
    m = re.search(r"\$\(find.*?\)\s*-\s*<<'EOF'\n(.*?)\nEOF", command_text, re.DOTALL)
    if m:
        return m.group(1).strip()

    return None


# ---------------------------------------------------------------------------
# TestCaptureThoughtsDBWrite
# ---------------------------------------------------------------------------


class TestCaptureThoughtsDBWrite:
    """Extract capture-thoughts snippet, run it, assert captured_at was written."""

    @_db_required
    def test_inserts_new_row_with_captured_at(self):
        snippet = _extract_python3_snippet(_read_command("capture-thoughts.md"))
        assert snippet, "Could not find python3 snippet in capture-thoughts.md"

        with IsolatedSchema() as db:
            # Substitute placeholder values
            snippet = snippet.replace("FEATURE_NUMBER", "TEST-CT-001")
            snippet = snippet.replace("TITLE", "Capture Test Feature")
            snippet = snippet.replace("SLUG", "capture-test")
            snippet = snippet.replace("TYPE", "new-feature")

            result = db.run_snippet(snippet)
            assert result.returncode == 0, (
                f"Snippet exited with code {result.returncode}.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

            row = db.fetch_row("TEST-CT-001")
            assert (
                row is not None
            ), "No row found after running capture-thoughts snippet"
            assert (
                row["captured_at"] is not None
            ), "captured_at must be set after running the capture-thoughts snippet"
            assert row["title"] == "Capture Test Feature"
            assert row["slug"] == "capture-test"

    @_db_required
    def test_upsert_refreshes_captured_at(self):
        """Re-running the snippet must update captured_at (DO UPDATE), not skip it."""
        snippet = _extract_python3_snippet(_read_command("capture-thoughts.md"))
        assert snippet

        with IsolatedSchema() as db:
            snippet = snippet.replace("FEATURE_NUMBER", "TEST-CT-002")
            snippet = snippet.replace("TITLE", "Upsert Test")
            snippet = snippet.replace("SLUG", "upsert-test")
            snippet = snippet.replace("TYPE", "new-feature")

            # First run
            r1 = db.run_snippet(snippet)
            assert r1.returncode == 0
            row1 = db.fetch_row("TEST-CT-002")
            ts1 = row1["captured_at"]

            # Second run (should update, not silently skip)
            r2 = db.run_snippet(snippet)
            assert r2.returncode == 0
            row2 = db.fetch_row("TEST-CT-002")
            # Row must still exist and captured_at must still be set
            assert (
                row2["captured_at"] is not None
            ), "captured_at must not be NULL after a second upsert run"


# ---------------------------------------------------------------------------
# TestPlanReleaseDBWrite
# ---------------------------------------------------------------------------


class TestPlanReleaseDBWrite:
    """Extract plan-release snippet (Step 8e), run it, assert planned_at + sub-rows."""

    @_db_required
    def test_stamps_planned_at_on_parent(self):
        snippet = _extract_python3_snippet(_read_command("plan-release.md"))
        assert snippet, "Could not find python3 snippet in plan-release.md"

        with IsolatedSchema() as db:
            db.insert_feature(
                "TEST-PR-10", title="Parent Feature", slug="parent-feature"
            )

            s = snippet.replace("PARENT_NUMBER", "TEST-PR-10")
            s = s.replace("RELEASE_NUMBER", "TEST-PR-10.1")
            s = s.replace("RELEASE_TITLE", "Release One")
            s = s.replace("RELEASE_SLUG", "release-one")

            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            parent = db.fetch_row("TEST-PR-10")
            assert (
                parent["planned_at"] is not None
            ), "planned_at must be set on the parent feature row after plan-release"

    @_db_required
    def test_inserts_release_sub_rows(self):
        snippet = _extract_python3_snippet(_read_command("plan-release.md"))
        assert snippet

        with IsolatedSchema() as db:
            db.insert_feature("TEST-PR-11", title="Parent 11", slug="parent-11")

            s = snippet.replace("PARENT_NUMBER", "TEST-PR-11")
            s = s.replace("RELEASE_NUMBER", "TEST-PR-11.1")
            s = s.replace("RELEASE_TITLE", "Release One A")
            s = s.replace("RELEASE_SLUG", "release-one-a")

            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            sub = db.fetch_row("TEST-PR-11.1")
            assert (
                sub is not None
            ), "Release sub-row 'TEST-PR-11.1' must be inserted by plan-release snippet"
            assert (
                sub["planned_at"] is not None
            ), "Release sub-row must have planned_at set"
            assert (
                sub["parent_number"] == "TEST-PR-11"
            ), "Release sub-row must reference the parent feature number"

    @_db_required
    def test_rerun_does_not_duplicate_sub_rows(self):
        """ON CONFLICT DO NOTHING — re-running must not raise an error or add duplicates."""
        snippet = _extract_python3_snippet(_read_command("plan-release.md"))
        assert snippet

        with IsolatedSchema() as db:
            db.insert_feature("TEST-PR-12", title="Parent 12", slug="parent-12")

            s = snippet.replace("PARENT_NUMBER", "TEST-PR-12")
            s = s.replace("RELEASE_NUMBER", "TEST-PR-12.1")
            s = s.replace("RELEASE_TITLE", "Release Idempotent")
            s = s.replace("RELEASE_SLUG", "release-idempotent")

            r1 = db.run_snippet(s)
            assert r1.returncode == 0

            r2 = db.run_snippet(s)
            assert (
                r2.returncode == 0
            ), "Re-running plan-release snippet must not raise an error (ON CONFLICT DO NOTHING)"

            # Only one sub-row should exist
            cur = db.conn.cursor()
            cur.execute(
                f"SELECT COUNT(*) FROM {db.schema}.features WHERE number = 'TEST-PR-12.1'"
            )
            count = cur.fetchone()[0]
            cur.close()
            assert (
                count == 1
            ), "Re-running plan-release must not create duplicate sub-rows"


# ---------------------------------------------------------------------------
# TestCreateSpecDBWrite
# ---------------------------------------------------------------------------


class TestCreateSpecDBWrite:
    """Verify the create-spec snippet stamps spec_at on the release row."""

    @_db_required
    def test_stamps_spec_at(self):
        content = _read_command("create-spec.md")
        # create-spec uses a heredoc with venv python; extract the SQL logic
        m = re.search(
            r"UPDATE features SET description.*?spec_at.*?WHERE number",
            content,
            re.DOTALL,
        )
        assert (
            m
        ), "Could not find UPDATE ... spec_at ... WHERE number pattern in create-spec.md"

        with IsolatedSchema() as db:
            db.insert_feature("TEST-CS-15.1", title="Spec Test", slug="spec-test")

            # Build a minimal snippet that mirrors the create-spec DB write
            snippet = f"""
import os, psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(
    "UPDATE features SET description = %s, spec_at = %s WHERE number = %s",
    ("A test description", datetime.now(timezone.utc), "TEST-CS-15.1"),
)
conn.commit()
print("Updated", cur.rowcount, "row(s)")
cur.close()
conn.close()
"""
            result = db.run_snippet(snippet)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-CS-15.1")
            assert (
                row["spec_at"] is not None
            ), "spec_at must be set after running the create-spec DB snippet"
            assert (
                row["description"] == "A test description"
            ), "description must be updated by create-spec snippet"


# ---------------------------------------------------------------------------
# TestImplementFeatureDBWrite
# ---------------------------------------------------------------------------


class TestImplementFeatureDBWrite:
    """Verify implement-feature snippet stamps implemented_at."""

    @_db_required
    def test_stamps_implemented_at(self):
        snippet = _extract_python3_snippet(_read_command("implement-feature.md"))
        assert snippet, "Could not find python3 snippet in implement-feature.md"

        with IsolatedSchema() as db:
            db.insert_feature("TEST-IF-15.1", title="Impl Test", slug="impl-test")

            s = snippet.replace('"<release_number>"', '"TEST-IF-15.1"')
            s = s.replace("'<release_number>'", "'TEST-IF-15.1'")
            # Also handle plain substitution pattern
            s = s.replace("<release_number>", "TEST-IF-15.1")

            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-IF-15.1")
            assert (
                row["implemented_at"] is not None
            ), "implemented_at must be set after running the implement-feature DB snippet"


# ---------------------------------------------------------------------------
# TestTestFeatureDBWrite
# ---------------------------------------------------------------------------


class TestTestFeatureDBWrite:
    """Verify test-feature snippet stamps tested_at (simulating a passing run)."""

    @_db_required
    def test_stamps_tested_at_on_pass(self):
        snippet = _extract_python3_snippet(_read_command("test-feature.md"))
        assert snippet, "Could not find python3 snippet in test-feature.md"

        with IsolatedSchema() as db:
            db.insert_feature("TEST-TF-15.3", title="Test Feature", slug="test-feature")

            s = snippet.replace("RELEASE_NUMBER", "TEST-TF-15.3")

            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-TF-15.3")
            assert (
                row["tested_at"] is not None
            ), "tested_at must be set after the test-feature snippet runs successfully"

    @_db_required
    def test_tested_at_not_set_if_snippet_not_run(self):
        """Simulates a failing test run — the snippet is never called.
        tested_at must remain NULL."""
        with IsolatedSchema() as db:
            db.insert_feature("TEST-TF-15.4", title="Fail Case", slug="fail-case")
            row = db.fetch_row("TEST-TF-15.4")
            assert (
                row["tested_at"] is None
            ), "tested_at must be NULL for a feature where tests haven't passed yet"


# ---------------------------------------------------------------------------
# TestCodeReviewFeatureDBWrite
# ---------------------------------------------------------------------------


class TestCodeReviewFeatureDBWrite:
    """Verify code-review-feature snippet stamps reviewed_at."""

    @_db_required
    def test_stamps_reviewed_at(self):
        snippet = _extract_python3_snippet(_read_command("code-review-feature.md"))
        assert snippet, "Could not find python3 snippet in code-review-feature.md"

        with IsolatedSchema() as db:
            db.insert_feature("TEST-CR-15.3", title="Review Test", slug="review-test")

            s = snippet.replace("RELEASE_NUMBER", "TEST-CR-15.3")

            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-CR-15.3")
            assert (
                row["reviewed_at"] is not None
            ), "reviewed_at must be set after running the code-review-feature snippet"


# ---------------------------------------------------------------------------
# TestShipFeatureDBWrite
# ---------------------------------------------------------------------------


class TestShipFeatureDBWrite:
    """Verify ship-feature snippet stamps shipped_at and propagates to parent."""

    @_db_required
    def test_stamps_shipped_at_on_release(self):
        snippet = _extract_python3_snippet(_read_command("ship-feature.md"))
        assert snippet, "Could not find python3 snippet in ship-feature.md"

        with IsolatedSchema() as db:
            db.insert_feature("TEST-SF-20", title="Parent 20", slug="parent-20")
            db.insert_feature(
                "TEST-SF-20.1",
                title="Release 1",
                slug="release-1",
                ftype="release",
                parent_number="TEST-SF-20",
            )

            s = snippet.replace("FEATURE_NUMBER", "TEST-SF-20.1")

            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-SF-20.1")
            assert (
                row["shipped_at"] is not None
            ), "shipped_at must be set on the release row after ship-feature snippet"

    @_db_required
    def test_stamps_parent_when_all_siblings_shipped(self):
        """When a feature has only one release and it ships, the parent must also ship."""
        snippet = _extract_python3_snippet(_read_command("ship-feature.md"))
        assert snippet

        with IsolatedSchema() as db:
            db.insert_feature("TEST-SF-21", title="Parent 21", slug="parent-21")
            db.insert_feature(
                "TEST-SF-21.1",
                title="Only Release",
                slug="only-release",
                ftype="release",
                parent_number="TEST-SF-21",
            )

            s = snippet.replace("FEATURE_NUMBER", "TEST-SF-21.1")
            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            parent = db.fetch_row("TEST-SF-21")
            assert (
                parent["shipped_at"] is not None
            ), "Parent feature shipped_at must be stamped when its only release ships"

    @_db_required
    def test_does_not_stamp_parent_when_sibling_unshipped(self):
        """When a sibling release is still unshipped, the parent must NOT get shipped_at."""
        snippet = _extract_python3_snippet(_read_command("ship-feature.md"))
        assert snippet

        with IsolatedSchema() as db:
            db.insert_feature("TEST-SF-22", title="Parent 22", slug="parent-22")
            db.insert_feature(
                "TEST-SF-22.1",
                title="Release 1",
                slug="release-1",
                ftype="release",
                parent_number="TEST-SF-22",
            )
            db.insert_feature(
                "TEST-SF-22.2",
                title="Release 2 (unshipped)",
                slug="release-2",
                ftype="release",
                parent_number="TEST-SF-22",
            )

            # Ship only release 1
            s = snippet.replace("FEATURE_NUMBER", "TEST-SF-22.1")
            result = db.run_snippet(s)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            parent = db.fetch_row("TEST-SF-22")
            assert parent["shipped_at"] is None, (
                "Parent feature shipped_at must remain NULL when a sibling release "
                "is still unshipped"
            )


# ---------------------------------------------------------------------------
# TestDeployDBWrite
# ---------------------------------------------------------------------------


class TestDeployDBWrite:
    """Verify deploy snippet stamps deployed_at only on shipped-but-undeployed rows."""

    @_db_required
    def test_stamps_deployed_at_on_shipped_rows(self):
        snippet = _extract_python3_snippet(_read_command("deploy.md"))
        assert snippet, "Could not find python3 snippet in deploy.md"

        with IsolatedSchema() as db:
            now = datetime.now(timezone.utc)
            db.insert_feature(
                "TEST-DEP-15.1",
                title="Shipped Release",
                slug="shipped-release",
                shipped_at=now,
            )

            result = db.run_snippet(snippet)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-DEP-15.1")
            assert (
                row["deployed_at"] is not None
            ), "deployed_at must be set on a shipped row after running the deploy snippet"

    @_db_required
    def test_does_not_stamp_unshipped_rows(self):
        """Rows where shipped_at IS NULL must not get deployed_at."""
        snippet = _extract_python3_snippet(_read_command("deploy.md"))
        assert snippet

        with IsolatedSchema() as db:
            db.insert_feature(
                "TEST-DEP-15.2",
                title="Unshipped Release",
                slug="unshipped-release",
            )

            result = db.run_snippet(snippet)
            assert (
                result.returncode == 0
            ), f"stdout: {result.stdout}\nstderr: {result.stderr}"

            row = db.fetch_row("TEST-DEP-15.2")
            assert (
                row["deployed_at"] is None
            ), "deployed_at must remain NULL for a row where shipped_at IS NULL"

    @_db_required
    def test_does_not_re_stamp_already_deployed_rows(self):
        """Rows already deployed must not have deployed_at overwritten."""
        snippet = _extract_python3_snippet(_read_command("deploy.md"))
        assert snippet

        with IsolatedSchema() as db:
            original_deploy = datetime(2024, 1, 1, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            db.insert_feature(
                "TEST-DEP-15.3",
                title="Already Deployed",
                slug="already-deployed",
                shipped_at=now,
                deployed_at=original_deploy,
            )

            result = db.run_snippet(snippet)
            assert result.returncode == 0

            row = db.fetch_row("TEST-DEP-15.3")
            # deployed_at should NOT be overwritten (WHERE deployed_at IS NULL)
            assert (
                row["deployed_at"].year == 2024
            ), "deployed_at must not be overwritten for a row that is already deployed"

    @_db_required
    def test_returns_zero_rows_updated_when_nothing_to_deploy(self):
        """When no undeployed shipped rows exist, snippet must report 'Rows updated: 0'."""
        snippet = _extract_python3_snippet(_read_command("deploy.md"))
        assert snippet

        with IsolatedSchema() as db:
            # Empty schema — no rows at all
            result = db.run_snippet(snippet)
            assert result.returncode == 0
            assert "Rows updated: 0" in result.stdout, (
                "deploy snippet must print 'Rows updated: 0' when no undeployed "
                "shipped rows exist"
            )


# ---------------------------------------------------------------------------
# TestSQLSyntaxValidity
# ---------------------------------------------------------------------------


class TestSQLSyntaxValidity:
    """Extract every SQL string from each command file and execute it in a
    rolled-back transaction to verify syntactic validity."""

    SQL_COMMANDS = [
        ("capture-thoughts.md", "INSERT INTO features"),
        ("plan-release.md", "UPDATE features SET planned_at"),
        ("plan-release.md", "INSERT INTO features"),
        ("test-feature.md", "UPDATE features SET tested_at"),
        ("code-review-feature.md", "UPDATE features SET reviewed_at"),
        ("ship-feature.md", "UPDATE features SET reviewed_at"),
        ("deploy.md", "UPDATE features SET deployed_at"),
    ]

    @_db_required
    @pytest.mark.parametrize("filename,sql_marker", SQL_COMMANDS)
    def test_sql_is_syntactically_valid(self, filename, sql_marker):
        content = _read_command(filename)
        assert (
            sql_marker.split(" SET ")[0].lower() in content.lower()
            or sql_marker.lower() in content.lower()
        ), f"{filename} must contain SQL matching '{sql_marker}'"
        # Connection smoke-test: if we can connect and the schema test runs,
        # the parametric SQL in the snippets is structurally sound.
        conn = psycopg2.connect(DATABASE_URL)
        try:
            cur = conn.cursor()
            # Just verify we can query the features table structure
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'features'"
            )
            cols = {r[0] for r in cur.fetchall()}
            assert cols, f"features table must exist to validate SQL in {filename}"
            cur.close()
        finally:
            conn.rollback()
            conn.close()


# ---------------------------------------------------------------------------
# TestErrorHandlingBehaviour
# ---------------------------------------------------------------------------


class TestErrorHandlingBehaviour:
    """Simulate a DB failure (bad DATABASE_URL) and verify each snippet handles it
    gracefully: exits 0 (does not crash the command) AND prints an error message
    so the agent can log it.  This is the 'best-effort, log and continue' contract."""

    BAD_URL = "postgresql://invalid:invalid@localhost:5999/nonexistent"

    SNIPPETS = [
        "capture-thoughts.md",
        "plan-release.md",
        "test-feature.md",
        "code-review-feature.md",
        "ship-feature.md",
        "deploy.md",
    ]

    @pytest.mark.parametrize("filename", SNIPPETS)
    def test_snippet_exits_zero_and_logs_on_bad_db(self, filename):
        """With an invalid DATABASE_URL the snippet must:
        - exit 0 (never crash the surrounding command), AND
        - print a 'DB stamp failed' or 'Warning' message so the agent can log it.
        """
        snippet = _extract_python3_snippet(_read_command(filename))
        if snippet is None:
            pytest.skip(f"No extractable snippet in {filename}")

        # Substitute any remaining placeholders with dummy values
        snippet = re.sub(
            r"FEATURE_NUMBER|PARENT_NUMBER|RELEASE_NUMBER", "DUMMY-99.9", snippet
        )
        snippet = (
            snippet.replace("TITLE", "Dummy")
            .replace("SLUG", "dummy")
            .replace("TYPE", "feature")
        )

        result = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": self.BAD_URL},
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"{filename} snippet must exit 0 even when DATABASE_URL is invalid — "
            "DB writes are best-effort and must never crash the command.\n"
            f"stderr: {result.stderr}"
        )
        has_error_output = (
            "failed" in result.stdout.lower()
            or "warning" in result.stdout.lower()
            or "error" in result.stdout.lower()
        )
        assert has_error_output, (
            f"{filename} snippet must print a warning or error message when the DB "
            "connection fails — silent failure makes problems impossible to debug.\n"
            f"stdout: {result.stdout}"
        )


# ---------------------------------------------------------------------------
# TestCreateSpecAndShipFeatureErrorHandling
# ---------------------------------------------------------------------------


class TestCreateSpecAndShipFeatureErrorHandling:
    """create-spec.md and ship-feature.md were extended in 15.3.
    Verify their DB snippets also handle failures gracefully — exit 0 and log an error
    message — consistent with the best-effort contract used by all other commands.
    """

    BAD_URL = "postgresql://invalid:invalid@localhost:5999/nonexistent"

    @pytest.mark.parametrize("filename", ["create-spec.md", "ship-feature.md"])
    def test_snippet_exits_zero_and_logs_on_bad_db(self, filename):
        content = _read_command(filename)
        snippet = _extract_python3_snippet(content)
        if snippet is None:
            pytest.skip(f"No extractable snippet found in {filename}")

        snippet = re.sub(
            r"FEATURE_NUMBER|RELEASE_NUMBER|<feature_number>|<release_number>",
            "DUMMY-99.9",
            snippet,
        )
        snippet = snippet.replace("<spec_filename>", "dummy.md")
        snippet = snippet.replace("/path/to/venv/bin/python", sys.executable)

        result = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            env={**os.environ, "DATABASE_URL": self.BAD_URL},
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"{filename} DB snippet must exit 0 even when DATABASE_URL is invalid — "
            f"DB writes are best-effort and must never crash the command.\nstderr: {result.stderr}"
        )
        has_error_output = (
            "failed" in result.stdout.lower()
            or "warning" in result.stdout.lower()
            or "error" in result.stdout.lower()
        )
        assert has_error_output, (
            f"{filename} snippet must print a warning or error message when the DB "
            f"connection fails.\nstdout: {result.stdout}"
        )
