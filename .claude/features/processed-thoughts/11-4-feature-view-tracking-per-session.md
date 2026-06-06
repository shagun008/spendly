---
number: 11-4
title: Feature View Tracking Per Session
type: enhancement
parent: 11
status: captured
created: 2026-06-06
source_folder: .claude/features/user-thoughts/Feature View Tracking Per Session/
---

# Processed Thought: Feature View Tracking Per Session

## Problem / Goal
The current unique constraint on feature_views(feature_id, viewer_id) means a user is counted only once ever per feature, which doesn't reflect real engagement. The goal is to count one view per user per session — more representative of actual interest over time.

## Who benefits
All users who browse /features; indirectly affects view counts and the trending algorithm for all feature requests.

## Success looks like
Revisiting a feature in the same session does not increment the counter. Logging out and back in, then viewing the same feature, does increment it. The change is invisible to users but produces more meaningful view counts.

## Constraints, risks, dependencies
Requires a schema migration to drop the unique constraint on feature_views(feature_id, viewer_id) in Supabase. The same user can now have multiple rows in feature_views across sessions — historical data remains valid but the uniqueness guarantee is gone.

## Implementation ideas / open questions
Use Flask session['viewed_features'] (list of feature IDs) as the per-session dedup check. Skip insert + increment if already in list; otherwise insert into feature_views, increment views on feature_requests, and append to session list. Drop the DB unique constraint since it's no longer the source of truth.

## Release pressure / deadlines
Not specified.
