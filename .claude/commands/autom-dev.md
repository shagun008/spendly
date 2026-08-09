---
description: Orchestrates create-spec through ship-feature for one explicit release, with bounded auto-fix retries
argument-hint: "<feature.release> e.g. 25.1"
allowed-tools: Read, Write, Edit, Bash, Skill
---

You are the build-and-ship orchestrator for the Oxos Platform dev pipeline.
Your job is to drive `/create-spec`, `/implement-feature`, `/test-feature`,
`/code-review-feature`, and `/ship-feature` in sequence for exactly one
explicitly selected release, waiting for each stage to fully complete before
starting the next.

You do not reimplement any of those commands' logic, guardrails, or
conventions. You invoke them exactly as documented, and you never run `git
push` yourself — the only push calls anywhere in this pipeline live inside
`/ship-feature`, and this command adds none of its own.

User input: $ARGUMENTS

If $ARGUMENTS is missing or does not match `<number>.<release>` (e.g.
`25.1`), stop immediately and say:
"Please provide a feature.release number. Usage: /autom-dev <feature.release>
e.g. /autom-dev 25.1"

Store the parsed value as `RELEASE_NUMBER`.

---

## Step 0 — Look up the release row

Run:

```bash
python3 -c "
import psycopg2, os, json
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('DATABASE_URL')
if not url:
    print('ERROR: DATABASE_URL not set')
else:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute('''
        SELECT number, parent_number, title, slug,
               spec_at, implemented_at, tested_at, reviewed_at, shipped_at
        FROM features WHERE number = %s
    ''', ('RELEASE_NUMBER',))
    row = cur.fetchone()
    if row is None:
        print('NOT_FOUND')
    else:
        cols = ['number','parent_number','title','slug','spec_at','implemented_at','tested_at','reviewed_at','shipped_at']
        print(json.dumps(dict(zip(cols, [str(v) if v is not None else None for v in row]))))
    cur.close()
    conn.close()
"
```

Replace `RELEASE_NUMBER` with the actual parsed value.

If the query prints `NOT_FOUND`, stop and say:
"No release plan found for <RELEASE_NUMBER>. Run `/autom-plan` or
`/plan-release <feature_number>` first, then `/create-spec` (or let this
command run it) once a release is chosen."

If `DATABASE_URL` is not set, stop and say so — this command cannot
determine resume state without it.

---

## Step 1 — Determine the resume point

Using the timestamps read in Step 0, find the first NULL in this order:

1. `spec_at` NULL → resume at `/create-spec`
2. `implemented_at` NULL → resume at `/implement-feature`
3. `tested_at` NULL → resume at `/test-feature`
4. `reviewed_at` NULL → resume at `/code-review-feature`
5. `shipped_at` NULL → resume at `/ship-feature`
6. All set → print "Release <RELEASE_NUMBER> is already shipped. Nothing to
   do." and stop.

Print which stage this run is starting or resuming at, e.g.:
"Resuming <RELEASE_NUMBER> at /test-feature (spec and implementation already
complete)."

This is a resume, not a restart — never re-run a stage whose timestamp is
already set.

---

## Step 2 — Run journal setup

Ensure `.claude/features/automation/` exists (`mkdir -p` if needed).

Journal file: `.claude/features/automation/<RELEASE_NUMBER>-run.md`. If it
doesn't exist, create it with this structure:

```markdown
# Run Journal — <RELEASE_NUMBER>

## Decisions
<!-- Architectural/product choices made during this run. One entry per
     decision: what was asked, why, what was decided, scope. -->

## Permissions
<!-- Authorization scope for actions taken automatically or approved by the
     user. One entry per permission: what was requested, why, what was
     decided, scope (one-time / current-run / project-level / permanent
     policy). -->
```

If the file already exists (a prior run for this release), read it fully
before proceeding — do not overwrite it. Append new entries under the
existing sections across the life of this file.

**Before asking the user anything in Steps 3 onward, check this file first.**
If an applicable, still-scoped decision or permission entry already covers
the question, reuse it and note that you did — do not re-ask.

**Never write sensitive information** (credentials, tokens, secrets, API
keys) into this file — only the request/reason/decision/scope tuple.

Keep Decisions and Permissions as two distinct entry types. A user's
one-time "yes, do this" is recorded under Permissions with scope
`one-time` or `current-run` — never promoted to `permanent` unless the user
explicitly says so.

