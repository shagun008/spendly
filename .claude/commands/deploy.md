---
description: Deploy Spendly to Railway
allowed-tools: Bash(railway up), Bash(python3 -c)
---

You are deploying the Spendly expense tracker to Railway.

## Step 1 — Deploy

Run:
```
railway up
```

## Step 2 — Report

Print the full output from the command.
If it succeeds, say: "Deployed successfully." then continue to Step 3.
If it fails, show the error output and say: "Deploy failed — see error above." Stop here — do not run Step 3.

## Step 3 — Stamp deployed_at in the database

Run:

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
            WHERE id = (
                SELECT id FROM features
                WHERE shipped_at IS NOT NULL AND deployed_at IS NULL
                ORDER BY shipped_at DESC
                LIMIT 1
            )
            RETURNING number, title
        ''', (now,))
        updated = cur.fetchall()
        if not updated:
            print('WARNING: 0 rows updated — no undeployed releases found (check shipped_at is set and deployed_at is NULL)')
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
