from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from .db import get_db, now_iso

auth_bp = Blueprint("auth", __name__)


GENDER_OPTIONS = {"Male", "Female", "Other", "Prefer not to say"}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.home"))
    if request.method == "POST":
        db = get_db()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        gender = request.form.get("gender", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = None
        if not full_name or not email or not username or not gender or not password:
            error = "Please fill in all required fields."
        elif gender not in GENDER_OPTIONS:
            error = "Please select a valid gender option."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            error = "That username is already taken."
        elif db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            error = "That email is already registered."

        if error:
            flash(error, "error")
            return render_template("register.html", form=request.form)

        cur = db.execute(
            "INSERT INTO users (username, email, password_hash, full_name, gender, "
            "location, dark_mode, joined_at) VALUES (?,?,?,?,?,?,0,?)",
            (username, email, generate_password_hash(password), full_name, gender,
             "", now_iso()),
        )
        db.commit()
        session["user_id"] = cur.lastrowid
        return redirect(url_for("main.home"))

    return render_template("register.html", form={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.home"))
    if request.method == "POST":
        db = get_db()
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        user = db.execute("SELECT * FROM users WHERE username=? OR email=?",
                           (identifier, identifier.lower())).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("main.home"))
        flash("Invalid username/email or password.", "error")
        return render_template("login.html", identifier=identifier)
    return render_template("login.html", identifier="")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
