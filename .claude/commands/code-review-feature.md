---
description: Runs parallel security and quality code 
  review for a specific Spendly feature. Pass the spec 
  name as argument e.g. /code-review-feature 03-login
allowed-tools: Bash(git diff), Bash(git diff --staged)
---

Run the full code review pipeline for the feature 
specified in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /code-review-feature 
<spec-name> e.g. /code-review-feature 03-login"

## Pre-flight Check

Before invoking any subagents, collect the diff:
- Run `git diff` for unstaged changes
- Run `git diff --staged` for staged changes
- Combine both into a single diff

If both are empty, stop immediately and say:
"No changes detected. Implement the feature before 
running code review."

---

## Step 1: Parallel Review

Invoke both subagents simultaneously with the same 
context:

**spendly-security-reviewer** receives:
- The combined diff from the pre-flight check
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py` and 
  `database/` directory
- Instruction: Review only the changed code for 
  security vulnerabilities. Do not comment on quality 
  or style.

**spendly-quality-reviewer** receives:
- The combined diff from the pre-flight check
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py`, `database/` 
  directory, and `templates/` directory
- Instruction: Review only the changed code for quality, 
  Flask best practices, and maintainability. Do not 
  comment on security concerns.

Both subagents must run in parallel. Do not wait for 
one to finish before starting the other.

---

## Step 2: Unified Report

Once both subagents have completed, combine their 
findings into a single unified report. De-duplicate 
any overlapping findings — if both agents flagged the 
same line for different reasons, merge them into one 
finding with both perspectives noted.

Structure the combined report as:
Code Review Report — $ARGUMENTS
Security Findings
[spendly-security-reviewer output]
Quality Findings
[spendly-quality-reviewer output]
Combined Action Plan
Ordered checklist of everything that needs to be fixed,
prioritized by severity:

[Critical/High security findings first]
[Quality CHANGES REQUESTED items second]
[Medium/Low security findings third]
[Quality APPROVED WITH SUGGESTIONS items last]

Overall Verdict
APPROVED — ready to commit
APPROVED WITH SUGGESTIONS — can commit, address
suggestions in future steps
CHANGES REQUESTED — must fix before committing,
see action plan above
---

## Step 3: Write Report to Database

**This step runs immediately after presenting the report — BEFORE asking about the action plan.**
The review report must be persisted to the database so the roadmap page shows the clickable double-ring dot.

Write the code review report to the database — extract the release number from `$ARGUMENTS`
(leading digits and dots before the first `-`, e.g. `15.3` from `15.3-harness-integration-live-updates`).
Compose the review report string from the unified report produced in Step 2, then run:

```bash
python3 -c "
import psycopg2, os
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('DATABASE_URL')
report = '''REVIEW_REPORT_CONTENT'''
if not url:
    print('Warning: DATABASE_URL not set — skipping DB stamp')
else:
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        now = datetime.now(timezone.utc)
        cur.execute(
            'UPDATE features SET reviewed_at = %s, review_report = %s WHERE number = %s',
            (now, report, 'RELEASE_NUMBER')
        )
        if cur.rowcount == 0:
            print('WARNING: 0 rows updated — check that RELEASE_NUMBER was substituted correctly and the row exists')
        else:
            print('Rows updated:', cur.rowcount)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB stamp failed: {e}')
"
```

Replace `REVIEW_REPORT_CONTENT` with the full unified review report text from Step 2.
If the DB write fails, log the error and continue.

---

## Step 4: Ask for Approval

After writing the report to the database, ask:

"Do you want me to implement the action plan now?"

Wait for explicit user confirmation before making
any changes. Do not touch any files until the user
approves.

**IMPORTANT:** If the user says yes to implementing the action plan, you MUST still complete Step 5 (Update Status) after the implementation. Do not skip the registry update and `/status` refresh.

---

## Step 5: Update Status

After presenting the report (regardless of verdict):
1. Read `.claude/features/registry.md`
2. Find the release sub-row whose Specs column matches `$ARGUMENTS`
3. If the release sub-row status is not already `👀 In Review`, update it to `👀 In Review`
4. Update the parent feature row status if needed
6. Run `/status` to refresh the live feature status view from the database.

---

## Pipeline Reminder

After review is complete, end with:
```
👀 Reviewed! Next: /ship-feature
```
---

## Rules
- Do NOT edit any files before user approval
- Do NOT start one reviewer before the other — 
  both must run in parallel
- Do NOT skip the pre-flight diff check
- Do NOT proceed if the spec file at 
  `.claude/specs/$ARGUMENTS.md` does not exist — 
  report it and stop
- If either subagent fails or returns no output, 
  report it and do not present a partial review 
  as complete