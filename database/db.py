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

    cur.execute("""
        ALTER TABLE features ADD COLUMN IF NOT EXISTS deployed_at TIMESTAMP
    """)

    cur.execute("""
        ALTER TABLE features ADD COLUMN IF NOT EXISTS release_subtype TEXT
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

    # AUTO-GENERATED by /ship-feature Step 9d — do not edit by hand.
    # columns: number, parent_number, title, slug, type, release_subtype, description,
    #          captured_at, planned_at, spec_at, implemented_at,
    #          tested_at, reviewed_at, shipped_at
    rows = [
        (
            '01',
            None,
            'Database Setup',
            'database-setup',
            'feature',
            None,
            'Sets up the database with tables for users and expenses, along with helpers to initialise and seed it with sample data.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '02',
            None,
            'Registration',
            'registration',
            'feature',
            None,
            'Lets new visitors create a Spendly account with a name, email, and password. Includes input validation and secure password storage.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '03',
            None,
            'Login and Logout',
            'login-and-logout',
            'feature',
            None,
            'Lets registered users sign in to access their expenses and sign out when done. Sessions persist across page loads.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '04',
            None,
            'Profile Page',
            'profile-page',
            'feature',
            None,
            'Builds the profile page UI — user info, spending summary, transaction history, and category breakdown — using static placeholder data before the real database is wired up.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '05',
            None,
            'Backend Routes for Profile Page',
            'backend-routes-for-profile-page',
            'feature',
            None,
            'Connects the profile page to live database data so every user sees their own expenses, summary stats, and category breakdown instead of placeholder content.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '06',
            None,
            'Date Filter on Profile',
            'date-filter-profile',
            'feature',
            None,
            'Adds a date-range filter to the profile page so users can narrow their transaction history, stats, and category breakdown to a specific period. Includes quick presets like This Month and Last 3 Months.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '07',
            None,
            'Add Expense',
            'add-expense',
            'feature',
            None,
            'Lets logged-in users add a new expense by filling out a form with amount, category, date, and an optional description. The expense is saved immediately and appears on the profile page.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '08',
            None,
            'Edit Expense',
            'edit-expense',
            'feature',
            None,
            'Lets users correct a previously logged expense by editing its amount, category, date, or description through a pre-filled form. Only the owner of an expense can edit it.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '09',
            None,
            'Delete Expense',
            'delete-expense',
            'feature',
            None,
            'Lets users remove an expense they no longer need directly from the profile page. Deletion is permanent and restricted to the expense owner.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '10',
            None,
            'Mobile Nav',
            'mobile-nav',
            'feature',
            None,
            'Fixes navigation on mobile by adding a hamburger menu that reveals all nav links on small screens, replacing the previous layout where most links were hidden.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '11',
            None,
            'Feature Requests and Public Discovery',
            'feature-requests-and-public-discovery',
            'feature',
            None,
            'A public feature requests board where users can submit, browse, upvote, and discuss product improvement ideas across three releases.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '11-1',
            '11',
            'DB, Submission, and /features Page',
            'feature-requests-core',
            'release',
            'new-feature',
            'Introduces the core feature requests system — a public /features page where visitors can browse community ideas and logged-in users can submit, edit, and delete their own requests. View counts track engagement from the start.',
            None,
            None,
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '11-2',
            '11',
            'Upvoting and Trending',
            'feature-requests-voting',
            'release',
            'enhancement',
            "Activates upvoting so users can express preference for any request they didn't submit themselves. Adds a Trending sort that surfaces the most engaged ideas by combining votes, views, and recency.",
            None,
            None,
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '11-3',
            '11',
            'Home Page Latest Features Section',
            'home-latest-features-section',
            'release',
            'enhancement',
            'Adds a Latest Features section to the home page so every visitor can see recent community requests without leaving the landing page. A View All link drives them to the full /features page.',
            None,
            None,
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '12',
            None,
            'Migration to Supabase',
            'migration-to-supabase',
            'feature',
            None,
            'Migrates the database layer from local SQLite to Supabase (PostgreSQL) so data persists across Railway deployments.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '12.1',
            '12',
            'Swap Database Layer',
            'supabase-db-layer',
            'release',
            'new-feature',
            'Swaps the local SQLite database for a hosted Supabase (PostgreSQL) instance so data survives server restarts and redeployments. All existing routes continue to work identically.',
            None,
            None,
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '12.2',
            '12',
            'Local Data Migration',
            'local-data-migration-to-supabase',
            'release',
            'new-feature',
            'Migrates users and expenses from the local SQLite file into Supabase, preserving original IDs. The local file is kept as a backup throughout.',
            None,
            None,
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '14',
            None,
            'Add README File',
            'add-readme-file',
            'feature',
            None,
            'Adds a README.md to the repository covering the project overview, tech stack, setup instructions, and routes.',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
            '2026-05-01 00:00:00',
        ),
        (
            '15',
            None,
            'Developer Roadmap Page',
            'developer-roadmap-page',
            'feature',
            None,
            "A public /roadmap page giving full transparency into the Spendly feature pipeline — what's shipped, in progress, and planned.",
            '2026-06-07 00:00:00',
            '2026-06-07 00:00:00',
            None,
            None,
            None,
            None,
            None,
        ),
        (
            '15.1',
            '15',
            'DB Layer + Pipeline Table',
            'roadmap-pipeline',
            'release',
            'new-feature',
            "Introduces a public /roadmap page with a pipeline table showing every feature's progress across dev stages, with a dot and date for each completed stage.",
            None,
            None,
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
        ),
        (
            '15.2',
            '15',
            'Expand-in-Place Detail View',
            'roadmap-detail',
            'release',
            'enhancement',
            'Makes the roadmap interactive — clicking any feature or release row expands a detail card inline showing its description. No page reload needed.',
            None,
            None,
            '2026-06-12 00:00:00',
            '2026-06-12 00:00:00',
            '2026-06-13 05:41:00',
            '2026-06-13 05:41:00',
            '2026-06-13 05:41:00',
        ),
        (
            '15.3',
            '15',
            'Harness Integration',
            'roadmap-harness-integration',
            'release',
            'enhancement',
            None,
            None,
            None,
            '2026-06-13 14:00:00',
            '2026-06-13 15:00:00',
            '2026-06-13 16:00:00',
            '2026-06-13 17:16:00',
            '2026-06-13 17:16:00',
        ),
        (
            '15.4',
            '15',
            'Release-Level Type Classification',
            'release-type-classification',
            'release',
            'enhancement',
            None,
            None,
            None,
            '2026-06-13 18:00:00',
            '2026-06-13 18:30:00',
            '2026-06-13 19:16:04.532115',
            None,
            None,
        ),
        (
            '15.5',
            '15',
            'Roadmap Stage Metrics',
            'roadmap-stage-metrics',
            'release',
            'enhancement',
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
    ]

    for row in rows:
        cur.execute(
            "INSERT INTO features"
            " (number, parent_number, title, slug, type, release_subtype, description,"
            "  captured_at, planned_at, spec_at, implemented_at,"
            "  tested_at, reviewed_at, shipped_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            row,
        )

    conn.commit()
    cur.close()
    conn.close()
