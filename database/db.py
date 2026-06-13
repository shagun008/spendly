import os
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash


def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it to your .env file or Railway Variables."
        )
    return psycopg2.connect(url)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feature_requests (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            page        TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'submitted',
            views       INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feature_votes (
            id          SERIAL PRIMARY KEY,
            feature_id  INTEGER NOT NULL REFERENCES feature_requests(id) ON DELETE CASCADE,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at  TIMESTAMP DEFAULT NOW(),
            UNIQUE (feature_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feature_views (
            id          SERIAL PRIMARY KEY,
            feature_id  INTEGER NOT NULL REFERENCES feature_requests(id) ON DELETE CASCADE,
            viewer_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            viewed_at   TIMESTAMP DEFAULT NOW(),
            UNIQUE (feature_id, viewer_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS features (
            id              SERIAL PRIMARY KEY,
            number          TEXT      UNIQUE NOT NULL,
            parent_number   TEXT,
            title           TEXT      NOT NULL,
            slug            TEXT      NOT NULL,
            type            TEXT      NOT NULL DEFAULT 'feature',
            description     TEXT,
            captured_at     TIMESTAMP,
            planned_at      TIMESTAMP,
            spec_at         TIMESTAMP,
            implemented_at  TIMESTAMP,
            tested_at       TIMESTAMP,
            reviewed_at     TIMESTAMP,
            shipped_at      TIMESTAMP,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
        (name, email, generate_password_hash(password)),
    )
    user_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def seed_db():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS count FROM users")
    if cur.fetchone()["count"] > 0:
        cur.close()
        conn.close()
        return

    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cur.fetchone()["id"]

    expenses = [
        (user_id, 12.50, "Food", "2026-04-01", "Lunch at cafe"),
        (user_id, 35.00, "Transport", "2026-04-02", "Monthly bus pass"),
        (user_id, 120.00, "Bills", "2026-04-03", "Electricity bill"),
        (user_id, 45.00, "Health", "2026-04-05", "Pharmacy"),
        (user_id, 20.00, "Entertainment", "2026-04-07", "Movie ticket"),
        (user_id, 89.99, "Shopping", "2026-04-09", "New shirt"),
        (user_id, 8.00, "Food", "2026-04-11", "Coffee and snack"),
        (user_id, 15.00, "Other", "2026-04-12", "Miscellaneous"),
    ]
    for expense in expenses:
        cur.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (%s, %s, %s, %s, %s)",
            expense,
        )

    conn.commit()
    cur.close()
    conn.close()


def seed_features():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS count FROM features")
    if cur.fetchone()["count"] > 0:
        cur.close()
        conn.close()
        return

    shipped = "2026-05-01 00:00:00"

    # columns: number, parent_number, title, slug, type, description,
    #          captured_at, planned_at, spec_at, implemented_at,
    #          tested_at, reviewed_at, shipped_at
    s = shipped  # all stage timestamps for backfilled shipped features
    rows = [
        (
            "01",
            None,
            "Database Setup",
            "database-setup",
            "feature",
            "Sets up the database with tables for users and expenses, along with helpers to initialise and seed it with sample data.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "02",
            None,
            "Registration",
            "registration",
            "feature",
            "Lets new visitors create a Spendly account with a name, email, and password. Includes input validation and secure password storage.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "03",
            None,
            "Login and Logout",
            "login-and-logout",
            "feature",
            "Lets registered users sign in to access their expenses and sign out when done. Sessions persist across page loads.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "04",
            None,
            "Profile Page",
            "profile-page",
            "feature",
            "Builds the profile page UI — user info, spending summary, transaction history, and category breakdown — using static placeholder data before the real database is wired up.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "05",
            None,
            "Backend Routes for Profile Page",
            "backend-routes-for-profile-page",
            "feature",
            "Connects the profile page to live database data so every user sees their own expenses, summary stats, and category breakdown instead of placeholder content.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "06",
            None,
            "Date Filter on Profile",
            "date-filter-profile",
            "feature",
            "Adds a date-range filter to the profile page so users can narrow their transaction history, stats, and category breakdown to a specific period. Includes quick presets like This Month and Last 3 Months.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "07",
            None,
            "Add Expense",
            "add-expense",
            "feature",
            "Lets logged-in users add a new expense by filling out a form with amount, category, date, and an optional description. The expense is saved immediately and appears on the profile page.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "08",
            None,
            "Edit Expense",
            "edit-expense",
            "feature",
            "Lets users correct a previously logged expense by editing its amount, category, date, or description through a pre-filled form. Only the owner of an expense can edit it.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "09",
            None,
            "Delete Expense",
            "delete-expense",
            "feature",
            "Lets users remove an expense they no longer need directly from the profile page. Deletion is permanent and restricted to the expense owner.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "10",
            None,
            "Mobile Nav",
            "mobile-nav",
            "feature",
            "Fixes navigation on mobile by adding a hamburger menu that reveals all nav links on small screens, replacing the previous layout where most links were hidden.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "11",
            None,
            "Feature Requests and Public Discovery",
            "feature-requests-and-public-discovery",
            "feature",
            "A public feature requests board where users can submit, browse, upvote, and discuss product improvement ideas across three releases.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "11-1",
            "11",
            "DB, Submission, and /features Page",
            "feature-requests-core",
            "release",
            "Introduces the core feature requests system — a public /features page where visitors can browse community ideas and logged-in users can submit, edit, and delete their own requests. View counts track engagement from the start.",
            None,
            None,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "11-2",
            "11",
            "Upvoting and Trending",
            "feature-requests-voting",
            "release",
            "Activates upvoting so users can express preference for any request they didn't submit themselves. Adds a Trending sort that surfaces the most engaged ideas by combining votes, views, and recency.",
            None,
            None,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "11-3",
            "11",
            "Home Page Latest Features Section",
            "home-latest-features-section",
            "release",
            "Adds a Latest Features section to the home page so every visitor can see recent community requests without leaving the landing page. A View All link drives them to the full /features page.",
            None,
            None,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "12",
            None,
            "Migration to Supabase",
            "migration-to-supabase",
            "feature",
            "Migrates the database layer from local SQLite to Supabase (PostgreSQL) so data persists across Railway deployments.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "12.1",
            "12",
            "Swap Database Layer",
            "supabase-db-layer",
            "release",
            "Swaps the local SQLite database for a hosted Supabase (PostgreSQL) instance so data survives server restarts and redeployments. All existing routes continue to work identically.",
            None,
            None,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "12.2",
            "12",
            "Local Data Migration",
            "local-data-migration-to-supabase",
            "release",
            "Migrates users and expenses from the local SQLite file into Supabase, preserving original IDs. The local file is kept as a backup throughout.",
            None,
            None,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "14",
            None,
            "Add README File",
            "add-readme-file",
            "feature",
            "Adds a README.md to the repository covering the project overview, tech stack, setup instructions, and routes.",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        (
            "15",
            None,
            "Developer Roadmap Page",
            "developer-roadmap-page",
            "feature",
            "A public /roadmap page giving full transparency into the Spendly feature pipeline — what's shipped, in progress, and planned.",
            "2026-06-07",
            "2026-06-07",
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "15.1",
            "15",
            "DB Layer + Pipeline Table",
            "roadmap-pipeline",
            "release",
            "Introduces a public /roadmap page with a pipeline table showing every feature's progress across dev stages, with a dot and date for each completed stage.",
            None,
            None,
            "2026-06-08",
            "2026-06-08",
            "2026-06-08",
            "2026-06-08",
            "2026-06-08",
        ),
        (
            "15.2",
            "15",
            "Expand-in-Place Detail View",
            "roadmap-detail",
            "release",
            "Makes the roadmap interactive — clicking any feature or release row expands a detail card inline showing its description. No page reload needed.",
            None,
            None,
            "2026-06-12",
            "2026-06-12",
            None,
            None,
            None,
        ),
        (
            "15.3",
            "15",
            "Harness Integration",
            "roadmap-harness-integration",
            "release",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    ]

    for row in rows:
        cur.execute(
            "INSERT INTO features"
            " (number, parent_number, title, slug, type, description,"
            "  captured_at, planned_at, spec_at, implemented_at,"
            "  tested_at, reviewed_at, shipped_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            row,
        )

    conn.commit()
    cur.close()
    conn.close()
