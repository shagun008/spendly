---
number: 12
title: Migration to Supabase
type: new-feature
parent: null
status: captured
created: 2026-06-01
source_folder: .claude/features/user-thoughts/Migration to Supabase/
---

# Processed Thought: Migration to Supabase

## Problem / Goal
Railway's filesystem is ephemeral — SQLite data is lost on every redeploy. Migrating to Supabase (PostgreSQL) provides persistent, managed storage without changing hosting provider.

## Who benefits
All users (data survives redeployments); the developer (production-ready setup with free-tier managed DB).

## Success looks like
App runs on Railway with Supabase as the database, all data persists across redeployments, and all existing routes work identically.

## Constraints, risks, dependencies
Supabase project must be created manually first. psycopg2 placeholders differ from sqlite3 (`?` → `%s`). Schema SQL must be rewritten (`SERIAL`, `NOW()`). Existing data needs CSV export/import with sequence resets after migration.

## Implementation ideas / open questions
- Install `psycopg2-binary`, add to `requirements.txt`
- Replace `sqlite3` with `psycopg2` in `database/db.py`
- Use `RealDictCursor` for dict-like row access (replaces `sqlite3.Row`)
- Replace all `?` with `%s` in `database/queries.py`
- Rewrite schema: `SERIAL PRIMARY KEY`, `NOW()` instead of `datetime('now')`
- Set `DATABASE_URL` env var on Railway
- Supabase MCP can automate schema creation and data verification
- Neon is a noted alternative to Supabase

## Release pressure / deadlines
Not specified.

Created: 2026-06-02 22:30 EST
