"""Feature 16.1 — Improvement Loop Skill

This feature adds a new /improvement-loop slash command — a developer workflow
tool that runs a structured 5-phase improvement cycle when invoked manually after
test failures or code review issues.  There are no HTTP routes, DB schema changes,
or template changes to test.

Test scope
----------
1.  Command file existence — improvement-loop.md exists in .claude/commands/
2.  Frontmatter — has description, argument-hint, and allowed-tools
3.  Phase coverage — all 5 phases are present (Gather Context, Root Cause Analysis,
    Architectural Assessment, Generate Improvement Plan, Implementation + Validation
    + Learning Capture)
4.  Decision framework — Option A, Option B, Option C are all present
5.  User approval gate — Phase 4 waits for explicit user approval before Phase 5
6.  Error handling — missing argument, invalid stage, no spec file, no failures
    detected, unable to resolve, learning capture write failure
6b. Stage argument — --stage flag accepted with valid values (implement, test,
    review, ship); invalid stage rejected
7.  Learning capture — references .claude/features/improvements/ directory and
    includes trigger_stage field
8.  Manual invocation only — no auto-trigger hooks in other commands
9.  Output format — phase headers and final "Is the system better?" question
10. Rules section — Never implement without approval, always run tests, always
    capture learnings
11. README updated — /improvement-loop appears in the command table
12. No DB changes — command does not write to the features table
"""

import os
import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"


def _read_command(filename: str) -> str:
    """Read and return the full text of a command markdown file."""
    path = COMMANDS_DIR / filename
    assert path.exists(), f"Command file not found: {path}"
    return path.read_text(encoding="utf-8")


def _read_file(filepath: pathlib.Path) -> str:
    """Read and return the full text of any file."""
    assert filepath.exists(), f"File not found: {filepath}"
    return filepath.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Command file existence
# ---------------------------------------------------------------------------


class TestCommandFileExists:
    """The improvement-loop command file must exist."""

    def test_improvement_loop_md_exists(self):
        path = COMMANDS_DIR / "improvement-loop.md"
        assert path.exists(), (
            "improvement-loop.md must exist in .claude/commands/"
        )


# ---------------------------------------------------------------------------
# 2. Frontmatter
# ---------------------------------------------------------------------------


class TestFrontmatter:
    """The command file must have valid YAML frontmatter with the required fields."""

    def test_has_description(self):
        content = _read_command("improvement-loop.md")
        assert "description:" in content, (
            "improvement-loop.md frontmatter must include a 'description:' field"
        )

    def test_has_argument_hint(self):
        content = _read_command("improvement-loop.md")
        assert "argument-hint:" in content, (
            "improvement-loop.md frontmatter must include an 'argument-hint:' field"
        )

    def test_has_allowed_tools(self):
        content = _read_command("improvement-loop.md")
        assert "allowed-tools:" in content, (
            "improvement-loop.md frontmatter must include an 'allowed-tools:' field"
        )

    def test_frontmatter_is_first_thing(self):
        content = _read_command("improvement-loop.md")
        assert content.startswith("---"), (
            "improvement-loop.md must start with YAML frontmatter (---)"
        )


# ---------------------------------------------------------------------------
# 3. Phase coverage — all 5 phases must be present
# ---------------------------------------------------------------------------


class TestPhaseCoverage:
    """The command must implement all 5 phases from the spec."""

    @pytest.mark.parametrize(
        "phase",
        [
            "Phase 1",
            "Phase 2",
            "Phase 3",
            "Phase 4",
            "Phase 5",
        ],
    )
    def test_phase_present(self, phase):
        content = _read_command("improvement-loop.md")
        assert phase in content, (
            f"improvement-loop.md must contain '{phase}' — "
            "all 5 phases are required by the spec"
        )

    def test_phase_1_gather_context(self):
        content = _read_command("improvement-loop.md")
        assert "Gather Context" in content, (
            "Phase 1 must be labeled 'Gather Context'"
        )

    def test_phase_2_root_cause_analysis(self):
        content = _read_command("improvement-loop.md")
        assert "Root Cause Analysis" in content, (
            "Phase 2 must be labeled 'Root Cause Analysis'"
        )

    def test_phase_3_architectural_assessment(self):
        content = _read_command("improvement-loop.md")
        assert "Architectural Assessment" in content, (
            "Phase 3 must be labeled 'Architectural Assessment'"
        )

    def test_phase_4_improvement_plan(self):
        content = _read_command("improvement-loop.md")
        assert "Improvement Plan" in content, (
            "Phase 4 must generate an 'Improvement Plan'"
        )

    def test_phase_5_implementation_validation_learning(self):
        content = _read_command("improvement-loop.md")
        assert "Implementation" in content and "Validation" in content and "Learning Capture" in content, (
            "Phase 5 must cover Implementation, Validation, and Learning Capture"
        )


