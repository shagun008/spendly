---
number: 19
title: Profile Layout and Navbar Updates
type: new-feature
parent: null
status: planned
releases: 2
created: 2026-06-25
---

# Release Plan: Profile Layout and Navbar Updates

## Roadmap description
Side-by-side profile layout on desktop and a clean user icon menu in the navbar.

## Summary
This feature modernizes the Profile page layout and the navbar navigation. Release 1 adds a responsive side-by-side layout for the Profile Card and Analytics Dashboard on desktop screens (stacked on mobile). Release 2 replaces the username text and standalone Logout link in the navbar with a Lucide user icon that opens a dropdown menu on desktop and replaces the hamburger icon with a user icon on mobile when logged in, while relabelling navigation items for consistency. No new routes or database changes are required — all work is in templates, CSS, and JS.

## Releases

### Release 1 — Responsive Profile Layout (MVP)
- **Scope:** Wrap the Profile Card and Analytics Dashboard in a side-by-side container on desktop (>900px breakpoint), stacked vertically on mobile. CSS-only changes to `profile.css` with a minor wrapper div addition in `profile.html`. No routes, DB, or JS changes.
- **Spec slug:** `responsive-profile-layout`
- **Spec arg:** `19.1 responsive-profile-layout`
- **Depends on:** nothing
- **Risk:** low

### Release 2 — Navbar User Menu
- **Scope:** Replace username text with a Lucide user icon + dropdown on desktop (containing "My Profile" and "Log Out"). Replace hamburger icon with user icon on mobile when logged in (tapping opens the existing mobile menu). Relabel "Logout" → "Log Out" and username text → "My Profile" in mobile menu. Remove standalone "Logout" text from desktop nav. Preserve all existing routes, permissions, and behaviours.
- **Spec slug:** `navbar-user-menu`
- **Spec arg:** `19.2 navbar-user-menu`
- **Depends on:** nothing (independent of Release 1)
- **Risk:** medium (dropdown UX + responsive icon swap logic)

## Deferred / Out of scope
- Adding "Change Password" or other profile actions to the desktop dropdown — not requested by user, can be added later as an enhancement
- `<details>/<summary>` no-JS fallback for the desktop dropdown — the app already depends on JS for modals and analytics, so this is not needed

## Open questions
- None remaining — desktop and mobile behaviour is fully specified in the processed thought
