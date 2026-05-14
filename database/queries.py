"""Read-only query helpers for the profile page.

Each helper opens its own sqlite3 connection via get_db(), executes a
parameterised query, formats the result for direct rendering by
templates/profile.html, and closes the connection before returning.
"""
from datetime import datetime

from database.db import get_db


def _date_clause(date_from, date_to):
    """Return a fixed SQL fragment and its bind params for optional date filtering.

    The returned clause string is always a literal SQL keyword fragment — no user
    data is ever interpolated into it. User-supplied dates travel via ? placeholders.
    """
    if date_from and date_to:
        return "AND date BETWEEN ? AND ?", (date_from, date_to)
    if date_from:
        return "AND date >= ?", (date_from,)
    if date_to:
        return "AND date <= ?", (date_to,)
    return "", ()


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None

    name = row["name"]
    tokens = name.split()
    initials = "".join(t[0] for t in tokens[:2]).upper() if tokens else ""

    created_at = row["created_at"].split(" ")[0]
    member_since = datetime.strptime(created_at, "%Y-%m-%d").strftime("%B %Y")

    return {
        "name": name,
        "email": row["email"],
        "member_since": member_since,
        "initials": initials,
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    clause, params = _date_clause(date_from, date_to)
    sql = (
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ?"
    )
    if clause:
        sql = sql + " " + clause
    sql = sql + " ORDER BY date DESC, id DESC LIMIT ?"
    conn = get_db()
    rows = conn.execute(sql, (user_id, *params, limit)).fetchall()
    conn.close()
    return [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        }
        for row in rows
    ]


def get_summary_stats(user_id, date_from=None, date_to=None):
    clause, params = _date_clause(date_from, date_to)
    totals_sql = "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?"
    top_sql = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ?"
    if clause:
        totals_sql = totals_sql + " " + clause
        top_sql = top_sql + " " + clause
    top_sql = top_sql + " GROUP BY category ORDER BY total DESC LIMIT 1"
    conn = get_db()
    totals = conn.execute(totals_sql, (user_id, *params)).fetchone()
    top = conn.execute(top_sql, (user_id, *params)).fetchone()
    conn.close()

    total = totals["total"]
    count = totals["cnt"]
    top_category = top["category"] if top is not None else "—"

    return {
        "total_spent": f"₹{total:,.2f}",
        "transaction_count": count,
        "top_category": top_category,
    }


def get_category_breakdown(user_id, date_from=None, date_to=None):
    clause, params = _date_clause(date_from, date_to)
    sql = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ?"
    if clause:
        sql = sql + " " + clause
    sql = sql + " GROUP BY category ORDER BY total DESC"
    conn = get_db()
    rows = conn.execute(sql, (user_id, *params)).fetchall()
    conn.close()

    if not rows:
        return []

    overall_total = sum(row["total"] for row in rows)
    if overall_total == 0:
        return []

    categories = [
        {
            "name": row["category"],
            "amount": f"₹{row['total']:,.2f}",
            "pct": round(row["total"] * 100 / overall_total),
            "_total": row["total"],
        }
        for row in rows
    ]

    pct_sum = sum(c["pct"] for c in categories)
    if pct_sum != 100:
        categories[0]["pct"] += 100 - pct_sum

    return [
        {"name": c["name"], "amount": c["amount"], "pct": c["pct"]}
        for c in categories
    ]
