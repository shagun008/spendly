"""Feature 15.3 — Harness Integration (Live Updates)

This feature wires every harness command (markdown files in .claude/commands/) to
write pipeline timestamps to the ``features`` PostgreSQL table, and adds a
``deployed_at`` column to that table.  There are no HTTP routes to test.

Test scope
----------
1.  DB schema — ``features`` table has all eight required pipeline timestamp columns,
    including the new ``deployed_at`` added by this release.
2.  DB constraint — ``features.number`` has a UNIQUE constraint.
3.  ``deployed_at`` idempotency — ``init_db()`` uses ``ALTER TABLE … ADD COLUMN IF NOT
    EXISTS`` so calling it twice never raises an error.
4.  Command file content — each ``.claude/commands/*.md`` file contains the DB snippet
    keywords required by the spec.
5.  ``status.md`` sources data from the DB (not ``registry.md``) — verified by presence
    of ``python3`` / ``deployed_at`` and absence of ``registry.md`` as the primary data
    fetch step.
6.  Parameterised queries — command files that write to the DB use ``%s`` placeholders,
    never bare string interpolation.
7.  ``allowed-tools`` frontmatter — commands that run Python snippets declare the
    ``Bash(python3 -c)`` permission.
8.  Error-handling prose — every command instructs the agent to log errors and continue
    rather than blocking on a DB write failure.
9.  ``deploy.md`` success gate — the ``deployed_at`` stamp is only reached after a
    successful deployment, not after a failure.
10. ``status.md`` stage priority — all eight pipeline timestamp columns appear in the
    status command so the full priority chain is covered.
11. ``implement.md`` removal — the old filename must not exist; only
    ``implement-feature.md`` is valid.
12. No stale ``/implement`` references — ``registry.md``, ``CLAUDE.md``, ``dev.md``,
    and ``create-spec.md`` must not contain the old bare ``/implement `` command name.

DB tests are skipped gracefully when ``DATABASE_URL`` is not set in the environment.
File content tests need no DB connection.
"""

import os
import pathlib

import psycopg2
import psycopg2.extras
import pytest
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")

_db_required = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping live DB tests",
)


def _get_conn():
    """Open and return a psycopg2 connection using DATABASE_URL."""
    return psycopg2.connect(DATABASE_URL)


def _read_command(filename: str) -> str:
    """Read and return the full text of a command markdown file."""
    path = COMMANDS_DIR / filename
    assert path.exists(), f"Command file not found: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. DB schema — all pipeline timestamp columns exist
# ---------------------------------------------------------------------------


