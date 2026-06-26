---
number: 20
title: Profile Card Layout & Dropdown Updates
type: new-feature
parent: null
status: captured
created: 2026-06-25 23:38 EST
source_folder: .claude/features/user-thoughts/User Profile Page Updates/
---

# Processed Thought: Profile Card Layout & Dropdown Updates

## Problem / Goal
Profile card is mostly empty; the navbar dropdown trigger and "My Profile" item use the same icon (confusing); no "Change Password" option in the dropdown; the Change Password button still sits on the profile card.

## Who benefits
Logged-in users — navigation clarity, tighter profile layout, consistent password-change access.

## Success looks like
- Distinct icons for dropdown trigger vs "My Profile" menu item.
- Dropdown shows: My Profile → Change Password → Log Out.
- Profile card contains 4 stacked rows (profile info + 3 stat cards: Total Spent This Month, Transactions, Top Category) within the current card height.
- Old Change Password button on the profile card is removed.

## Constraints, risks, dependencies
- Must not change routes or behaviour — only move where the entry points live.
- Must stay responsive (mobile stacked).
- Reuse existing Lucide icons only.

## Implementation ideas / open questions
- Use distinct Lucide icons (e.g. `user-circle` for "My Profile", `circle-user`/`chevron-down` for trigger).
- Add new dropdown row that routes to existing change-password flow.
- Pack 4 cards into a fixed-height grid/flex layout inside the profile card.

## Release pressure / deadlines
Not specified.
