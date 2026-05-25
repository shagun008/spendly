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
- A subfolder is **unprocessed** if no file in `processed-thoughts/` contains its name as a substring
- If **one unprocessed subfolder** found: enter file-input mode for that subfolder automatically
- If **multiple unprocessed subfolders** found: ask the user which one to process, then enter file-input mode
- If **no subfolders at all**: enter **interactive mode** (Step 2a)

---

## Step 1 — Read the feature registry
Read `.claude/features/registry.md` to understand:
- All existing features and their numbers
- The highest current feature number (for new feature numbering)
- All sub-numbers per parent (for enhancement numbering)

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

Once all answers are collected, skip to Step 3.

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

Does this look right? Reply with any corrections, or say "looks good" to continue.
```

Wait for the user to confirm or correct before proceeding.

Use the confirmed values as the discovery field answers and proceed to Step 3.

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

Save to: `.claude/features/processed-thoughts/<assigned_number>-<slug>.md`

Use this exact format:

```markdown
---
number: <assigned_number>
title: <Title Case title>
type: new-feature | enhancement
parent: <parent number if enhancement, else null>
status: captured
created: <today's date YYYY-MM-DD>
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

## Step 7b — Update status.md

Rewrite `.claude/features/status.md` by reading the full registry and
regenerating all sections grouped by status. Follow the same format as
`/status` command output. Set "Last updated" to today's date.

---

## Step 8 — Report to the user

Print:
```
Number:             <assigned_number>
Title:              <title>
Type:               <new-feature | enhancement>
Processed thought:  .claude/features/processed-thoughts/<assigned_number>-<slug>.md
```

Then say:
"Thought captured. Run `/plan-release <assigned_number>` to decompose this into
releases before moving to spec creation."
