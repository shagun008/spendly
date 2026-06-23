---
description: Commit, push, create PR, merge, and clean up after a feature is complete
allowed-tools: Read, Bash, mcp__github__create_pull_request, mcp__github__merge_pull_request, mcp__github__delete_branch, Bash(railway*)
---

## Step 0 — Pre-flight Checks

Before doing any work, verify prerequisites:

1. **GitHub auth** — run `gh auth status` or check that `mcp__github__create_pull_request` is available. If neither `gh` CLI nor GitHub MCP is connected, stop immediately and say: "GitHub auth not available. Run `gh auth login` or connect GitHub MCP via `/mcp`, then re-run `/ship-feature`."

2. **Working directory** — run `git status`. If there are uncommitted changes that are NOT part of this feature, warn the user and ask whether to stash them before proceeding.

3. **Branch** — run `git branch --show-current`. If already on `main`, stop and say: "Already on main. Switch to the feature branch first."

Store the branch name as CURRENT_BRANCH.

## Step 2 — Generate commit message
Run:
```bash
git diff --staged
git diff
git log main..HEAD --oneline
```
Read .claude/specs/ to find the spec for the current feature.

Generate a Conventional Commit message:
- feat: new feature
- fix: bug fix
- chore: config or tooling
- docs: documentation only

Always include the release number as a scope in parentheses.
Format: `type(number): description`

Rules:
- Lowercase
- No period at the end
- Under 72 characters
- Describes what the user can now do, not what the code does
- Never add a Co-Authored-By trailer
- Do NOT include the PR number — GitHub squash merge appends it automatically

Good: "feat(15.2): expand roadmap rows inline to show feature description"
Bad: "feat: added detail view to roadmap.html"

## Step 2b — README check
Before committing, check whether README.md needs updating for this feature:
- If the feature adds a new user-visible capability: add it to the
  Features list in the About Spendly section
- If the feature adds a new entry to the roadmap: add a row to the
  Feature Roadmap table
- If the tech stack changed: update the Tech Stack table
- If none of the above apply: no README update needed

If README.md was updated, stage it with the rest of the changes.
Report: "✓ README checked — <updated | no changes needed>"

## Step 3 — Commit
```bash
git add .
git commit -m "<generated-message>"
```
Report: "✓ Committed — <message>"

## Step 4 — Push to feature branch
```bash
git push -u origin CURRENT_BRANCH
```
Report: "✓ Pushed — CURRENT_BRANCH"

## Step 5 — Create PR via GitHub MCP
Use the GitHub MCP server to create a pull request
from CURRENT_BRANCH into main.

Title: plain English feature name, no conventional commit prefix
Example: "Add delete expense functionality"

Description:
```markdown
## What this PR does
<one paragraph from the spec overview section>

## Changes
<bullet list of every file changed with one line description each>

## Definition of done
<copy the definition of done checklist from the spec,
mark every item as checked [x]>

## How to test
1. Run python app.py
2. Log in as demo@spendly.com / demo123
3. <specific steps from the spec to verify this feature works>
```

Report: "✓ PR created — <PR URL>"

## Step 6 — Merge PR via GitHub MCP
Use the GitHub MCP server to merge the pull request
just created. Use regular merge (not squash) so the PR
shows a proper diff on GitHub.

Report: "✓ PR merged to main"

## Step 7 — Delete remote branch via GitHub MCP
Use `git push origin --delete CURRENT_BRANCH` to delete the remote branch.

Report: "✓ Remote branch deleted"

## Step 8 — Switch to main and pull
```bash
git checkout main
git pull origin main
```
Report: "✓ Switched to main — up to date"

## Step 9 — Delete local feature branch
```bash
git branch -D CURRENT_BRANCH
```
Report: "✓ Local branch deleted"

## Step 9a — Stamp reviewed_at and shipped_at in the database

Read the spec to identify the feature number (e.g. `15.2`).

