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

    cur.execute("""
        ALTER TABLE features ADD COLUMN IF NOT EXISTS test_report TEXT
    """)

    cur.execute("""
        ALTER TABLE features ADD COLUMN IF NOT EXISTS review_report TEXT
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
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
            '2026-06-08 00:00:00',
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
            'Keeps the public roadmap up to date automatically as features move through the pipeline — no manual editing needed.',
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
            'Adds a type badge (New Feature, Enhancement, or Bug Fix) to each release row on the roadmap, so visitors can see at a glance what kind of work each release represents.',
            None,
            None,
            '2026-06-13 18:00:00',
            '2026-06-13 18:30:00',
            '2026-06-13 19:16:04.532115',
            '2026-06-13 20:22:27.361465',
            '2026-06-13 20:22:27.361465',
        ),
        (
            '15.6',
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
        ),
        (
            '15.5',
            '15',
            'Release Notes Modal',
            'release-notes-modal',
            'release',
            None,
            None,
            '2026-06-14 04:57:35.592068',
            None,
            '2026-06-21 22:41:01.095483',
            '2026-06-21 23:04:00',
            '2026-06-21 23:32:40',
            '2026-06-21 23:45:00',
            '2026-06-22 04:24:10.226909',
        ),
        (
            '16',
            None,
            'Post-Review Improvement Loop',
            'post-review-improvement-loop',
            'feature',
            None,
            'A structured improvement cycle that catches test failures and code review issues, fixes root causes, and prevents the same problems from recurring.',
            '2026-06-21 19:41:14.185055',
            '2026-06-21 19:48:51.263221',
            '2026-06-21 20:02:33.458198',
            '2026-06-21 20:15:58.410238',
            '2026-06-21 20:29:17.958222',
            '2026-06-21 20:40:50.997769',
            '2026-06-21 20:59:42.363131',
        ),
        (
            '16.1',
            '16',
            'Improvement Loop Skill',
            'improvement-loop',
            'release',
            'new-feature',
            'A structured improvement cycle that catches test failures and code review issues, fixes root causes, and prevents the same problems from recurring.',
            None,
            None,
            '2026-06-21 20:02:33.458198',
            '2026-06-21 20:15:58.410238',
            '2026-06-21 20:29:17.958222',
            '2026-06-21 20:40:50.997769',
            '2026-06-21 20:59:42.363131',
        ),
        (
            '15.7',
            '15',
            'Grouping Foundational Features',
            'grouping-foundational-features',
            'release',
            'new-feature',
            'Groups the first 10 features under a collapsible "Foundational Features" header and makes parent features expand to show their releases.',
            None,
            None,
            '2026-06-23 12:00:00',
            '2026-06-23 12:00:00',
            '2026-06-23 17:59:21.818737',
            '2026-06-23 18:47:57.169846',
            '2026-06-23 19:12:48.412956',
        ),
        (
            '17',
            None,
            'User Profile Page Updates',
            'user-profile-page-updates',
            'feature',
            None,
            None,
            '2026-06-23 21:54:58.385781',
            '2026-06-23 22:07:06.527922',
            '2026-06-24 00:18:31.478228',
            '2026-06-24 00:31:33.463778',
            '2026-06-24 01:09:26.160019',
            '2026-06-24 01:19:58.470165',
            '2026-06-24 14:31:03.123185',
        ),
        (
            '17.1',
            '17',
            'Change Password',
            'change-password',
            'release',
            'new-feature',
            'Lets logged-in users change their password securely by verifying their current password first.',
            None,
            '2026-06-23 22:07:06.527922',
            '2026-06-24 00:18:31.478228',
            '2026-06-24 00:31:33.463778',
            '2026-06-24 01:09:26.160019',
            '2026-06-24 01:19:58.470165',
            '2026-06-24 01:54:49.633550',
        ),
        (
            '17.2',
            '17',
            'Quick Add Expense Modal',
            'quick-add-expense-modal',
            'release',
            'new-feature',
            'Lets logged-in users add a new expense from the Profile page via a popup modal — no separate page, no nav item, same fast form.',
            None,
            '2026-06-23 22:07:06.527922',
            '2026-06-24 02:20:40.148120',
            '2026-06-24 02:29:27.114059',
            '2026-06-24 02:43:08.711972',
            '2026-06-24 02:59:26.356579',
            '2026-06-24 03:12:08.676480',
        ),
        (
            '17.3',
            '17',
            'Embedded Analytics Dashboard',
            'embedded-analytics-dashboard',
            'release',
            'new-feature',
            'Adds spending charts to your Profile page so you can see trends, category breakdowns, and monthly comparisons without navigating away.',
            None,
            '2026-06-23 22:07:06.527922',
            '2026-06-24 03:42:09.776096',
            '2026-06-24 03:58:42.759383',
            '2026-06-24 12:46:19.329167',
            '2026-06-24 13:31:27.174381',
            '2026-06-24 14:31:03.123185',
        ),
        (
            '18',
            None,
            'Quick Edit Expense from Profile',
            'quick-edit-expense-from-profile',
            'feature',
            None,
            None,
            '2026-06-24 20:27:39.824769',
            '2026-06-24 20:27:39.824769',
            '2026-06-24 20:27:39.824769',
            '2026-06-24 20:27:39.824769',
            '2026-06-24 22:32:02.931707',
            '2026-06-24 23:02:48.354359',
            '2026-06-25 01:18:18.091977',
        ),
        (
            '18.1',
            '18',
            'Quick Edit Expense Modal',
            'quick-edit-expense-modal',
            'release',
            'new-feature',
            None,
            None,
            '2026-06-24 20:27:39.824769',
            '2026-06-24 20:27:39.824769',
            '2026-06-24 20:27:39.824769',
            '2026-06-24 22:32:02.931707',
            '2026-06-24 23:02:48.354359',
            '2026-06-25 01:18:18.091977',
        ),
        (
            '19',
            None,
            'Profile Layout and Navbar Updates',
            'profile-layout-and-navbar-updates',
            'feature',
            None,
            'Side-by-side profile layout on desktop and a clean user icon menu in the navbar.',
            '2026-06-25 12:54:42.775987',
            '2026-06-25 22:00:54.921556',
            '2026-06-25 22:16:17.535622',
            '2026-06-25 22:28:54.366622',
            '2026-06-25 23:11:37.429557',
            '2026-06-25 23:16:50.301792',
            None,
        ),
        (
            '19-1',
            '19',
            'Responsive Profile Layout',
            'responsive-profile-layout',
            'release',
            'enhancement',
            None,
            None,
            '2026-06-25 22:00:54.921556',
            None,
            None,
            None,
            None,
            None,
        ),
        (
            '19-2',
            '19',
            'Navbar User Menu',
            'navbar-user-menu',
            'release',
            'enhancement',
            None,
            None,
            '2026-06-25 22:00:54.921556',
            None,
            None,
            None,
            None,
            None,
        ),
        (
            '19-1',
            '19',
            'Responsive Profile Layout',
            'responsive-profile-layout',
            'release',
            'new-feature',
            'Makes the Profile Card and Analytics Dashboard sit side-by-side on desktop screens, stacking vertically on mobile for a better use of space.',
            None,
            None,
            '2026-06-25 22:16:17.535622',
            '2026-06-25 22:28:54.366622',
            '2026-06-25 23:11:37.429557',
            '2026-06-25 23:16:50.301792',
            '2026-06-25 23:25:16.879862',
            "Test Report — 19.1\n\nStart: 2026-06-25 22:16:17 EST\nEnd:   2026-06-25 23:11:37 EST\nDuration: ~55 minutes\n\n24 tests passed, 0 failed.\n\nCoverage:\n- Desktop: user icon dropdown renders with My Profile and Log Out items\n- Desktop: standalone Logout link removed from nav\n- Mobile: hamburger replaced by user icon when logged in\n- Mobile: menu shows My Profile and Log Out (relabelled)\n- Logged-out state: hamburger unchanged, no user icon\n- All existing nav links preserved\n- ARIA attributes present on trigger and dropdown",
            "Code Review Report — 19.1\n\nStart: 2026-06-25 23:12:00 EST\nEnd:   2026-06-25 23:16:50 EST\nDuration: ~5 minutes\n\nSecurity Findings\nNo security vulnerabilities identified. No new routes or DB queries introduced.\n\nQuality Findings\n- Clean separation: nav_desktop_links and nav_mobile_links macros\n- Lucide loaded before main.js to ensure icons render\n- ARIA attributes correctly applied\n- CSS variables used throughout\n\nOverall Verdict: APPROVED — ready to commit",
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