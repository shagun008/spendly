---
number: 21
title: Oxos Profile Page
type: new-feature
parent: null
status: captured
created: 2026-07-13 00:29 EST
source_folder: .claude/features/user-thoughts/Auto En Platform/
---

# Processed Thought: Oxos Profile Page

## Problem / Goal
Build a new Oxos Profile page within the existing authenticated application experience. This page serves as the central profile/dashboard for the Oxos platform, providing users with a high-level view of available business capabilities, platform context, and organizational knowledge.

## Who benefits
All authenticated users of the Spendly application. The page is part of the authenticated user flow and provides a unified dashboard view for the Oxos platform.

## Success looks like
A responsive page with three primary sections in clear visual hierarchy:
- Business Outcomes section with Reports card and Business Applications card (showing Expense as initial application)
- Context section with interactive Supabase card that flips to show database tables
- Learnings section displaying top 5 best practices from claude.md
The design follows existing patterns: card-based layouts, hover effects, rounded corners, smooth animations, and responsive design that works on desktop and tablet.

## Constraints, risks, dependencies
- Must use existing authentication and routing (no separate auth flow)
- Must follow existing architecture, styling, and UI conventions
- Expense Business Application card opens existing Expense Profile page in a new tab
- Not to be confused with future public Oxos homepage (separate feature)

## Implementation ideas / open questions
- Reuse the existing nav-user-menu component
- Design card components with extensibility for multiple business applications, reports, and data systems
- Implement card flip animation for Context section (front shows database icon/name, back shows table list)
- Extract learnings content from claude.md file initially (can be database-driven later)
- Use existing CSS variables and design system patterns

## Release pressure / deadlines
Not specified