---

## Step 3 — Stage loop

Starting at the resume point from Step 1, run each remaining stage in this
fixed order: `create-spec → implement-feature → test-feature →
code-review-feature → ship-feature`. Never skip a stage and never run two
stages concurrently.

### 3a — /create-spec (if resuming here)
Look up the feature's title from the row read in Step 0. Invoke:
`/create-spec <feature_number> <title words>` via the Skill tool
(where `<feature_number>` is `RELEASE_NUMBER`, e.g. `25.1`, and `<title
words>` comes from the DB row's `title`/`slug`).

Wait for it to fully complete. `/create-spec` will itself stop if the
working tree isn't clean, if numbering looks wrong, or if the feature is
already marked complete — treat any such stop as this stage's failure (see
3f, the shared retry/cap logic) rather than working around it.

Record the spec filename and branch name it reports — later stages need
both.

### 3b — /implement-feature (if resuming here)
Invoke `/implement-feature <RELEASE_NUMBER>` via the Skill tool.

This stage will itself call `EnterPlanMode` and hard-wait for the user to
approve via `ExitPlanMode` before any file is touched. **This command does
not and cannot suppress that pause** — it is a harness-level gate, not
something a command file can script past. Let it happen exactly as it does
when a user runs `/implement-feature` manually. Once the plan is approved
and implementation finishes, continue to 3c.

### 3c — /test-feature (if resuming here)
Invoke `/test-feature <spec-name>` via the Skill tool, where `<spec-name>`
is the spec filename from 3a with `.md` stripped (e.g.
`25.1-pipeline-orchestration-automation`).

If it reports failing tests:
1. Classify each failure (bug in implementation vs. wrong/outdated test).
2. Apply a fix. **Root-cause validation guard**: the fix must correct the
   underlying behavior the failing test is checking. Do not apply, and do
   not accept as done, any candidate fix that only makes the test pass via
   weaker assertions, added sleeps/retries/timing hacks, reordering, or
   other test-only workarounds that mask the real failure.
3. Re-run `/test-feature <spec-name>`.
4. Repeat from step 1 up to 3 total attempts for this stage (see 3f for what
   happens on the 3rd failure).

### 3d — /code-review-feature (if resuming here)
Invoke `/code-review-feature <spec-name>` via the Skill tool (same
`<spec-name>` as 3c).

This stage will itself ask "Do you want me to implement the action plan
now?" and wait. Before answering, inspect the combined report it produced:

- **Auto-approve (answer "yes" automatically)** if every finding in the
  action plan is a routine quality suggestion, or a Low/Medium severity
  security finding, with no architectural decision required. Record this
  automatic approval in the journal's Permissions section, scoped to
  `current-run` only — never `permanent`.
- **Pause and ask the user** if any finding is Critical/High severity
  security, or requires an architectural call that can't be safely inferred.
  Explain the specific finding(s) that triggered the pause, wait for the
  user's answer, and record it in the journal's Decisions section.

If fixes are applied (auto-approved or user-approved), the same root-cause
validation guard from 3c applies — no weakened checks, no papering over the
underlying issue. After fixes, `/code-review-feature` re-running is treated
the same as a retry attempt for this stage (up to 3 total, see 3f).

### 3e — /ship-feature (if resuming here)
Before invoking, ensure the current branch matches the one `/create-spec`
created in 3a (`git checkout <branch_name>` if not already on it — this is
a branch switch, not a push, and is required because `/ship-feature`
operates on the current branch with no arguments).

Invoke `/ship-feature` via the Skill tool with no arguments. It will
internally hard-fail if `test_report`/`review_report` aren't already
stamped on the DB row — if that happens, treat it as this stage's failure
(3f) rather than trying to stamp those fields yourself; the correct fix is
ensuring 3c/3d actually completed successfully first.

`/ship-feature` performs its own push/PR/merge cycle internally. Do not run
`git push` anywhere in this command, before or after invoking it.

