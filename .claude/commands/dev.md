---
description: Interactive dev workflow menu — pick a step to run next
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are the Spendly dev workflow assistant.
Your job is to present the full dev workflow as an interactive UI using
AskUserQuestion with previews, resolve any arguments from the live registry,
then print the exact command for the user to run.

## Step 1 — Read the registry

Read `.claude/features/registry.md` in full.
Parse every release sub-row (rows where Number contains a dot and Title starts with →).
Build these lists:

- `in_progress`  — releases with status 🔧 In Progress
- `in_review`    — releases with status 👀 In Review
- `planned`      — releases with status 📋 Planned (not yet Spec'd)
- `specced`      — releases with status 📝 Spec'd
- `captured`     — feature rows with status 💡 Captured (no release sub-rows yet)

## Step 2 — Show the workflow picker (Question 1)

Call AskUserQuestion with ONE question. Header: "Workflow step".

Present exactly 4 options. Each option's preview pane shows what the step does
and what command(s) it will run, using live data from the registry.

Build each option's preview dynamically:

**Option 1 — "Ideate"**
Label: "Ideate"
Description: "Capture a thought or plan a release"
Preview:
```
Commands in this group
──────────────────────
/capture-thoughts
  Log a new feature idea from user-thoughts/

/plan-release <number>
  Decompose a captured feature into releases

──────────────────────
💡 Captured features
<list each item in `captured` as "  • <number> — <title>", or "  (none)" if empty>
```

**Option 2 — "Spec"**
Label: "Spec"
Description: "Write a spec and create a feature branch"
Preview:
```
Command
──────────────────────
/create-spec <number> <slug>
  Write a full spec and check out a feature branch

──────────────────────
📋 Ready to spec
<list each item in `planned` as "  • <number> — <title>  →  /create-spec <number> <slug>" where slug is derived from title (lowercase kebab-case max 40 chars), or "  (none — run /plan-release first)" if empty>
```

**Option 3 — "Build"**
Label: "Build"
Description: "Implement, test, or review a feature"
Preview:
```
Commands in this group
──────────────────────
/implement-feature <number>
  Execute a spec'd feature

/test-feature <spec-name>
  Write + run pytest tests

/code-review-feature <spec-name>
  Run parallel security + quality review

──────────────────────
📝 Spec'd
<list each item in `specced` as "  • <number> — <title>", or "  (none)" if empty>

🔧 In progress
<list each item in `in_progress` as "  • <number> — <title>", or "  (none)" if empty>

👀 In review
<list each item in `in_review` as "  • <number> — <title>", or "  (none)" if empty>
```

**Option 4 — "Ship"**
Label: "Ship"
Description: "Commit, PR, squash merge, clean up, and deploy"
Preview:
```
Commands in this group
──────────────────────
/ship-feature
  Commit all changes, open a PR, squash merge,
  delete the branch, and update the registry.

  Run this when code review is complete
  and the feature is ready to merge to main.

/deploy
  Deploy the latest main to Railway.

  Run this after /ship-feature to push
  the merged changes to production.
```

Wait for the user to select one of the four options.

## Step 3 — Drill down (Question 2)

Based on the selection from Question 1, show a second AskUserQuestion to
either pick a sub-command or confirm, using previews.

---

### If "Ideate" was selected

Call AskUserQuestion with ONE question. Header: "Ideate".
Options:

**Option A — "Capture thoughts"**
Label: "Capture thoughts"
Description: "Log a new feature idea"
Preview:
```
/capture-thoughts

Reads files from .claude/features/user-thoughts/,
writes a structured summary to processed-thoughts/,
and adds a 💡 Captured entry to the registry.
```

**Option B — "Plan a release"**
Label: "Plan a release"
Description: "Decompose a captured feature into releases"
Preview (build dynamically):
If `captured` is empty:
```
/plan-release

No captured features yet.
Run /capture-thoughts first to log a feature idea.
```
If `captured` has items:
```
/plan-release <number>

Captured features available to plan:
<list each as "  • <number> — <title>">

Select this option then pick a feature below.
```

**Option C — "Back"**
Label: "Back"
Description: "Return to the workflow menu"
Preview:
```
← Go back to the workflow step picker
```

Wait for selection.

- If "Capture thoughts": go to Step 4 with command `/capture-thoughts`
- If "Plan a release" and `captured` is empty: print "No captured features — run /capture-thoughts first." and re-run from Step 2.
- If "Plan a release" and `captured` has exactly one item: go to Step 4 with command `/plan-release <number>`
- If "Plan a release" and `captured` has multiple items: show a third AskUserQuestion (header: "Which feature?") with one option per captured feature (max 4). Each option label is "<number> — <title>", description is "Plan releases for this feature", preview is `/plan-release <number>`. After selection go to Step 4.
- If "Back": re-run from Step 2.

---

### If "Spec" was selected

If `planned` is empty: print "No planned releases — run /plan-release first." and re-run from Step 2.

If `planned` has exactly one item: go directly to Step 4 with command `/create-spec <number> <slug>` (derive slug from title: lowercase, kebab-case, max 40 chars).

If `planned` has multiple items: call AskUserQuestion with ONE question. Header: "Which release?".
One option per planned release (max 4):
- Label: "<number> — <title>"
- Description: "Create spec for this release"
- Preview:
```
/create-spec <number> <slug>

Writes .claude/specs/<number>-<slug>.md
Creates branch feature/<slug>
Updates the registry to 📝 Spec'd
```

After selection go to Step 4 with the resolved command.

---

### If "Build" was selected

Call AskUserQuestion with ONE question. Header: "Build step".
Options (up to 4):

**Option A — "Implement"**
Label: "Implement"
Description: "Execute a spec'd feature"
Preview (build dynamically):
If `specced` is empty:
```
/implement-feature <number>

No spec'd features yet.
Run /create-spec first.
```
Else:
```
/implement-feature <number>

Spec'd features ready to implement:
<list each as "  • <number> — <title>">
```

**Option B — "Test"**
Label: "Test"
Description: "Write + run pytest tests"
Preview:
If `in_progress` is empty:
```
/test-feature <spec-name>

Nothing in progress.
Run /implement-feature first.
```
Else:
```
/test-feature <spec-name>

Features in progress:
<list each as "  • <number> — <title>  (<spec-filename>)">
```

**Option C — "Code review"**
Label: "Code review"
Description: "Run parallel security + quality review"
Preview:
If `in_review` is empty:
```
/code-review-feature <spec-name>

Nothing in review yet.
Run /test-feature first.
```
Else:
```
/code-review-feature <spec-name>

Features in review:
<list each as "  • <number> — <title>  (<spec-filename>)">
```

**Option D — "Back"**
Label: "Back"
Description: "Return to the workflow menu"
Preview:
```
← Go back to the workflow step picker
```

Wait for selection.

- If "Implement" and `specced` is empty: print "No spec'd features — run /create-spec first." and re-run from Step 2.
- If "Implement" and one item: go to Step 4 with `/implement-feature <number>`.
- If "Implement" and multiple: show sub-question (header: "Which feature?") with one option per specced item. After selection go to Step 4.
- If "Test" and `in_progress` is empty: print "Nothing in progress — run /implement-feature first." and re-run from Step 2.
- If "Test" and one item: go to Step 4 with `/test-feature <spec-filename>`.
- If "Test" and multiple: show sub-question. After selection go to Step 4.
- If "Code review" and `in_review` is empty: print "Nothing in review — run /test-feature first." and re-run from Step 2.
- If "Code review" and one item: go to Step 4 with `/code-review-feature <spec-filename>`.
- If "Code review" and multiple: show sub-question. After selection go to Step 4.
- If "Back": re-run from Step 2.

---

### If "Ship" was selected

Call AskUserQuestion with ONE question. Header: "Ship step".
Options:

**Option A — "Ship feature"**
Label: "Ship feature"
Description: "Commit, PR, squash merge, and clean up"
Preview:
```
/ship-feature

Commits all changes, opens a PR on GitHub,
squash merges it, deletes the branch, and
updates the registry to ✅ Shipped.

Run this when code review is complete.
```

**Option B — "Deploy"**
Label: "Deploy"
Description: "Deploy the latest main to Railway"
Preview:
```
/deploy

Runs `railway up` to deploy the current
state of main to production on Railway.

Run this after /ship-feature.
```

**Option C — "Back"**
Label: "Back"
Description: "Return to the workflow menu"
Preview:
```
← Go back to the workflow step picker
```

- If "Ship feature": go to Step 4 with `/ship-feature`
- If "Deploy": go to Step 4 with `/deploy`
- If "Back": re-run from Step 2.

---

## Step 4 — Print the resolved command

Print the final command clearly:

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
  Ready to run:  <resolved command>
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
Type the command above to execute it, or type /dev to come back.
```

Do NOT execute the command yourself. Just display it so the user can type it.
