# Spendly — CLAUDE.md

Spendly is a personal expense tracking web app built with Flask and SQLite.
This file is the single source of truth for project conventions, schema, and roadmap.
Read it before writing any code or spec.

---

## Tech Stack

- **Backend:** Python 3 / Flask
- **Database:** SQLite via `sqlite3` (no ORM)
- **Auth:** `werkzeug.security` for password hashing
- **Frontend:** Jinja2 templates, vanilla CSS, vanilla JS
- **Icons:** Lucide (loaded via CDN in `base.html`)
- **Fonts:** DM Serif Display (headings), DM Sans (body) via Google Fonts
- **Testing:** pytest + pytest-flask
- **Server:** gunicorn (production via `Procfile`)

---

## Project Structure

```
app.py                  # All Flask routes
database/
  db.py                 # Connection helper, init_db, seed_db, create_user, get_user_by_email
  queries.py            # All query helpers (reads + mutations)
templates/              # Jinja2 templates (all extend base.html)
static/
  css/                  # One CSS file per page + style.css (global)
  js/main.js            # Shared JS (hamburger menu)
tests/                  # pytest test files, one per spec step
.claude/
  specs/                # Feature specs (one per step)
  commands/             # Slash command definitions
  agents/               # Subagent definitions
```

---

## Database Schema

**Table: `users`**

| Column          | Type    | Constraints                        |
|-----------------|---------|------------------------------------|
| id              | INTEGER | PRIMARY KEY AUTOINCREMENT          |
| name            | TEXT    | NOT NULL                           |
| email           | TEXT    | UNIQUE NOT NULL                    |
| password_hash   | TEXT    | NOT NULL                           |
| created_at      | TEXT    | DEFAULT (datetime('now'))          |

**Table: `expenses`**

| Column      | Type    | Constraints                            |
|-------------|---------|----------------------------------------|
| id          | INTEGER | PRIMARY KEY AUTOINCREMENT              |
| user_id     | INTEGER | NOT NULL REFERENCES users(id)          |
| amount      | REAL    | NOT NULL                               |
| category    | TEXT    | NOT NULL                               |
| date        | TEXT    | NOT NULL (format: YYYY-MM-DD)          |
| description | TEXT    | nullable                               |
| created_at  | TEXT    | DEFAULT (datetime('now'))              |

**Valid categories** (defined in `app.py` as `VALID_CATEGORIES`):
`Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other`

---

## Existing Routes

| Method | Path                      | Function              | Access      |
|--------|---------------------------|-----------------------|-------------|
| GET    | `/`                       | `landing`             | public      |
| GET    | `/terms`                  | `terms`               | public      |
| GET    | `/privacy`                | `privacy`             | public      |
| GET/POST | `/register`             | `register`            | public      |
| GET/POST | `/login`               | `login`               | public      |
| GET    | `/logout`                 | `logout`              | logged-in   |
| GET    | `/profile`                | `profile`             | logged-in   |
| GET    | `/analytics`              | `analytics`           | logged-in   |
| GET/POST | `/expenses/add`         | `add_expense`         | logged-in   |
| GET/POST | `/expenses/<id>/edit`   | `edit_expense`        | logged-in   |
| POST   | `/expenses/<id>/delete`   | `delete_expense_route`| logged-in   |

---

## CSS Variables

Always use these variables — never hardcode hex values.

```css
--ink              /* #0f0f0f  — primary text */
--ink-soft         /* #2d2d2d  — secondary text */
--ink-muted        /* #6b6b6b  — muted text */
--ink-faint        /* #a0a0a0  — placeholder text */
--paper            /* #f7f6f3  — page background */
--paper-warm       /* #f0ede6  — section background */
--paper-card       /* #ffffff  — card background */
--accent           /* #1a472a  — primary accent (green) */
--accent-light     /* #e8f0eb  — accent tint */
--accent-2         /* #c17f24  — secondary accent (amber) */
--accent-2-light   /* #fdf3e3  — secondary accent tint */
--danger           /* #c0392b  — error/delete */
--danger-light     /* #fdecea  — error background */
--border           /* #e4e1da  — standard border */
--border-soft      /* #eeebe4  — subtle border */
--font-display     /* DM Serif Display */
--font-body        /* DM Sans */
--radius-sm        /* 6px */
--radius-md        /* 12px */
--radius-lg        /* 20px */
--nav-height       /* 60px */
--max-width        /* 1200px */
--auth-width       /* 440px */
```

**Responsive breakpoints:**
- `@media (max-width: 900px)` — tablet
- `@media (max-width: 600px)` — mobile (hamburger nav activates here)

---

## Implementation Rules

These rules apply to every feature. No exceptions.

- **No SQLAlchemy or ORMs** — use raw `sqlite3` queries only
- **Parameterised queries only** — never interpolate user data into SQL strings
- **Passwords hashed with werkzeug** — `generate_password_hash` / `check_password_hash`
- **Use CSS variables** — never hardcode hex values
- **All templates extend `base.html`** — use `{% extends "base.html" %}`
- **Auth guard on every protected route** — check `session.get("user_id")` and redirect to `/login` if missing
- **Ownership check on all expense mutations** — queries must include `AND user_id = ?` to prevent cross-user access
- **Flash messages for all user-facing outcomes** — success and error states
- **Currency displayed in ₹** — format amounts as `₹{amount:,.2f}`
- **Dates stored as `YYYY-MM-DD` strings** — validate with `datetime.strptime(value, "%Y-%m-%d")`

---

## Testing Conventions

- One test file per spec step: `tests/test_<step_number>-<feature_slug>.py`
- Use `pytest-flask` fixtures (`client`, `app`)
- Tests must not share state — each test sets up and tears down its own data
- Test both the happy path and key error cases (missing fields, bad input, unauthorised access)

---

## Feature Roadmap

| Step | Feature                        | Status    |
|------|--------------------------------|-----------|
| 01   | Database setup                 | ✅ Done   |
| 02   | Registration                   | ✅ Done   |
| 03   | Login and logout               | ✅ Done   |
| 04   | Profile page                   | ✅ Done   |
| 05   | Backend routes for profile     | ✅ Done   |
| 06   | Date filter on profile         | ✅ Done   |
| 07   | Add expense                    | ✅ Done   |
| 08   | Edit expense                   | ✅ Done   |
| 09   | Delete expense                 | ✅ Done   |
| 10   | Mobile nav                     | ✅ Done   |

Next step to implement: **11**
