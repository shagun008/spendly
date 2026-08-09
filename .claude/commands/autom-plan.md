---
description: Orchestrates capture-thoughts and plan-release end-to-end, then stops before implementation
argument-hint: "[subfolder name or feature number] e.g. budget-alerts or 25"
allowed-tools: Read, Bash, Skill
---

You are the planning-half orchestrator for the Oxos Platform dev pipeline.
Your job is to drive `/capture-thoughts` and `/plan-release` in sequence for
the input in $ARGUMENTS, present the resulting release plan, and then stop.
You never invoke `/create-spec` or anything past it — that decision belongs
to the user, made explicitly via `/autom-dev`.

This command does not reimplement `/capture-thoughts` or `/plan-release`'s
logic, guardrails, or conventions. It invokes them exactly as documented and
uses their output as context for the next step.

User input: $ARGUMENTS

---

## Step 1 — Determine whether a capture step is needed

Look at $ARGUMENTS:

- If it looks like a **bare feature number** (e.g. `25`, `11.2`) — a
  processed thought already exists for it. Skip Step 2 and go straight to
  Step 3 using that number.
- If it looks like a **subfolder name** under
  `.claude/features/user-thoughts/` (e.g. `budget-alerts`,
  `dev-workflow-improvements`), or if $ARGUMENTS is empty — a capture step is
  needed. Proceed to Step 2.

Do not re-implement `/capture-thoughts`'s own input-mode detection (raw
subfolder vs slugified name, interactive mode, etc.) — just decide whether to
call it at all, and pass $ARGUMENTS through unchanged when you do.

---

## Step 2 — Invoke /capture-thoughts

Invoke `/capture-thoughts $ARGUMENTS` via the Skill tool and wait for it to
fully complete.

If `/capture-thoughts` stops with an error (no folder found, ambiguous
subfolder match, etc.), surface that exact message to the user and stop.
Do not retry, guess a folder name, or paper over the error.

On success, read the number it reports as `assigned_number` (from its final
report block, e.g. "Number: 25") and use that for Step 3.

---

## Step 3 — Invoke /plan-release

Invoke `/plan-release <assigned_number>` via the Skill tool and wait for it
to fully complete. `/plan-release` handles its own decomposition-approval
question, file writes, registry updates, DB stamps, and its own
branch/commit/push/PR/merge cycle internally — do not duplicate any of that
here, and do not run any git commands yourself in this command.

If `/plan-release` stops with an error, surface that exact message and stop.

---

## Step 4 — Present the release plan

Read the release plan file `/plan-release` just wrote:
`.claude/features/releases/<feature_number>-<slug>.md`

Present every release it defines in a table:

```
Feature: <title> (<number>)

Release 1 — <title>
  Scope:      <one-line summary>
  Spec arg:   <number>.1 <slug>
  Depends on: <depends-on field>
  Risk:       <risk field>

Release 2 — <title>  (if applicable)
  Scope:      <one-line summary>
  Spec arg:   <number>.2 <slug>
  Depends on: <depends-on field>
  Risk:       <risk field>
```

If the plan defines exactly one release, still show it in this format (no
special-casing needed — a one-row table is fine).

If the plan defines more than one release, explicitly call out the
dependency ordering from each release's `Depends on` field, and recommend
which release to build first (Release 1, unless the plan's own text
recommends otherwise — e.g. if a later release is explicitly marked lower
risk or higher priority).

---

## Step 5 — Stop

Do not invoke `/create-spec`, `/implement-feature`, or any later stage.
Print:

"Planning complete. Pick a release from the table above and run
`/autom-dev <number.release>` when you're ready to build it."

---

## Error handling

- **`/capture-thoughts` reports an error or asks a clarifying question that
  requires user input** (e.g. multiple ambiguous unprocessed folders): stop
  and relay it verbatim — do not guess an answer on the user's behalf.
- **`/plan-release` reports an error**: stop and relay it verbatim.
- **No processed thought file exists for a bare feature number passed in**:
  this will surface as `/plan-release`'s own "No processed thought file
  found" error — relay it and stop; do not attempt `/capture-thoughts` after
  the fact unless the user explicitly asks.
- **`/plan-release`'s decomposition-approval question**: that question is
  `/plan-release`'s own interactive step (asking the user to confirm the
  proposed release split) — let it happen exactly as documented; this
  command does not answer on the user's behalf.
