---
description: Show a live summary of all feature and release statuses
allowed-tools: Read, Write, Glob
---

You are a project status reporter for the Spendly expense tracker.
Your job is to read the feature registry and produce a clear, grouped
summary of what's in flight, what's waiting, and what's shipped.

## Step 1 — Read the registry
Read `.claude/features/registry.md` in full.
Parse every row — both feature rows and release sub-rows (rows where
Number contains a dot and Title starts with →).

## Step 2 — Group by status
Collect all release sub-rows and group them by status symbol:
- 🔧 In Progress
- 👀 In Review
- 📋 Planned
- 💡 Captured
- ✅ Shipped

For Captured rows (feature-level only, no release plan yet): use the
feature row itself since no release sub-rows exist yet.

For Shipped: collect only the 5 most recently added (lowest numbers last
= oldest; use reverse order to find most recent).

## Step 3 — Print the summary
Print in this exact format:

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
Spendly — Feature Status
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

🔧 In Progress
  <feature_number> <title>
  (or "Nothing in progress")

👀 In Review
  <feature_number> <title>
  (or "Nothing in review")

📋 Planned — ready to spec
  <feature_number> <title> → run /create-spec <feature_number> <slug>
  (or "Nothing planned yet")

💡 Captured — needs release planning
  <feature_number> <title> → run /plan-release <feature_number>
  (or "Nothing captured yet")

✅ Recently Shipped
  <feature_number> <title>
  (last 5 only)

╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

## Step 4 — Update status.md
Rewrite `.claude/features/status.md` with the same grouped content
plus a "Last updated: <today's date YYYY-MM-DD>" line at the top.

## Step 5 — Prompt next action
After the summary, print one line suggesting the most relevant next action:
- If anything is In Progress: "Continue implementation, then run `/test-feature <spec-name>`"
- Else if anything is Planned: "Run `/create-spec <number> <slug>` to start the next planned release"
- Else if anything is Captured: "Run `/plan-release <number>` to plan the next captured feature"
- Else: "Run `/capture-thoughts` to add a new feature idea"
