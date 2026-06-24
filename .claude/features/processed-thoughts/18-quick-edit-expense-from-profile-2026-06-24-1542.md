---
number: 18
title: Quick Edit Expense from Profile
type: new-feature
parent: null
status: captured
created: 2026-06-24 15:42 EST
source_folder: .claude/features/user-thoughts/User Profile Page Updates/
---

# Processed Thought: Quick Edit Expense from Profile

## Problem / Goal
Reduce friction when users need to correct or update an expense. Currently Edit Expense opens a separate page, pulling users out of the Profile flow. Goal is to keep users in context by opening a modal instead, and to explore ways to make editing faster and more intuitive.

## Who benefits
All logged-in Spendly users who manage expenses on their Profile page.

## Success looks like
Clicking Edit Expense opens a modal with the same fields and functionality as the current Edit Expense page. Submitting saves the expense directly to the user's list. The old edit page, route, and unused code are deleted.

## Constraints, risks, dependencies
Must preserve all existing edit fields and validation. Must enforce ownership check (user_id) on update. Modal must work within the existing Jinja2 + vanilla CSS/JS stack.

## Implementation ideas / open questions
Modal-based edit form reusing existing edit template/fields. Explore inline editing, keyboard shortcuts, smart defaults, and recently-used category suggestions to make editing faster and more intuitive.

## Release pressure / deadlines
Not specified.