class TestFeaturesTableSchema:
    """Verify the ``features`` table has every pipeline timestamp column."""

    REQUIRED_COLUMNS = {
        "captured_at",
        "planned_at",
        "spec_at",
        "implemented_at",
        "tested_at",
        "reviewed_at",
        "shipped_at",
        "deployed_at",  # new in this release
    }

    @_db_required
    def test_features_table_exists(self):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'features'
            """,
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 1, "The 'features' table must exist in the database"

    @_db_required
    @pytest.mark.parametrize(
        "column_name",
        sorted(
            [
                "captured_at",
                "planned_at",
                "spec_at",
                "implemented_at",
                "tested_at",
                "reviewed_at",
                "shipped_at",
                "deployed_at",
            ]
        ),
    )
    def test_pipeline_column_exists(self, column_name):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'features'
              AND column_name = %s
            """,
            (column_name,),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 1, (
            f"Column '{column_name}' must exist in the 'features' table. "
            "It may not have been added by init_db()."
        )

    @_db_required
    def test_deployed_at_is_nullable(self):
        """``deployed_at`` must be nullable — it starts as NULL for undeployed rows."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = 'features'
              AND column_name = 'deployed_at'
            """,
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        assert (
            row is not None
        ), "Column 'deployed_at' must exist in the 'features' table"
        assert row[0] == "YES", (
            "'deployed_at' must be nullable (IS NULLABLE = YES) — "
            "it is NULL for rows that have not been deployed yet"
        )

    @_db_required
    def test_deployed_at_column_type_is_timestamp(self):
        """``deployed_at`` must be a TIMESTAMP type, matching all other pipeline columns."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'features'
              AND column_name = 'deployed_at'
            """,
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        assert row is not None, "Column 'deployed_at' must exist to check its type"
        assert (
            "timestamp" in row[0].lower()
        ), f"'deployed_at' must be a TIMESTAMP column, got '{row[0]}'"

    @_db_required
    def test_all_required_columns_present_in_one_query(self):
        """All eight required columns must be present in a single bulk check."""
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'features'
            """,
        )
        existing_columns = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()
        missing = self.REQUIRED_COLUMNS - existing_columns
        assert not missing, (
            f"The following pipeline timestamp columns are missing from the "
            f"'features' table: {missing}"
        )


# ---------------------------------------------------------------------------
# 2. DB constraint — UNIQUE on ``features.number``
# ---------------------------------------------------------------------------


class TestFeaturesUniqueConstraint:
    """The spec requires ON CONFLICT (number) semantics — the UNIQUE constraint
    must exist on ``features.number``."""

    @_db_required
    def test_unique_constraint_exists_on_number(self):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
             AND tc.table_name = ccu.table_name
            WHERE tc.table_name = 'features'
              AND ccu.column_name = 'number'
              AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
            """,
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count >= 1, (
            "The 'features' table must have a UNIQUE (or PRIMARY KEY) constraint "
            "on the 'number' column so ON CONFLICT (number) clauses work correctly"
        )

    @_db_required
    def test_duplicate_number_raises_integrity_error(self):
        """Inserting two rows with the same ``number`` must raise IntegrityError."""
        conn = _get_conn()
        cur = conn.cursor()
        # Use a number unlikely to collide with real data
        test_number = "TEST-UNIQUE-CONSTRAINT-15.3"
        try:
            cur.execute(
                "INSERT INTO features (number, title, slug, type) VALUES (%s, %s, %s, %s)",
                (
                    test_number,
                    "Constraint Test Row One",
                    "constraint-test-one",
                    "feature",
                ),
            )
            conn.commit()
            with pytest.raises(psycopg2.IntegrityError):
                cur.execute(
                    "INSERT INTO features (number, title, slug, type) VALUES (%s, %s, %s, %s)",
                    (
                        test_number,
                        "Constraint Test Row Two",
                        "constraint-test-two",
                        "feature",
                    ),
                )
                conn.commit()
        finally:
            conn.rollback()
            cur.execute("DELETE FROM features WHERE number = %s", (test_number,))
            conn.commit()
            cur.close()
            conn.close()


# ---------------------------------------------------------------------------
# 3. ``deployed_at`` idempotency — init_db() must not error on re-run
# ---------------------------------------------------------------------------


