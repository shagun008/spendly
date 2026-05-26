"""Query helpers for the profile page and expense mutations.

Each helper opens its own sqlite3 connection via get_db(), executes a
parameterised query, and closes the connection before returning.
"""

from datetime import datetime, timezone

from database.db import get_db


def _make_initials(name):
    tokens = name.split()
    return "".join(t[0] for t in tokens[:2]).upper() if tokens else ""


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
    initials = _make_initials(name)

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
        "SELECT id, date, description, category, amount FROM expenses "
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
            "id": row["id"],
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


def insert_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


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
        {"name": c["name"], "amount": c["amount"], "pct": c["pct"]} for c in categories
    ]


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, amount, category, date, description "
        "FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "amount": row["amount"],
        "category": row["category"],
        "date": row["date"],
        "description": row["description"] or "",
    }


def update_expense(expense_id, user_id, amount, category, expense_date, description):
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount=?, category=?, date=?, description=? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, expense_date, description, expense_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount


# ------------------------------------------------------------------ #
# Feature request helpers                                              #
# ------------------------------------------------------------------ #


def _relative_time(created_at):
    try:
        dt = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return created_at
    delta = datetime.now(timezone.utc).replace(tzinfo=None) - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m} min ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = seconds // 86400
    if d < 30:
        return f"{d} day{'s' if d != 1 else ''} ago"
    mo = d // 30
    if mo < 12:
        return f"{mo} month{'s' if mo != 1 else ''} ago"
    yr = d // 365
    return f"{yr} year{'s' if yr != 1 else ''} ago"


def _fr_row_to_dict(row):
    return {
        "id": row["id"],
        "page": row["page"],
        "title": row["title"],
        "description": row["description"],
        "description_snippet": row["description"][:100]
        + ("…" if len(row["description"]) > 100 else ""),
        "status": row["status"],
        "views": row["views"],
        "vote_count": row["vote_count"],
        "initials": _make_initials(row["name"]),
        "time_ago": _relative_time(row["created_at"]),
        "created_at": row["created_at"],
        "user_id": row["user_id"],
    }


def get_feature_requests(
    page_filter=None, status_filter=None, sort="latest", exclude_user_id=None
):
    conditions = []
    params = []

    if page_filter:
        conditions.append("fr.page = ?")
        params.append(page_filter)
    if status_filter:
        conditions.append("fr.status = ?")
        params.append(status_filter)
    if exclude_user_id is not None:
        conditions.append("fr.user_id != ?")
        params.append(exclude_user_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    order = {
        "latest": "fr.created_at DESC, fr.id DESC",
        "most_upvoted": "vote_count DESC, fr.created_at DESC, fr.id DESC",
        "most_viewed": "fr.views DESC, fr.created_at DESC, fr.id DESC",
    }.get(sort, "fr.created_at DESC, fr.id DESC")

    sql = f"""
        SELECT fr.id, fr.user_id, fr.page, fr.title, fr.description,
               fr.status, fr.views, fr.created_at,
               u.name,
               COUNT(fv.id) AS vote_count
        FROM feature_requests fr
        JOIN users u ON u.id = fr.user_id
        LEFT JOIN feature_votes fv ON fv.feature_id = fr.id
        {where}
        GROUP BY fr.id
        ORDER BY {order}
    """
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_fr_row_to_dict(r) for r in rows]


def get_own_feature_requests(user_id):
    sql = """
        SELECT fr.id, fr.user_id, fr.page, fr.title, fr.description,
               fr.status, fr.views, fr.created_at,
               u.name,
               COUNT(fv.id) AS vote_count
        FROM feature_requests fr
        JOIN users u ON u.id = fr.user_id
        LEFT JOIN feature_votes fv ON fv.feature_id = fr.id
        WHERE fr.user_id = ?
        GROUP BY fr.id
        ORDER BY fr.created_at DESC
    """
    conn = get_db()
    rows = conn.execute(sql, (user_id,)).fetchall()
    conn.close()
    return [_fr_row_to_dict(r) for r in rows]


def get_feature_request_by_id(feature_id):
    sql = """
        SELECT fr.id, fr.user_id, fr.page, fr.title, fr.description,
               fr.status, fr.views, fr.created_at,
               u.name,
               COUNT(fv.id) AS vote_count
        FROM feature_requests fr
        JOIN users u ON u.id = fr.user_id
        LEFT JOIN feature_votes fv ON fv.feature_id = fr.id
        WHERE fr.id = ?
        GROUP BY fr.id
    """
    conn = get_db()
    row = conn.execute(sql, (feature_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _fr_row_to_dict(row)


def insert_feature_request(user_id, page, title, description):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO feature_requests (user_id, page, title, description) VALUES (?, ?, ?, ?)",
        (user_id, page, title, description),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_feature_request(feature_id, user_id, page, title, description):
    conn = get_db()
    cursor = conn.execute(
        "UPDATE feature_requests SET page=?, title=?, description=?, updated_at=datetime('now') "
        "WHERE id=? AND user_id=?",
        (page, title, description, feature_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount


def delete_feature_request(feature_id, user_id):
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM feature_requests WHERE id=? AND user_id=?",
        (feature_id, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount


def count_user_feature_requests(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) FROM feature_requests WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row[0]


def increment_feature_view(feature_id, viewer_id):
    conn = get_db()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO feature_views (feature_id, viewer_id) VALUES (?, ?)",
        (feature_id, viewer_id),
    )
    if cursor.rowcount:
        conn.execute(
            "UPDATE feature_requests SET views = views + 1 WHERE id=?",
            (feature_id,),
        )
    conn.commit()
    conn.close()
    return bool(cursor.rowcount)
