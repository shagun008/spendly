# Oxos Platform — with Spendly inside

> **It's now a platform, not just an app.**
> Spendly — the personal expense tracker — is one of the business applications living inside the **Oxos Platform**. Open the app and you land on a dashboard that shows what the platform can do, the data systems behind it, and what the team has learned building it. Spendly is the first (and currently flagship) application on that dashboard.

---

## 👋 Start here — what is this, in plain English?

If you've never seen this project before, here's the whole story in a paragraph.

**Oxos** is a small web dashboard. Its first real application is **Spendly**, a private expense tracker: you log in, type in what you spent (groceries, transport, bills, and so on), and the app shows you where your money goes — all in ₹. Over time, the dashboard grew from "just the expense tracker" into a *platform*: a home page that showcases business capabilities, the underlying data systems (like Supabase), and a set of engineering best-practices the project is built on. Think of it like a launchpad: Spendly is the first rocket sitting on it, and more can be added later.

Everything is private to you. You register with an email and password, and only you can see your own expenses.

**Three ways to read the rest of this document:**

- 🏢 **[For executives / decision-makers](#-for-executives-the-30-second-version)** — why this project exists and what it proves
- 💼 **[For the business / product reader](#-for-the-business--product-reader)** — what you can actually do with it today
- 🛠️ **[For engineers / builders](#-for-engineers--builders)** — how it's built and how features get shipped

---

## 🏢 For executives: the 30-second version

**What it is:** A working proof-of-concept that an AI-assisted team can ship enterprise applications through a *governed, consistent pipeline* — where every change is written down as a spec, tested, and reviewed by multiple independent autonomous agents before it ever reaches production.

**Why it matters:** Most AI-assisted coding produces code. This project produces *process*. Every feature — even a database migration — flows through the same disciplined steps, and the project's own public roadmap page is generated *automatically* from the pipeline's progress. There is no manual "remember to update the status doc." The system writes its own history.

**What's been proven:**
- 20+ features shipped through the full pipeline, every one spec'd → tested → reviewed → merged.
- A complete move to a more scalable cloud database, handled as two governed pipeline releases — not a risky manual switch.
- A self-documenting system: the public `/roadmap` page reflects real pipeline state at all times.

**Bottom line:** This is less a product and more a *demonstration that disciplined AI software delivery can be built, observed, and trusted.*

---

## 💼 For the business / product reader

**What can I use today?**

| Capability | What it means for you |
|---|---|
| **Track expenses** | Log what you spend across 7 categories — Food, Transport, Bills, Health, Entertainment, Shopping, Other. |
| **See the picture** | A profile page shows your full history, filters by date range, and displays charts of where your money goes. |
| **Stay private & secure** | Register with email + password (hashed, never stored in plain text). Your data is yours alone. |
| **Have a say** | A community feature lets users submit and vote on ideas for what to build next. |
| **A dashboard home** | The landing page is the Oxos Platform: a clean view of business capabilities, the data systems behind them, and curated learnings. |

**Who is it for right now?** Individuals who want a lightweight, private way to track personal spending — and anyone curious to see a well-run AI-assisted engineering project from the inside.

**What's next?** A public-facing Oxos homepage is planned (separate from the current authenticated dashboard). The platform is deliberately designed so more business applications can be added alongside Spendly.

---

## 🛠️ For engineers / builders

This section is the technical core. Skip up if you're not here for the build details.

### Tech Stack

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

### The Development Harness

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

## Live Demo

**[https://expense-tracker-production-635c.up.railway.app](https://expense-tracker-production-635c.up.railway.app)**

> Note: the Oxos Platform dashboard is part of the authenticated experience — you'll create an account (or log in) to see it. A public marketing homepage is planned for a future release.

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
| 16 | Post-Review Improvement Loop | 1 | ✅ Shipped |
| 17 | User Profile Page Updates | 3 shipped | ✅ Shipped |
| 18 | Quick Edit Expense from Profile | 1 | ✅ Shipped |
| 19 | Profile Layout and Navbar Updates | 2 shipped | ✅ Shipped |
| 20 | Profile Card Layout & Dropdown Updates | 1 shipped | ✅ Shipped |
| 21 | Oxos Profile Page | 2 shipped | ✅ Shipped |

Next up: **15.6 — Roadmap Stage Metrics**
