"""Tests for Feature 25.1 — Pipeline Orchestration Automation.

Spec: .claude/specs/25.1-pipeline-orchestration-automation.md

Scope
-----
This feature adds two new Claude Code command files —
`.claude/commands/autom-plan.md` and `.claude/commands/autom-dev.md` — that
orchestrate the existing dev pipeline. It introduces no Flask routes, no
database schema changes, and no templates, so these tests validate the
command files' documented structure and content against the spec's own
Definition of Done rather than runtime HTTP behaviour, a live DB, or the
commands' actual runtime execution (Claude Code commands are prompts, not
executable Python — there is nothing to import or call). No Flask test
client, no `app`/`client` fixtures, and no `init_db()` are used here because
this feature has no routes and no schema changes to exercise.

Every assertion below is derived from a specific line item in the spec's
"Definition of done" section or from a requirement stated in "Overview",
"In scope", "Error handling", or "Rules for implementation" — not from
whatever the implementation happens to say beyond what the spec requires.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
AUTOMATION_DIR = REPO_ROOT / ".claude" / "features" / "automation"

AUTOM_PLAN = COMMANDS_DIR / "autom-plan.md"
AUTOM_DEV = COMMANDS_DIR / "autom-dev.md"


@pytest.fixture
def autom_plan_text():
    return AUTOM_PLAN.read_text()


@pytest.fixture
def autom_dev_text():
    return AUTOM_DEV.read_text()


# ---------------------------------------------------------------------------
# /autom-plan
# ---------------------------------------------------------------------------


class TestAutomPlanExists:
    """DoD: "/autom-plan exists as a command (and matching skill)..."."""

    def test_command_file_exists(self):
        assert AUTOM_PLAN.exists(), "Expected .claude/commands/autom-plan.md to exist"

    def test_has_frontmatter(self, autom_plan_text):
        assert autom_plan_text.startswith(
            "---\n"
        ), "Command file must open with YAML frontmatter"
        assert "description:" in autom_plan_text
        assert "argument-hint:" in autom_plan_text


class TestAutomPlanNeverImplements:
    """DoD: "...runs /capture-thoughts then /plan-release and stops without
    invoking /create-spec or any later stage."

    /autom-plan's whole job is to stop before implementation. It may still
    *mention* later-stage command names in prose (e.g. explaining that it
    never calls them, or telling the user to run /autom-dev next) — the real
    requirement is that it never issues an active "Invoke /create-spec"-style
    instruction. We check for that active-invocation phrasing rather than a
    bare substring, since the command file legitimately contains negative
    statements like "Never call /create-spec"."""

    def test_never_actively_invokes_create_spec(self, autom_plan_text):
        # Case-sensitive: real invocations in these command files use the
        # imperative "Invoke `/cmd ...`" (capital I); lowercase "invoke"
        # appears only inside prohibitive prose like "you never invoke".
        assert "Invoke `/create-spec" not in autom_plan_text

    def test_never_actively_invokes_implement_feature(self, autom_plan_text):
        assert "Invoke `/implement-feature" not in autom_plan_text

    def test_never_actively_invokes_test_or_review_or_ship(self, autom_plan_text):
        for forbidden in ("/test-feature", "/code-review-feature", "/ship-feature"):
            assert f"Invoke `{forbidden}" not in autom_plan_text

    def test_never_runs_git_push(self, autom_plan_text):
        assert not re.search(r"`git push", autom_plan_text)

    def test_explicitly_stops_and_hands_off_to_autom_dev(self, autom_plan_text):
        assert "/autom-dev" in autom_plan_text
        assert re.search(r"stop", autom_plan_text, re.IGNORECASE)


class TestAutomPlanInvokesUpstream:
    """DoD: "...runs /capture-thoughts then /plan-release..."."""

    def test_invokes_capture_thoughts(self, autom_plan_text):
        assert "/capture-thoughts" in autom_plan_text

    def test_invokes_plan_release(self, autom_plan_text):
        assert "/plan-release" in autom_plan_text

    def test_capture_thoughts_precedes_plan_release(self, autom_plan_text):
        # Overview: "runs /capture-thoughts -> /plan-release" — ordering
        # matters, not just presence.
        assert autom_plan_text.index("/capture-thoughts") < autom_plan_text.index(
            "/plan-release"
        )


class TestAutomPlanMultiReleasePresentation:
    """DoD: "/autom-plan presents every release from a multi-release plan,
    with a recommendation of which to build first, and requires an explicit
    user selection before any /autom-dev run is suggested."

    Also spec's Error handling: "/plan-release returns multiple releases
    inside /autom-plan — must never auto-select or auto-run more than the
    one release the user explicitly chooses; presenting all options and
    stopping is the only correct behavior."
    """

    def test_documents_presenting_every_release(self, autom_plan_text):
        lowered = autom_plan_text.lower()
        assert "release plan" in lowered
        assert re.search(r"every release|all releases|more than one release", lowered)

    def test_documents_a_recommendation_of_which_release_to_build_first(
        self, autom_plan_text
    ):
        assert re.search(r"recommend", autom_plan_text, re.IGNORECASE)
        assert re.search(r"build first|release 1", autom_plan_text, re.IGNORECASE)

    def test_requires_explicit_user_selection_before_suggesting_autom_dev(
        self, autom_plan_text
    ):
        # The command must not auto-run /autom-dev on the user's behalf —
        # it should tell the user to pick and run it themselves.
        assert "Pick a release" in autom_plan_text or re.search(
            r"pick\s+a\s+release", autom_plan_text, re.IGNORECASE
        )
        assert "Invoke `/autom-dev" not in autom_plan_text

    def test_never_auto_selects_a_release_when_multiple_exist(self, autom_plan_text):
        lowered = autom_plan_text.lower()
        assert re.search(r"never\s+(auto-select|auto-run|select).{0,40}", lowered) or (
            "recommend" in lowered and "stop" in lowered
        )


# ---------------------------------------------------------------------------
# /autom-dev
# ---------------------------------------------------------------------------


class TestAutomDevExists:
    """DoD: "/autom-dev <feature.release> exists as a command (and matching
    skill)..."."""

    def test_command_file_exists(self):
        assert AUTOM_DEV.exists(), "Expected .claude/commands/autom-dev.md to exist"

    def test_has_frontmatter(self, autom_dev_text):
        assert autom_dev_text.startswith("---\n")
        assert "description:" in autom_dev_text
        assert "argument-hint:" in autom_dev_text


