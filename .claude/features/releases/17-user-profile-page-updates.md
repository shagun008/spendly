---
number: 17
title: User Profile Page Updates
type: new-feature
parent: null
status: planned
releases: 3
created: 2026-06-23
---

# Release Plan: User Profile Page Updates

## Roadmap description
Make the Profile page your one-stop hub — change password, add expenses via a quick modal, and view spending insights without navigating away.

## Summary
This feature consolidates three standalone pages into the Profile experience. First, the disabled Change Password button is wired up with a secure modal form. Second, the Add Expense nav item is replaced by a "+" button next to the Profile title that opens a modal with the same fields and validation — the standalone Add Expense page, route, nav link, and template are removed. Third, an embedded Analytics dashboard is added between the profile card and filter bar with switchable chart views (spending trends, category breakdown, monthly comparisons) using Chart.js via CDN — the standalone Analytics page, route, nav link, and template are removed. The result is a simpler nav and a Profile page that handles account management, expense creation, and financial insights.

## Releases

### Release 1 — Change Password (MVP)
- **Scope:** Backend route `POST /profile/change-password` that verifies the current password, validates the new password (minimum length, confirmation match), and updates the hash. Enable the existing disabled "Change Password" button on the profile card to open a modal with current password, new password, and confirm password fields. Flash success/error messages.
- **Spec slug:** `change-password`
- **Spec arg:** `17.1 change-password`
- **Depends on:** nothing
- **Risk:** low

### Release 2 — Quick Add Expense Modal
- **Scope:** Add a "+" button to the right of the "My Profile" title heading (horizontally aligned, same row). Clicking opens a modal containing the same form fields and validation as the current Add Expense page (amount, category, date, description). On submit the expense is saved and the page refreshes showing the new expense. Remove the standalone Add Expense nav item from `base.html` (both desktop `.nav-links` and mobile `.nav-mobile-menu`). Delete `templates/add_expense.html`, the `/expenses/add` route from `app.py`, and `static/css/add_expense.css`.
- **Spec slug:** `quick-add-expense-modal`
- **Spec arg:** `17.2 quick-add-expense-modal`
- **Depends on:** Release 1
- **Risk:** medium

### Release 3 — Embedded Analytics Dashboard
- **Scope:** Add a compact Analytics section between the profile card and the filter bar on the Profile page. Include switchable views: spending trends (line chart), category breakdown (pie/bar chart), and monthly comparisons. Use Chart.js loaded via CDN for visualizations. Remove the standalone Analytics nav item from `base.html` (both desktop and mobile). Delete `templates/analytics.html` and the `/analytics` route from `app.py`. Explore additional visualizations (savings progress, etc.) if time permits.
- **Spec slug:** `embedded-analytics-dashboard`
- **Spec arg:** `17.3 embedded-analytics-dashboard`
- **Depends on:** Release 2
- **Risk:** medium

## Deferred / Out of scope
- Quick-add templates (preset amounts/categories) — future user thought
- Recurring expenses — future user thought
- Smart category suggestions — future user thought

## Open questions
- Chart.js version to pin via CDN (latest stable)
- Whether to reuse existing category-breakdown query logic for the analytics charts
