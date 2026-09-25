from datetime import date, timedelta
from .db import get_db


def _fmt_time(total_seconds):
    total_seconds = int(total_seconds or 0)
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


def _fmt_mmss(total_seconds):
    total_seconds = int(total_seconds or 0)
    m, s = divmod(total_seconds, 60)
    return f"{m:02d}:{s:02d}"


def user_summary(user_id, quiz_types=None):
    db = get_db()
    if quiz_types:
        placeholders = ",".join("?" * len(quiz_types))
        games = db.execute(
            f"SELECT * FROM game_history WHERE user_id=? AND quiz_type IN ({placeholders})",
            (user_id, *quiz_types)).fetchall()
    else:
        games = db.execute("SELECT * FROM game_history WHERE user_id=?", (user_id,)).fetchall()

    total_games = len(games)
    total_correct = sum(g["correct"] for g in games)
    total_wrong = sum(g["wrong"] for g in games)
    total_score = sum(g["score"] for g in games)
    total_questions = sum(g["questions_played"] for g in games)
    total_time = sum(g["time_seconds"] for g in games)

    accuracy = round((total_correct / total_questions) * 100, 2) if total_questions else 0.0
    avg_time = total_time / total_games if total_games else 0
    avg_score = round(total_score / total_games, 2) if total_games else 0
    avg_questions = round(total_questions / total_games, 2) if total_games else 0
    wrong_rate = round(100 - accuracy, 2) if total_questions else 0.0

    highest_score = max((g["score"] for g in games), default=0)
    highest_questions = max((g["questions_played"] for g in games), default=0)
    highest_correct = max((g["correct"] for g in games), default=0)
    highest_wrong = max((g["wrong"] for g in games), default=0)
    highest_time = max((g["time_seconds"] for g in games), default=0)

    return {
        "total_games": total_games, "total_correct": total_correct, "total_wrong": total_wrong,
        "total_score": total_score, "total_questions": total_questions,
        "total_time": _fmt_time(total_time), "accuracy": accuracy, "avg_time": _fmt_mmss(avg_time),
        "avg_score": avg_score, "avg_questions": avg_questions, "wrong_rate": wrong_rate,
        "highest_score": highest_score, "highest_questions": highest_questions,
        "highest_correct": highest_correct, "highest_wrong": highest_wrong,
        "highest_time": _fmt_mmss(highest_time),
    }


def category_performance(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT category_name, COUNT(*) games, SUM(questions_played) questions, "
        "SUM(correct) correct, SUM(wrong) wrong, MAX(score) best "
        "FROM game_history WHERE user_id=? AND quiz_type='nq1' "
        "GROUP BY category_name ORDER BY questions DESC", (user_id,)).fetchall()
    out = []
    for r in rows:
        questions = r["questions"] or 0
        correct = r["correct"] or 0
        acc = round((correct / questions) * 100) if questions else 0
        out.append({"name": r["category_name"], "games": r["games"], "questions": questions,
                     "correct": correct, "wrong": r["wrong"] or 0, "accuracy": acc,
                     "best_score": r["best"] or 0})
    return out


def category_wise_played(user_id):
    rows = category_performance(user_id)
    total = sum(r["questions"] for r in rows) or 1
    result = [{"name": r["name"], "questions": r["questions"],
               "pct": round(r["questions"] / total * 100)} for r in rows]
    return result, sum(r["questions"] for r in rows)


def most_played_category(user_id):
    rows = category_performance(user_id)
    if not rows:
        return None
    return max(rows, key=lambda r: r["questions"])


def last_category_played(user_id):
    db = get_db()
    g = db.execute("SELECT * FROM game_history WHERE user_id=? AND quiz_type='nq1' "
                    "ORDER BY played_at DESC LIMIT 1", (user_id,)).fetchone()
    if not g:
        return None
    cat = db.execute("SELECT * FROM categories WHERE name=?", (g["category_name"],)).fetchone()
    return {"name": g["category_name"], "key": cat["key"] if cat else None}


def get_streak(user_id):
    db = get_db()
    prog = db.execute("SELECT * FROM daily_progress WHERE user_id=?", (user_id,)).fetchone()
    if not prog:
        return {"current": 0, "longest": 0}
    today = date.today()
    current = prog["current_streak"] or 0
    if prog["last_play_date"]:
        last = date.fromisoformat(prog["last_play_date"])
        if last < today - timedelta(days=1):
            current = 0
    return {"current": current, "longest": prog["longest_streak"] or 0}


def leaderboard_rows(period="all"):
    db = get_db()
    since_clause = ""
    params = []
    if period != "all":
        now = date.today()
        if period == "today":
            since = now.isoformat()
        elif period == "week":
            since = (now - timedelta(days=7)).isoformat()
        elif period == "month":
            since = (now - timedelta(days=30)).isoformat()
        else:
            since = None
        if since:
            since_clause = "AND (gh.played_at >= ? OR gh.played_at IS NULL)"
            params.append(since)

    query = f"""
        SELECT u.id, u.username,
               COALESCE(SUM(gh.score),0) score,
               COALESCE(SUM(gh.questions_played),0) questions,
               COUNT(gh.id) games,
               COALESCE(SUM(gh.time_seconds),0) time_s
        FROM users u
        LEFT JOIN game_history gh ON gh.user_id = u.id {since_clause}
        GROUP BY u.id
        ORDER BY score DESC
    """
    rows = db.execute(query, params).fetchall()
    out = []
    for rank, r in enumerate(rows, start=1):
        out.append({"rank": rank, "user_id": r["id"], "username": r["username"],
                     "score": r["score"], "questions": r["questions"], "games": r["games"],
                     "time": _fmt_time(r["time_s"])})
    return out
