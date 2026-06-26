---
description: Capture early feature thinking and assign a feature number before spec creation
argument-hint: "Optional: subfolder name in .claude/features/user-thoughts/ e.g. 'budget-alerts'"
allowed-tools: Read, Write, Glob
---

You are a senior product analyst helping capture early thinking about a new feature or
enhancement for the Spendly expense tracker. Your goal is to read raw artifacts the user
has dropped into a thoughts subfolder, synthesise them into a structured output, and save
the result as a processed thought file ready for release planning.

User input: $ARGUMENTS

---

## Step 0 — Detect input mode

**If $ARGUMENTS is provided:**
- Treat it as a subfolder name inside `.claude/features/user-thoughts/`
- Check that `.claude/features/user-thoughts/<arguments>/` exists
- If it does not exist, stop and say:
  "No folder found at `.claude/features/user-thoughts/<arguments>/`.
  Create the folder and add your notes, screenshots, or other artifacts to it, then re-run this command."
- If it exists, enter **file-input mode** (Steps 2b onward)

**If $ARGUMENTS is empty:**
- List all subfolders in `.claude/features/user-thoughts/`
- List all files in `.claude/features/processed-thoughts/` to identify already-processed slugs
- A subfolder is **unprocessed** if no file in `processed-thoughts/` matches it in any of these four combinations:
  - raw subfolder name vs raw filename
  - raw subfolder name vs slugified filename (lowercase, spaces→hyphens)
  - slugified subfolder name vs raw filename
  - slugified subfolder name vs slugified filename
  This ensures a match regardless of whether the folder or file uses spaces, hyphens, or mixed casing.
- If **one unprocessed subfolder** found: show the folder name to the user and ask "I found one unprocessed thought folder: `<name>`. Shall I process this one?" — wait for confirmation before proceeding
- If **multiple unprocessed subfolders** found: list all of them and ask the user which one to process — if two or more have similar names, show them all explicitly and ask the user to confirm which one they mean
- After the user confirms which subfolder to process, remind them: "Processing `<name>`. After capture, continue with: `/plan-release <number>` → `/create-spec <number.release> <slug>` → `/implement-feature <number.release>`"
- If **no subfolders at all**: enter **interactive mode** (Step 2a)

---

## Step 1 — Read the feature registry
Read `.claude/features/registry.md` to understand:
- All existing features and their numbers
- The highest current feature number (for new feature numbering)
- All sub-numbers per parent (for enhancement numbering)

---

## File naming convention for user-thoughts

Any file written into a `user-thoughts/` subfolder — whether by the user or by this
command — must include a timestamp in its name:

```
<descriptive-name>-YYYY-MM-DD-HHMM.txt
```

Example: `notes-2026-06-13-1616.txt`

When writing a new file into a user-thoughts subfolder during interactive mode (Step 2a),
get the current EST timestamp first:

```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d-%H%M'))"
```

Use that timestamp in the filename.

---

## Step 2a — Interactive mode (no input folder)

Walk through these questions one at a time. Free-form answers are fine.
If the user says "skip" or leaves an answer blank, record it as "Not specified."

Ask for a title first:
"What is a short title for this idea? (e.g. 'Budget Alerts', 'Export to CSV')"

Then ask discovery questions:
1. "What problem does this solve, or what goal does it help achieve?"
2. "Who is affected or who benefits from this? (e.g. all users, admins, power users)"
3. "What does success look like? How would you know this is done well?"
4. "Are there any known constraints, risks, or dependencies to be aware of?"
5. "Any rough implementation ideas or open questions you'd like to capture?"
6. "Is there a deadline or release pressure attached to this?"

Once all answers are collected, write the raw answers to a new file in the subfolder
using the timestamped naming convention above, then skip to Step 3.

---

## Step 2b — File-input mode (subfolder provided or detected)

Read every file in `.claude/features/user-thoughts/<subfolder>/`:

- `.md` and `.txt` files: read as text in full
- Image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`): read visually —
  describe what is visible, extract any text, identify UI mockups, wireframes, or diagrams,
  note any annotations or labels
- Other file types: note the filename and type; extract whatever is readable

After reading all files, synthesise the content into the 6 discovery fields:
- **Problem / Goal** — what problem is being solved or what outcome is desired
- **Who benefits** — who is affected or gains value
- **Success looks like** — how you would know the feature is done well
- **Constraints, risks, dependencies** — anything that limits or complicates the work
- **Implementation ideas / open questions** — rough technical ideas or unresolved questions
- **Release pressure / deadlines** — any time constraints mentioned

Present the inferred values to the user in this format:
```
I found the following in .claude/features/user-thoughts/<subfolder>/:
  Files read: <list of filenames>

Here is what I inferred:

  Title:                  <inferred title>
  Problem / Goal:         <inferred text>
  Who benefits:           <inferred text>
  Success looks like:     <inferred text>
  Constraints/risks:      <inferred text>
  Implementation ideas:   <inferred text>
  Deadlines:              <inferred text>

