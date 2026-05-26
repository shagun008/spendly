---
number: 11
title: Feature Requests Page and Public Feature Discovery
type: new-feature
parent: null
status: planned
created: 2026-05-25
source_folder: .claude/features/user-thoughts/Feature Requests Page and Public Feature Discovery/
---

# Processed Thought: Feature Requests Page and Public Feature Discovery

## Problem / Goal
Users have no way to suggest product improvements, and there is no public-facing space where feature ideas can be discovered, voted on, or tracked. The goal is a community-style feature request system where logged-in users can submit ideas and upvote, and anyone can browse, filter and search.

## Who benefits
All logged-in users (can submit and vote); all visitors (can browse the public All Features page); product team (gains a structured signal on what users want most).

## Success looks like
Logged-in users see a "Features" nav link; can submit requests tagged to an app page; Home page shows latest 6 requests with category filters; a public All Features page supports search, filter, sort, and upvoting with duplicate prevention; view counts and a trending score drive ranking; submitter identity is never exposed beyond initials.

## Constraints, risks, dependencies
Privacy is mandatory — full name, email, and username must never appear on public pages; only initials avatar shown. Voting must require login — unauthenticated users who try to upvote should be prompted to log in rather than silently blocked. Duplicate vote prevention required (1 vote per user per feature, enforced at DB level via unique constraint on feature_votes(feature_id, user_id)). Users cannot upvote their own requests — enforced on the backend (check session user_id != created_by) and surfaced on the frontend as a disabled button with a tooltip. View tracking needs a session/user anchor. Trending score formula must be defined and consistently applied. Spam prevention: limit each user to a maximum of 5 submitted feature requests. Status management (submitted → under review → planned → completed) is manual for now — no UI needed in this release; may be implemented in a future release.

## Implementation ideas / open questions
Three new DB tables: feature_requests, feature_votes, feature_views. Page dropdown is a hardcoded static list (e.g. Home, Profile, Analytics, Add Expense, Edit Expense, Other) — no dynamic page registry needed, may be implemented in a future release. Trending score = (upvotes × 5) + (views × 1) + recency bonus. Optimistic UI updates for voting. Clicking a feature card opens a detail modal (not a separate page) — view count increments on modal open. Submitter can edit or delete their own request; ownership check required (user_id must match session user). Match existing retro/editorial card design from the Issues module.

**Home page cards:** Show vote count and view count only — no upvote button. Cards are browse-only; clicking through takes the user to the full /features page.

**Public /features page (single route, two states):**
- Logged-out: standard public listing — search, filter, sort, upvote button (prompts login on click), card detail modal, no submission form.
- Logged-in: two-column layout — left panel shows the user's own submitted requests with edit/delete controls; right panel shows the submission form to add a new request. Upvote button is disabled on the user's own requests.

**Nav link:** /features is visible in the main nav to all visitors (logged-in and logged-out).

## Release pressure / deadlines
None mentioned.
