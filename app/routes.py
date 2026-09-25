from functools import wraps
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for, session,
                    request, g, jsonify, flash)
from .db import get_db
from . import stats as S

main_bp = Blueprint("main", __name__)


def _fmt_date(iso_str):
    try:
        return datetime.fromisoformat(iso_str).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso_str or ""


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.get("user"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@main_bp.route("/")
@login_required
def home():
    user = g.user
    cat_played, total_nq1_questions = S.category_wise_played(user["id"])
    top6 = cat_played[:6]
    most_played = S.most_played_category(user["id"])
    last_cat = S.last_category_played(user["id"])
    return render_template(
        "home.html", user=user,
        category_played=top6, total_nq1_questions=total_nq1_questions,
        most_played=most_played, last_cat=last_cat,
    )


@main_bp.route("/quizzes")
@login_required
def quizzes():
    db = get_db()
    q = request.args.get("q", "").strip()
    cats = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    if q:
        cats = [c for c in cats if q.lower() in c["name"].lower()]
    return render_template("quizzes.html", categories=cats, search=q)


@main_bp.route("/play/nq1/<key>")
@login_required
def play_nq1(key):
    db = get_db()
    cat = db.execute("SELECT * FROM categories WHERE key=?", (key,)).fetchone()
    if not cat:
        return redirect(url_for("main.quizzes"))
    return render_template("play.html", mode="nq1", category=cat, allow_hints=True)


@main_bp.route("/play/nq2")
@login_required
def play_nq2():
    return render_template("play.html", mode="nq2", category=None, allow_hints=True)


@main_bp.route("/play/daily")
@login_required
def play_daily():
    return render_template("play.html", mode="daily", category=None, allow_hints=False)


@main_bp.route("/history")
@login_required
def history():
    db = get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 15
    where = ["user_id=?"]
    params = [g.user["id"]]

    search = request.args.get("q", "").strip()
    cat_filter = request.args.get("category", "").strip()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()

    if search:
        where.append("(category_name LIKE ? OR CAST(game_no AS TEXT) LIKE ?)")
        like = f"%{search}%"
        params += [like, like]
    if cat_filter and cat_filter != "All":
        where.append("category_name=?")
        params.append(cat_filter)
    if from_date:
        where.append("played_at >= ?")
        params.append(from_date)
    if to_date:
        where.append("played_at <= ?")
        params.append(to_date + " 23:59:59")

    where_sql = " AND ".join(where)
    total = db.execute(f"SELECT COUNT(*) c FROM game_history WHERE {where_sql}", params).fetchone()["c"]
    games = db.execute(
        f"SELECT * FROM game_history WHERE {where_sql} ORDER BY played_at DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page]).fetchall()
    pages = max(1, (total + per_page - 1) // per_page)

    all_categories = [r["category_name"] for r in db.execute(
        "SELECT DISTINCT category_name FROM game_history WHERE user_id=? ORDER BY category_name",
        (g.user["id"],)).fetchall()]

    games_fmt = []
    for row in games:
        d = dict(row)
        d["date_label"] = _fmt_date(d["played_at"])
        d["time_label"] = f"{d['time_seconds'] // 60:02d}:{d['time_seconds'] % 60:02d}"
        games_fmt.append(d)

    return render_template("history.html", games=games_fmt, page=page, pages=pages,
                            search=search, cat_filter=cat_filter or "All",
                            all_categories=all_categories,
                            from_date=from_date, to_date=to_date)


@main_bp.route("/leaderboard")
@login_required
def leaderboard():
    period = request.args.get("period", "all")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 15
    rows = S.leaderboard_rows(period)
    total_players = len(rows)
    my_rank = next((r for r in rows if r["user_id"] == g.user["id"]), None)
    pages = max(1, (total_players + per_page - 1) // per_page)
    page_rows = rows[(page - 1) * per_page: page * per_page]
    return render_template("leaderboard.html", rows=page_rows, period=period,
                            total_players=total_players, my_rank=my_rank,
                            page=page, pages=pages)


@main_bp.route("/profile")
@login_required
def profile():
    summary = S.user_summary(g.user["id"], quiz_types=["nq1"])
    cat_perf = S.category_performance(g.user["id"])
    streak = S.get_streak(g.user["id"])
    joined_label = _fmt_date(g.user["joined_at"])
    return render_template("profile.html", summary=summary, cat_perf=cat_perf,
                            streak=streak, joined_label=joined_label)


@main_bp.route("/profile/clear-data", methods=["POST"])
@login_required
def clear_data():
    """Permanently wipes all quiz data (history, progress, scores, streaks)
    for the CURRENT account only. The user row itself (login, email, full
    name, gender, dark mode preference) is left untouched, and no other
    account is ever affected -- every statement below is scoped to
    user_id = g.user['id']."""
    db = get_db()
    uid = g.user["id"]
    from . import quiz_engine as QE
    QE.exit_without_saving(uid)  # discard any in-progress game first

    db.execute("DELETE FROM game_history WHERE user_id=?", (uid,))
    db.execute("DELETE FROM category_progress WHERE user_id=?", (uid,))
    db.execute("DELETE FROM nq2_progress WHERE user_id=?", (uid,))
    db.execute("DELETE FROM daily_progress WHERE user_id=?", (uid,))
    db.commit()

    flash("All your quiz data has been cleared. Your score, history and "
          "progress are back to a fresh start.", "success")
    return redirect(url_for("main.profile"))


@main_bp.route("/all-quiz")
@login_required
def all_quiz():
    # All Quiz page reflects Normal Quiz 2 ("Play All Quiz") activity only.
    summary = S.user_summary(g.user["id"], quiz_types=["nq2"])
    return render_template("all_quiz.html", summary=summary)


@main_bp.route("/toggle-dark-mode", methods=["POST"])
@login_required
def toggle_dark_mode():
    db = get_db()
    new_val = 0 if g.user["dark_mode"] else 1
    db.execute("UPDATE users SET dark_mode=? WHERE id=?", (new_val, g.user["id"]))
    db.commit()
    return jsonify({"dark_mode": bool(new_val)})