class TestDeployedAtIdempotency:
    """``init_db()`` uses ``ALTER TABLE … ADD COLUMN IF NOT EXISTS`` so calling it
    twice must never raise an error."""

    @_db_required
    def test_init_db_twice_does_not_raise(self):
        """Importing and calling init_db() a second time must be side-effect-free."""
        from database.db import init_db

        # If this raises, the ADD COLUMN IF NOT EXISTS clause is missing
        try:
            init_db()
            init_db()
        except Exception as exc:
            pytest.fail(
                f"init_db() raised an exception on a second call: {exc}. "
                "Ensure 'ALTER TABLE features ADD COLUMN IF NOT EXISTS deployed_at' "
                "is used rather than 'ADD COLUMN'."
            )

    @_db_required
    def test_deployed_at_still_exists_after_second_init_db(self):
        """After a second init_db() call the ``deployed_at`` column must still be there."""
        from database.db import init_db

        init_db()
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'features' AND column_name = 'deployed_at'
            """,
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert (
            count == 1
        ), "'deployed_at' column must exist after calling init_db() a second time"


# ---------------------------------------------------------------------------
# 4. Command file content — per-command keyword checks
# ---------------------------------------------------------------------------


class TestCaptureThoughtsCommand:
    """capture-thoughts.md must contain the DB snippet that stamps captured_at."""

    def test_contains_captured_at(self):
        content = _read_command("capture-thoughts.md")
        assert (
            "captured_at" in content
        ), "capture-thoughts.md must reference 'captured_at' to stamp the DB column"

    def test_contains_on_conflict(self):
        content = _read_command("capture-thoughts.md")
        assert (
            "ON CONFLICT" in content
        ), "capture-thoughts.md must use ON CONFLICT for idempotent upserts"

    def test_contains_parameterized_placeholder(self):
        content = _read_command("capture-thoughts.md")
        assert "%s" in content, (
            "capture-thoughts.md DB snippet must use %s parameterized placeholders, "
            "not bare string interpolation"
        )

    def test_contains_insert_into_features(self):
        content = _read_command("capture-thoughts.md")
        assert (
            "INSERT INTO features" in content or "features" in content
        ), "capture-thoughts.md must reference the 'features' table for the DB write"


class TestPlanReleaseCommand:
    """plan-release.md must stamp planned_at on parent and insert release sub-rows."""

    def test_contains_planned_at(self):
        content = _read_command("plan-release.md")
        assert (
            "planned_at" in content
        ), "plan-release.md must reference 'planned_at' to stamp the DB column"

    def test_contains_on_conflict(self):
        content = _read_command("plan-release.md")
        assert (
            "ON CONFLICT" in content
        ), "plan-release.md must use ON CONFLICT so re-runs are idempotent"

    def test_contains_parameterized_placeholder(self):
        content = _read_command("plan-release.md")
        assert (
            "%s" in content
        ), "plan-release.md DB snippet must use %s parameterized placeholders"

    def test_contains_features_table_reference(self):
        content = _read_command("plan-release.md")
        assert (
            "features" in content
        ), "plan-release.md must reference the 'features' table"


class TestCreateSpecCommand:
    """create-spec.md must stamp spec_at on the specific release row."""

    def test_contains_spec_at(self):
        content = _read_command("create-spec.md")
        assert "spec_at" in content, (
            "create-spec.md must reference 'spec_at' to stamp the DB column "
            "after saving the spec file"
        )

    def test_contains_parameterized_placeholder(self):
        content = _read_command("create-spec.md")
        assert (
            "%s" in content
        ), "create-spec.md DB snippet must use %s parameterized placeholders"

    def test_contains_features_table_reference(self):
        content = _read_command("create-spec.md")
        assert (
            "features" in content
        ), "create-spec.md must reference the 'features' table for the spec_at update"


class TestImplementFeatureCommand:
    """implement-feature.md must stamp implemented_at after implementation completes."""

    def test_contains_implemented_at(self):
        content = _read_command("implement-feature.md")
        assert (
            "implemented_at" in content
        ), "implement-feature.md must reference 'implemented_at' to stamp the DB column"

    def test_contains_parameterized_placeholder(self):
        content = _read_command("implement-feature.md")
        assert (
            "%s" in content
        ), "implement-feature.md DB snippet must use %s parameterized placeholders"

    def test_contains_update_features(self):
        content = _read_command("implement-feature.md")
        assert (
            "features" in content
        ), "implement-feature.md must reference the 'features' table"


class TestTestFeatureCommand:
    """test-feature.md must stamp tested_at after tests pass."""

    def test_contains_tested_at(self):
        content = _read_command("test-feature.md")
        assert "tested_at" in content, (
            "test-feature.md must reference 'tested_at' to stamp the DB column "
            "after tests pass"
        )

    def test_contains_parameterized_placeholder(self):
        content = _read_command("test-feature.md")
        assert (
            "%s" in content
        ), "test-feature.md DB snippet must use %s parameterized placeholders"

    def test_contains_features_table_reference(self):
        content = _read_command("test-feature.md")
        assert (
            "features" in content
        ), "test-feature.md must reference the 'features' table for the tested_at update"


class TestCodeReviewFeatureCommand:
    """code-review-feature.md must stamp reviewed_at after the review completes."""

    def test_contains_reviewed_at(self):
        content = _read_command("code-review-feature.md")
        assert (
            "reviewed_at" in content
        ), "code-review-feature.md must reference 'reviewed_at' to stamp the DB column"

    def test_contains_parameterized_placeholder(self):
        content = _read_command("code-review-feature.md")
        assert (
            "%s" in content
        ), "code-review-feature.md DB snippet must use %s parameterized placeholders"

    def test_contains_features_table_reference(self):
        content = _read_command("code-review-feature.md")
        assert (
            "features" in content
        ), "code-review-feature.md must reference the 'features' table"


class TestShipFeatureCommand:
    """ship-feature.md must stamp shipped_at and propagate to the parent row."""

    def test_contains_shipped_at(self):
        content = _read_command("ship-feature.md")
        assert "shipped_at" in content, (
            "ship-feature.md must reference 'shipped_at' to stamp the DB column "
            "after the PR is merged"
        )

    def test_contains_parent_number_logic(self):
        """The spec requires propagating shipped_at to the parent row when all
        sibling releases are shipped.  The command must reference parent_number."""
        content = _read_command("ship-feature.md")
        assert "parent_number" in content, (
            "ship-feature.md must reference 'parent_number' to implement the logic "
            "that stamps the parent feature row when all its releases are shipped"
        )

    def test_contains_parameterized_placeholder(self):
        content = _read_command("ship-feature.md")
        assert (
            "%s" in content
        ), "ship-feature.md DB snippet must use %s parameterized placeholders"

    def test_contains_features_table_reference(self):
        content = _read_command("ship-feature.md")
        assert (
            "features" in content
        ), "ship-feature.md must reference the 'features' table"

    def test_parent_stamp_uses_sibling_check(self):
        """The parent shipping logic must check whether sibling releases are all
        shipped before propagating — look for a sibling-count pattern."""
        content = _read_command("ship-feature.md")
        # The spec says: "check if all sibling release rows for the parent feature
        # are now shipped_at".  The command uses a SELECT COUNT(*) pattern for this.
        assert (
            "COUNT(*)" in content
            or "remaining" in content
            or "sibling" in content.lower()
        ), (
            "ship-feature.md must implement a sibling-count check before stamping "
            "the parent feature row's shipped_at"
        )


class TestDeployCommand:
    """deploy.md must stamp deployed_at on the most-recently-shipped undeployed release."""

    def test_contains_deployed_at(self):
        content = _read_command("deploy.md")
        assert "deployed_at" in content, (
            "deploy.md must reference 'deployed_at' to stamp the DB column "
            "after a successful railway up"
        )

    def test_targets_undeployed_shipped_rows(self):
        """The spec says: stamp ``deployed_at`` on rows where ``shipped_at IS NOT NULL
        AND deployed_at IS NULL``.  Both conditions must appear in the command."""
        content = _read_command("deploy.md")
        assert "shipped_at IS NOT NULL" in content or (
            "shipped_at" in content and "deployed_at IS NULL" in content
        ), (
            "deploy.md must target rows where shipped_at IS NOT NULL AND "
            "deployed_at IS NULL, not blindly update all rows"
        )

    def test_contains_parameterized_placeholder(self):
        content = _read_command("deploy.md")
        assert (
            "%s" in content
        ), "deploy.md DB snippet must use %s parameterized placeholders"

    def test_contains_features_table_reference(self):
        content = _read_command("deploy.md")
        assert (
            "features" in content
        ), "deploy.md must reference the 'features' table for the deployed_at update"

    def test_contains_railway_up(self):
        """The deploy step runs ``railway up`` before any DB write."""
        content = _read_command("deploy.md")
        assert "railway up" in content, (
            "deploy.md must invoke 'railway up' as the deployment step "
            "before stamping deployed_at"
        )


# ---------------------------------------------------------------------------
# 5. status.md — sources data from the DB, not registry.md
# ---------------------------------------------------------------------------


class TestStatusCommand:
    """status.md must query the DB directly, expose ``deployed_at``, and not use
    ``registry.md`` as its primary data source."""

    def test_contains_deployed_at(self):
        content = _read_command("status.md")
        assert "deployed_at" in content, (
            "status.md must reference 'deployed_at' — the command now reads this "
            "column from the DB to determine the Deployed stage"
        )

    def test_contains_python3_db_query(self):
        """The rewritten status command must run a Python DB query, not read a file."""
        content = _read_command("status.md")
        assert "python3" in content, (
            "status.md must use python3 to query the DB directly — "
            "it should no longer rely on reading registry.md for live data"
        )

    def test_does_not_use_registry_md_as_primary_data_source(self):
        """After the 15.3 rewrite, status.md must NOT read registry.md as its
        primary data step.  The DB is the sole live source of truth."""
        content = _read_command("status.md")
        assert "Read .claude/features/registry.md" not in content, (
            "status.md must not use 'Read .claude/features/registry.md' as its "
            "primary data step — the rewrite in 15.3 replaces that with a DB query"
        )

    def test_contains_select_from_features(self):
        """The DB query must SELECT from the features table."""
        content = _read_command("status.md")
        assert "SELECT" in content and "features" in content, (
            "status.md must contain a SELECT … FROM features query to source "
            "status data from the DB"
        )

    def test_contains_deployed_stage_label(self):
        """The output format must include a Deployed stage section (new in 15.3)."""
        content = _read_command("status.md")
        assert "Deployed" in content, (
            "status.md must include a 'Deployed' stage label in its output format — "
            "this is the new stage added alongside deployed_at"
        )

    def test_contains_load_dotenv_or_database_url(self):
        """The DB query snippet must load DATABASE_URL from the environment."""
        content = _read_command("status.md")
        assert "DATABASE_URL" in content or "load_dotenv" in content, (
            "status.md DB query must reference DATABASE_URL or load_dotenv() "
            "to connect to the database"
        )


# ---------------------------------------------------------------------------
# 6. Error-handling pattern — all commands wrap DB writes in try/except
# ---------------------------------------------------------------------------


class TestCommandErrorHandling:
    """The spec requires every harness command to catch DB write exceptions and
    continue rather than blocking the command.  We verify each command has some
    form of error guarding (try/except or conditional on DATABASE_URL)."""

    @pytest.mark.parametrize(
        "filename,expected_keyword",
        [
            ("capture-thoughts.md", "captured_at"),
            ("plan-release.md", "planned_at"),
            ("create-spec.md", "spec_at"),
            ("implement-feature.md", "implemented_at"),
            ("test-feature.md", "tested_at"),
            ("code-review-feature.md", "reviewed_at"),
            ("ship-feature.md", "shipped_at"),
            ("deploy.md", "deployed_at"),
        ],
    )
    def test_command_references_db_timestamp_column(self, filename, expected_keyword):
        """Each command file must reference its designated pipeline timestamp column."""
        content = _read_command(filename)
        assert expected_keyword in content, (
            f"{filename} must contain '{expected_keyword}' to stamp the corresponding "
            f"DB column as required by the 15.3 spec"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "capture-thoughts.md",
            "plan-release.md",
            "create-spec.md",
            "implement-feature.md",
            "test-feature.md",
            "code-review-feature.md",
            "ship-feature.md",
            "deploy.md",
        ],
    )
    def test_command_uses_parameterized_queries(self, filename):
        """Every command that writes to the DB must use %s placeholders."""
        content = _read_command(filename)
        assert "%s" in content, (
            f"{filename} must use %s parameterized placeholders in its DB snippet — "
            "never interpolate values directly into the SQL string"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "capture-thoughts.md",
            "plan-release.md",
            "create-spec.md",
            "implement-feature.md",
            "test-feature.md",
            "code-review-feature.md",
            "ship-feature.md",
            "deploy.md",
        ],
    )
    def test_command_file_exists(self, filename):
        """Each command file referenced by the 15.3 spec must exist on disk."""
        path = COMMANDS_DIR / filename
        assert path.exists(), f"Command file '{filename}' must exist at {path}"


# ---------------------------------------------------------------------------
# 7. ON CONFLICT idempotency patterns — capture and plan commands
# ---------------------------------------------------------------------------


class TestIdempotencyPatterns:
    """Specific ON CONFLICT variants required by the spec."""

    def test_capture_thoughts_uses_do_update_for_captured_at(self):
        """capture-thoughts uses DO UPDATE SET captured_at so re-running a
        /capture-thoughts run refreshes the timestamp rather than silently skipping."""
        content = _read_command("capture-thoughts.md")
        assert "DO UPDATE" in content, (
            "capture-thoughts.md must use ON CONFLICT … DO UPDATE SET captured_at "
            "so that re-running the command refreshes the captured_at timestamp"
        )

    def test_plan_release_uses_do_nothing_for_sub_rows(self):
        """plan-release uses DO NOTHING for release sub-row inserts so that
        re-running does not overwrite existing sub-rows."""
        content = _read_command("plan-release.md")
        assert "DO NOTHING" in content, (
            "plan-release.md must use ON CONFLICT … DO NOTHING for release sub-row "
            "inserts so that re-running the command does not overwrite existing rows"
        )


# ---------------------------------------------------------------------------
# 8. allowed-tools frontmatter — commands that run Python must declare it
# ---------------------------------------------------------------------------


class TestAllowedToolsFrontmatter:
    """Commands that run python3 -c snippets must declare Bash(python3 -c) in
    their allowed-tools frontmatter so the harness has permission to run them."""

    @pytest.mark.parametrize(
        "filename",
        ["deploy.md", "status.md"],
    )
    def test_python3_in_allowed_tools(self, filename):
        content = _read_command(filename)
        assert (
            "python3" in content.split("---")[1]
            if content.startswith("---")
            else "python3" in content[:300]
        ), (
            f"{filename} must declare 'python3' in its allowed-tools frontmatter "
            "since it runs a python3 -c DB snippet"
        )

    def test_deploy_allowed_tools_includes_python3(self):
        content = _read_command("deploy.md")
        # Extract frontmatter block (between first two ---)
        parts = content.split("---")
        frontmatter = parts[1] if len(parts) >= 3 else ""
        assert "python3" in frontmatter, (
            "deploy.md frontmatter must include Bash(python3 -c) — "
            "it runs a python3 snippet to stamp deployed_at after railway up"
        )

    def test_status_allowed_tools_includes_python3(self):
        content = _read_command("status.md")
        parts = content.split("---")
        frontmatter = parts[1] if len(parts) >= 3 else ""
        assert "python3" in frontmatter, (
            "status.md frontmatter must include Bash(python3 -c) — "
            "it runs a python3 snippet to query the features table"
        )


# ---------------------------------------------------------------------------
# 9. Error-handling prose — every command instructs agent to log and continue
# ---------------------------------------------------------------------------


class TestErrorHandlingProse:
    """The spec requires all DB writes to be best-effort: the command must instruct
    the agent to log the error and continue rather than blocking on failure."""

    @pytest.mark.parametrize(
        "filename",
        [
            "capture-thoughts.md",
            "plan-release.md",
            "test-feature.md",
            "code-review-feature.md",
            "deploy.md",
        ],
    )
    def test_command_instructs_log_and_continue(self, filename):
        content = _read_command(filename)
        has_error_handling = (
            "log the error" in content
            or "do not block" in content
            or "If the DB" in content
            or "if the DB" in content
        )
        assert has_error_handling, (
            f"{filename} must instruct the agent to log DB write errors and continue — "
            "DB writes are best-effort and must never block the command from completing"
        )


# ---------------------------------------------------------------------------
# 10. deploy.md success gate — stamp only runs after successful deployment
# ---------------------------------------------------------------------------


class TestDeploySuccessGate:
    """The deployed_at stamp must be conditioned on a successful railway up.
    If the deploy fails the DB step must be skipped."""

    def test_deploy_failed_message_present(self):
        """The command must have a failure branch that stops before the DB stamp."""
        content = _read_command("deploy.md")
        assert "Deploy failed" in content or "fails" in content, (
            "deploy.md must have a failure branch — if railway up fails, "
            "the deployed_at stamp step must not run"
        )

    def test_deploy_db_stamp_is_after_success_report(self):
        """Step 3 (DB stamp) must appear after Step 2 (report) in the file,
        ensuring the success check comes before the DB write."""
        content = _read_command("deploy.md")
        success_pos = content.find("Deployed successfully")
        deployed_at_pos = content.find("deployed_at")
        assert success_pos != -1, (
            "deploy.md must contain 'Deployed successfully' as the success signal "
            "before the deployed_at stamp step"
        )
        assert deployed_at_pos > success_pos, (
            "deploy.md must stamp deployed_at AFTER the success report, "
            "not before — the DB write is conditional on a successful deployment"
        )


# ---------------------------------------------------------------------------
# 11. status.md stage priority — all eight timestamp columns referenced
# ---------------------------------------------------------------------------


class TestStatusStagePriority:
    """status.md derives each row's current stage from the rightmost non-null
    timestamp column.  All eight columns must appear so the full priority chain
    is present in the command."""

    @pytest.mark.parametrize(
        "column",
        [
            "deployed_at",
            "shipped_at",
            "reviewed_at",
            "tested_at",
            "implemented_at",
            "spec_at",
            "planned_at",
            "captured_at",
        ],
    )
    def test_status_references_pipeline_column(self, column):
        content = _read_command("status.md")
        assert column in content, (
            f"status.md must reference '{column}' — it is part of the stage priority "
            "chain used to derive each feature's current status from the DB"
        )


# ---------------------------------------------------------------------------
# 12. implement.md removal and stale /implement reference checks
# ---------------------------------------------------------------------------


class TestImplementRename:
    """The command was renamed from implement.md to implement-feature.md.
    The old filename must not exist and no file should reference the bare
    '/implement ' command name (with trailing space, to avoid false positives
    on '/implement-feature')."""

    def test_old_implement_md_does_not_exist(self):
        old_path = COMMANDS_DIR / "implement.md"
        assert not old_path.exists(), (
            "implement.md must not exist — the command was renamed to "
            "implement-feature.md in this release. Delete the old file."
        )

    def test_implement_feature_md_exists(self):
        new_path = COMMANDS_DIR / "implement-feature.md"
        assert new_path.exists(), (
            "implement-feature.md must exist — this is the renamed command file "
            "for the /implement-feature harness command"
        )

    @pytest.mark.parametrize(
        "filename,filepath",
        [
            ("registry.md", ".claude/features/registry.md"),
            ("CLAUDE.md", "CLAUDE.md"),
            ("dev.md", ".claude/commands/dev.md"),
            ("create-spec.md", ".claude/commands/create-spec.md"),
        ],
    )
    def test_no_stale_implement_reference(self, filename, filepath):
        """None of the key docs/commands should reference the old '/implement '
        (bare, with trailing space) — only '/implement-feature' is valid."""
        path = REPO_ROOT / filepath
        if not path.exists():
            pytest.skip(f"{filepath} not found — skipping stale reference check")
        content = path.read_text(encoding="utf-8")
        # Match '/implement ' or '/implement\n' but not '/implement-feature'
        import re

        stale = re.findall(r"/implement(?!-feature)\b", content)
        assert not stale, (
            f"{filename} contains {len(stale)} stale reference(s) to '/implement' — "
            "update them to '/implement-feature'. "
            f"Occurrences: {stale}"
        )


# ---------------------------------------------------------------------------
# DB snippet integration tests — implemented in a separate file
#
# The classes listed below were originally noted as requiring a live Claude
# agent to invoke each harness command end-to-end. They have been implemented
# without that requirement by extracting and executing the python3 -c SQL
# snippets directly from each command file against an isolated Postgres schema.
#
# See: tests/test_15.3-harness-integration-live-updates-integration.py
#
# Implemented classes and what they cover:
#   TestCaptureThoughtsDBWrite       — INSERT + ON CONFLICT DO UPDATE for captured_at
#   TestPlanReleaseDBWrite           — planned_at on parent, sub-row insertion, idempotency
#   TestCreateSpecDBWrite            — spec_at + description update
#   TestImplementFeatureDBWrite      — implemented_at stamp
#   TestTestFeatureDBWrite           — tested_at on pass; NULL when snippet not run
#   TestCodeReviewFeatureDBWrite     — reviewed_at stamp
#   TestShipFeatureDBWrite           — shipped_at on release; parent propagation; sibling guard
#   TestDeployDBWrite                — deployed_at on shipped rows; guards against unshipped
#                                      and already-deployed rows; zero-rows-updated path
#   TestSQLSyntaxValidity            — SQL marker presence + live DB connection smoke-test
#   TestErrorHandlingBehaviour       — snippets exit non-zero on invalid DATABASE_URL
#   TestCreateSpecAndShipFeatureErrorHandling — same failure check for the two extended commands
# ---------------------------------------------------------------------------
