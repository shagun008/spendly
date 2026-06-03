"""Query helpers for the profile page and expense mutations."""

from datetime import datetime, timezone

import psycopg2.extras

from database.db import get_db


def _make_initials(name):
    tokens = name.split()
    return "".join(t[0] for t in tokens[:2]).upper() if tokens else ""


def _date_clause(date_from, date_to):
    if date_from and date_to:
        return "AND date BETWEEN %s AND %s", (date_from, date_to)
    if date_from:
        return "AND date >= %s", (date_from,)
    if date_to:
        return "AND date <= %s", (date_to,)
    return "", ()


def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT name, email, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return None

    name = row["name"]
    initials = _make_initials(name)

    created_at = str(row["created_at"])[:10]
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
        "WHERE user_id = %s"
    )
    if clause:
        sql = sql + " " + clause
    sql = sql + " ORDER BY date DESC, id DESC LIMIT %s"
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, (user_id, *params, limit))
    rows = cur.fetchall()
    cur.close()
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
    totals_sql = "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = %s"
    top_sql = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = %s"
    if clause:
        totals_sql = totals_sql + " " + clause
        top_sql = top_sql + " " + clause
    top_sql = top_sql + " GROUP BY category ORDER BY total DESC LIMIT 1"
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(totals_sql, (user_id, *params))
    totals = cur.fetchone()
    cur.execute(top_sql, (user_id, *params))
    top = cur.fetchone()
    cur.close()
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
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (%s, %s, %s, %s, %s)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    clause, params = _date_clause(date_from, date_to)
    sql = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = %s"
    if clause:
        sql = sql + " " + clause
    sql = sql + " GROUP BY category ORDER BY total DESC"
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, (user_id, *params))
    rows = cur.fetchall()
    cur.close()
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, amount, category, date, description "
        "FROM expenses WHERE id = %s AND user_id = %s",
        (expense_id, user_id),
    )
    row = cur.fetchone()
    cur.close()
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
    cur = conn.cursor()
    cur.execute(
        "UPDATE expenses SET amount=%s, category=%s, date=%s, description=%s "
        "WHERE id = %s AND user_id = %s",
        (amount, category, expense_date, description, expense_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM expenses WHERE id = %s AND user_id = %s",
        (expense_id, user_id),
    )
    conn.commit()
    rowcount = cur.rowcount
    cur.close()
    conn.close()
    return rowcount


# ------------------------------------------------------------------ #
# Feature request helpers                                              #
# ------------------------------------------------------------------ #


def _relative_time(created_at):
    try:
        if hasattr(created_at, "strftime"):
            dt = created_at.replace(tzinfo=None)
        else:
            dt = datetime.strptime(str(created_at)[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(created_at)
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


# Trending score: (votes * 5) + views + recency bonus (max +7 for requests < 7 days old)
_TRENDING_ORDER = (
    "(vote_count * 5 + fr.views + GREATEST(0, 7 - EXTRACT(EPOCH FROM (NOW() - fr.created_at)) / 86400)) DESC,"
    " fr.id DESC"
)


def get_feature_requests(
    page_filter=None,
    status_filter=None,
    sort="latest",
    exclude_user_id=None,
    limit=None,
):
    conditions = []
    params = []

    if page_filter:
        conditions.append("fr.page = %s")
        params.append(page_filter)
    if status_filter:
        conditions.append("fr.status = %s")
        params.append(status_filter)
    if exclude_user_id is not None:
        conditions.append("fr.user_id != %s")
        params.append(exclude_user_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    order = {
        "latest": "fr.created_at DESC, fr.id DESC",
        "most_upvoted": "vote_count DESC, fr.created_at DESC, fr.id DESC",
        "most_viewed": "fr.views DESC, fr.created_at DESC, fr.id DESC",
        "trending": _TRENDING_ORDER,
    }.get(sort, "fr.created_at DESC, fr.id DESC")

    limit_clause = "LIMIT %s" if limit is not None else ""
    if limit is not None:
        params.append(int(limit))

    sql = f"""
        SELECT fr.id, fr.user_id, fr.page, fr.title, fr.description,
               fr.status, fr.views, fr.created_at,
               u.name,
               COUNT(fv.id) AS vote_count
        FROM feature_requests fr
        JOIN users u ON u.id = fr.user_id
        LEFT JOIN feature_votes fv ON fv.feature_id = fr.id
        {where}
        GROUP BY fr.id, fr.user_id, fr.page, fr.title, fr.description,
                 fr.status, fr.views, fr.created_at, u.name
        ORDER BY {order}
        {limit_clause}
    """
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
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
        WHERE fr.user_id = %s
        GROUP BY fr.id, fr.user_id, fr.page, fr.title, fr.description,
                 fr.status, fr.views, fr.created_at, u.name
        ORDER BY fr.created_at DESC
    """
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, (user_id,))
    rows = cur.fetchall()
    cur.close()
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
        WHERE fr.id = %s
        GROUP BY fr.id, fr.user_id, fr.page, fr.title, fr.description,
                 fr.status, fr.views, fr.created_at, u.name
    """
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, (feature_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return None
    return _fr_row_to_dict(row)


def insert_feature_request(user_id, page, title, description):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO feature_requests (user_id, page, title, description)"
        " VALUES (%s, %s, %s, %s) RETURNING id",
        (user_id, page, title, description),
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def update_feature_request(feature_id, user_id, page, title, description):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE feature_requests SET page=%s, title=%s, description=%s, updated_at=NOW() "
        "WHERE id=%s AND user_id=%s",
        (page, title, description, feature_id, user_id),
    )
    conn.commit()
    rowcount = cur.rowcount
    cur.close()
    conn.close()
    return rowcount


def delete_feature_request(feature_id, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM feature_requests WHERE id=%s AND user_id=%s",
        (feature_id, user_id),
    )
    conn.commit()
    rowcount = cur.rowcount
    cur.close()
    conn.close()
    return rowcount


def count_user_feature_requests(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT COUNT(*) AS count FROM feature_requests WHERE user_id=%s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["count"]


def increment_feature_view(feature_id, viewer_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feature_views (feature_id, viewer_id) VALUES (%s, %s)"
        " ON CONFLICT (feature_id, viewer_id) DO NOTHING",
        (feature_id, viewer_id),
    )
    is_new_view = bool(cur.rowcount)
    if is_new_view:
        cur.execute(
            "UPDATE feature_requests SET views = views + 1 WHERE id=%s",
            (feature_id,),
        )
    conn.commit()
    cur.close()
    conn.close()
    return is_new_view


def toggle_feature_vote(feature_id, user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO feature_votes (feature_id, user_id) VALUES (%s, %s)"
        " ON CONFLICT (feature_id, user_id) DO NOTHING",
        (feature_id, user_id),
    )
    if cur.rowcount == 1:
        voted = True
    else:
        cur.execute(
            "DELETE FROM feature_votes WHERE feature_id = %s AND user_id = %s",
            (feature_id, user_id),
        )
        voted = False
    conn.commit()
    cur.execute(
        "SELECT COUNT(*) AS count FROM feature_votes WHERE feature_id = %s",
        (feature_id,),
    )
    vote_count = cur.fetchone()["count"]
    cur.close()
    conn.close()
    return voted, vote_count


def get_voted_feature_ids(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT feature_id FROM feature_votes WHERE user_id = %s",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row["feature_id"] for row in rows}