class TestAutomDevArgumentValidation:
    """Spec Error handling: "Missing or invalid feature/release argument to
    /autom-dev — if <feature.release> is missing, malformed, or does not
    match an existing release row, stop immediately and print usage
    guidance; do not guess a target."."""

    def test_documents_usage_guidance_on_missing_or_malformed_argument(
        self, autom_dev_text
    ):
        lowered = autom_dev_text.lower()
        assert "missing" in lowered or "malformed" in lowered
        assert "usage" in lowered or "/autom-dev <feature.release>" in autom_dev_text

    def test_documents_no_release_row_found_error(self, autom_dev_text):
        lowered = autom_dev_text.lower()
        assert "not_found" in lowered or "no release plan found" in lowered
        assert "/autom-plan" in autom_dev_text or "/plan-release" in autom_dev_text

    def test_does_not_guess_a_target(self, autom_dev_text):
        assert re.search(r"do not guess", autom_dev_text, re.IGNORECASE)


class TestAutomDevInvokesDownstreamInOrder:
    """DoD: "/autom-dev <feature.release> ... runs /create-spec ->
    /implement-feature -> /test-feature -> /code-review-feature ->
    /ship-feature in order, waiting for each stage to complete."."""

    def test_mentions_all_five_pipeline_commands(self, autom_dev_text):
        for cmd in (
            "/create-spec",
            "/implement-feature",
            "/test-feature",
            "/code-review-feature",
            "/ship-feature",
        ):
            assert cmd in autom_dev_text

    def test_commands_appear_in_pipeline_order(self, autom_dev_text):
        commands = [
            "/create-spec",
            "/implement-feature",
            "/test-feature",
            "/code-review-feature",
            "/ship-feature",
        ]
        positions = [autom_dev_text.index(cmd) for cmd in commands]
        assert positions == sorted(positions)

    def test_documents_waiting_for_each_stage_to_complete(self, autom_dev_text):
        assert re.search(
            r"wait(?:ing)?\s+for\s+(it|each stage)\s+to\s+(fully\s+)?complete",
            autom_dev_text,
            re.IGNORECASE,
        )

    def test_never_runs_two_stages_concurrently(self, autom_dev_text):
        assert re.search(
            r"never run two\s+stages concurrently", autom_dev_text, re.IGNORECASE
        )


