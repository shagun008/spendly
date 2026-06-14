# Thought: Release-level type classification (new-feature / enhancement / bug-fix)

## Core idea

Right now the `type` column on the `features` table is set on the parent feature row
during `/capture-thoughts` and hardcoded to `'feature'`. This loses meaningful
information and is set too early — at capture time you don't yet know how the work
will decompose.

The agreed approach:

- **Parent feature rows** — no type. They are containers/labels only.
- **Release sub-rows** — each gets a single type assigned during `/plan-release`,
  when you actually know what each release does:
  - `new-feature` — net-new capability, likely needs new routes or DB changes
  - `enhancement` — improvement to something that already exists
  - `bug-fix` — corrects broken or incorrect behaviour

A single parent feature can have releases of mixed types (e.g. Release 1 fixes a bug,
Release 2 adds a new capability). No aggregation or "dominant type" is needed on
the parent — the roadmap reads types from release sub-rows directly.

## What needs to change

1. `capture-thoughts.md` — remove the type question at Step 3 and drop `type` from
   the DB insert for parent feature rows.
2. `plan-release.md` — for each release defined in the plan, ask or infer the type
   (`new-feature`, `enhancement`, `bug-fix`) and include it in the release plan file
   and the DB insert for sub-rows.
3. `database/db.py` — the `type` column can remain as-is on the schema; parent rows
   will simply have NULL or a neutral default, release rows will have the meaningful value.
4. Roadmap page — render the release type as a badge on each release row.

## What this is NOT

- Not a multi-type/array approach on the parent row — kept deliberately simple.
- Not a change to the capture-thoughts UX beyond removing one question.
- Not urgent — the app works fine without it. This is a quality/accuracy improvement.


Created: 2026-06-13 13:32 EST
