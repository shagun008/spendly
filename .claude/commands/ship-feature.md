---
description: Commit, push, create PR, merge, and clean up after a feature is complete
allowed-tools: Read, Bash, mcp__github__create_pull_request, mcp__github__merge_pull_request, mcp__github__delete_branch, Bash(railway*)
---

## Step 1 — Identify current branch
```bash
git branch --show-current
```
Store this as CURRENT_BRANCH.

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

Good: "feat(15.2): expand roadmap rows inline to show feature description (#27)"
Bad: "feat: added detail view to roadmap.html"

Note: the PR number is not known until Step 5. Generate the message without it first,
then after the PR is created in Step 5, amend the commit to append (#PR_NUMBER) and
force-push before merging.

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
just created. Use squash merge.

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
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
now = datetime.now(timezone.utc)
cur.execute(
    \"UPDATE features SET reviewed_at = %s, shipped_at = %s WHERE number = %s\",
    (now, now, 'FEATURE_NUMBER')
)
print('Rows updated:', cur.rowcount)
conn.commit()
cur.close()
conn.close()
"
```

Report: "✓ DB stamped — reviewed_at + shipped_at set for FEATURE_NUMBER"

## Step 9b — Update registry and status

1. Read `.claude/features/registry.md`
2. Derive the spec filename from CURRENT_BRANCH slug — find the matching release
   sub-row whose Specs column contains that slug
3. Update that release sub-row Status to `✅ Shipped`
4. Check if all release sub-rows for this parent feature are now `✅ Shipped`
   - If yes: update the parent feature row Status to `✅ Shipped`
   - If no: update the parent feature row Status to reflect the least-complete remaining release
5. Rewrite `.claude/features/status.md` by reading the full registry and
   regenerating all sections grouped by status, in this order:
   🔧 In Progress, 👀 In Review, 📝 Spec'd, 📋 Planned, 💡 Captured, ✅ Recently Shipped (last 5).
   Set "Last updated" to today's date.

## Step 9c — Update CLAUDE.md roadmap table
Read `.claude/features/registry.md` and rewrite the Feature Roadmap table
in `CLAUDE.md` to match. Rules:
- Include only rows where the Parent column is `—` (top-level features only,
  no release sub-rows)
- Preserve the exact table format: `| Feature | Name | Status |`
- Map registry status symbols to the table as-is (e.g. `✅ Shipped`, `🔧 In Progress`)
- Update the "Next feature to implement" line to the next integer after the
  highest feature number in the registry

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
- Always use squash merge
- Always delete both remote and local branch after merge
- If GitHub MCP is not connected stop and say:
  "GitHub MCP is not connected. Run /mcp to check connection."
- If push fails due to no upstream, use git push -u origin CURRENT_BRANCH
- Never proceed to merge if PR creation fails
- Do NOT deploy to Railway — deployment is handled separately by the user
