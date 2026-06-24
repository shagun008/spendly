---
number: 18
title: Quick Edit Expense from Profile
type: new-feature
parent: null
status: planned
releases: 1
created: 2026-06-24
---

# Release Plan: Quick Edit Expense from Profile

## Roadmap description
Edit any expense straight from your Profile page in a quick modal — no more navigating to a separate edit page.

## Summary
This feature replaces the dedicated Edit Expense page with a modal on the Profile page. The "Edit" link in each expense row opens a modal pre-populated with the expense's current values, using the same fields and validation as the existing Edit Expense page (amount, category, date, description). Submitting saves the expense in place via the existing `update_expense` query helper and the Profile page refreshes. Once the modal is working, the standalone edit page, its route, its CSS, and any unused code are deleted. Faster-editing enhancements (keyboard shortcuts, recently-used category suggestions) are explored if time permits.

## Releases

### Release 1 — Quick Edit Expense Modal (MVP)
- **Scope:** Convert the Edit Expense workflow from a dedicated page to a modal on the Profile page. The "Edit" link per expense row opens a modal containing the same form fields and validation as the current Edit Expense page (`amount`, `category`, `date`, `description`). Submitting saves via the existing `update_expense` helper and refreshes the Profile page. Delete `templates/edit_expense.html`, the `/expenses/<id>/edit` route from `app.py`, any edit-specific CSS, and unused imports/code. Explore faster-editing enhancements (keyboard shortcuts, recently-used category suggestions) if time permits.
- **Spec slug:** `quick-edit-expense-modal`
- **Spec arg:** `18.1 quick-edit-expense-modal`
- **Depends on:** nothing
- **Risk:** medium

## Deferred / Out of scope
- Quick-add templates (preset amounts/categories) — future user thought
- Recurring expenses — future user thought
- Smart category suggestions — future user thought

## Open questions
- Whether to explore faster-editing enhancements (inline editing, keyboard shortcuts, recently-used category suggestions) within this release or defer them.
