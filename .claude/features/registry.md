# Feature Registry

This file is the single source of truth for feature numbering, status, and traceability.
It is updated automatically by `/capture-thoughts`, `/plan-release`, `/create-spec`,
`/implement-feature`, `/test-feature`, `/code-review-feature`, and `/ship-feature`.

## Status Legend

| Symbol | Meaning |
|--------|---------|
| 💡 Captured | Processed thought written, ready for /plan-release |
| 📋 Planned | Release plan written, ready for /create-spec |
| 📝 Spec'd | Spec created, ready for /implement-feature |
| 🔧 In Progress | Implementation underway |
| 👀 In Review | Tests written and/or under code review |
| ✅ Shipped | Merged to main |

## Registry

Feature rows show the least-complete release status.
Release sub-rows (indented with →) show individual release status.

| Number | Title | Type | Parent | Status | Specs |
|--------|-------|------|--------|--------|-------|
| 01 | Database Setup | feature | — | ✅ Shipped | 1 release |
| 01.1 | → Database Setup | release | 01 | ✅ Shipped | 01-database-setup |
| 02 | Registration | feature | — | ✅ Shipped | 1 release |
| 02.1 | → Registration | release | 02 | ✅ Shipped | 02-registration |
| 03 | Login and Logout | feature | — | ✅ Shipped | 1 release |
| 03.1 | → Login and Logout | release | 03 | ✅ Shipped | 03-login-and-logout |
| 04 | Profile Page | feature | — | ✅ Shipped | 1 release |
| 04.1 | → Profile Page | release | 04 | ✅ Shipped | 04-profile-page |
| 05 | Backend Routes for Profile Page | feature | — | ✅ Shipped | 1 release |
| 05.1 | → Backend Routes for Profile Page | release | 05 | ✅ Shipped | 05-backend-routes-for-profile-page |
| 06 | Date Filter on Profile | feature | — | ✅ Shipped | 1 release |
| 06.1 | → Date Filter on Profile | release | 06 | ✅ Shipped | 06-date-filter-profile |
| 07 | Add Expense | feature | — | ✅ Shipped | 1 release |
| 07.1 | → Add Expense | release | 07 | ✅ Shipped | 07-add-expense |
| 08 | Edit Expense | feature | — | ✅ Shipped | 1 release |
| 08.1 | → Edit Expense | release | 08 | ✅ Shipped | 08-edit-expense |
| 09 | Delete Expense | feature | — | ✅ Shipped | 1 release |
| 09.1 | → Delete Expense | release | 09 | ✅ Shipped | 09-delete-expense |
| 10 | Mobile Nav | feature | — | ✅ Shipped | 1 release |
| 10.1 | → Mobile Nav | release | 10 | ✅ Shipped | 10-mobile-nav |
| 11 | Feature Requests Page and Public Feature Discovery | new-feature | — | ✅ Shipped | 3 releases planned |
| 11.1 | → DB, Submission, and /features Page (Core) | release | 11 | ✅ Shipped | 11-1-feature-requests-core.md |
| 11.2 | → Upvoting and Trending | release | 11 | ✅ Shipped | 11-2-feature-requests-voting.md |
| 11.3 | → Home Page "Latest Features" Section | release | 11 | ✅ Shipped | 11-3-home-latest-features-section.md |
| 12 | Migration to Supabase | new-feature | — | ✅ Shipped | 2 releases planned |
| 12.1 | → Swap Database Layer | release | 12 | ✅ Shipped | 12.1-supabase-db-layer.md |
| 12.2 | → Local Data Migration | release | 12 | ✅ Shipped | 12.2-local-data-migration-to-supabase.md |
| 14 | Add README File | new-feature | — | ✅ Shipped | 1 release |
| 14.1 | → Add README File | release | 14 | ✅ Shipped | 14-add-readme-file |
| 15 | Developer Roadmap Page | new-feature | — | 🔧 In Progress | 7 releases planned |
| 15.1 | → DB Layer + Pipeline Table | release | 15 | ✅ Shipped | 15.1-roadmap-pipeline.md |
| 15.2 | → Expand-in-Place Detail View | release | 15 | ✅ Shipped | 15.2-roadmap-detail.md |
| 15.3 | → Harness Integration (Live Updates) | release | 15 | ✅ Shipped | 15.3-harness-integration-live-updates.md |
| 15.4 | → Release-Level Type Classification | release | 15 | ✅ Shipped | 15.4-release-type-classification.md |
| 15.5 | → Release Notes Modal | release | 15 | ✅ Shipped | 15.5-release-notes-modal.md |
| 15.6 | → Roadmap Stage Metrics | release | 15 | 💡 Captured | — |
| 15.7 | → Grouping Foundational Features | release | 15 | ✅ Shipped | 15.7-grouping-foundational-features.md |
| 16 | Post-Review Improvement Loop | new-feature | — | ✅ Shipped | 1 release |
| 16.1 | → Improvement Loop Skill | release | 16 | ✅ Shipped | 16.1-improvement-loop.md |
| 17 | User Profile Page Updates | new-feature | — | ✅ Shipped | 3 releases planned |
| 17.1 | → Change Password | release | 17 | ✅ Shipped | 17.1-change-password.md |
| 17.2 | → Quick Add Expense Modal | release | 17 | ✅ Shipped | 17.2-quick-add-expense-modal.md |
| 17.3 | → Embedded Analytics Dashboard | release | 17 | ✅ Shipped | 17.3-embedded-analytics-dashboard.md |
| 18 | Quick Edit Expense from Profile | new-feature | — | ✅ Shipped | 1 release |
| 18.1 | → Quick Edit Expense Modal | release | 18 | ✅ Shipped | 18.1-quick-edit-expense-modal.md |
| 19 | Profile Layout and Navbar Updates | new-feature | — | ✅ Shipped | 2 releases planned |
| 19.1 | → Responsive Profile Layout | release | 19 | ✅ Shipped | 19.1-responsive-profile-layout.md |
| 19.2 | → Navbar User Menu | release | 19 | ✅ Shipped | 19.2-navbar-user-menu.md |
| 20 | Profile Card Layout & Dropdown Updates | new-feature | — | ✅ Shipped | 1 release planned |
| 20.1 | → Profile Card Layout & Dropdown Updates | release | 20 | ✅ Shipped | 20.1-profile-card-layout-dropdown-updates.md |
| 21 | Oxos Profile Page | new-feature | — | ✅ Shipped | 2 releases |
| 21.1 | → Oxos Profile Page MVP | release | 21 | ✅ Shipped | 21.1-oxos-profile-page-mvp.md |
| 21.2 | → Context Section with Card Flip | release | 21 | 👀 In Review | 21.2-oxos-context-flip.md |

## Numbering Rules

**New features** use the next integer: 11, 12, 13 …

**Enhancements** use the parent number with a hyphen-separated sub-number:
- 10-1, 10-2, 10-3 … for enhancements to feature 10

**Multi-release features** use parent + release number (hyphen-separated):
- 11-1, 11-2 … for releases of feature 11

Sub-numbers increment independently per parent.
Feature row status always reflects the least-complete release.