class TestAutomDevFreshSessionResumability:
    """DoD: "/autom-dev can be invoked in a fresh session against a release
    plan that was generated in an earlier, separate session (no dependency
    on /autom-plan having just run)."

    Spec "In scope": "/autom-dev loads its target release from the release
    plan file and the features DB table rather than requiring /autom-plan to
    have just run in the same session — a previously generated plan can be
    picked up later."
    """

    def test_loads_target_from_features_db_table(self, autom_dev_text):
        assert re.search(r"features\s+(table|WHERE number)", autom_dev_text)
        assert "SELECT" in autom_dev_text

    def test_does_not_require_autom_plan_to_have_just_run(self, autom_dev_text):
        # The command must not assume in-session state from /autom-plan —
        # it should be documented as loadable from persisted state instead.
        assert "/autom-plan" in autom_dev_text
        # Its only reference to /autom-plan should be as a fallback
        # instruction when no release row/plan is found, not as a
        # same-session prerequisite.
        assert "must have just run" not in autom_dev_text
        assert "in the same session" not in autom_dev_text


class TestAutomDevStageResumability:
    """DoD: "Given a release whose implemented_at is already set but
    tested_at is not, /autom-dev resumes at /test-feature rather than
    re-running /create-spec or /implement-feature."."""

    def test_documents_resume_point_precedence_order(self, autom_dev_text):
        # The five timestamp columns must be checked in this exact order to
        # find "the first NULL", per the spec's state-store columns.
        for column, next_stage in (
            ("spec_at", "/create-spec"),
            ("implemented_at", "/implement-feature"),
            ("tested_at", "/test-feature"),
            ("reviewed_at", "/code-review-feature"),
            ("shipped_at", "/ship-feature"),
        ):
            assert column in autom_dev_text, f"Expected {column} to be referenced"
            assert next_stage in autom_dev_text

    def test_implemented_at_set_but_tested_at_null_resumes_at_test_feature(
        self, autom_dev_text
    ):
        # This is the exact DoD scenario: implemented_at set, tested_at
        # NULL -> resume at /test-feature.
        assert re.search(
            r"`tested_at`\s+NULL\s*(→|->)\s*resume at\s*`/test-feature`",
            autom_dev_text,
        )

    def test_documents_never_restarting_from_create_spec_on_resume(
        self, autom_dev_text
    ):
        assert re.search(
            r"resum(e|ing)|never\s+re-run\s+a\s+stage\s+whose\s+timestamp\s+is\s+already\s+set",
            autom_dev_text,
            re.IGNORECASE,
        )
        assert "This is a resume, not a restart" in autom_dev_text or re.search(
            r"not\s+a\s+restart", autom_dev_text, re.IGNORECASE
        )

    def test_all_stages_complete_reports_already_shipped_and_stops(
        self, autom_dev_text
    ):
        assert re.search(r"already shipped", autom_dev_text, re.IGNORECASE)


class TestAutomDevNeverPushes:
    """Spec Rules for implementation: "/autom-dev must invoke /ship-feature
    for the push/PR/merge steps exactly as that command already does; it
    must not add any push logic of its own or push at any other point in
    the run."

    The command file legitimately *mentions* "git push" in prose while
    explaining this rule, so we check there is no actual runnable
    `git push` shell command (backtick-fenced), not merely an absence of
    the phrase.
    """

    def test_never_contains_a_runnable_git_push_command(self, autom_dev_text):
        # A real invocation always has an upstream/remote argument, e.g.
        # "git push -u origin ..." or "git push origin --delete ..." (see
        # ship-feature.md). Bare "git push" with no argument only appears
        # here as prose forbidding the action, never as a runnable command.
        assert not re.search(r"git push\s+(-u|origin)", autom_dev_text)

    def test_documents_the_no_push_rule(self, autom_dev_text):
        assert re.search(r"never run\s+`git push", autom_dev_text, re.IGNORECASE)

    def test_delegates_push_pr_merge_to_ship_feature(self, autom_dev_text):
        assert re.search(
            r"ship-feature.{0,80}(push|PR|merge)|performs its own push/PR/merge",
            autom_dev_text,
            re.IGNORECASE,
        )


