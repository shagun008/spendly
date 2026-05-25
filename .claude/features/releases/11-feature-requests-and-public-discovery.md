---
number: 11
title: Feature Requests Page and Public Feature Discovery
type: new-feature
parent: null
status: planned
releases: 3
created: 2026-05-25
---

# Release Plan: Feature Requests Page and Public Feature Discovery

## Summary
This feature introduces a community-style feature request system. A single /features route serves both logged-out visitors (public listing with search, filter, sort, and detail modal) and logged-in users (two-column layout with their own requests, edit/delete controls, and a submission form). Upvoting with self-vote prevention and a trending score are added in Release 2. The home page gets a "Latest Features" section in Release 3.

## Releases

### Release 1 — DB, Submission, and /features Page (Core)
- **Scope:** 3 new DB tables (feature_requests, feature_votes, feature_views). /features nav link visible to all visitors. Logged-out state: public listing with search, filter by page/status, sort (Latest, Most Upvoted, Most Viewed), card detail modal, view count increments on modal open, initials avatar only. Logged-in state: two-column layout — left panel shows all other users' requests (same as public view); right panel shows the user's own requests with edit/delete controls and a submission form. Hardcoded page dropdown, title and description fields with validation, 5-request-per-user spam limit, ownership check on edit/delete.
- **Spec slug:** feature-requests-core
- **Spec arg:** `11.1 feature-requests-core`
- **Depends on:** nothing
- **Risk:** medium

### Release 2 — Upvoting and Trending
- **Scope:** Upvote/remove-vote toggle on cards and detail modal. Self-vote prevention — disabled button with tooltip on the user's own requests. Unauthenticated users prompted to log in when they click upvote. 1-vote-per-user enforced via DB unique constraint on feature_votes(feature_id, user_id) and backend check. Trending score = (upvotes × 5) + (views × 1) + recency bonus. Trending sort option added to /features page.
- **Spec slug:** feature-requests-voting
- **Spec arg:** `11.2 feature-requests-voting`
- **Depends on:** Release 1
- **Risk:** low

### Release 3 — Home Page "Latest Features" Section
- **Scope:** New "Latest Features" section on the home page showing the latest 6 feature request cards. Category filter tabs. Cards show vote count and view count only — no upvote button. "View All Features →" CTA linking to /features.
- **Spec slug:** feature-requests-home
- **Spec arg:** `11.3 feature-requests-home`
- **Depends on:** Release 2
- **Risk:** low

## Deferred / Out of scope
- **Status management UI** — changing a request's status (submitted → under review → planned → completed) is manual only for now; no UI needed in these releases. Deferred to a future release.
- **Admin/moderation tooling** — no admin role exists in Spendly yet; deferred entirely.

## Open questions
None remaining.
