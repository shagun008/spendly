---
number: 25
title: Pipeline Orchestration Automation
type: new-feature
parent: null
status: planned
releases: 1
created: 2026-08-08
---

# Release Plan: Pipeline Orchestration Automation

## Roadmap description
Two new commands that walk a feature idea through planning, building, testing, and shipping automatically, pausing only when a real decision is needed.

## Summary
The Oxos Platform dev pipeline currently requires each stage — capture, plan,
spec, implement, test, review, ship — to be invoked and watched manually as a
separate slash command, even when a stage completes cleanly with nothing for
the user to weigh in on. This feature adds two orchestration commands,
`/autom-plan` and `/autom-dev`, that drive the existing pipeline commands in
sequence without duplicating their logic, guardrails, or conventions.
`/autom-plan` covers the planning half (`/capture-thoughts` →
`/plan-release`) and always stops before any implementation begins, letting
the user choose which planned release to build. `/autom-dev` covers the
build-and-ship half (`/create-spec` → `/implement-feature` →
`/test-feature` → `/code-review-feature` → `/ship-feature`) for exactly one
explicitly selected release, auto-fixing test failures and review findings
with a 3-retry cap per stage before pausing to ask the user. Given the tight
coupling between the two commands and the fact that they were specified
together as one coherent capability, this is scoped as a single release
rather than split further.

## Releases

### Release 1 — Autom-Plan & Autom-Dev Orchestration Commands (MVP)
- **Scope:**
  - New command `/autom-plan`: runs `/capture-thoughts` → `/plan-release`,
    presents the resulting release plan (or all releases if multiple),
    recommends which to build first, and stops — never auto-implements.
  - New command `/autom-dev <feature.release>`: runs `/create-spec` →
    `/implement-feature` → `/test-feature` → `/code-review-feature` →
    `/ship-feature` for exactly one selected release. Waits for each stage
    to complete before starting the next. Auto-fixes failing tests and
    auto-implements code-review findings, re-running the relevant stage
    until it passes or the 3-retry cap is hit, at which point it stops,
    summarizes the issue and its recommendation, and asks the user for
    permission to continue.
  - `/autom-dev` does not require `/autom-plan` to have run immediately
    before it in the same session — it loads the target release from the
    already-written release plan file (`.claude/features/releases/`) and
    registry/DB state, so a previously generated plan can be picked up in a
    later, separate session.
  - Stage-level resumability: if a run is interrupted or a stage fails after
    an earlier stage has already completed (e.g. `/test-feature` fails after
    `/implement-feature` succeeded), the next `/autom-dev` invocation for
    that release resumes from the failed/incomplete stage using the
    already-recorded pipeline timestamps — it does not restart from
    `/create-spec` or redo completed work.
  - Root-cause validation guard on test/review auto-fixes: when
    `/autom-dev` auto-fixes a failing test or review finding, it must
    correct the underlying behavior the fix is meant to address. It must
    not make a test pass via weaker assertions, added sleeps/retries/timing
    hacks, reordering, or other test-only workarounds that mask the
    original failure instead of fixing it.
  - Decision memory and permission memory are tracked as two distinct
    concerns, not one conflated file: decision memory records
    architectural/product choices the user made (what was decided and why);
    permission memory records authorization scope for actions
    (one-time / current-run / project-level / permanent policy). A single
    "yes, do this" from the user is recorded as scoped to that instance and
    is never auto-promoted to a permanent authorization.
  - Structured run summary printed at the end of every `/autom-dev` run:
    stages completed, artifacts generated, files changed, tests executed,
    review findings, shipping status, decisions recorded, bugs/improvements
    discovered, and any deviations from the expected workflow.
  - Final duplication audit as the last step of an `/autom-dev` run: before
    reporting completion, re-check the repository for any duplicate or
    redundant commands/skills/config/DB structures introduced during the
    run, and remove or refactor anything unnecessary.
  - Both commands call the existing commands/skills exactly as documented —
    preserving their guardrails (including the git push policy, which stays
    scoped to `/ship-feature`'s existing steps) — and reuse the existing
    `features` DB table (pipeline timestamp columns, `test_report`,
    `review_report`) as the state store instead of introducing a new one.
- **Spec slug:** pipeline-orchestration-automation
- **Spec arg:** `25.1 pipeline-orchestration-automation`
- **Depends on:** nothing — orchestrates existing commands as they exist today
- **Risk:** medium — `/autom-dev` can auto-implement fixes and auto-ship
  without a prompt at every individual stage; mitigated by the 3-retry cap
  per stage and an explicit safe-to-continue vs. needs-user-input
  distinction that pauses on destructive/irreversible actions, architectural
  ambiguity, conflicting requirements, or anything that could corrupt
  project state.

## Deferred / Out of scope
- **`--dry-run` mode for `/autom-dev`** — printing the stage-by-stage plan
  without executing anything. Not required for the MVP to be useful; can be
  added as a fast follow if the retry/auto-fix behavior proves risky enough
  in practice to want a preview step.
- **A dedicated `auto_pipeline_at`-style DB column** for `/status`/roadmap
  visibility into "mid-automation" state. Deferred in favor of the
  structured run-summary output, which already surfaces this per-run; a DB
  column can be added later if concurrent visibility into an in-flight
  automated run turns out to be needed.
- **Composing a `--auto` flag into `/test-feature` / `/code-review-feature`
  themselves** (the separate idea captured in
  `thoughts_2026-06-24_19-16.md`). `/autom-dev` will drive those commands as
  they exist today, handling the "skip the approval prompt" behavior at the
  orchestration layer rather than inside the underlying commands. That flag
  remains its own potential future feature.

## Open questions
- Should any spec containing an "Open questions" section always force
  `/autom-dev` to pause before implementation, or only specific categories
  of open question (e.g. ones affecting schema or auth)?
- Should `/autom-dev` stop at feature boundaries when a feature has multiple
  planned releases, or is "one release per run" — with the user explicitly
  selecting each run's target release — sufficient guardrail on its own?