class TestAutomDevRetryPolicy:
    """DoD: "A failing test or review finding is auto-remediated and the
    stage is re-run, up to 3 attempts; on the 3rd failure the run stops and
    prints the issue, what was attempted, and a recommendation, and waits
    for the user."."""

    def test_documents_three_attempt_cap(self, autom_dev_text):
        assert re.search(r"3\s+(total\s+)?attempts?", autom_dev_text, re.IGNORECASE)

    def test_documents_stop_and_ask_on_exhaustion(self, autom_dev_text):
        lowered = autom_dev_text.lower()
        assert "stop" in lowered
        assert re.search(r"ask(?:ing)?\s+the\s+user", lowered)

    def test_stop_report_contains_the_three_required_parts(self, autom_dev_text):
        # DoD is explicit: the issue, what was attempted, and a
        # recommendation must all be printed together on the 3rd failure.
        lowered = autom_dev_text.lower()
        assert "the failure" in lowered or "the issue" in lowered
        assert "what was attempted" in lowered
        assert "recommended next action" in lowered or "recommendation" in lowered

    def test_stop_message_requires_a_reply_not_just_informational(self, autom_dev_text):
        assert re.search(
            r"must be a\s+question requiring a reply", autom_dev_text, re.IGNORECASE
        )

    def test_does_not_advance_past_a_failed_stage_or_attempt_a_fourth_try(
        self, autom_dev_text
    ):
        assert re.search(
            r"Do not advance\s+to the next stage or attempt a 4th try",
            autom_dev_text,
            re.IGNORECASE,
        )

    def test_does_not_suppress_plan_mode_approval(self, autom_dev_text):
        assert "EnterPlanMode" in autom_dev_text or "ExitPlanMode" in autom_dev_text
        assert re.search(
            r"(cannot|does not|never)\s+(suppress|bypass|skip)",
            autom_dev_text,
            re.IGNORECASE,
        )

    def test_does_not_suppress_critical_high_severity_review_pause(
        self, autom_dev_text
    ):
        # Rules: "never suppress ... /code-review-feature's Critical/High-
        # severity pause."
        assert re.search(r"Critical/High", autom_dev_text)
        assert re.search(
            r"never\s+suppress.{0,120}Critical/High|Critical/High.{0,120}pause",
            autom_dev_text,
            re.IGNORECASE | re.DOTALL,
        )


class TestAutomDevAmbiguousOrDestructiveActionGuard:
    """Spec Error handling: "Ambiguous or destructive action encountered
    mid-run — e.g. a spec decision that can't be safely inferred, or any
    action that would require bypassing an existing guardrail (git push
    policy, ownership checks) — the run must pause, explain the exact
    decision needed, and wait for the user rather than guessing."."""

    def test_documents_pausing_on_ambiguous_or_destructive_action(self, autom_dev_text):
        lowered = autom_dev_text.lower()
        assert "ambiguous" in lowered or "destructive" in lowered
        assert "pause" in lowered

    def test_documents_not_guessing(self, autom_dev_text):
        assert re.search(r"do not guess", autom_dev_text, re.IGNORECASE)


class TestAutomDevRootCauseGuard:
    """DoD/Spec: "Root-cause validation guidance embedded in /autom-dev's
    auto-fix step, explicitly barring weaker assertions, sleeps/retries/
    timing hacks, or other test-only workarounds as a substitute for fixing
    the underlying behavior."."""

    def test_forbids_weakening_assertions(self, autom_dev_text):
        lowered = autom_dev_text.lower()
        assert "root-cause" in lowered or "root cause" in lowered
        assert "sleep" in lowered or "retries" in lowered or "timing hack" in lowered

    def test_forbids_weaker_assertions_explicitly(self, autom_dev_text):
        assert re.search(r"weaker assertions", autom_dev_text, re.IGNORECASE)

    def test_root_cause_guard_applies_to_review_fixes_too(self, autom_dev_text):
        # Spec says this guard applies to both /test-feature auto-fix and
        # /code-review-feature auto-fix cycles, not just tests.
        assert re.search(
            r"same root-cause\s+validation guard", autom_dev_text, re.IGNORECASE
        )


class TestAutomDevCodeReviewAutoApprovalPolicy:
    """Spec "In scope": auto-fix behavior applies to failing tests *and*
    code-review findings, with an explicit severity-based pause/auto-approve
    split, and any approval must be recorded with a bounded scope (never
    blanket future authorization, per Rules for implementation)."""

    def test_documents_auto_approve_for_low_medium_findings(self, autom_dev_text):
        assert re.search(r"Low/Medium", autom_dev_text)

    def test_documents_pause_for_critical_high_or_architectural_findings(
        self, autom_dev_text
    ):
        assert re.search(r"pause and ask the user", autom_dev_text, re.IGNORECASE)

    def test_auto_approval_recorded_as_current_run_never_permanent(
        self, autom_dev_text
    ):
        assert re.search(
            r"current-run.{0,40}never.{0,10}`?permanent`?",
            autom_dev_text,
            re.IGNORECASE | re.DOTALL,
        )


