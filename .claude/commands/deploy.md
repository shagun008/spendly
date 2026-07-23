---
description: Deploy Oxos Platform to Railway
allowed-tools: Bash(python3 -c), mcp__plugin_railway_railway__deploy
---

You are deploying the Oxos Platform application to Railway.

## Step 0 — Pre-flight Checks

Before deploying, verify prerequisites:

1. **Railway MCP** — verify Railway MCP server is connected by checking that `mcp__plugin_railway_railway__deploy` is available. If not, stop and say: "Railway MCP not connected. Check MCP settings."

2. **Database URL** — verify `DATABASE_URL` is set: `python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); assert os.environ.get('DATABASE_URL'), 'DATABASE_URL not set'"`. If not set, stop and say: "DATABASE_URL not set in .env file."

## Step 1 — Deploy via Railway MCP

Use the Railway MCP server to deploy:

```
mcp__plugin_railway_railway__deploy
```

## Step 2 — Report

If deployment succeeds, say: "Deployed successfully." then continue to Step 3.
If it fails, show the error output and say: "Deploy failed — see error above." Stop here — do not run Step 3.

## Step 3 — Stamp deployed_at in the database

Stamp ALL shipped releases that haven't been deployed yet:

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
        cur.execute('''
            UPDATE features
            SET deployed_at = %s
            WHERE shipped_at IS NOT NULL AND deployed_at IS NULL
            RETURNING number, title
        ''', (now,))
        updated = cur.fetchall()
        if not updated:
            print('WARNING: 0 rows updated — no undeployed releases found')
        else:
            for row in updated:
                print(f'  Stamped {row[0]} — {row[1]}')
            print('Rows updated:', len(updated))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB stamp failed: {e}')
"
```

If `Rows updated: 0`, say: "No undeployed releases found — skipping DB stamp."
If the DB write fails, log the error and continue.

## Step 4 — Update registry

1. Read `.claude/features/registry.md`
2. Find all release sub-rows where `shipped_at IS NOT NULL` in the DB but the registry status is not yet `✅ Shipped`
3. Update those rows to `✅ Shipped` in the registry
