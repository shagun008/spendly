---
description: Analyse a captured thought and decompose it into release-sized units before spec creation
argument-hint: "Feature number e.g. 11 or 10.1"
allowed-tools: Read, Write, Glob, Bash, Skill
---

You are a senior engineer and release planner for the Spendly expense tracker.
Your job is to read a captured thought file, analyse its scope and complexity,
and decompose it into the right number of release-sized units — each one small
enough to be a single spec and a single PR.

This is the stage where splitting happens. `/create-spec` always works on one
already-decomposed release unit; it never splits work itself.

User input: $ARGUMENTS

## Step 1 — Parse the feature number
Extract the feature number from $ARGUMENTS (e.g. `11` or `10.1`).
If missing, ask: "Which feature number would you like to plan? (e.g. 11 or 10.1)"

## Step 2 — Find and read the processed thought file
List all files in `.claude/features/processed-thoughts/`.
Find the file whose name starts with `<feature_number>-`.
Read it fully.

If no matching file exists, stop and say:
"No processed thought file found for feature <number>. Run `/capture-thoughts` first."

## Step 3 — Read context
Read the following to understand what already exists:
- `CLAUDE.md` — implementation rules, existing routes, schema, CSS variables
- All files in `.claude/specs/` — what has already been built

## Step 4 — Analyse scope and complexity
From the thought file, identify everything implied:
- New routes needed
- Database changes (new tables, columns, constraints)
- New templates or significant template changes
- New JS or CSS files
- Third-party dependencies
- Auth or permission changes
- Any cross-cutting concerns (e.g. affects multiple pages)

Use this to assess overall complexity:
- **Simple:** 1–2 routes, no DB changes, small UI — fits in one spec
- **Medium:** 2–4 routes or 1 DB change — likely 1–2 specs
- **Complex:** Multiple DB changes, many routes, or multi-page UI — 2–4 specs

## Step 5 — Design the release decomposition
Split the work into releases using these principles:

1. **Each release must be independently deployable** — it should leave the app in
   a working state, not a half-built one.
2. **MVP first** — Release 1 should be the smallest thing that delivers value.
3. **Dependencies flow forward** — Release N+1 must depend on Release N, not the other way.
4. **One spec per release** — each release maps to exactly one `/create-spec` call.
5. **Deferred work is explicit** — anything not in any release is listed as deferred.

If the feature is simple, one release is fine. Do not split unnecessarily.

## Step 6 — Present the recommendation
Show the user the proposed decomposition in plain English before writing anything.
Format:

```
Feature: <title> (<number>)

Proposed decomposition: <N> release(s)

Release 1 — <short title>
  What's included: <scope>
  Suggested spec slug: <slug>
  Depends on: <existing spec numbers or "nothing">
  Risk: low | medium | high

Release 2 — <short title>  (if applicable)
  What's included: <scope>
  Suggested spec slug: <slug>
  Depends on: Release 1
  Risk: low | medium | high

Deferred: <anything not included>

Open questions: <any unresolved items from the thought file>
```

Ask: "Does this decomposition look right, or would you like to adjust it?"

Wait for the user to confirm or redirect before proceeding.

## Step 7 — Write the release plan file
Once confirmed, save to: `.claude/features/releases/<feature_number>-<slug>.md`

Use this exact format:

```markdown
---
number: <feature_number>
title: <Title Case>
type: new-feature | enhancement
parent: <parent number or null>
status: planned
releases: <count>
created: <today's date YYYY-MM-DD>
---

# Release Plan: <title>

## Roadmap description
<one sentence for a non-technical audience — what this feature does and why it matters to a user of the app. This is what appears on the public /roadmap page. Under 25 words, no jargon, no route names, no file names. Example: "A public board where users can submit and upvote ideas for new features.">

## Summary
<one paragraph describing what this feature does and how it was decomposed>

## Releases

### Release 1 — <short title> (MVP)
- **Scope:** <what's included>
- **Spec slug:** <slug — what to pass to /create-spec>
- **Spec arg:** `<feature_number>.1 <slug>`
- **Depends on:** <feature or spec numbers, or "nothing">
- **Risk:** low | medium | high

### Release 2 — <short title>
- **Scope:** <what's included>
- **Spec slug:** <slug>
- **Spec arg:** `<feature_number>.2 <slug>`
- **Depends on:** Release 1
- **Risk:** low | medium | high

## Deferred / Out of scope
<anything explicitly excluded from all releases, with rationale>

## Open questions
<unresolved items that need answering before or during implementation>
```

## Step 8 — Update the registry
In `.claude/features/registry.md`:
1. Find the feature row for this feature number. Update its Status to `📋 Planned`
   and Specs column to `<N> releases planned`
