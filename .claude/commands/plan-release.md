---
description: Analyse a captured thought and decompose it into release-sized units before spec creation
argument-hint: "Feature number e.g. 11 or 10.1"
allowed-tools: Read, Write, Glob, Bash, mcp__github__create_pull_request, mcp__github__merge_pull_request, mcp__github__list_pull_requests
---

You are a senior engineer and release planner for the Spendly expense tracker.
Your job is to read a captured thought file, analyse its scope and complexity,
and decompose it into the right number of release-sized units — each one small
enough to be a single spec and a single PR.

This is the stage where splitting happens. `/create-spec` always works on one
already-decomposed release unit; it never splits work itself.

User input: $ARGUMENTS

## Step 1 — Parse the feature number
Extract the feature number from $ARGUMENTS (e.g. `11` or `10.1`).
If missing, ask: "Which feature number would you like to plan? (e.g. 11 or 10.1)"

## Step 2 — Find and read the processed thought file
List all files in `.claude/features/processed-thoughts/`.
Find the file whose name starts with `<feature_number>-`.
Read it fully.

If no matching file exists, stop and say:
"No processed thought file found for feature <number>. Run `/capture-thoughts` first."

## Step 3 — Read context
Read the following to understand what already exists:
- `CLAUDE.md` — implementation rules, existing routes, schema, CSS variables
- All files in `.claude/specs/` — what has already been built

## Step 4 — Analyse scope and complexity
From the thought file, identify everything implied:
- New routes needed
- Database changes (new tables, columns, constraints)
- New templates or significant template changes
- New JS or CSS files
- Third-party dependencies
- Auth or permission changes
- Any cross-cutting concerns (e.g. affects multiple pages)

Use this to assess overall complexity:
- **Simple:** 1–2 routes, no DB changes, small UI — fits in one spec
- **Medium:** 2–4 routes or 1 DB change — likely 1–2 specs
- **Complex:** Multiple DB changes, many routes, or multi-page UI — 2–4 specs

## Step 5 — Design the release decomposition
Split the work into releases using these principles:

1. **Each release must be independently deployable** — it should leave the app in
   a working state, not a half-built one.
2. **MVP first** — Release 1 should be the smallest thing that delivers value.
3. **Dependencies flow forward** — Release N+1 must depend on Release N, not the other way.
4. **One spec per release** — each release maps to exactly one `/create-spec` call.
5. **Deferred work is explicit** — anything not in any release is listed as deferred.

If the feature is simple, one release is fine. Do not split unnecessarily.

## Step 6 — Present the recommendation
Show the user the proposed decomposition in plain English before writing anything.
Format:

```
Feature: <title> (<number>)

Proposed decomposition: <N> release(s)

Release 1 — <short title>
  What's included: <scope>
  Suggested spec slug: <slug>
  Depends on: <existing spec numbers or "nothing">
  Risk: low | medium | high

Release 2 — <short title>  (if applicable)
  What's included: <scope>
  Suggested spec slug: <slug>
  Depends on: Release 1
  Risk: low | medium | high

Deferred: <anything not included>

Open questions: <any unresolved items from the thought file>
```

Ask: "Does this decomposition look right, or would you like to adjust it?"

Wait for the user to confirm or redirect before proceeding.

## Step 7 — Write the release plan file
Once confirmed, save to: `.claude/features/releases/<feature_number>-<slug>.md`

Use this exact format:

```markdown
---
number: <feature_number>
title: <Title Case>
type: new-feature | enhancement
parent: <parent number or null>
status: planned
releases: <count>
created: <today's date YYYY-MM-DD>
---

# Release Plan: <title>

## Summary
<one paragraph describing what this feature does and how it was decomposed>

## Releases

### Release 1 — <short title> (MVP)
- **Scope:** <what's included>
- **Spec slug:** <slug — what to pass to /create-spec>
- **Spec arg:** `<feature_number>.1 <slug>`
- **Depends on:** <feature or spec numbers, or "nothing">
- **Risk:** low | medium | high

### Release 2 — <short title>
- **Scope:** <what's included>
- **Spec slug:** <slug>
- **Spec arg:** `<feature_number>.2 <slug>`
- **Depends on:** Release 1
- **Risk:** low | medium | high

## Deferred / Out of scope
<anything explicitly excluded from all releases, with rationale>

## Open questions
<unresolved items that need answering before or during implementation>
```

## Step 8 — Update the registry
In `.claude/features/registry.md`:
1. Find the feature row for this feature number. Update its Status to `📋 Planned`
   and Specs column to `<N> releases planned`
2. Remove the placeholder release sub-row (the one with `→ <title>` and `💡 Captured`)
3. Add one release sub-row per release in the plan:
   | <feature_number>.1 | → <release_1_title> | release | <feature_number> | 📋 Planned | — |
   | <feature_number>.2 | → <release_2_title> | release | <feature_number> | 📋 Planned | — |

## Step 8b — Update status.md
Rewrite `.claude/features/status.md` by reading the full registry and
regenerating all sections grouped by status. Follow the same format as
`/status` command output. Set "Last updated" to today's date.

## Step 8c — Commit and push all planning artefacts
Create a planning branch, stage everything under `.claude/features/`, commit, push, then use the GitHub MCP to create and merge the PR.

Run these git steps in order:
```
git checkout main
git pull origin main
git checkout -b plan/<feature_number>-<slug>
git add .claude/
git commit -m "plan: release plan for <feature_number> <title>"
git push --set-upstream origin plan/<feature_number>-<slug>
```

Then use `mcp__github__create_pull_request` to create the PR:
- owner: derive from `git remote get-url origin`
- repo: derive from `git remote get-url origin`
- title: `plan: <feature_number> <title>`
- body: `Release plan and processed thought for feature <feature_number>. Auto-generated by /plan-release.`
- head: `plan/<feature_number>-<slug>`
- base: `main`

Report: "✓ PR created — <PR URL>"

Then use `mcp__github__merge_pull_request` to squash merge it:
- owner/repo: same as above
- pull_number: from the PR just created
- merge_method: `squash`

Then clean up:
```
git checkout main
git pull origin main
```

Report the PR URL and confirm the merge before continuing to Step 9.

## Step 9 — Report to the user
Print:
```
Feature:       <number> — <title>
Releases:      <count>
Release plan:  .claude/features/releases/<number>-<slug>.md
```

Then print one line per release showing the exact command to run:
```
To create specs, run:
  /create-spec <feature_number>.1 <release_1_slug>    ← Release 1: <release_1_title>
  /create-spec <feature_number>.2 <release_2_slug>    ← Release 2: <release_2_title>
```

If only one release, still use dot notation:
```
  /create-spec <feature_number>.1 <slug>    ← Release 1 (single release)
```
