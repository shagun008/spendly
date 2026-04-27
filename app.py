import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"

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

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm  = request.form.get("confirm_password", "")

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

    email    = request.form.get("email", "").strip()
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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Arjun Sharma",
        "email": "arjun.sharma@example.com",
        "member_since": "January 15, 2025",
        "initials": "AS",
    }

    stats = {
        "total_spent": "₹340.49",
        "transaction_count": 8,
        "top_category": "Bills",
    }

    transactions = [
        {"date": "Apr 12, 2026", "description": "Miscellaneous",    "category": "Other",         "amount": "₹8.00"},
        {"date": "Apr 11, 2026", "description": "Coffee and snack", "category": "Food",          "amount": "₹8.00"},
        {"date": "Apr 09, 2026", "description": "New shirt",        "category": "Shopping",      "amount": "₹89.99"},
        {"date": "Apr 07, 2026", "description": "Movie ticket",     "category": "Entertainment", "amount": "₹20.00"},
        {"date": "Apr 05, 2026", "description": "Pharmacy",         "category": "Health",        "amount": "₹45.00"},
        {"date": "Apr 03, 2026", "description": "Electricity bill", "category": "Bills",         "amount": "₹120.00"},
        {"date": "Apr 02, 2026", "description": "Monthly bus pass", "category": "Transport",     "amount": "₹35.00"},
        {"date": "Apr 01, 2026", "description": "Lunch at cafe",    "category": "Food",          "amount": "₹12.50"},
    ]

    categories = [
        {"name": "Bills",         "amount": "₹120.00", "pct": 35},
        {"name": "Shopping",      "amount": "₹89.99",  "pct": 26},
        {"name": "Health",        "amount": "₹45.00",  "pct": 13},
        {"name": "Transport",     "amount": "₹35.00",  "pct": 10},
        {"name": "Entertainment", "amount": "₹20.00",  "pct": 6},
        {"name": "Food",          "amount": "₹20.50",  "pct": 6},
        {"name": "Other",         "amount": "₹8.00",   "pct": 2},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
