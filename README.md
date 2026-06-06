# Spendly

Spendly is a personal expense tracker — and a proof of concept for structured, governed AI-assisted software delivery.

---

## Why This Matters

**12 features · 15 spec releases · 0 unreviewed merges · 1 database migration handled as a governed pipeline feature**

This project is a proof of concept for AI-assisted software delivery — a repeatable pipeline that takes a feature from raw idea to production code with structured governance built into every step. Every feature was spec'd before it was built, tested before it was reviewed, and code-reviewed (in parallel, by two independent agents) before it was merged. Nothing shipped without passing through the full pipeline.

- 12 features shipped across 15 spec releases
- Every feature spec'd, tested, and code-reviewed before merge
- A full database migration (SQLite → Supabase PostgreSQL) handled end-to-end as a pipeline feature — not a manual one-off
- A repeatable system: raw idea to shipped pull request with zero untracked steps
- Infrastructure changes subject to the same governance as product features

---

## Live Demo / Screenshots

**[https://expense-tracker-production-635c.up.railway.app](https://expense-tracker-production-635c.up.railway.app)**

> Screenshots coming soon.

---

## About Spendly

Spendly solves a simple problem: tracking personal expenses without the overhead of a spreadsheet or the complexity of a full financial tool. Users log in, record what they spent, and see where their money goes — privately, quickly, and on any device. All amounts are displayed in ₹.

**Features:**

- **Auth** — register, log in, and log out with securely hashed passwords
- **Expenses** — add, edit, and delete expenses across 7 categories: Food, Transport, Bills, Health, Entertainment, Shopping, and Other
- **Profile** — view your full expense history with date-range filters and running totals
- **Analytics** — visual breakdown of spending by category and over time
- **Community** — submit feature requests, upvote ideas, and discover what other users are asking for; requests are ranked by votes and unique views
- **Mobile** — fully responsive at all screen sizes with a hamburger navigation menu

---

## The Development Harness

Every feature in this project was built through a structured AI-assisted pipeline — a set of commands that enforce a consistent workflow from capturing an idea to shipping reviewed, tested code, with no manual steps in between.

The pipeline follows this path for every feature:

```
User notes / screenshot
        │
        ▼
/capture-thoughts          (💡 Captured)
        │
        ▼
/plan-release              (📋 Planned)
        │
        ▼
/create-spec + Plan Mode   (🔧 In Progress)
        │
        ▼
/test-feature              (👀 In Review)
        │
        ▼
/code-review-feature       (security + quality agents, parallel)
        │
        ▼
/ship-feature              (✅ Shipped)
```

| Command | What it does |
|---|---|
| `/capture-thoughts` | Reads free-form notes and synthesises them into a structured feature brief |
| `/plan-release` | Decomposes a feature into release-sized units with a written plan |
| `/create-spec` | Writes a formal spec file and creates a dedicated feature branch |
| `/test-feature` | Generates pytest tests from the spec and runs them |
| `/code-review-feature` | Launches a security reviewer and a quality reviewer in parallel |
| `/ship-feature` | Commits, opens a pull request, squash-merges, and cleans up the branch |

The pipeline proved capable beyond routine feature work. When the project outgrew SQLite and required a migration to Supabase PostgreSQL — including data migration scripts, not just schema changes — that work was handled as two spec'd pipeline releases (12.1 and 12.2), subject to the same governance as every other feature. Infrastructure changes treated as first-class deliverables, not one-off tasks.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.x (Python 3) |
| Database | PostgreSQL via Supabase (psycopg2) |
| Auth | werkzeug.security |
| Frontend | Jinja2 templates, vanilla CSS, vanilla JS |
| Icons | Lucide (CDN) |
| Fonts | DM Serif Display + DM Sans (Google Fonts) |
| Testing | pytest + pytest-flask |
| Server | gunicorn |

---

## Feature Roadmap

| # | Feature | Status |
|---|---|---|
| 01 | Database Setup | ✅ Shipped |
| 02 | Registration | ✅ Shipped |
| 03 | Login and Logout | ✅ Shipped |
| 04 | Profile Page | ✅ Shipped |
| 05 | Backend Routes for Profile | ✅ Shipped |
| 06 | Date Filter on Profile | ✅ Shipped |
| 07 | Add Expense | ✅ Shipped |
| 08 | Edit Expense | ✅ Shipped |
| 09 | Delete Expense | ✅ Shipped |
| 10 | Mobile Nav | ✅ Shipped |
| 11 | Feature Requests and Public Discovery | ✅ Shipped |
| 12 | Migration to Supabase | ✅ Shipped |

Next feature: TBD
