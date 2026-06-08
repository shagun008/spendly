---
number: 15
title: Developer Roadmap Page
type: new-feature
parent: null
status: captured
created: 2026-06-07
source_folder: .claude/features/user-thoughts/Developer Roadmap Page/
---

# Processed Thought: Developer Roadmap Page

## Problem / Goal
Visitors and users have no visibility into what's being built on Spendly. A public /roadmap page gives transparency into the full feature pipeline — what's shipped, in progress, and planned.

## Who benefits
All visitors — public, no login required.

## Success looks like
A pipeline table where each row is a feature and each column is a dev stage (Captured → Planned → In Progress → In Review → Shipped), with ✓ + timestamp per completed stage. Clicking a row opens a structured detail card showing title, status, description, and release breakdown.

## Constraints, risks, dependencies
Requires a new `features` DB table seeded from the existing registry. Per-stage timestamps need to be backfilled for all existing shipped features — exact dates are unknown and will need to be approximated or left null.

## Implementation ideas / open questions
- New `features` table with `captured_at`, `planned_at`, `in_progress_at`, `in_review_at`, `shipped_at` columns per stage
- Query helpers: `get_all_features()` and `get_feature_by_number(number)` in `queries.py`
- Routes: `GET /roadmap` (pipeline table) and `GET /roadmap/<number>` (detail card)
- Detail card shows: title, feature number, status badge, description, release breakdown, optional PR link
- Nav link added to public nav (visible when logged out)
- `roadmap.css` in `static/css/`
- Seed function to populate the features table from the registry on first run

## Release pressure / deadlines
None specified.

## Resolved open questions

- **Backfilled timestamps for shipped features:** Show "May 2026" for all existing shipped features where exact timestamps are unknown.
- **Detail view interaction:** Expand-in-place on the table row — no separate `/roadmap/<number>` page. Clicking a row expands it inline to show the detail card.

## Architectural decisions

- **Remove `.claude/features/status.md`** — it's a derived cache, redundant once the `features` DB table is the source of truth. The `/status` command should query the DB instead of reading this file.
- **Keep `.claude/features/registry.md`** — retained as a git-tracked audit trail checked into the repo. Useful as a human-readable backup when DB is unavailable (new machine, empty DB). Commands read from the DB; the registry is updated alongside the DB but is no longer authoritative.
- **`features` DB table is the source of truth** — all harness commands (`/capture-thoughts`, `/plan-release`, `/create-spec`, `/ship-feature`, `/status`) read from and write to the DB. The registry is updated in parallel as a backup, not as the primary store.
