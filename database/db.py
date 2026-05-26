import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "spendly.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS feature_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            page        TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'submitted',
            views       INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS feature_votes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id  INTEGER NOT NULL REFERENCES feature_requests(id),
            user_id     INTEGER NOT NULL REFERENCES users(id),
            created_at  TEXT    DEFAULT (datetime('now')),
            UNIQUE (feature_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS feature_views (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id  INTEGER NOT NULL REFERENCES feature_requests(id),
            viewer_id   INTEGER NOT NULL REFERENCES users(id),
            viewed_at   TEXT    DEFAULT (datetime('now')),
            UNIQUE (feature_id, viewer_id)
        );
    """)
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


def seed_db():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    if row[0] > 0:
        conn.close()
        return

    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

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
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
