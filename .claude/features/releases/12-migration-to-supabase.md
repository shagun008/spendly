---
number: 12
title: Migration to Supabase
type: new-feature
parent: null
status: planned
releases: 2
created: 2026-06-02
---

# Release Plan: Migration to Supabase

## Summary
Spendly currently uses SQLite, which is ephemeral on Railway — all data is lost on every redeploy. This feature migrates the database layer to Supabase (managed PostgreSQL) to provide persistent storage in production. Release 1 swaps the entire database layer (driver, schema, queries) to work with Postgres via a required DATABASE_URL env var. Release 2 handles migrating existing local SQLite data into Supabase so no local users or expenses are lost during the switchover.

## Releases

### Release 1 — Swap Database Layer (MVP)
- **Scope:** Install psycopg2-binary; rewrite database/db.py to use psycopg2 with RealDictCursor and read DATABASE_URL from env (no SQLite fallback); rewrite schema SQL for Postgres (SERIAL PRIMARY KEY, NOW()); update all queries in database/queries.py replacing ? with %s; update init_db() to create tables on Supabase; verify all existing routes work end-to-end.
- **Spec slug:** supabase-db-layer
- **Spec arg:** `12.1 supabase-db-layer`
- **Depends on:** nothing
- **Risk:** medium

### Release 2 — Local Data Migration
- **Scope:** One-off script to export users and expenses from local SQLite to CSV; import CSVs into Supabase preserving original IDs; reset Postgres sequences after import (setval to MAX(id)) so new inserts don't collide; verify migrated data is intact via row counts and spot checks.
- **Spec slug:** supabase-local-data-migration
- **Spec arg:** `12.2 supabase-local-data-migration`
- **Depends on:** Release 1
- **Risk:** low

## Deferred / Out of scope
- Railway data migration — the Railway SQLite DB will be wiped and started fresh on first deploy with Supabase.
- Neon as an alternative provider — not needed if Supabase works as expected.

## Open questions
None remaining.