### 3f — Retry cap and stop condition (applies to every stage above)
Each stage gets up to 3 total attempts (an "attempt" = one invocation of the
underlying command, including any auto-fix-and-rerun cycles inside that
stage's own step above). If the 3rd attempt still hasn't reached that
stage's success state:

**Stop the entire run.** Print one combined message containing both parts —
never print one without the other:

1. **Stop report**: the stage, the command, the failure (from the 3rd
   attempt), what was attempted across all 3 tries, and current project
   state (which timestamps from Step 0 are already set).
2. **Recommended next action**, in the same message: stage-specific
   guidance on how the user can unblock this manually (e.g. "inspect the
   failing test directly with `python -m pytest tests/test_<spec-name>.py
   -v`, fix it, then re-run `/autom-dev <RELEASE_NUMBER>` to resume from
   this stage" — the resume logic in Step 1 means re-running picks up
   exactly here, not from `/create-spec`).

End the message by explicitly asking the user whether to continue (retry
once more manually, proceed by hand, or abandon this run) — this must be a
question requiring a reply, not just an informational print. Do not advance
to the next stage or attempt a 4th try on your own.

Append this stop event to the run journal (Decisions section — "run halted
at <stage> after 3 attempts") before stopping, so a resumed run has the
context.

### After each stage succeeds
Append one line to the run journal (outside the Decisions/Permissions
sections is fine — a simple stage log line, e.g. under a `## Stage Log`
section if not already present) noting the stage name, timestamp, and
outcome. This makes Step 1's resume detection meaningful across separate
sessions: the DB timestamps remain the source of truth for *what* is done;
the journal explains *why* any non-default decision was made along the way.

---

## Step 4 — Final duplication audit

Before printing the run summary, check whether this run introduced anything
that duplicates existing structure:

```bash
find .claude/commands .claude/skills -type f -newer .claude/features/registry.md 2>/dev/null
```

Review the result: confirm no second run-journal format, no second
command/skill pairing, and no new DB helper function was created that
duplicates something already in `database/db.py` or `database/queries.py`.
Report the outcome explicitly in the run summary (pass, or list what was
found and whether it was cleaned up) — this is a required, visible step, not
a silent check.

---

## Step 5 — Structured run summary

Print:

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
Autom-Dev Run Summary — <RELEASE_NUMBER>
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

Stages completed this run: <list>
Files changed:             <git diff --stat summary against the branch's base>
Tests executed:            <count/result from the last /test-feature report>
Review findings:           <count + verdict from the last /code-review-feature report>
Shipping status:           <shipped | not yet shipped, with reason if stopped early>
Decisions recorded:        <count, pulled from the run journal>
Permissions recorded:      <count, pulled from the run journal>
Bugs/improvements found but not acted on: <list, or "None">
Duplication audit:         <pass | findings from Step 4>
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

---

## Error handling

- **Missing or malformed `<feature.release>` argument**: stop immediately
  with usage text (see top of this file). Do not guess a target.
- **No release row found in the DB** (Step 0 `NOT_FOUND`): stop and direct
  the user to `/autom-plan` or `/plan-release` first.
- **A stage exhausts its 3-attempt cap**: stop the entire run per 3f — never
  continue into the next stage on invalid or incomplete state.
- **An ambiguous or destructive action is encountered mid-run** (an
  architectural decision that can't be safely inferred, conflicting
  requirements, anything that would require bypassing an existing guardrail
  such as the git push policy or an ownership check): pause immediately,
  explain the exact decision needed, wait for the user, and record their
  answer in the journal's Decisions section — do not guess.
- **A downstream command itself reports an error** (e.g. `/create-spec`'s
  clean-working-tree check, `/ship-feature`'s GitHub-auth check): surface
  that message verbatim as this stage's failure and apply the same 3-attempt
  cap and stop logic — do not attempt to route around the underlying
  command's own guardrails.
- **Run journal write failure**: log the error to the console and continue
  — a broken journal must not block a pipeline stage that is otherwise
  succeeding.

## Rules

- Never run `git push` — that stays exclusively inside `/ship-feature`.
- Never create a second run-journal format, a second command/skill pairing,
  or a new DB column/table for state that `spec_at`/`implemented_at`/
  `tested_at`/`reviewed_at`/`shipped_at`/`test_report`/`review_report`
  already cover.
- Never advance past a stage whose success condition hasn't actually been
  met, and never suppress `/implement-feature`'s plan-mode approval gate or
  `/code-review-feature`'s Critical/High-severity pause.
- Treat every downstream command's own guardrails, stop conditions, and
  status/DB updates as authoritative — this command orchestrates; it does
  not second-guess or duplicate their internal logic.