```

Use these inferred values as the discovery field answers and proceed to Step 3. If the user wants to correct any field, they can tell you before you move on — otherwise continue automatically.

---

## Step 3 — Classify: new feature or enhancement?

Show the user the list of existing features from the registry.
Ask: "Is this a brand new feature, or an enhancement to one of the features listed above?"

If enhancement: ask which feature number it enhances.

---

## Step 4 — Assign a number

**New feature:** next integer after the highest feature number in the registry.
Example: if highest is 10, assign 11.

**Enhancement:** parent number + next available sub-number.
Example: if feature 10 has no enhancements yet, assign 10.1.
If 10.1 and 10.2 exist, assign 10.3.

Store this as `assigned_number`.

---

## Step 5 — Derive the slug

From the title, create a file-safe slug:
- Lowercase, hyphens instead of spaces
- Only a-z, 0-9, and -
- Maximum 40 characters
Example: "Budget Alerts" → budget-alerts

---

## Step 6 — Write the processed thought file

Get the current datetime in EST by running:
```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d-%H%M'))"
```

Save to: `.claude/features/processed-thoughts/<assigned_number>-<slug>-<datetime>.md`

Where `<datetime>` is the EST timestamp in the format `YYYY-MM-DD-HHMM`
(e.g. `2026-06-13-1612`).

Example: `16-release-notes-modal-2026-06-13-1612.md`

Use this exact format:

```markdown
---
number: <assigned_number>
title: <Title Case title>
type: new-feature | enhancement
parent: <parent number if enhancement, else null>
status: captured
created: <datetime in format YYYY-MM-DD HH:MM EST>
source_folder: .claude/features/user-thoughts/<subfolder>/
---

# Processed Thought: <title>

## Problem / Goal
<confirmed answer>

## Who benefits
<confirmed answer>

## Success looks like
<confirmed answer>

## Constraints, risks, dependencies
<confirmed answer>

## Implementation ideas / open questions
<confirmed answer>

## Release pressure / deadlines
<confirmed answer>
```

If in interactive mode (no source folder), set `source_folder: null`.

---

## Step 7 — Update the registry

Add two new rows to the registry table in `.claude/features/registry.md`:

1. Feature row:
   | <assigned_number> | <title> | new-feature or enhancement | parent or — | 💡 Captured | — |

2. Placeholder release sub-row (will be replaced by /plan-release):
   | <assigned_number>.? | → <title> | release | <assigned_number> | 💡 Captured | — |

Insert both in numerical order (enhancements after their parent).

---

## Step 7a — Stamp captured_at in the database

Run the following Python snippet, substituting FEATURE_NUMBER, TITLE, SLUG,
PARENT_NUMBER, and IS_ENHANCEMENT with the values assigned in this run.

- For a **new feature**: PARENT_NUMBER = None, IS_ENHANCEMENT = False
- For an **enhancement**: PARENT_NUMBER = the parent feature number as a string (e.g. '15'), IS_ENHANCEMENT = True

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
        parent_number = PARENT_NUMBER  # e.g. '15' for enhancement, None for new feature
        row_type = 'release' if IS_ENHANCEMENT else 'feature'
        cur.execute('''
            INSERT INTO features (number, parent_number, title, slug, type, captured_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (number) DO UPDATE
              SET parent_number = EXCLUDED.parent_number,
                  type = EXCLUDED.type,
                  captured_at = EXCLUDED.captured_at
        ''', ('FEATURE_NUMBER', parent_number, 'TITLE', 'SLUG', row_type, now))
        if cur.rowcount == 0:
            print('WARNING: 0 rows upserted — check that FEATURE_NUMBER is correct and the INSERT ran')
        else:
            print('Rows upserted:', cur.rowcount)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB stamp failed: {e}')
"
```

If the DB write fails, log the error and continue — do not block the command.

---

## Step 7b — Refresh status

Run `/status` to refresh the live feature status view from the database.

---

## Step 8 — Report to the user

Print:
```
Number:             <assigned_number>
Title:              <title>
Type:               <new-feature | enhancement>
Processed thought:  .claude/features/processed-thoughts/<assigned_number>-<slug>-<datetime>.md
```

Then say:
"✅ **Thought captured!**

| Field | Value |
|-------|-------|
| **Number** | `<assigned_number>` |
| **Title** | `<title>` |
| **Type** | `<new-feature \| enhancement>` |
| **Processed thought** | `.claude/features/processed-thoughts/<assigned_number>-<slug>-<datetime>.md` |

Let me know if you'd like to make any changes to the processed thought, or if you'd like to move to the next stage: `/plan-release <assigned_number>`.

---

## 🚀 Development Pipeline

> This is an enhancement to an existing feature. It must go through the full pipeline.

| Step | Command | Status | What it does |
|------|---------|--------|--------------|
| 1 | `/capture-thoughts` | ✅ Done | Captures thought, assigns number |
| 2 | `/plan-release <assigned_number>` | ⬜ Pending | Decomposes into releases, writes `releases/` |
| 3 | `/create-spec <assigned_number.release> <slug>` | ⬜ Pending | Writes spec, creates feature branch |
| 4 | `/implement-feature <assigned_number.release>` | ⬜ Pending | Reads spec, plans + executes implementation |
| 5 | `/test-feature <assigned_number.release>-<slug>` | ⬜ Pending | Writes + runs pytest tests |
| 6 | `/code-review-feature <assigned_number.release>-<slug>` | ⬜ Pending | Parallel security + quality review |
| 7 | `/ship-feature` | ⬜ Pending | Commit, PR, squash merge, cleanup |

**Next step:** Run `/plan-release <assigned_number>` to begin release planning."
