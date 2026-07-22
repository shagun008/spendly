---
number: 23
title: Readme Platform Revamp
type: new-feature
parent: null
status: captured
created: 2026-07-22 08:27 EST
source_folder: .claude/features/user-thoughts/Readme Platform Revamp/
---

# Processed Thought: Readme Platform Revamp

## Problem / Goal
The project has evolved from a single "Spendly expense tracker" into the "Oxos Platform" — a dashboard that hosts Spendly as one business application among others, and which showcases engineering best practices (Learnings section) and data systems (Supabase). The current README.md still reads as a single-app proof-of-concept and is engineer/process-centric. It also has internally inconsistent feature counts (headline says "14 features · 20 spec releases" while body says "15 features shipped across 21 spec releases"). The /platform homepage (feature 21) is already shipped and live. Goal: rewrite README.md to lead with "platform, not a single app" framing, serve three reading tracks (executives, business/product, engineers), be understandable by non-technical readers, stay engaging and honest, fix inconsistent feature counts, and preserve engineer-grade pipeline/tech-stack content.

## Who benefits
All readers of the repository — executives and decision-makers, business/product readers, non-technical visitors, and engineers/builders. The README is the front door to the project.

## Success looks like
A README that:
- Leads with the "platform, not a single app" framing
- Serves three clear reading tracks: executives, business/product, engineers
- Is understandable by a non-technical reader (plain English, concrete analogies)
- Stays engaging and honest (Oxos dashboard is part of the authenticated experience; public homepage is a future feature not yet built)
- Fixes the inconsistent feature counts
- Preserves the engineer-grade pipeline diagram and tech-stack content

## Constraints, risks, dependencies
- Must preserve the existing engineer-grade content (tech stack, pipeline ASCII, command table)
- Must stay honest: the Oxos dashboard is authenticated; public marketing homepage is a future feature not yet built
- Tone must remain accessible without dumbing down the technical detail

## Implementation ideas / open questions
- Restructure into reading tracks by audience rather than one linear doc
- Open with a plain-English paragraph and a "three ways to read this" menu
- Carry the pipeline/tech-stack sections to the engineer section intact
- Remove contradictory hard numbers; use a verifiable statement instead

## Release pressure / deadlines
Not specified