Run the following Python snippet, substituting FEATURE_NUMBER:

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
        cur.execute(
            \"UPDATE features SET reviewed_at = COALESCE(reviewed_at, %s), shipped_at = %s WHERE number = %s\",
            (now, now, 'FEATURE_NUMBER')
        )
        if cur.rowcount == 0:
            print('WARNING: 0 rows updated — check that FEATURE_NUMBER was substituted correctly and the row exists')
        else:
            print('Rows updated:', cur.rowcount)
        # Stamp parent shipped_at if all sibling releases are now shipped
        cur.execute('''
            SELECT COUNT(*) FROM features
            WHERE parent_number = (SELECT parent_number FROM features WHERE number = %s)
            AND shipped_at IS NULL
            AND number != %s
        ''', ('FEATURE_NUMBER', 'FEATURE_NUMBER'))
        remaining = cur.fetchone()[0]
        if remaining == 0:
            cur.execute('''
                UPDATE features SET shipped_at = %s
                WHERE number = (SELECT parent_number FROM features WHERE number = %s)
                AND parent_number IS NULL
            ''', (now, 'FEATURE_NUMBER'))
            if cur.rowcount:
                print('Parent feature shipped_at stamped.')
        # Propagate pipeline timestamps from release sub-rows to parent
        # so the roadmap page shows all green dots on the parent row
        cur.execute('''
            UPDATE features parent SET
                captured_at = COALESCE(parent.captured_at, (SELECT captured_at FROM features child WHERE child.parent_number = parent.number AND child.captured_at IS NOT NULL LIMIT 1)),
                planned_at = COALESCE(parent.planned_at, (SELECT planned_at FROM features child WHERE child.parent_number = parent.number AND child.planned_at IS NOT NULL LIMIT 1)),
                spec_at = COALESCE(parent.spec_at, (SELECT spec_at FROM features child WHERE child.parent_number = parent.number AND child.spec_at IS NOT NULL LIMIT 1)),
                implemented_at = COALESCE(parent.implemented_at, (SELECT implemented_at FROM features child WHERE child.parent_number = parent.number AND child.implemented_at IS NOT NULL LIMIT 1)),
                tested_at = COALESCE(parent.tested_at, (SELECT tested_at FROM features child WHERE child.parent_number = parent.number AND child.tested_at IS NOT NULL LIMIT 1)),
                reviewed_at = COALESCE(parent.reviewed_at, (SELECT reviewed_at FROM features child WHERE child.parent_number = parent.number AND child.reviewed_at IS NOT NULL LIMIT 1))
            WHERE parent.number = (SELECT parent_number FROM features WHERE number = %s)
              AND parent.parent_number IS NULL
        ''', ('FEATURE_NUMBER',))
        if cur.rowcount:
            print('Parent pipeline timestamps propagated from releases.')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB stamp failed: {e}')
"
```

Report: "✓ DB stamped — reviewed_at + shipped_at set for FEATURE_NUMBER, parent timestamps propagated"

## Step 9b — Update registry and status

1. Read `.claude/features/registry.md`
2. Derive the spec filename from CURRENT_BRANCH slug — find the matching release
   sub-row whose Specs column contains that slug
3. Update that release sub-row Status to `✅ Shipped`
4. Check if all release sub-rows for this parent feature are now `✅ Shipped`
   - If yes: update the parent feature row Status to `✅ Shipped`
   - If no: update the parent feature row Status to reflect the least-complete remaining release

## Step 9c — Update CLAUDE.md roadmap table
Read `.claude/features/registry.md` and rewrite the Feature Roadmap table
in `CLAUDE.md` to match. Rules:
- Include only rows where the Parent column is `—` (top-level features only,
  no release sub-rows)
- Preserve the exact table format: `| Feature | Name | Status |`
- Map registry status symbols to the table as-is (e.g. `✅ Shipped`, `🔧 In Progress`)
- Update the "Next feature to implement" line to the next integer after the
  highest feature number in the registry

## Step 9d — Regenerate seed_features() from live DB

This step keeps `seed_features()` in `database/db.py` in sync with the live DB so
that test runs (which TRUNCATE and reseed) never restore stale data.

Run the following script. It reads every row from the `features` table and rewrites
the body of `seed_features()` in `database/db.py` in place:

```bash
python3 - <<'PYEOF'
import os, re, textwrap
url = open('.env').read().split('DATABASE_URL=')[1].split('\n')[0].strip()
import psycopg2, psycopg2.extras

