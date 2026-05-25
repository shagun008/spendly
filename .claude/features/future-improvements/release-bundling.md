# Future Improvement: Release Bundling

## The idea
Allow multiple feature numbers (new features, enhancements, bug fixes) to be grouped
under a named release (e.g. `v2.0`, `sprint-14`) and shipped together as one coordinated
push to main, rather than each feature merging independently as it's completed.

## Example scenario
A release called `v2.0` might contain:
- Feature 11 — Budgeting Suite (new feature)
- Feature 10.1 — Enhanced User Profile (enhancement)
- Feature 13 — Bug fixes (bug fix)

All three would be developed on separate branches but held until all are ready,
then shipped together as one release.

## What the current workflow supports
- Multiple feature numbers can be created and developed in parallel ✅
- Each feature has its own branch, spec, tests, and PR ✅
- Features merge to main independently as they complete ✅

## What's missing
- A named release container that groups feature numbers together
- A way to assign feature numbers to a release (upfront, during planning, or at ship time)
- A release branch strategy (e.g. `release/v2.0` as an integration branch before main)
- A gate that holds all features until the full release is ready to ship
- Package-level status tracking in the registry

## Open questions to resolve before designing
1. Who decides which feature numbers belong to a release, and when?
   - Upfront before work starts?
   - Tagged during capture-thoughts or plan-release?
   - Grouped at ship time after features are built?

2. Should the release have its own git branch?
   - Yes — `release/v2.0` acts as an integration branch; features merge into it, not main
   - No — the release is a tracking concept only; features still merge to main independently

## Commands likely needed
- `/create-release` — name a release and assign feature numbers to it
- `/ship-release` — merge all features in a release together and push to main
- Updates to `/ship-feature` — merge to release branch instead of main when a release bundle is active
