# Spendly

Spendly is a personal expense tracker — and a proof of concept for structured, governed AI-assisted software delivery.

---

## Why This Matters

**14 features · 20 spec releases · 0 unreviewed merges · the harness writes its own progress to the live roadmap**

This project is a proof of concept for AI-assisted software delivery — a repeatable pipeline that takes a feature from raw idea to production code with structured governance built into every step. Every feature was spec'd before it was built, tested before it was reviewed, and code-reviewed (in parallel, by two independent agents) before it was merged. Nothing shipped without passing through the full pipeline.

- 15 features shipped across 21 spec releases
- Every feature spec'd, tested, and code-reviewed before merge
- The harness is self-documenting: every pipeline command (`/capture-thoughts`, `/plan-release`, `/create-spec`, `/implement-feature`, `/test-feature`, `/code-review-feature`, `/ship-feature`, `/deploy`) writes a timestamp to the live database — so the public `/roadmap` page reflects the real pipeline state automatically, with no manual updates
- A full database migration (SQLite → Supabase PostgreSQL) handled end-to-end as two spec'd pipeline releases — not a manual one-off
- A repeatable system: raw idea to shipped pull request with zero untracked steps

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
- **Profile** — view your full expense history with date-range filters and running totals; add or edit expenses inline via quick modals; change your password securely from the profile card; analytics and profile card displayed side-by-side on desktop
- **Analytics** — visual breakdown of spending by category and over time, embedded in the Profile page with switchable chart views (trends, categories, monthly comparison)
- **Community** — submit feature requests, upvote ideas, and discover what other users are asking for; requests are ranked by votes and unique views
- **Roadmap** — public `/roadmap` page showing the full feature pipeline; each stage shown as a dot with a date/time tooltip on hover; click any feature row to expand an inline detail card with its description and release type badge (New Feature / Enhancement / Bug Fix); the page is kept live automatically as the harness runs
- **Mobile** — fully responsive at all screen sizes with a hamburger navigation menu; logged-in users see a user menu on desktop with My Profile, Change Password, and Log Out, and a stacked user menu inside the hamburger drawer on mobile

---

## The Development Harness

Every feature in this project was built through a structured AI-assisted pipeline — a set of commands that enforce a consistent workflow from capturing an idea to shipping reviewed, tested code, with no manual steps in between.

The pipeline follows this path for every feature:

```
User notes / screenshot
        │
        ▼
/capture-thoughts          (💡 Captured)   ← stamps captured_at in DB
        │
        ▼
/plan-release              (📋 Planned)    ← stamps planned_at in DB
        │
        ▼
/create-spec + Plan Mode   (📝 Spec'd)     ← stamps spec_at in DB
        │
        ▼
/implement-feature         (🔧 In Progress) ← stamps implemented_at in DB
        │
        ▼
/test-feature              (👀 In Review)  ← stamps tested_at in DB
        │
        ▼
/code-review-feature       (security + quality agents, parallel)
        │                                  ← stamps reviewed_at in DB
        ▼
/ship-feature              (✅ Shipped)    ← stamps shipped_at in DB
        │
        ▼
/deploy                                    ← stamps deployed_at in DB
```

Every stage timestamp lands in the `features` table. The public `/roadmap` page reads directly from that table — so it reflects the true pipeline state at all times, with no manual updates.

| Command | What it does |
|---|---|
| `/capture-thoughts` | Reads free-form notes and synthesises them into a structured feature brief |
| `/plan-release` | Decomposes a feature into release-sized units with a written plan |
| `/create-spec` | Writes a formal spec file and creates a dedicated feature branch |
| `/implement-feature` | Reads the spec, plans implementation, and executes it |
| `/test-feature` | Generates pytest tests from the spec and runs them |
| `/code-review-feature` | Launches a security reviewer and a quality reviewer in parallel |
| `/ship-feature` | Commits, opens a pull request, squash-merges, and cleans up the branch |
| `/deploy` | Deploys the current main branch to Railway |
| `/dev` | Interactive workflow picker — shows the next recommended step with live registry context |
| `/status` | Reads the live DB and prints the current status of every feature and release |
| `/improvement-loop` | Runs a structured 5-phase improvement cycle after any pipeline stage; auto-detects the trigger stage from conversation context; captures learnings to log |

The pipeline proved capable well beyond routine feature work. When the project outgrew SQLite and required a migration to Supabase PostgreSQL — including data migration scripts, not just schema changes — that work was handled as two spec'd pipeline releases (12.1 and 12.2), subject to the same governance as every other feature. Infrastructure changes treated as first-class deliverables, not one-off tasks.

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

| # | Feature | Releases | Status |
|---|---|---|---|
| 01 | Database Setup | 1 | ✅ Shipped |
| 02 | Registration | 1 | ✅ Shipped |
| 03 | Login and Logout | 1 | ✅ Shipped |
| 04 | Profile Page | 1 | ✅ Shipped |
| 05 | Backend Routes for Profile | 1 | ✅ Shipped |
| 06 | Date Filter on Profile | 1 | ✅ Shipped |
| 07 | Add Expense | 1 | ✅ Shipped |
| 08 | Edit Expense | 1 | ✅ Shipped |
| 09 | Delete Expense | 1 | ✅ Shipped |
| 10 | Mobile Nav | 1 | ✅ Shipped |
| 11 | Feature Requests and Public Discovery | 3 | ✅ Shipped |
| 12 | Migration to Supabase | 2 | ✅ Shipped |
| 14 | Add README File | 1 | ✅ Shipped |
| 15 | Developer Roadmap Page | 7 shipped, 1 captured | 🔧 In Progress |
| 17 | User Profile Page Updates | 3 shipped | ✅ Shipped |
| 18 | Quick Edit Expense from Profile | 1 | ✅ Shipped |
| 19 | Profile Layout and Navbar Updates | 2 shipped | ✅ Shipped |

Next up: **15.6 — Roadmap Stage Metrics**
