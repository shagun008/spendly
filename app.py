import math
import os
import sqlite3
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
)
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import (
    get_user_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
    delete_expense,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spendly-dev-secret")

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    return render_template("landing.html")


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
    except sqlite3.IntegrityError:
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

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=date_from or "",
        date_to=date_to or "",
        presets=presets,
        active_preset=active_preset,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        today = date.today().isoformat()
        return render_template(
            "add_expense.html", today=today, categories=VALID_CATEGORIES
        )

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
        return render_template(
            "add_expense.html",
            categories=VALID_CATEGORIES,
            form=request.form,
            today=date.today().isoformat(),
        )

    insert_expense(session["user_id"], amount, category, raw_date, description)
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=VALID_CATEGORIES,
        )

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
        return render_template(
            "edit_expense.html",
            expense=expense,
            form=request.form,
            categories=VALID_CATEGORIES,
        )

    update_expense(id, session["user_id"], amount, category, raw_date, description)
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


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