# ---------------------------------------------------------------------------
# 4. Decision framework — Option A/B/C
# ---------------------------------------------------------------------------


class TestDecisionFramework:
    """Phase 4 must present three improvement options."""

    @pytest.mark.parametrize(
        "option",
        [
            "Option A",
            "Option B",
            "Option C",
        ],
    )
    def test_option_present(self, option):
        content = _read_command("improvement-loop.md")
        assert option in content, (
            f"improvement-loop.md must present '{option}' in the decision framework"
        )

    def test_option_a_is_minimal_fix(self):
        content = _read_command("improvement-loop.md")
        assert "Minimal Fix" in content or "minimal fix" in content, (
            "Option A must be the minimal fix option"
        )

    def test_option_b_is_fix_plus_improvement(self):
        content = _read_command("improvement-loop.md")
        assert "Small Improvement" in content or "small improvement" in content, (
            "Option B must include a small improvement beyond the fix"
        )

    def test_option_c_is_architectural(self):
        content = _read_command("improvement-loop.md")
        assert "Architectural Improvement" in content or "architectural improvement" in content, (
            "Option C must include architectural improvement"
        )


# ---------------------------------------------------------------------------
# 5. User approval gate
# ---------------------------------------------------------------------------


class TestUserApprovalGate:
    """Phase 4 must wait for explicit user approval before Phase 5 begins."""

    def test_asks_for_approval(self):
        content = _read_command("improvement-loop.md")
        assert "approval" in content.lower() or "proceed" in content.lower(), (
            "Phase 4 must ask the user for approval before proceeding to Phase 5"
        )

    def test_wait_for_user_approval(self):
        content = _read_command("improvement-loop.md")
        assert "Wait for" in content or "wait for" in content or "explicit user" in content, (
            "The command must explicitly wait for user approval in Phase 4"
        )


# ---------------------------------------------------------------------------
# 6. Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """The command must handle all error cases from the spec."""

    def test_missing_argument_handling(self):
        content = _read_command("improvement-loop.md")
        assert "missing argument" in content.lower() or "no argument" in content.lower() or "usage:" in content.lower(), (
            "Command must handle missing argument with usage instructions"
        )

    def test_no_spec_file_handling(self):
        content = _read_command("improvement-loop.md")
        assert "No spec file" in content or "no spec file" in content.lower(), (
            "Command must warn when no spec file is found but continue"
        )

    def test_no_failures_detected_handling(self):
        content = _read_command("improvement-loop.md")
        assert "No issues detected" in content or "nothing to improve" in content.lower(), (
            'Command must report "No issues detected" and exit when tests pass'
        )

    def test_unable_to_resolve_handling(self):
        content = _read_command("improvement-loop.md")
        assert "unable to resolve" in content.lower() or "Unable to resolve" in content, (
            "Command must handle the case where it cannot resolve the issue"
        )

    def test_learning_capture_write_failure_handling(self):
        content = _read_command("improvement-loop.md")
        assert "write fail" in content.lower() or "log the error" in content or "do not block" in content, (
            "Command must handle learning capture write failure gracefully"
        )


# ---------------------------------------------------------------------------
# 7. Learning capture
# ---------------------------------------------------------------------------


class TestLearningCapture:
    """Phase 5c must write a learning capture to .claude/features/improvements/."""

    def test_references_improvements_directory(self):
        content = _read_command("improvement-loop.md")
        assert ".claude/features/improvements" in content, (
            "Command must reference .claude/features/improvements/ for learning capture"
        )

    def test_uses_timestamp_in_filename(self):
        content = _read_command("improvement-loop.md")
        assert "timestamp" in content.lower() or "datetime" in content.lower() or "%Y-%m-%d" in content, (
            "Learning capture filename must include a timestamp"
        )

    def test_learning_capture_contains_required_sections(self):
        """The learning capture template must include the sections from the thought file."""
        content = _read_command("improvement-loop.md")
        required_sections = [
            "Issue Summary",
            "Root Cause",
            "Fix Applied",
            "Improvement Applied",
            "Future Prevention",
        ]
        for section in required_sections:
            assert section in content, (
                f"Learning capture template must include '{section}' section"
            )

    def test_learning_capture_includes_trigger_stage(self):
        """The learning capture template must include a trigger_stage field."""
        content = _read_command("improvement-loop.md")
        assert "trigger_stage" in content, (
            "Learning capture template must include 'trigger_stage' frontmatter field "
            "to record which pipeline stage triggered the improvement"
        )

    def test_learning_capture_trigger_stage_section(self):
        """The learning capture must have a Trigger Stage section with explanation."""
        content = _read_command("improvement-loop.md")
        assert "Trigger Stage" in content, (
            "Learning capture template must include a 'Trigger Stage' section header"
        )


