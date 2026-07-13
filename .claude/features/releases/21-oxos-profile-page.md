---
number: 21
title: Oxos Profile Page
type: new-feature
parent: null
status: planned
releases: 2
created: 2026-07-13
---

# Release Plan: Oxos Profile Page

## Roadmap description
A central dashboard page for the Oxos platform showing business capabilities, data systems, and implementation learnings for authenticated users.

## Summary
This feature creates a new Oxos Profile page within the authenticated Spendly application. The page provides a unified dashboard with three sections: Business Outcomes (reports and applications), Context (interactive data system cards), and Learnings (best practices extracted from project conventions). Release 1 delivers the core page with Business Outcomes and Learnings sections. Release 2 adds the interactive Context section with card flip animations for database visibility.

## Releases

### Release 1 — Oxos Profile Page MVP
- **Scope:** New authenticated route `/oxos`, template extending base.html with Business Outcomes section (Reports and Business Applications cards), Learnings section (static top 5 best practices from claude.md), responsive card-based layout following existing design system. Expense card opens existing profile page in new tab.
- **Spec slug:** oxos-profile-page-mvp
- **Spec arg:** `21.1 oxos-profile-page-mvp`
- **Depends on:** nothing
- **Risk:** low

### Release 2 — Context Section with Card Flip
- **Scope:** Interactive Context section on Oxos Profile page with Supabase card that flips on click to show database tables. CSS transition animation. Extensible card component design for future data systems (Snowflake, PostgreSQL, APIs, S3).
- **Spec slug:** oxos-context-flip
- **Spec arg:** `21.2 oxos-context-flip`
- **Depends on:** Release 1
- **Risk:** low

## Deferred / Out of scope
- Dynamic retrieval of database table metadata via Supabase API (tables hardcoded in Release 2)
- Database-backed learnings content (static extraction in Release 1)
- Additional business applications beyond Expense (structure supports future additions)

## Open questions
- Route path confirmed: `/platform` for the Oxos Profile page