2. Remove the placeholder release sub-row (the one with `→ <title>` and `💡 Captured`)
3. Add one release sub-row per release in the plan:
   | <feature_number>.1 | → <release_1_title> | release | <feature_number> | 📋 Planned | — |
   | <feature_number>.2 | → <release_2_title> | release | <feature_number> | 📋 Planned | — |

## Step 8b — Commit, push, and merge via /ship-feature
Stage all planning artefacts, commit, then call `/ship-feature` to handle the branch creation, push, PR lifecycle, and merge.

Run these git steps in order:
```
git add .claude/
git commit -m "plan: release plan for <feature_number> <title>"
```

Then run `/ship-feature`. It will:
1. Create a new branch `plan/<feature_number>-<slug>` from main
2. Cherry-pick the commit onto it
3. Push the branch
4. Create a PR, merge it, and clean up

Report the PR URL and confirm the merge before continuing to Step 9.

## Step 8d — Write the Summary into the features DB table
Extract the Summary paragraph from the release plan file you just wrote (the
paragraph under `## Summary`). Run the following to upsert it into the
`description` column for the parent feature row:

```bash
python3 - <<'EOF'
import os, re, psycopg2
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('DATABASE_URL')
if not url:
    print('Warning: DATABASE_URL not set — skipping DB update')
else:
    try:
        with open(".claude/features/releases/<release_plan_filename>") as f:
            content = f.read()
        m = re.search(r'## Roadmap description\n+(.+?)(?=\n##|\Z)', content, re.DOTALL)
        description = ' '.join(m.group(1).strip().split()) if m else None
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            "UPDATE features SET description = %s WHERE number = %s",
            (description, "<feature_number>"),
        )
        conn.commit()
        if cur.rowcount == 0:
            print('WARNING: 0 rows updated — check that <feature_number> is correct and the parent row exists')
        else:
            print(f"Updated {cur.rowcount} row(s)")
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB update failed: {e}')
EOF
```

Replace `<release_plan_filename>` and `<feature_number>` with the actual values.
If the DB update fails, log the error and continue — do not block the plan creation.

If the release plan is later edited and re-run, this step re-executes and
overwrites the previous description — keeping the DB in sync with the file.

## Step 8e — Stamp planned_at and insert release sub-rows in the database

For each release defined in this plan, determine its `release_subtype`:
- `new-feature` — adds a net-new capability (new route, new page, new DB table)
- `enhancement` — improves something that already exists
- `bug-fix` — corrects broken or incorrect behaviour

Then run the following Python snippet. Substitute PARENT_NUMBER and build RELEASE_ROWS
as a list of tuples — one per release defined in this plan:

```bash
python3 -c "
import psycopg2, os
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('DATABASE_URL')
if not url:
    print('Warning: DATABASE_URL not set — skipping DB stamp')
else:
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        now = datetime.now(timezone.utc)
        # Stamp planned_at on the parent feature row
        cur.execute(
            'UPDATE features SET planned_at = %s WHERE number = %s',
            (now, 'PARENT_NUMBER')
        )
        if cur.rowcount == 0:
            print('WARNING: 0 rows updated for parent PARENT_NUMBER — check the number is correct and the row exists')
        # Insert release sub-rows — idempotent, skip if already exist
        # Tuple format: (number, parent_number, title, slug, type, release_subtype)
        # release_subtype is one of: new-feature, enhancement, bug-fix
        release_rows = [
            ('RELEASE_NUMBER', 'PARENT_NUMBER', 'RELEASE_TITLE', 'RELEASE_SLUG', 'release', 'RELEASE_SUBTYPE'),
            # one tuple per release
        ]
        inserted = 0
        for row in release_rows:
            cur.execute('''
                INSERT INTO features (number, parent_number, title, slug, type, release_subtype, planned_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (number) DO NOTHING
            ''', (*row, now))
            inserted += cur.rowcount
        if inserted == 0:
            print('WARNING: 0 sub-rows inserted — rows may already exist (OK on re-run) or RELEASE_NUMBER placeholders were not substituted')
        else:
            print(f'Sub-rows inserted: {inserted}')
        print('Done')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB stamp failed: {e}')
"
```

If the DB write fails, log the error and continue — do not block the command.

## Step 9 — Report to the user
Print:
```
Feature:       <number> — <title>
Releases:      <count>
Release plan:  .claude/features/releases/<number>-<slug>.md
```

Then print one line per release showing the exact command to run:
```
To create specs, run:
  /create-spec <feature_number>.1 <release_1_slug>    ← Release 1: <release_1_title>
  /create-spec <feature_number>.2 <release_2_slug>    ← Release 2: <release_2_title>
```

If only one release, still use dot notation:
```
  /create-spec <feature_number>.1 <slug>    ← Release 1 (single release)
```

---

## Pipeline Reminder

After the release plan is written, end with:
```
📋 Planned! Next: /create-spec <number.release> <slug> → /implement-feature → /test-feature → /code-review-feature → /ship-feature
```