# ---------------------------------------------------------------------------
# 6b. Stage argument handling
# ---------------------------------------------------------------------------


class TestStageArgument:
    """The command must accept and validate a --stage flag."""

    def test_accepts_stage_flag(self):
        content = _read_command("improvement-loop.md")
        assert "--stage" in content, (
            "Command must accept a --stage flag to record which pipeline stage triggered the improvement"
        )

    def test_valid_stage_values_documented(self):
        content = _read_command("improvement-loop.md")
        valid_stages = ["implement", "test", "review", "ship"]
        for stage in valid_stages:
            assert stage in content, (
                f"Command must document '{stage}' as a valid --stage value"
            )

    def test_invalid_stage_handling(self):
        content = _read_command("improvement-loop.md")
        assert "invalid stage" in content.lower() or "Invalid stage" in content, (
            "Command must handle invalid --stage values gracefully"
        )

    def test_stage_in_argument_hint(self):
        content = _read_command("improvement-loop.md")
        assert "stage" in content.split("---")[1].lower(), (
            "argument-hint frontmatter must mention the --stage flag"
        )


# ---------------------------------------------------------------------------
# 8. Manual invocation only — no auto-trigger hooks
# ---------------------------------------------------------------------------


class TestManualInvocationOnly:
    """The command must be manually triggered — no auto-trigger hooks."""

    def test_no_auto_trigger_references(self):
        content = _read_command("improvement-loop.md")
        # The command should not reference hooking into test-feature or code-review-feature
        assert "auto-trigger" not in content.lower() and "auto trigger" not in content.lower(), (
            "Command must not implement auto-trigger — it is manual-only"
        )

    def test_references_manual_invocation(self):
        content = _read_command("improvement-loop.md")
        assert "manual" in content.lower(), (
            "Command documentation must indicate it is manually triggered"
        )


# ---------------------------------------------------------------------------
# 9. Output format
# ---------------------------------------------------------------------------


class TestOutputFormat:
    """The command must produce structured output with phase summaries."""

    def test_phase_output_headers(self):
        content = _read_command("improvement-loop.md")
        assert "Phase 1" in content and "Phase 2" in content, (
            "Output must include numbered phase headers"
        )

    def test_final_better_question(self):
        content = _read_command("improvement-loop.md")
        assert "better than" in content.lower() or "system better" in content.lower(), (
            'Final output must answer: "Is the system better than it was before?"'
        )


# ---------------------------------------------------------------------------
# 10. Rules section
# ---------------------------------------------------------------------------


class TestRulesSection:
    """The command must include a Rules section with required constraints."""

    def test_rules_section_exists(self):
        content = _read_command("improvement-loop.md")
        assert "Rules" in content, (
            "Command must include a 'Rules' section"
        )

    def test_never_implement_without_approval(self):
        content = _read_command("improvement-loop.md")
        assert "without user approval" in content or "approval" in content, (
            "Rules must state: never implement without user approval"
        )

    def test_always_run_tests(self):
        content = _read_command("improvement-loop.md")
        assert "run tests" in content.lower() or "always run" in content.lower(), (
            "Rules must state: always run tests after implementing"
        )

    def test_always_capture_learnings(self):
        content = _read_command("improvement-loop.md")
        assert "capture learnings" in content.lower() or "learning capture" in content.lower(), (
            "Rules must state: always capture learnings"
        )


# ---------------------------------------------------------------------------
# 11. README updated
# ---------------------------------------------------------------------------


class TestReadmeUpdated:
    """README.md must document the new /improvement-loop command."""

    def test_readme_mentions_improvement_loop(self):
        readme_path = REPO_ROOT / "README.md"
        if not readme_path.exists():
            pytest.skip("README.md not found")
        content = _read_file(readme_path)
        assert "/improvement-loop" in content, (
            "README.md must mention the /improvement-loop command"
        )


# ---------------------------------------------------------------------------
# 12. No DB changes
# ---------------------------------------------------------------------------


class TestNoDBChanges:
    """The improvement-loop command does not write to the features table."""

    def test_no_insert_into_features(self):
        content = _read_command("improvement-loop.md")
        assert "INSERT INTO features" not in content, (
            "improvement-loop.md must not INSERT into the features table"
        )

    def test_no_update_features(self):
        content = _read_command("improvement-loop.md")
        # UPDATE features would be a DB write — this command doesn't do that
        # Check for the specific pattern, not just the word "update" which
        # could appear in prose
        assert "UPDATE features" not in content, (
            "improvement-loop.md must not UPDATE the features table"
        )