class TestAutomDevRunJournal:
    """DoD: "The run journal file records at least one decision and one
    permission entry with request/reason/decision/scope during a run, and a
    later run does not re-ask a question whose recorded decision still
    applies."

    Spec Rules: "The run journal (decision/permission memory) must not
    persist sensitive information, and must not treat a single approval as
    blanket future authorization."
    """

    def test_references_automation_directory(self, autom_dev_text):
        assert ".claude/features/automation/" in autom_dev_text

    def test_documents_distinct_decisions_and_permissions_sections(
        self, autom_dev_text
    ):
        assert "## Decisions" in autom_dev_text
        assert "## Permissions" in autom_dev_text

    def test_decision_and_permission_entries_capture_request_reason_decision_scope(
        self, autom_dev_text
    ):
        # DoD requires each entry to record request/reason/decision/scope.
        assert "request/reason/decision/scope" in autom_dev_text or (
            re.search(r"what was asked", autom_dev_text, re.IGNORECASE)
            and re.search(r"why", autom_dev_text)
            and re.search(r"what was decided", autom_dev_text, re.IGNORECASE)
            and re.search(r"scope", autom_dev_text, re.IGNORECASE)
        )

    def test_documents_scope_values(self, autom_dev_text):
        for scope_value in ("one-time", "current-run", "project-level", "permanent"):
            assert (
                scope_value in autom_dev_text
            ), f"Expected scope value {scope_value!r}"

    def test_documents_checking_journal_before_asking_and_not_reasking(
        self, autom_dev_text
    ):
        assert re.search(r"do not re-ask", autom_dev_text, re.IGNORECASE)
        assert re.search(r"check this file first", autom_dev_text, re.IGNORECASE)

    def test_forbids_persisting_sensitive_information(self, autom_dev_text):
        lowered = autom_dev_text.lower()
        assert "sensitive" in lowered
        # Rules explicitly names the category of data barred from the
        # journal.
        assert "credential" in lowered or "token" in lowered or "secret" in lowered

    def test_forbids_treating_single_approval_as_blanket_authorization(
        self, autom_dev_text
    ):
        assert re.search(
            r"never\s+promoted\s+to\s+`?permanent`?\s+unless\s+the\s+user\s+explicitly",
            autom_dev_text,
            re.IGNORECASE,
        )

    def test_journal_write_failure_does_not_block_pipeline(self, autom_dev_text):
        # Error handling: "Journal write failure — if the run journal file
        # cannot be written, log the error to the console and continue; a
        # broken journal must not block the pipeline stage that is already
        # in progress."
        assert re.search(r"journal write failure", autom_dev_text, re.IGNORECASE)
        assert re.search(r"must not block", autom_dev_text, re.IGNORECASE)


class TestAutomDevDuplicationAudit:
    """DoD: "Every /autom-dev run performs and reports a final duplication
    audit before completion."."""

    def test_documents_a_duplication_audit_step(self, autom_dev_text):
        assert re.search(r"duplicat", autom_dev_text, re.IGNORECASE)

    def test_duplication_audit_runs_before_the_run_summary(self, autom_dev_text):
        audit_pos = autom_dev_text.lower().index("duplication audit")
        summary_pos = autom_dev_text.index("Autom-Dev Run Summary")
        assert (
            audit_pos < summary_pos
        ), "Duplication audit must be reported before the final run summary"

    def test_duplication_audit_result_is_required_and_visible(self, autom_dev_text):
        assert re.search(
            r"required, visible step, not\s+a\s+silent check",
            autom_dev_text,
            re.IGNORECASE,
        )


class TestAutomDevRunSummary:
    """DoD: "Every /autom-dev run ends with a structured summary listing
    stages completed, files changed, tests executed, review findings, and
    any bugs/improvements discovered."."""

    def test_documents_structured_run_summary_fields(self, autom_dev_text):
        for field in (
            "Stages completed",
            "Files changed",
            "Tests executed",
            "Review findings",
            "Shipping status",
            "Bugs/improvements",
        ):
            assert field in autom_dev_text, f"Expected run summary field {field!r}"

    def test_run_summary_is_the_final_step(self, autom_dev_text):
        # Spec Overview / DoD implies the summary is printed at the *end* of
        # every run - it should be the last major step documented, after
        # the duplication audit.
        summary_heading_positions = [
            m.start()
            for m in re.finditer(r"^## Step \d+", autom_dev_text, re.MULTILINE)
        ]
        assert summary_heading_positions, "Expected numbered Step headings"
        last_step_start = summary_heading_positions[-1]
        assert (
            "Run Summary" in autom_dev_text[last_step_start:]
            or "run summary" in autom_dev_text[last_step_start:].lower()
        )


