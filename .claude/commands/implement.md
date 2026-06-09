---
description: Read a spec file, produce an implementation plan, execute it, and update status tracking
argument-hint: "Release number e.g. 15.1"
allowed-tools: Read, Write, Edit, Glob, Bash, mcp__github__create_pull_request, mcp__github__merge_pull_request, mcp__github__list_pull_requests
---

You are a senior developer implementing a feature for the Spendly expense tracker.
Your job is to read the spec for the given release number, enter Plan Mode to produce
an implementation plan, execute it, then update status tracking.

User input: $ARGUMENTS

## Step 1 — Parse the release number

Extract the release number from $ARGUMENTS (e.g. `15.1` or `11-2`).
If missing, ask: "Which release number would you like to implement? (e.g. 15.1)"

## Step 2 — Find and read the spec file

List all files in `.claude/specs/`.
Find the file whose name starts with `<release_number>-`.

If no matching spec file exists, stop and say:
"No spec file found for release <number>. Run `/create-spec` first."

Read the spec file fully.

## Step 3 — Read context

Read the following to understand the current codebase state:
- `CLAUDE.md` — implementation rules, schema, CSS variables
- `app.py` — existing routes and structure
- `database/db.py` — existing schema and helper functions
- `database/queries.py` — existing query helpers
- All relevant templates in `templates/` that the spec references

## Step 4 — Enter Plan Mode

Call `EnterPlanMode`.

In Plan Mode:
- Produce a step-by-step implementation plan based on the spec
- Each step must reference the exact file to change and what to change
- Call out any ambiguities or decisions made
- Present the plan for user approval before proceeding

Wait for the user to approve the plan via ExitPlanMode before touching any files.

## Step 5 — Execute the plan

Implement every step in the approved plan. Follow all rules in `CLAUDE.md`:
- No SQLAlchemy or ORMs — raw `psycopg2` queries only
- Parameterised queries only — never interpolate user data into SQL strings
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard on every protected route
- Ownership check on all expense mutations
- Flash messages for all user-facing outcomes
- Currency in ₹
- Dates stored as YYYY-MM-DD strings

## Step 6 — Update status tracking

After implementation is complete:

### 6a — Update the `features` DB table

Run a Python one-liner to set `implemented_at` for this release:

```bash
python - <<'EOF'
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute(
    "UPDATE features SET implemented_at = NOW() WHERE number = %s",
    ("<release_number>",),
)
conn.commit()
print(f"Updated {cur.rowcount} row(s)")
cur.close()
conn.close()
EOF
```

Replace `<release_number>` with the actual release number (e.g. `15.1`).

### 6b — Update registry.md

1. Read `.claude/features/registry.md`
2. Find the release sub-row whose Number matches the release number
3. Update its Status from `📝 Spec'd` to `🔧 In Progress`
4. Find the parent feature row and update its Status to `🔧 In Progress`
   if it was previously `📝 Spec'd`

### 6c — Rewrite status.md

Rewrite `.claude/features/status.md` by reading the full registry and
regenerating all sections grouped by status. Set "Last updated" to today's date.

Use this format:

```markdown
# Spendly — Feature Status
Last updated: YYYY-MM-DD

## 🔧 In Progress
- **<number>** <title> (`feature/<slug>`)

## 👀 In Review
...

## 📋 Planned — ready to spec
...

## 📝 Spec'd — ready to implement
...

## 💡 Captured — needs release planning
...

## ✅ Recently Shipped (last 5)
...
```

## Step 7 — Report to the user

Print:
```
Release:     <number> — <title>
Spec:        .claude/specs/<spec_filename>
Status:      🔧 In Progress
```

Then say:
"Implementation complete. Run `/test-feature <spec-name>` when ready to test."