conn = psycopg2.connect(url)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
    SELECT number, parent_number, title, slug, type, release_subtype, description,
           captured_at, planned_at, spec_at, implemented_at,
           tested_at, reviewed_at, shipped_at
    FROM features ORDER BY id ASC
""")
rows = cur.fetchall()
cur.close(); conn.close()

def fmt(v):
    if v is None:
        return 'None'
    s = str(v)
    # Strip timezone suffix for consistency — stored as UTC
    s = re.sub(r'\+00:00$', '', s)
    return repr(s)

tuple_lines = []
for r in rows:
    vals = [
        fmt(r['number']), fmt(r['parent_number']),
        fmt(r['title']), fmt(r['slug']),
        fmt(r['type']), fmt(r['release_subtype']),
        fmt(r['description']),
        fmt(r['captured_at']), fmt(r['planned_at']),
        fmt(r['spec_at']), fmt(r['implemented_at']),
        fmt(r['tested_at']), fmt(r['reviewed_at']),
        fmt(r['shipped_at']),
    ]
    inner = ',\n            '.join(vals)
    tuple_lines.append(f'        (\n            {inner},\n        )')

rows_block = ',\n'.join(tuple_lines)

new_body = f'''\
def seed_features():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS count FROM features")
    if cur.fetchone()["count"] > 0:
        cur.close()
        conn.close()
        return

    # AUTO-GENERATED by /ship-feature Step 9d — do not edit by hand.
    # columns: number, parent_number, title, slug, type, release_subtype, description,
    #          captured_at, planned_at, spec_at, implemented_at,
    #          tested_at, reviewed_at, shipped_at
    rows = [
{rows_block}
    ]

    for row in rows:
        cur.execute(
            "INSERT INTO features"
            " (number, parent_number, title, slug, type, release_subtype, description,"
            "  captured_at, planned_at, spec_at, implemented_at,"
            "  tested_at, reviewed_at, shipped_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            row,
        )

    conn.commit()
    cur.close()
    conn.close()
'''

db_path = 'database/db.py'
source = open(db_path).read()
# Replace from 'def seed_features():' to the end of its function body
new_source = re.sub(
    r'def seed_features\(\):.*?(?=\n\ndef |\n\nif |\Z)',
    new_body.rstrip(),
    source,
    flags=re.DOTALL,
)
open(db_path, 'w').write(new_source)
print(f'seed_features() regenerated — {len(rows)} rows written to {db_path}')
PYEOF
```

If the script fails, log the error and continue — do not block the ship.
Report: "✓ seed_features() regenerated — N rows"

## Final summary
Print:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
/ship-feature complete
✓ Committed — <message>
✓ Pushed — <branch>
✓ PR created and merged
✓ Remote branch deleted
✓ Switched to main
✓ Local branch deleted
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

## Rules
- Never commit directly to main
- Always use regular merge (not squash) so PRs show a proper diff on GitHub
- Always delete both remote and local branch after merge
- If GitHub MCP is not connected stop and say:
  "GitHub MCP is not connected. Run /mcp to check connection."
- If push fails due to no upstream, use git push -u origin CURRENT_BRANCH
- Never proceed to merge if PR creation fails
- Do NOT deploy to Railway — deployment is handled separately by the user
- Use merge_method: "merge" (regular merge) when calling mcp__github__merge_pull_request — never squash

---

## Pipeline Reminder

After shipping, end with:
```
✅ Shipped! Pipeline complete.
```
