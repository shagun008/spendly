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

    # columns: number, parent_number, title, slug, type,
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
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        ("02", None, "Registration", "registration", "feature", s, s, s, s, s, s, s),
        (
            "03",
            None,
            "Login and Logout",
            "login-and-logout",
            "feature",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        ("04", None, "Profile Page", "profile-page", "feature", s, s, s, s, s, s, s),
        (
            "05",
            None,
            "Backend Routes for Profile Page",
            "backend-routes-for-profile-page",
            "feature",
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
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        ("07", None, "Add Expense", "add-expense", "feature", s, s, s, s, s, s, s),
        ("08", None, "Edit Expense", "edit-expense", "feature", s, s, s, s, s, s, s),
        (
            "09",
            None,
            "Delete Expense",
            "delete-expense",
            "feature",
            s,
            s,
            s,
            s,
            s,
            s,
            s,
        ),
        ("10", None, "Mobile Nav", "mobile-nav", "feature", s, s, s, s, s, s, s),
        (
            "11",
            None,
            "Feature Requests and Public Discovery",
            "feature-requests-and-public-discovery",
            "feature",
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
            s,
            s,
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
            s,
            s,
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
            s,
            s,
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
            s,
            s,
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
            s,
            s,
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
            None,
            None,
            "2026-06-08",
            None,
            None,
            None,
            None,
        ),
        (
            "15.2",
            "15",
            "Expand-in-Place Detail View",
            "roadmap-detail",
            "release",
            None,
            None,
            None,
            None,
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
        ),
    ]

    for row in rows:
        cur.execute(
            "INSERT INTO features"
            " (number, parent_number, title, slug, type,"
            "  captured_at, planned_at, spec_at, implemented_at,"
            "  tested_at, reviewed_at, shipped_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            row,
        )

    conn.commit()
    cur.close()
    conn.close()
