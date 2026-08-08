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
  - Decision/permission memory: a project-local file recording what was
    requested, why, what the user decided, and the scope of that decision
    (one-time / current-run / project-level / permanent policy) — reused
    across `/autom-dev` runs so the same question isn't asked twice for a
    decision that still applies. No sensitive information is persisted.
  - Structured run summary printed at the end of every `/autom-dev` run:
    stages completed, artifacts generated, files changed, tests executed,
    review findings, shipping status, decisions recorded, bugs/improvements
    discovered, and any deviations from the expected workflow.
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
