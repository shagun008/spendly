---
number: 20
title: Profile Card Layout & Dropdown Updates
type: new-feature
parent: null
status: planned
releases: 1
created: 2026-06-25
---

# Release Plan: Profile Card Layout & Dropdown Updates

## Roadmap description
Tightens the profile card with stat cards and adds "Change Password" to the navbar dropdown with distinct icons.

## Summary
This feature makes three related improvements to the logged-in user experience. First, it gives the navbar dropdown trigger a different Lucide icon from the "My Profile" menu item so the two are visually distinct. Second, it adds a "Change Password" row to the dropdown between "My Profile" and "Log Out", removing the redundant button from the profile card. Third, it packs four rows (profile info plus three stat cards: Total Spent This Month, Transactions, Top Category) into the profile card's current height so the space is used efficiently. All three changes are UI-only — no new routes, no DB changes, no new dependencies.

## Releases

### Release 1 — Profile Card Layout & Dropdown Updates (MVP)
- **Scope:** Distinct dropdown icons, "Change Password" dropdown row with profile card button removed, 4-row profile card layout (profile info + 3 stat cards)
- **Spec slug:** profile-card-layout-dropdown-updates
- **Spec arg:** `20.1 profile-card-layout-dropdown-updates`
- **Depends on:** 19.2-navbar-user-menu
- **Risk:** low

## Deferred / Out of scope
Nothing.

## Open questions
None.