# ---------------------------------------------------------------------------
# No-duplication guards (project-wide, apply to both commands)
# ---------------------------------------------------------------------------


class TestNoSkillDuplication:
    """Spec Rules for implementation: "No duplicate commands/skills/config/
    DB/process structures — before writing autom-plan.md / autom-dev.md,
    re-confirm no existing command/skill already provides the required
    behavior (per the research already done for this spec: none do)."

    Every existing pipeline command lives only under .claude/commands/ —
    none of them have a paired .claude/skills/<name>/SKILL.md. This feature
    must follow the same convention rather than introducing a second,
    inconsistent skill-pairing mechanism.
    """

    def test_no_autom_plan_skill_directory(self):
        assert not (SKILLS_DIR / "autom-plan").exists()

    def test_no_autom_dev_skill_directory(self):
        assert not (SKILLS_DIR / "autom-dev").exists()

    def test_no_skills_directory_introduced_for_any_existing_command(self):
        # If .claude/skills/ exists at all, this feature did not introduce
        # it as a new pairing convention exclusively for these two commands.
        if SKILLS_DIR.exists():
            existing_command_stems = {p.stem for p in COMMANDS_DIR.glob("*.md")} - {
                "autom-plan",
                "autom-dev",
            }
            skill_dirs = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
            assert not (skill_dirs & existing_command_stems), (
                "Existing commands should not suddenly have paired skill dirs "
                "introduced by this feature"
            )

    def test_commands_are_the_only_definition(self):
        assert AUTOM_PLAN.exists()
        assert AUTOM_DEV.exists()


class TestAutomationDirectoryExists:
    """Spec Files to create: ".claude/features/automation/ — new directory
    holding the run journal file(s) written by /autom-dev... must live
    under this project-local, git-tracked path rather than anywhere outside
    the repo."."""

    def test_automation_directory_created(self):
        assert AUTOMATION_DIR.exists()
        assert AUTOMATION_DIR.is_dir()

    def test_automation_directory_is_inside_the_repo(self):
        # Must be project-local/git-tracked, i.e. a real subpath of the repo
        # root, not a symlink pointing outside it.
        resolved = AUTOMATION_DIR.resolve()
        assert str(resolved).startswith(str(REPO_ROOT.resolve()))


class TestNoNewRoutesOrSchema:
    """DoD: "No new Flask route, template, or DB table/column is introduced
    by this feature (verified by diffing app.py, templates/, and
    database/db.py against main)."

    A full git diff against main is out of scope for a unit test (git state
    varies across branches/CI checkouts), so this is a static content
    check: the new command names must not appear as routes, templates, or
    schema objects anywhere in the app's source.
    """

    def test_app_py_has_no_autom_routes(self):
        app_py = (REPO_ROOT / "app.py").read_text()
        assert '"/autom-plan"' not in app_py
        assert '"/autom-dev"' not in app_py
        assert "'/autom-plan'" not in app_py
        assert "'/autom-dev'" not in app_py

    def test_db_py_has_no_automation_table_or_column(self):
        db_py = (REPO_ROOT / "database" / "db.py").read_text()
        assert not re.search(r"CREATE TABLE[^;]*automation", db_py, re.IGNORECASE)
        assert not re.search(r"ADD COLUMN[^;]*auto_pipeline_at", db_py, re.IGNORECASE)

    def test_no_new_templates_named_for_the_automation_commands(self):
        templates_dir = REPO_ROOT / "templates"
        if templates_dir.exists():
            template_names = {p.stem for p in templates_dir.glob("*.html")}
            assert "autom_plan" not in template_names
            assert "autom_dev" not in template_names
            assert "autom-plan" not in template_names
            assert "autom-dev" not in template_names

    def test_dry_run_mode_is_deferred_not_built(self, autom_dev_text):
        # Spec "Deferred to a future release": --dry-run mode for
        # /autom-dev must not have been built in this release.
        assert "--dry-run" not in autom_dev_text
