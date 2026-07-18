---
number: 22
title: Readme Platform Revamp
type: new-feature
parent: null
status: planned
releases: 1
created: 2026-07-18
---

# Release Plan: Readme Platform Revamp

## Roadmap description
Rewrite the project README so it explains the Oxos Platform and Spendly clearly for executives, business readers, and engineers alike.

## Summary
The project has grown from a single "Spendly expense tracker" into the Oxos Platform — a dashboard that hosts Spendly as one business application and showcases engineering best practices and data systems. The current README still describes a single app and is engineer/process-centric, with internally inconsistent feature counts. This release rewrites README.md to lead with the platform framing, serve three reading tracks (executives, business/product, engineers), and stay understandable by non-technical readers — while preserving the engineer-grade pipeline diagram and tech-stack content. Shipped as a single release since it is a self-contained documentation change with no code, routes, or schema impact.

## Releases

### Release 1 — Readme Platform Revamp (single release)
- **Scope:** Rewrite README.md: add plain-English intro leading with "platform, not a single app" framing; add a "three ways to read this" menu (executives / business / engineers); write an executive 30-second version, a business/product reader section, and preserve the engineer section (tech stack, pipeline diagram, command table); fix inconsistent feature counts; keep the live-demo and roadmap sections accurate and honest (Oxos dashboard is authenticated; public homepage is a future feature).
- **Spec slug:** readme-platform-revamp
- **Spec arg:** `22.1 readme-platform-revamp`
- **Depends on:** nothing
- **Risk:** low

## Deferred / Out of scope
- None. The README rewrite is self-contained.

## Open questions
- None.
