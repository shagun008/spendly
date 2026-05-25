---
description: Create a spec file and feature branch for the next Spendly feature
argument-hint: "Feature number and name e.g. 11 budget-alerts or 11.1 budget-alerts-mvp"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer spinning up a new feature for the
Spendly expense tracker. Always follow the rules in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status` and check for uncommitted, unstaged, or
untracked files. If any exist, stop immediately and tell
the user to commit or stash changes before proceeding.
DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:

1. `feature_number` — the full identifier passed by the user
   - Format A (single release): `11` → `feature_number = 11`
   - Format B (specific release): `11.1` → `feature_number = 11.1`
   - If Format B: extract `parent_feature_number` = `11`, `release_number` = `1`
   - If Format A: `parent_feature_number` = `feature_number`, `release_number` = 1 (implicit)

2. `feature_title` — human readable title in Title Case
   - Example: "Budget Alerts" or "Budget Alerts MVP"

3. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: budget-alerts, budget-alerts-mvp

4. `branch_name` — format: `feature/<feature_slug>` (slug only, no number)
   - Example: `feature/budget-alerts-mvp`

5. `spec_filename` — `<feature_number>-<feature_slug>.md`
   - Example: `11.1-budget-alerts-mvp.md` or `11-budget-alerts.md`

If you cannot infer these from $ARGUMENTS, ask the user
to clarify before proceeding.

## Step 3 — Check feature number is sequential
List all existing spec files in `.claude/specs/`.
Extract the highest existing feature number (ignoring release suffixes).
If `parent_feature_number` skips more than one ahead of the highest
existing feature, warn the user and ask them to confirm before
continuing. Example: if the highest existing spec is 10,
creating feature 12 should trigger a warning.

For release suffixes: if creating `11.2`, check that `11.1` already
exists. If not, warn the user and ask them to confirm.

## Step 4 — Check previous feature branch is merged
Run `git branch -r` and `git branch` to check that the branch
for the previous feature is not still open. If it is, warn the
user and ask them to confirm before continuing.

## Step 5 — Check branch name is not taken
Run `git branch` to list existing branches.
If `branch_name` is already taken, append a number:
`feature/budget-alerts-mvp-01`, `feature/budget-alerts-mvp-02` etc.

## Step 6 — Switch to main and pull latest
Run:
```
git checkout main
git pull origin main
```

## Step 7 — Create and switch to the feature branch
Run:
```
git checkout -b <branch_name>
```

## Step 8 — Research the codebase and discovery files
Read these files before writing the spec:
- `CLAUDE.md` — roadmap, conventions, schema (if it exists)
- `app.py` — existing routes and structure; note every route
  already defined so the spec does not duplicate them
- `database/db.py` — existing schema and functions; note every
  table and column already defined
- All templates in `templates/` — note existing templates so
  the spec does not create duplicates
- All files in `.claude/specs/` — avoid duplicating existing specs

Check `CLAUDE.md` to confirm the requested feature is not already
marked complete. If it is, warn the user and stop.

Also check for discovery files using `parent_feature_number`:
- List files in `.claude/features/processed-thoughts/` — look for one
  whose name starts with `<parent_feature_number>-`
- List files in `.claude/features/releases/` — look for one
  whose name starts with `<parent_feature_number>-`

If a processed thought file exists: read it fully and use the
Problem/Goal, Success criteria, and Constraints to enrich the
spec Overview.

If a release plan exists: read it fully, then find the section
for `Release <release_number>`. Scope the spec strictly to that
release's defined Scope. Note what is deferred (other releases)
and any open questions in the Release context section.

If neither exists: note "No discovery file found" in Release context.

## Step 9 — Write the spec
Generate a spec document with this exact structure:

---
# Spec: <feature_title>

## Overview
One paragraph describing what this feature does and why
it exists at this stage of the Spendly roadmap. If a processed
thought file exists, draw the problem statement and success
criteria from it to ground this in real user intent.

## Release context
Which release of the parent feature this spec represents (e.g.
"Release 1 of 3 — MVP"). What work is in scope for this release.
What was deferred to later releases. Any open questions from the
thought or release planning stage that are still unresolved.
If no discovery file was found: state "No discovery file found —
spec generated from arguments only."

## Depends on
Which previous features this feature requires to be complete.

## Routes
Every new route needed (do not include routes already in app.py):
- `METHOD /path` — description — access level (public/logged-in)

If no new routes: state "No new routes".

## Database changes
Any new tables, columns, or constraints needed.
Always verify against `database/db.py` before writing this —
do not list tables or columns that already exist.
If none: state "No database changes".

## Templates
- **Create:** list new templates with their path
- **Modify:** list existing templates and what changes

## Files to change
Every file that will be modified.

## Files to create
Every new file that will be created.

## New dependencies
Any new pip packages. If none: state "No new dependencies".

## Error handling
Specific error cases this feature must handle gracefully:
- Invalid or missing form input
- Unauthorised access attempts
- Database errors or constraint violations
- Any feature-specific edge cases

## UI/UX notes
- Form validation feedback (inline errors or flash messages)
- Redirect behaviour after successful actions
- Flash message copy for success and error states
- Accessibility requirements: all forms must have labels,
  buttons must have descriptive text, colour contrast must
  meet WCAG AA
- Responsive design: all new UI must work on mobile screen
  sizes; use existing CSS breakpoints from `static/css/style.css`

## Rules for implementation
Read `CLAUDE.md` for the full list of project constraints.
If `CLAUDE.md` does not exist, apply these defaults:
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`

## Definition of done
A specific testable checklist. Each item must be verifiable
by running the app, and each item must have a corresponding
pytest test case in the `tests/` directory.
---

## Step 10 — Save the spec
Save to: `.claude/specs/<spec_filename>`
Example: `.claude/specs/11.1-budget-alerts-mvp.md`

## Step 11 — Update feature registry and status
If `.claude/features/registry.md` exists:
1. Find the release sub-row whose Number matches `feature_number` (e.g. `11.1`).
   Update its Status to `🔧 In Progress` and Specs column to `<spec_filename>`.
2. Find the parent feature row whose Number matches `parent_feature_number` (e.g. `11`).
   Update its Status to reflect the least-complete release (🔧 In Progress).

If no matching row exists, skip this step silently.

Rewrite `.claude/features/status.md` by reading the full registry and
regenerating all sections grouped by status. Set "Last updated" to today's date.

## Step 12 — Report to the user
Print a short summary in this exact format:
```
Feature:   <feature_number>
Branch:    <branch_name>
Spec file: .claude/specs/<spec_filename>
Title:     <feature_title>
```

Then tell the user:
"Review the spec at `.claude/specs/<spec_filename>`
then enter Plan Mode to begin implementation."

Do not print the full spec in chat unless explicitly asked.
