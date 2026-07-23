---
description: Read a spec file, produce an implementation plan, execute it, and update status tracking
argument-hint: "Release number e.g. 15.1"
allowed-tools: Read, Write, Edit, Glob, Bash, mcp__github__create_pull_request, mcp__github__merge_pull_request, mcp__github__list_pull_requests
---

You are a senior developer implementing a feature for the Oxos Platform.
Your job is to read the spec for the given release number, enter Plan Mode to produce
an implementation plan, execute it, then update status tracking.

User input: $ARGUMENTS

## Step 0 — If no arguments given, show a picker

If $ARGUMENTS is empty or blank:
  Read `.claude/features/registry.md` in full.
  Find all release sub-rows with status 📝 Spec'd.

  If none exist:
    Print: "No spec'd features — run /create-spec first."
    Stop.

  If exactly one spec'd release exists:
    Call AskUserQuestion with ONE question. Header: "Which feature?".
    One option for the single spec'd release:
      - Label: "<number> — <title>"
      - Description: "Implement this release"
      - Preview:
        ```
        /implement-feature <number>

        Reads .claude/specs/<spec-filename>
        Produces an implementation plan and executes it.
        Updates registry to 🔧 In Progress when done.
        ```
    After confirmation, continue to Step 1 using that release number.

  If multiple spec'd releases exist:
    Call AskUserQuestion with ONE question. Header: "Which feature?".
    One option per spec'd release (max 4):
      - Label: "<number> — <title>"
      - Description: "Implement this release"
      - Preview:
        ```
        /implement-feature <number>

        Reads .claude/specs/<spec-filename>
        Produces an implementation plan and executes it.
        Updates registry to 🔧 In Progress when done.
        ```
    After selection, continue to Step 1 using the selected number.

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

## Step 5b — Validate SRI integrity hashes

After executing the plan, validate that all CDN script integrity hashes in
`templates/base.html` still match the actual served files. SRI mismatches cause
silent script-blocking in the browser with no server-side error.

For each `<script>` tag in `base.html` that has an `integrity="sha384-..."` attribute:

1. Extract the `src` URL and the current hash value
2. Fetch the resource and compute the correct hash:
   ```bash
   HASH=$(curl -s <CDN_URL> | openssl dgst -sha384 -binary | openssl base64 -A)
   echo "Expected: sha384-$HASH"
   ```
3. Compare the computed hash against the one in the template
4. If they don't match, update the `integrity` attribute with the correct hash
5. If they do match, report: "SRI hash for <CDN_URL> — valid ✓"

## Step 6 — Update status tracking

After implementation is complete:

### 6a — Update the `features` DB table

Run a Python one-liner to set `implemented_at` for this release:

```bash
python3 - <<'EOF'
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('DATABASE_URL')
if not url:
    print('Warning: DATABASE_URL not set — skipping DB stamp')
else:
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            "UPDATE features SET implemented_at = NOW() WHERE number = %s AND implemented_at IS NULL",
            ("<release_number>",),
        )
        conn.commit()
        if cur.rowcount == 0:
            print("WARNING: 0 rows updated — check that <release_number> was substituted correctly and the row exists")
        else:
            print(f"Updated {cur.rowcount} row(s)")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB stamp failed: {e}")
EOF
```

Replace `<release_number>` with the actual release number (e.g. `15.1`).

### 6b — Update registry.md

1. Read `.claude/features/registry.md`
2. Find the release sub-row whose Number matches the release number
3. Update its Status from `📝 Spec'd` to `🔧 In Progress`
4. Find the parent feature row and update its Status to `🔧 In Progress`
   if it was previously `📝 Spec'd`

### 6c — Refresh status

Run `/status` to refresh the live feature status view from the database.

## Step 7 — Report to the user

Print:
```
Release:     <number> — <title>
Spec:        .claude/specs/<spec_filename>
Status:      🔧 In Progress
```

Then say:
"Implementation complete. Run `/test-feature <spec-name>` when ready to test."

---

## Pipeline Reminder

After implementation is complete, end with:
```
🔧 Implemented! Next: /test-feature <spec-name> → /code-review-feature → /ship-feature
```

