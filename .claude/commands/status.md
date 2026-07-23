---
description: Show a live summary of all feature and release statuses
allowed-tools: Read, Write, Bash(python3 -c)
---

You are a project status reporter for the Oxos Platform.
Your job is to query the features database and produce a clear, grouped
summary of what's in flight, what's waiting, what's shipped, and what's deployed.

## Step 1 — Query the database

Run the following Python snippet to fetch all features:

```bash
python3 -c "
import psycopg2, os, json
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('''
    SELECT number, parent_number, title, slug,
           captured_at, planned_at, spec_at, implemented_at,
           tested_at, reviewed_at, shipped_at, deployed_at
    FROM features
    ORDER BY number
''')
rows = cur.fetchall()
cols = ['number','parent_number','title','slug',
        'captured_at','planned_at','spec_at','implemented_at',
        'tested_at','reviewed_at','shipped_at','deployed_at']
def row_to_dict(cols, r):
    d = dict(zip(cols, r))
    for k in cols[4:]:
        if d[k] is not None:
            d[k] = str(d[k])
    return d
print(json.dumps([row_to_dict(cols, r) for r in rows]))
cur.close()
conn.close()
"
```

If the query fails or returns no rows, print "No features in DB yet." and stop.

## Step 2 — Derive current stage per row

For each row, determine the current stage from the rightmost non-null timestamp
column, in this priority order:

1. `deployed_at` → 🚀 Deployed
2. `shipped_at` → ✅ Shipped
3. `reviewed_at` → 👀 In Review
4. `tested_at` → 👀 In Review
5. `implemented_at` → 🔧 In Progress
6. `spec_at` → 📝 Spec'd
7. `planned_at` → 📋 Planned
8. `captured_at` → 💡 Captured

Note: `tested_at` maps to 👀 In Review because testing is the gateway to review.

## Step 3 — Group and print the summary

Group rows by stage. For the ✅ Shipped section, show only the 5 most recent
(by `shipped_at` timestamp). Skip parent feature rows (where `parent_number IS NULL`)
from the active sections — use only release sub-rows (where `parent_number IS NOT NULL`)
unless no release sub-rows exist yet (i.e. for 💡 Captured features).

Print in this exact format:

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
Oxos Platform — Feature Status
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

🔧 In Progress
  <number> <title>
  (or "Nothing in progress")

👀 In Review
  <number> <title>
  (or "Nothing in review")

📝 Spec'd — ready to implement
  <number> <title> → run /implement-feature <number>
  (or "Nothing spec'd yet")

📋 Planned — ready to spec
  <number> <title> → run /create-spec <number> <slug>
  (or "Nothing planned yet")

💡 Captured — needs release planning
  <number> <title> → run /plan-release <number>
  (or "Nothing captured yet")

✅ Recently Shipped
  <number> <title>
  (last 5 only, or "Nothing shipped yet")

🚀 Deployed
  <number> <title>
  (or "Nothing deployed yet")

╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

## Step 4 — Prompt next action
After the summary, print one line suggesting the most relevant next action:
- If anything is In Progress: "Continue implementation, then run `/test-feature <spec-name>`"
- Else if anything is Spec'd: "Run `/implement-feature <number>` to start implementation"
- Else if anything is Planned: "Run `/create-spec <number> <slug>` to start the next planned release"
- Else if anything is Captured: "Run `/plan-release <number>` to plan the next captured feature"
- Else: "Run `/capture-thoughts` to add a new feature idea"
