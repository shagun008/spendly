---
number: 15
title: Developer Roadmap Page
type: new-feature
parent: null
status: planned
releases: 3
created: 2026-06-07
---

# Release Plan: Developer Roadmap Page

## Roadmap description
A public page showing full transparency into what's being built on Spendly — what's shipped, in progress, and planned.

## Summary
A public `/roadmap` page that gives any visitor full transparency into the Spendly feature pipeline. The page shows a table where each row is a feature and each column is a dev stage (Captured → Planned → In Progress → In Review → Shipped), with a tick and timestamp per completed stage. Clicking a row expands it in-place to show a structured detail card. The work is split into three releases: Release 1 builds the DB layer, seeds all existing features, and ships the pipeline table; Release 2 adds the expand-in-place detail view; Release 3 wires up the harness commands so the features table stays live as new features move through the pipeline.

## Releases

### Release 1 — DB Layer + Pipeline Table (MVP)
- **Scope:** New `features` table with per-stage `*_at` timestamp columns. Seed function populating it from the existing registry — existing shipped features backfilled with "May 2026" as the timestamp. `GET /roadmap` route (public, no auth) rendering the pipeline table. Nav link visible when logged out. `roadmap.css`. Remove `.claude/features/status.md` (DB is now source of truth).
- **Spec slug:** roadmap-pipeline
- **Spec arg:** `15.1 roadmap-pipeline`
- **Depends on:** nothing
- **Risk:** medium (new DB table + seed backfill)

### Release 2 — Expand-in-Place Detail View
- **Scope:** Clicking a feature row in the pipeline table expands it inline to show a detail card: title, feature number, status badge, description, release breakdown with per-release statuses, and optional PR link. Vanilla JS toggle, no page reload. Styling for the expanded row state in `roadmap.css`.
- **Spec slug:** roadmap-detail
- **Spec arg:** `15.2 roadmap-detail`
- **Depends on:** Release 1
- **Risk:** low

### Release 3 — Harness Integration (Live Updates)
- **Scope:** Update all harness commands to write to the `features` DB table as features advance through the pipeline. `/capture-thoughts` inserts a new row and sets `captured_at`. `/plan-release` sets `planned_at` and inserts release sub-rows. `/create-spec` sets `in_progress_at`. `/ship-feature` sets `shipped_at`. `/status` command reads from the DB instead of `status.md`. Remove `status.md` from the repo. Registry.md continues to be updated in parallel as a git-tracked backup.
- **Spec slug:** roadmap-harness-integration
- **Spec arg:** `15.3 roadmap-harness-integration`
- **Depends on:** Release 1
- **Risk:** medium (touches every harness command)

## Deferred / Out of scope
- **`/code-review-feature` and `/test-feature` writing to DB** — these commands don't advance the pipeline status so no DB write is needed; `in_review_at` is set by `/create-spec` or `/ship-feature` as appropriate.
- **Separate detail page** (`/roadmap/<number>`) — decided against; expand-in-place is the chosen interaction.
- **Date filter on the roadmap** — charts/filters can be added in a future release if needed.

## Open questions
All resolved:
- Backfilled timestamps for existing shipped features → show "May 2026"
- Detail view interaction → expand-in-place on the table row (no separate page)
