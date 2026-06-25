import math
import os
import psycopg2
import psycopg2.extras
from datetime import date, datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
    jsonify,
)
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import (
    get_db,
    init_db,
    seed_db,
    seed_features,
    create_user,
    get_user_by_email,
)
from database.queries import (
    get_user_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_category_breakdown,
    get_spending_trends,
    get_monthly_comparison,
    insert_expense,
    update_expense,
    delete_expense,
    get_feature_requests,
    get_own_feature_requests,
    get_feature_request_by_id,
    insert_feature_request,
    update_feature_request,
    delete_feature_request,
    count_user_feature_requests,
    increment_feature_view,
    toggle_feature_vote,
    get_voted_feature_ids,
    get_all_features,
)

load_dotenv()

app = Flask(__name__)
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Add it to your .env file or Railway Variables."
    )
app.secret_key = _secret_key

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

VALID_PAGES = [
    "Home",
    "Profile",
    "Analytics",
    "Other",
]

MAX_FEATURE_REQUESTS_PER_USER = 5

VALID_SORTS = ["latest", "most_upvoted", "most_viewed", "trending"]

VALID_STATUSES = ["submitted", "under_review", "planned", "completed"]


def _validate_feature_request_form(page, title, description):
    if page not in VALID_PAGES:
        return "Please select a valid page."
    if not title:
        return "Title is required."
    if len(title) > 120:
        return "Title must be 120 characters or fewer."
    if len(description) < 20:
        return "Description must be at least 20 characters."
    if len(description) > 1000:
        return "Description must be 1000 characters or fewer."
    return None


with app.app_context():
    init_db()
    seed_db()
    seed_features()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    latest_features = get_feature_requests(sort="latest", limit=6)
    return render_template("landing.html", latest_features=latest_features)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    if not name:
        flash("Name is required.")
        return render_template("register.html")
    if not email or "@" not in email:
        flash("A valid email address is required.")
        return render_template("register.html")
    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return render_template("register.html")
    if password != confirm:
        flash("Passwords do not match.")
        return render_template("register.html")

    try:
        create_user(name, email, password)
    except psycopg2.errors.UniqueViolation:
        flash("Email already registered.")
        return render_template("register.html")

    flash("Account created! Please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Email and password are required.")
        return render_template("login.html")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.")
        return render_template("login.html")

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def _parse_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except (ValueError, TypeError):
        return ""


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    date_from = _parse_date(request.args.get("date_from", ""))
    date_to = _parse_date(request.args.get("date_to", ""))

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = ""

    date_from = date_from or None
    date_to = date_to or None

    today = date.today()
    presets = {
        "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": ((today - timedelta(days=90)).isoformat(), today.isoformat()),
        "last_6_months": ((today - timedelta(days=180)).isoformat(), today.isoformat()),
    }

    active_preset = "all_time"
    for name, (pf, pt) in presets.items():
        if date_from == pf and date_to == pt:
            active_preset = name
            break

    user = get_user_by_id(user_id)
    stats = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    transactions = get_recent_transactions(
        user_id, date_from=date_from, date_to=date_to
    )
    categories = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    trends = get_spending_trends(user_id, date_from=date_from, date_to=date_to)
    monthly = get_monthly_comparison(user_id)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        trends=trends,
        monthly=monthly,
        valid_categories=VALID_CATEGORIES,
        date_from=date_from or "",
        date_to=date_to or "",
        presets=presets,
        active_preset=active_preset,
        edit_form=None,
    )


@app.route("/profile/change-password", methods=["POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    current = request.form.get("current_password", "")
    if not current:
        flash("Current password is required.")
        return redirect(url_for("profile"))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, password_hash FROM users WHERE id = %s", (session["user_id"],))
        user = cur.fetchone()

        if user is None or not check_password_hash(user["password_hash"], current):
            flash("Current password is incorrect.")
            return redirect(url_for("profile"))

        new = request.form.get("new_password", "")
        if len(new) < 8:
            flash("New password must be at least 8 characters.")
            return redirect(url_for("profile"))

        confirm = request.form.get("confirm_password", "")
        if new != confirm:
            flash("New passwords do not match.")
            return redirect(url_for("profile"))

        try:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new), session["user_id"]),
            )
            conn.commit()
        except psycopg2.Error:
            conn.rollback()
            flash("Could not update password. Please try again.")
            return redirect(url_for("profile"))

        # Regenerate session to invalidate any other sessions
        user_name = session.get("user_name")
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user_name
        flash("Password changed.", "success")
        return redirect(url_for("profile"))
    finally:
        cur.close()
        conn.close()


