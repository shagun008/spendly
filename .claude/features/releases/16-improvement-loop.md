---
number: 16
title: Post-Review Improvement Loop
type: new-feature
parent: null
status: planned
releases: 1
created: 2026-06-21
---

# Release Plan: Post-Review Improvement Loop

## Roadmap description
A structured improvement cycle that catches test failures and code review issues, fixes root causes, and prevents the same problems from recurring.

## Summary
The Post-Review Improvement Loop is a developer workflow skill that activates when tests fail, code review finds issues, or quality gates aren't met. Instead of making ad-hoc fixes, it follows a disciplined 5-phase workflow — Gather Context, Root Cause Analysis, Architectural Assessment, Generate Improvement Plan, and Implementation + Validation + Learning Capture — to ensure every fix addresses the root cause and leaves the codebase healthier than before. A decision framework (Option A/B/C) ensures the smallest sufficient change is made. This is a single-release feature: one new `/improvement-loop` slash command plus hooks into `/test-feature` and `/code-review-feature` that auto-trigger the loop as a parallel subagent when failures are detected.

## Releases

### Release 1 — Improvement Loop Skill
- **Scope:** New `/improvement-loop` slash command implementing the full 5-phase workflow. Decision framework choosing between minimal fix (A), fix+improvement (B), or fix+architectural improvement (C). Success criteria and failure conditions from the thought file. Hook into `/test-feature` and `/code-review-feature` to auto-trigger the loop when tests fail or review finds issues. Auto-trigger spawns a **parallel subagent** (via the `Agent` tool) that runs the full improvement loop independently — the parent command does not block. Manual invocation via `/improvement-loop <feature_number>` also supported. Learning capture writes to a `.claude/features/improvements/` log.
- **Spec slug:** improvement-loop
- **Spec arg:** `16.1 improvement-loop`
- **Depends on:** nothing
- **Risk:** low

## Deferred / Out of scope
- Dashboard UI for improvement history — the learning capture log is stored as markdown files; surfacing them in a web UI is a future enhancement.
- Automatic rollback on failed improvement — the loop validates before declaring success, but does not implement automatic git rollback.

## Open questions
- None remaining — auto-trigger uses a parallel subagent to avoid blocking the parent command, which is the right call given the multi-phase nature of the loop.
