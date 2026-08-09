---
number: 25
title: Pipeline Orchestration Automation
type: new-feature
parent: null
status: captured
created: 2026-08-08 12:04 EST
source_folder: .claude/features/user-thoughts/dev-workflow-improvements/
---

# Processed Thought: Pipeline Orchestration Automation

## Problem / Goal
Every stage of the dev pipeline (`/capture-thoughts` → `/plan-release` →
`/create-spec` → `/implement-feature` → `/test-feature` →
`/code-review-feature` → `/ship-feature`) is invoked manually and watched
individually, even when a stage finishes cleanly. This turns the user into a
relay between commands, makes it easy to skip or misorder steps or lose track
of release numbers, and adds friction on routine features with no real
decisions to make. The goal is to orchestrate the existing pipeline through a
small number of high-level commands, without duplicating any existing
command/skill/config/process logic — the automation is a thin orchestrator
over the existing methodology, not a replacement for it.

## Who benefits
The developer/user driving the Oxos Platform pipeline (currently just the
requesting user) — anyone running routine, low-drama features through the
standard pipeline benefits most; complex or ambiguous features still get
human checkpoints.

## Success looks like
Two new commands exist:

- **`/autom-plan`** — runs `/capture-thoughts` → `/plan-release`, then stops
  and presents the resulting release plan for the user to review. It never
  automatically begins implementation. If `/plan-release` produces multiple
  releases, it presents all of them, explains each release's scope,
  recommends which to execute first, and lets the user explicitly select one
  for `/autom-dev`. Default execution unit is one release per `/autom-dev`
  run.
- **`/autom-dev`** — executes exactly one explicitly-selected release,
  end-to-end: `/create-spec` → `/implement-feature` → `/test-feature` →
  `/code-review-feature` → `/ship-feature`. Waits for each stage to complete
  before starting the next. Auto-fixes failing tests and auto-implements
  code-review findings, re-running the relevant stage until it passes. Each
  stage/fix attempt is capped at 3 tries — if the desired outcome isn't
  reached by then, it stops, summarizes the issue and its recommendation, and
  asks the user for permission to continue.

Both commands reuse the existing commands/skills/conventions/guardrails/DB
structures as-is — calling them rather than reimplementing their logic. No
duplicate commands, skills, docs, config, or state mechanisms are introduced.
Each run produces a structured summary (stages completed, artifacts
generated, files changed, tests executed, review findings, shipping status,
user/permission decisions, errors, unresolved issues, discovered bugs and
improvements, and any deviations from the expected workflow) and can safely
resume from the last completed stage after a failure without restarting
finished stages.

## Constraints, risks, dependencies
- Must not duplicate existing command/skill/process/config/DB/helper logic —
  extend existing mechanisms (e.g. the features DB, `/status`,
  `/improvement-loop`) rather than inventing new ones.
- Must preserve every existing command's guardrails exactly as documented,
  including the git push policy (pushes only inside `/ship-feature`'s
  existing steps) and ownership/auth checks.
- Must distinguish actions that are safe to continue automatically
  (deterministic transitions, running the next authorized command, routine
  validation, non-blocking findings) from actions that require a paused,
  explicitly recorded user decision (destructive/irreversible actions,
  architectural ambiguity that can't be safely inferred, conflicting
  requirements, missing information that materially changes implementation,
  a permission that can't be auto-granted, or a failure where continuing
  could corrupt project state).
- Must not silently expand scope to unrelated improvements — bugs,
  improvements, out-of-scope opportunities, and workflow/automation problems
  discovered mid-run are recorded in the run summary, not auto-acted on,
  unless an existing project mechanism already covers that kind of tracking.
- Needs a permission/decision memory that distinguishes one-time approval,
  current-run approval, project-level workflow preference, and permanent
  policy — without persisting sensitive information and without treating a
  single prior approval as blanket permission going forward. Prefer an
  existing project configuration/convention over introducing a new memory
  mechanism.
- Before finishing, the repo should be re-reviewed for duplicate/redundant
  structures introduced by this work, and anything unnecessary removed or
  refactored.
- Related to (not a duplicate of) the earlier captured idea in this same
  folder — a per-command `--auto` flag on `/test-feature` and
  `/code-review-feature` that removes the in-command approval prompt. That
  flag, if it ships, could be composed into `/autom-dev`'s stage execution
  rather than `/autom-dev` reimplementing that behavior itself.

## Implementation ideas / open questions
Before building anything, inspect: existing command files, skill files,
project/workflow documentation, configuration files, existing
scripts/automation, the database structure, the testing infrastructure, and
any existing orchestration mechanisms — to identify the canonical location
and structure for new skills/commands and confirm nothing already solves
part of this.

State to track per automation run (reusing existing project state mechanisms
— e.g. the features DB / registry / status.md — rather than inventing a new
store): automation run ID, selected release, current workflow stage,
completed stages, generated artifacts, files changed, tests executed, review
findings, shipping status, user decisions, permission decisions, errors,
unresolved issues, discovered bugs, improvement opportunities, and
deviations from the expected workflow.

Failure handling: determine whether a stage failure is transient/safely
retryable; if so retry per that command's own conventions; if not, capture
the stage, command, failure, attempted remediation, current project state,
and a recommended next action; never blindly continue into later stages when
that could produce invalid or misleading results; preserve enough state to
resume without restarting completed stages; cap any single stage/fix attempt
at 3 tries before stopping to summarize and ask the user.

Open questions carried from the source thoughts:
- Should there be a `--dry-run` mode that prints the stage-by-stage plan
  without executing anything?
- Should `/autom-dev` stop at feature boundaries (e.g. after one release
  ships) before starting the next release of a multi-release feature, or is
  that already covered by "one release per run" being the default unit?
- Does this need a dedicated DB column (e.g. `auto_pipeline_at`) so
  `/status` and the roadmap can show a feature is mid-automation, or is a
  run summary/status line sufficient?
- What exactly counts as an "architectural decision that cannot safely be
  inferred" versus a routine implementation choice `/autom-dev` can make on
  its own — e.g. does any spec with an "Open questions" section always pause
  the run?

## Release pressure / deadlines
Not specified.

## Recommendations
Use two automations, not one. Your instinct here is right. Planning is a natural human checkpoint; implementation is where autonomous execution is most valuable.
Make one release the default execution boundary. If /plan-release produces 3 releases, don't let the automation consume the entire context window attempting all 3. Run /autom-dev release-x.1, then /autom-dev release-x.2, etc.
Don't make /autom-dev dependent on /autom-plan being immediately prior. It should be able to consume a previously generated release plan. That makes interrupted sessions recoverable.
Have a run journal, but don't create a new system if one already exists. The journal should record decisions, permissions, failures, findings, and stage status. This is especially important for preventing repetitive permission/clarification prompts.
Separate "decision memory" from "permission memory." A user saying "yes, do this operation" should not automatically become a permanent authorization.
Make the automation resumable. If /test-feature fails after implementation has completed, the next run shouldn't start from /create-spec again.
Treat the existing commands as the source of truth. The new automation should be an orchestrator, not a second implementation of your development methodology.
Add a final "duplication audit." This directly addresses your requirement that existing commands, skills, configs, database structures, etc. be reused rather than replicated.
For the truncate fix specifically, enforce root-cause validation. The automation should explicitly guard against "making the test pass" through weaker assertions, retries, sleeps, ordering hacks, or test-only workarounds when the documented fix calls for correcting the underlying behavior.
The biggest architectural principle I'd use is:
/autom-plan decides what should be done; /autom-dev executes one approved release; the existing workflow commands remain responsible for how it is done.