@app.route("/profile/add-expense", methods=["POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    raw_amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    raw_date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    error = None
    try:
        amount = float(raw_amount)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except ValueError:
        error = "Amount must be a number greater than 0."

    if not error and category not in VALID_CATEGORIES:
        error = "Please select a valid category."

    if not error:
        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            error = "Please enter a valid date."

    if not error and description and len(description) > 200:
        error = "Description must be 200 characters or fewer."

    if error:
        flash(error)
        return redirect(url_for("profile"))

    try:
        insert_expense(session["user_id"], amount, category, raw_date, description)
    except psycopg2.Error:
        flash("Could not save expense. Please try again.")
        return redirect(url_for("profile"))

    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/edit-expense", methods=["POST"])
def edit_expense_route():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense_id = request.form.get("expense_id")
    if not expense_id:
        flash("Expense not found.")
        return redirect(url_for("profile"))

    raw_amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    raw_date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    error = None
    try:
        amount = float(raw_amount)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except (ValueError, TypeError):
        error = "Amount must be a number greater than 0."

    if not error and category not in VALID_CATEGORIES:
        error = "Please select a valid category."

    if not error:
        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            error = "Please enter a valid date."

    if not error and description and len(description) > 200:
        error = "Description must be 200 characters or fewer."

    if error:
        flash(error)
        # Re-render profile with modal open and form values preserved
        user_id = session["user_id"]
        today = date.today()
        presets = {
            "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
            "last_3_months": ((today - timedelta(days=90)).isoformat(), today.isoformat()),
            "last_6_months": ((today - timedelta(days=180)).isoformat(), today.isoformat()),
        }
        active_preset = "all_time"
        user = get_user_by_id(user_id)
        stats = get_summary_stats(user_id)
        transactions = get_recent_transactions(user_id)
        categories = get_category_breakdown(user_id)
        trends = get_spending_trends(user_id)
        monthly = get_monthly_comparison(user_id)
        return render_template(
            "profile.html",
            user=user,
            stats=stats,
            transactions=transactions,
            categories=categories,
            trends=trends,
            monthly=monthly,
            valid_categories=VALID_CATEGORIES,
            date_from="",
            date_to="",
            presets=presets,
            active_preset=active_preset,
            edit_form=request.form,
        )

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE expenses SET amount=%s, category=%s, date=%s, description=%s "
            "WHERE id = %s AND user_id = %s",
            (amount, category, raw_date, description, expense_id, session["user_id"]),
        )
        updated = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
    except psycopg2.Error:
        flash("Could not update expense. Please try again.")
        return redirect(url_for("profile"))

    if updated == 0:
        flash("Expense not found.")
        return redirect(url_for("profile"))

    flash("Expense updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    deleted = delete_expense(id, session["user_id"])
    if deleted:
        flash("Expense deleted.", "success")
    return redirect(url_for("profile"))


@app.route("/features", methods=["GET", "POST"])
def features():
    user_id = session.get("user_id")
    sort = request.args.get("sort", "latest")
    if sort not in VALID_SORTS:
        sort = "latest"
    page_filter = request.args.get("page_filter", "")
    status_filter = request.args.get("status_filter", "")

    if page_filter and page_filter not in VALID_PAGES:
        page_filter = ""
    if status_filter and status_filter not in VALID_STATUSES:
        status_filter = ""

    if request.method == "POST":
        if not user_id:
            return redirect(url_for("login"))

        page = request.form.get("page", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        error = _validate_feature_request_form(page, title, description)
        if (
            error is None
            and count_user_feature_requests(user_id) >= MAX_FEATURE_REQUESTS_PER_USER
        ):
            error = f"You have reached the maximum of {MAX_FEATURE_REQUESTS_PER_USER} feature requests."

        if error:
            flash(error)
        else:
            insert_feature_request(user_id, page, title, description)
            flash("Feature request submitted.", "success")
            return redirect(url_for("features"))

    all_requests = get_feature_requests(
        page_filter=page_filter or None,
        status_filter=status_filter or None,
        sort=sort,
        exclude_user_id=user_id,
    )
    own_requests = get_own_feature_requests(user_id) if user_id else []

    voted_ids = get_voted_feature_ids(user_id) if user_id else set()

    return render_template(
        "features.html",
        all_requests=all_requests,
        own_requests=own_requests,
        voted_ids=voted_ids,
        valid_pages=VALID_PAGES,
        sort=sort,
        page_filter=page_filter,
        status_filter=status_filter,
        form=request.form if request.method == "POST" else {},
    )


@app.route("/features/<int:id>/edit", methods=["GET", "POST"])
def edit_feature_request(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    feature = get_feature_request_by_id(id)
    if feature is None:
        abort(404)
    if feature["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return render_template(
            "edit_feature_request.html",
            feature=feature,
            valid_pages=VALID_PAGES,
        )

    page = request.form.get("page", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    error = _validate_feature_request_form(page, title, description)

    if error:
        flash(error)
        return render_template(
            "edit_feature_request.html",
            feature=feature,
            valid_pages=VALID_PAGES,
            form=request.form,
        )

    rows = update_feature_request(id, session["user_id"], page, title, description)
    if rows == 0:
        abort(403)

    flash("Feature request updated.", "success")
    return redirect(url_for("features"))


@app.route("/features/<int:id>/delete", methods=["POST"])
def delete_feature_request_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    rows = delete_feature_request(id, session["user_id"])
    if rows == 0:
        abort(403)

    flash("Feature request deleted.", "success")
    return redirect(url_for("features"))


@app.route("/features/<int:id>/view", methods=["POST"])
def view_feature_request(id):
    if not session.get("user_id"):
        abort(401)
    feature = get_feature_request_by_id(id)
    if feature is None:
        abort(404)
    increment_feature_view(id, session["user_id"])
    updated = get_feature_request_by_id(id)
    return jsonify({"views": updated["views"]})


@app.route("/features/<int:id>/vote", methods=["POST"])
def vote_feature_request(id):
    if not session.get("user_id"):
        abort(401)
    feature = get_feature_request_by_id(id)
    if feature is None:
        abort(404)
    if feature["user_id"] == session["user_id"]:
        abort(403)
    voted, vote_count = toggle_feature_vote(id, session["user_id"])
    return jsonify({"voted": voted, "upvotes": vote_count})


@app.route("/roadmap")
def roadmap():
    features = get_all_features()
    foundational_nums = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}
    foundational_count = sum(1 for f in features if f["number"] in foundational_nums)
    parent_numbers = {f["parent_number"] for f in features if f["parent_number"]}
    return render_template(
        "roadmap.html",
        features=features,
        foundational_count=foundational_count,
        foundational_nums=foundational_nums,
        parent_numbers=parent_numbers,
    )


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
