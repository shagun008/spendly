---
number: 11-4
title: Feature View Tracking Per Session
type: enhancement
parent: 11
status: planned
releases: 1
created: 2026-06-06
---

# Release Plan: Feature View Tracking Per Session

## Summary
This enhancement changes how feature request views are counted. Currently a unique constraint on feature_views(feature_id, viewer_id) means a user is counted once ever per feature. The new behaviour counts one view per user per session — implemented via Flask's session object rather than a DB constraint, requiring a Supabase migration to drop the unique constraint.

## Releases

### Release 1 — Session-based view deduplication (MVP)
- **Scope:** Drop the UNIQUE constraint on feature_views(feature_id, viewer_id) in Supabase; update increment_feature_view() in queries.py to remove ON CONFLICT logic; update the view endpoint in app.py to check session['viewed_features'] before calling increment_feature_view() and append to it on a new view.
- **Spec slug:** feature-view-tracking-per-session
- **Spec arg:** `11-4.1 feature-view-tracking-per-session`
- **Depends on:** 11-1-feature-requests-core, 12.1-supabase-db-layer
- **Risk:** low

## Deferred / Out of scope
Nothing deferred — the full intended behaviour is covered in Release 1.

## Open questions
None — implementation approach is fully specified in the thought file.
