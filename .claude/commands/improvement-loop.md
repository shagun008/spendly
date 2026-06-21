---
description: Run a structured improvement cycle for a feature after test failures or code review issues
argument-hint: "Feature number and optional stage e.g. 15.1 --stage test"
allowed-tools: Read, Write, Edit, Glob, Bash
---

Run the Post-Review Improvement Loop for the feature specified in $ARGUMENTS.

Parse arguments:
- First positional argument: `<feature_number>` (required) — the feature to improve, e.g. `15.1`
- Optional flag: `--stage <stage>` — the pipeline stage that triggered this improvement. One of:
  - `implement` — code quality or design issue found during implementation
  - `test` — test failures after `/test-feature`
  - `review` — security or quality issues found during `/code-review-feature`
  - `ship` — issue found during `/ship-feature`
  - If not provided, prompt the user: "Which stage triggered this improvement? (implement / test / review / shop)"

If no feature number is provided, stop immediately and say:
"Please provide a feature number. Usage: /improvement-loop <feature_number> [--stage <implement|test|review|ship>]  e.g. /improvement-loop 15.1 --stage test"

Store the parsed values as `FEATURE_NUMBER` and `TRIGGER_STAGE`.

---

## Phase 1 — Gather Context

Collect everything needed to understand the problem:

1. Read the spec file: `.claude/specs/<feature_number>-*.md` (find by prefix match)
   - If no spec file exists, warn: "No spec file found for <feature_number> — continuing with source files only"
2. Read the source files:
   - `app.py` — routes and application structure
   - `database/db.py` — DB helpers and schema
   - `database/queries.py` — query helpers
   - Any templates referenced in the spec
3. Read recent git history: `git log --oneline -20`
4. Check for existing test output: `python -m pytest tests/ -v 2>&1 | tail -50`
5. Read the feature registry: `.claude/features/registry.md` — find the row for this feature

Note the `TRIGGER_STAGE` when printing the context summary — explain which pipeline stage detected the issue.

---

## Phase 2 — Root Cause Analysis

Analyse the gathered context to identify the underlying cause:

1. Cross-reference the spec requirements against the actual implementation
2. Identify what is failing and why — go beyond symptoms to the root cause
3. Ask: "What underlying assumption failed?" and "What pattern allowed this issue to emerge?"

Print the root cause analysis. Do not proceed to the next phase until the root cause is clearly identified.

---

## Phase 3 — Architectural Assessment

Evaluate whether the issue reveals deeper design problems:

1. Is the architecture still healthy? (clear boundaries, low coupling, single responsibilities)
2. Does the implementation align with the system design in CLAUDE.md?
3. Is there excessive coupling, missing abstractions, or technical debt?
4. Could a small refactor prevent future occurrences?

Print the architectural assessment.

---

## Phase 4 — Generate Improvement Plan

Present three options:

**Option A — Minimal Fix**
What is the smallest change that resolves the immediate issue?

**Option B — Fix + Small Improvement**
What change resolves the issue and improves maintainability slightly?

**Option C — Fix + Architectural Improvement**
What change resolves the issue and improves the underlying structure?

For each option, describe:
- What would change
- Risk level (low / medium / high)
- Impact on complexity

Then ask: "Which option would you like to proceed with? (A / B / C)"

**Wait for explicit user approval before proceeding to Phase 5.**

---

## Phase 5 — Implementation + Validation + Learning Capture

### 5a — Implement
Apply the approved fix. Follow all rules in CLAUDE.md:
- No SQLAlchemy or ORMs — raw psycopg2 queries only
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend base.html

### 5b — Validate
Run the test suite: `python -m pytest tests/ -v`
- If tests pass: proceed to learning capture
- If tests still fail: report the remaining failures and ask whether to iterate or escalate

### 5c — Learning Capture
Get the current timestamp:
```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d-%H%M'))"
```

Ensure the improvements directory exists:
```bash
mkdir -p .claude/features/improvements
```

Write a learning capture file to `.claude/features/improvements/<timestamp>-<feature_number>.md`:

```markdown
---
feature_number: <feature_number>
trigger_stage: <TRIGGER_STAGE>
date: <timestamp>
option_chosen: <A/B/C>
---

# Improvement Log — <feature_number>

## Trigger Stage
<TRIGGER_STAGE> — the pipeline stage that detected the issue and triggered this improvement cycle.

## Issue Summary
What happened? What was the failing test, review finding, or implementation concern?

## Root Cause
Why did it happen? What was the underlying cause?

## Fix Applied
What was changed? Which files were modified?

## Improvement Applied
What became better beyond just fixing the issue?

## Architectural Notes
Any observations about design health, coupling, or technical debt.

## Future Prevention
How can similar issues be avoided in the future?
```

If the write fails, log the error and continue — do not block.

---

## Final Output

Print a summary:

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
Improvement Loop Complete — <feature_number>
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

Phase 1 — Context:     <summary>
Phase 2 — Root Cause:  <root cause>
Phase 3 — Architecture: <assessment>
Phase 4 — Plan:        Option <A/B/C> — <rationale>
Phase 5 — Result:      <tests pass | tests fail | unable to resolve>

Learning capture: .claude/features/improvements/<timestamp>-<feature_number>.md

Is the system better than it was before the issue was discovered?
<yes — with explanation | no — with recommended next steps>
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

---

## Error Handling

- **Missing feature number**: Print usage with --stage flag and stop
- **Invalid stage**: If --stage is provided but not one of (implement, test, review, ship), print valid options and stop
- **No spec file found**: Warn and continue — use source files for context
- **No failures detected** (tests pass, no review issues): Print "No issues detected for <feature_number> — nothing to improve" and exit
- **Unable to resolve**: Report findings from all phases, recommend manual intervention
- **Learning capture write failure**: Log error to console, continue without blocking

## Rules
- Never implement without user approval in Phase 4
- Always run tests after implementing (Phase 5b)
- Always capture learnings (Phase 5c) — even if tests fail
- Follow all rules in CLAUDE.md for any code changes
