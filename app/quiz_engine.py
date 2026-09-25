"""Core quiz-session logic shared by Normal Quiz 1, Normal Quiz 2 and Daily Quiz.

The in-progress game state lives in the `active_quiz` database table (one
JSON blob per user), NOT in the browser's session cookie. This matters
because Normal Quiz 1 & 2 are unlimited-length: a player can keep
answering indefinitely, and a cookie-based session would eventually
overflow the browser's ~4KB cookie limit. Nothing is written to
game_history / progress tables until "Finish & Save" is clicked.
"Exit Without Saving" just deletes the active_quiz row.

Question delivery is index-based and computed on demand: for a game
started at dataset pointer `start_seq`, the question shown at UI index
`i` is dataset row `(start_seq + i) % total_dataset` -- this is what
gives "the screen always starts again at Question 1 but internally
continues from the next unused question" and the automatic wraparound
once a dataset/category is exhausted.
"""
import json
from datetime import date, timedelta

from .db import get_db, now_iso
from .config import Config

TABLES = {"nq1": "questions_nq1", "nq2": "questions_nq2", "daily": "questions_daily"}


# ---------------------------------------------------------------- state io
def _load_state(db, user_id):
    row = db.execute("SELECT state_json FROM active_quiz WHERE user_id=?", (user_id,)).fetchone()
    return json.loads(row["state_json"]) if row else None


def _save_state(db, user_id, state):
    db.execute(
        "INSERT INTO active_quiz (user_id, state_json) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET state_json=excluded.state_json",
        (user_id, json.dumps(state)),
    )
    db.commit()


def _clear_state(db, user_id):
    db.execute("DELETE FROM active_quiz WHERE user_id=?", (user_id,))
    db.commit()


# ---------------------------------------------------------------- helpers
def _row_for_index(db, state, index):
    """Fetch the dataset row that corresponds to UI question index `index`."""
    total = state["total_dataset"]
    if total == 0:
        return None
    seq = (state["start_seq"] + index) % total
    table = TABLES[state["type"]]
    if state["type"] == "nq1":
        return db.execute(f"SELECT * FROM {table} WHERE category_id=? AND seq=?",
                           (state["category_id"], seq)).fetchone()
    return db.execute(f"SELECT * FROM {table} WHERE seq=?", (seq,)).fetchone()


def _q_public(row, index, total):
    return {
        "index": index,
        "total": total,  # None => unlimited (Normal Quiz 1 / 2)
        "question": row["question"],
        "options": {"A": row["option_a"], "B": row["option_b"],
                    "C": row["option_c"], "D": row["option_d"]},
        "subcategory": row["subcategory"] if "subcategory" in row.keys() else "",
    }


# ---------------------------------------------------------------- public api
def start_quiz(user_id, quiz_type, category_key=None):
    db = get_db()

    if quiz_type == "nq1":
        cat = db.execute("SELECT * FROM categories WHERE key=?", (category_key,)).fetchone()
        if not cat:
            return False, "Unknown category."
        prog = db.execute("SELECT * FROM category_progress WHERE user_id=? AND category_id=?",
                           (user_id, cat["id"])).fetchone()
        if not prog:
            db.execute("INSERT INTO category_progress (user_id, category_id, next_seq, completed_count) "
                       "VALUES (?,?,0,0)", (user_id, cat["id"]))
            db.commit()
            prog = db.execute("SELECT * FROM category_progress WHERE user_id=? AND category_id=?",
                               (user_id, cat["id"])).fetchone()
        if cat["question_count"] == 0:
            return False, "No questions available for this category."
        state = {
            "type": "nq1", "category_key": category_key, "category_name": cat["name"],
            "category_id": cat["id"], "start_seq": prog["next_seq"],
            "total_dataset": cat["question_count"], "max_index": None,
            "answers": {}, "hints": [], "score": 0, "correct": 0, "wrong": 0,
            "max_hints": Config.MAX_HINTS_NORMAL,
        }
        _save_state(db, user_id, state)
        return True, None

    if quiz_type == "nq2":
        total = db.execute("SELECT COUNT(*) c FROM questions_nq2").fetchone()["c"]
        if total == 0:
            return False, "No questions available."
        prog = db.execute("SELECT * FROM nq2_progress WHERE user_id=?", (user_id,)).fetchone()
        if not prog:
            db.execute("INSERT INTO nq2_progress (user_id, next_seq) VALUES (?,0)", (user_id,))
            db.commit()
            prog = db.execute("SELECT * FROM nq2_progress WHERE user_id=?", (user_id,)).fetchone()
        state = {
            "type": "nq2", "category_key": None, "category_name": "Over All",
            "category_id": None, "start_seq": prog["next_seq"], "total_dataset": total,
            "max_index": None, "answers": {}, "hints": [],
            "score": 0, "correct": 0, "wrong": 0, "max_hints": Config.MAX_HINTS_NORMAL,
        }
        _save_state(db, user_id, state)
        return True, None

    if quiz_type == "daily":
        total = db.execute("SELECT COUNT(*) c FROM questions_daily").fetchone()["c"]
        if total == 0:
            return False, "No questions available."
        prog = db.execute("SELECT * FROM daily_progress WHERE user_id=?", (user_id,)).fetchone()
        if not prog:
            db.execute("INSERT INTO daily_progress (user_id, next_seq, last_play_date, answered_today, "
                       "current_streak, longest_streak) VALUES (?,0,NULL,0,0,0)", (user_id,))
            db.commit()
            prog = db.execute("SELECT * FROM daily_progress WHERE user_id=?", (user_id,)).fetchone()
        today = date.today().isoformat()
        if prog["last_play_date"] == today:
            return False, "You've already completed today's Daily Challenge. Come back tomorrow!"
        state = {
            "type": "daily", "category_key": None, "category_name": "Daily Quiz",
            "category_id": None, "start_seq": prog["next_seq"], "total_dataset": total,
            "max_index": Config.DAILY_QUESTIONS_PER_DAY, "answers": {}, "hints": [],
            "score": 0, "correct": 0, "wrong": 0, "max_hints": Config.MAX_HINTS_DAILY,
        }
        _save_state(db, user_id, state)
        return True, None

    return False, "Unknown quiz type."


def get_state(user_id):
    return _load_state(get_db(), user_id)


def get_question(user_id, index):
    db = get_db()
    state = _load_state(db, user_id)
    if not state or index < 0:
        return None
    if state["max_index"] is not None and index >= state["max_index"]:
        return None
    row = _row_for_index(db, state, index)
    if row is None:
        return None
    payload = _q_public(row, index, state["max_index"])
    key = str(index)
    payload["answered"] = state["answers"].get(key)
    payload["hint_used"] = key in state["hints"]
    # Reveal the correct answer + explanation as soon as the question has
    # been answered (or a hint was used) -- immediately, no extra click.
    if payload["hint_used"] or payload["answered"]:
        payload["correct_option"] = row["correct"]
        payload["explanation"] = row["explanation"]
    return payload


def submit_answer(user_id, index, option):
    db = get_db()
    state = _load_state(db, user_id)
    if not state or index < 0:
        return None
    if state["max_index"] is not None and index >= state["max_index"]:
        return None
    key = str(index)
    if key in state["answers"]:
        return get_question(user_id, index)  # already answered, no double scoring
    row = _row_for_index(db, state, index)
    if row is None:
        return None
    is_correct = (option or "").upper() == (row["correct"] or "").upper()
    if is_correct:
        state["score"] += Config.SCORE_CORRECT
        state["correct"] += 1
    else:
        state["score"] = max(0, state["score"] + Config.SCORE_WRONG)
        state["wrong"] += 1
    state["answers"][key] = {"option": option, "correct": is_correct}
    _save_state(db, user_id, state)
    return get_question(user_id, index)


def use_hint(user_id, index):
    db = get_db()
    state = _load_state(db, user_id)
    if not state:
        return None
    key = str(index)
    if key not in state["hints"] and len(state["hints"]) >= state["max_hints"]:
        return {"error": "No hints remaining."}
    if key not in state["hints"]:
        state["hints"].append(key)
        _save_state(db, user_id, state)
    return get_question(user_id, index)


def next_game_no(db, user_id):
    row = db.execute("SELECT COUNT(*) c FROM game_history WHERE user_id=?", (user_id,)).fetchone()
    return row["c"] + 1


def finish_and_save(user_id, time_seconds):
    db = get_db()
    state = _load_state(db, user_id)
    if not state:
        return None

    game_no = next_game_no(db, user_id)
    hints_used = len(state["hints"])
    n_answered = len(state["answers"])  # only advance progress past what was actually answered

    db.execute(
        "INSERT INTO game_history (user_id, quiz_type, category_name, game_no, played_at, "
        "questions_played, correct, wrong, score, time_seconds, hints_used) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, state["type"], state["category_name"], game_no, now_iso(), n_answered,
         state["correct"], state["wrong"], state["score"], max(0, int(time_seconds or 0)), hints_used),
    )

    total = state["total_dataset"]
    new_next = (state["start_seq"] + n_answered) % max(total, 1)

    if state["type"] == "nq1":
        db.execute("UPDATE category_progress SET next_seq=?, completed_count=completed_count+? "
                   "WHERE user_id=? AND category_id=?",
                   (new_next, n_answered, user_id, state["category_id"]))

    elif state["type"] == "nq2":
        db.execute("UPDATE nq2_progress SET next_seq=? WHERE user_id=?", (new_next, user_id))

    elif state["type"] == "daily":
        prog = db.execute("SELECT * FROM daily_progress WHERE user_id=?", (user_id,)).fetchone()
        today = date.today()
        last = date.fromisoformat(prog["last_play_date"]) if prog["last_play_date"] else None
        if last == today - timedelta(days=1):
            current_streak = (prog["current_streak"] or 0) + 1
        elif last != today:
            current_streak = 1
        else:
            current_streak = prog["current_streak"] or 0
        longest_streak = max(prog["longest_streak"] or 0, current_streak)
        db.execute(
            "UPDATE daily_progress SET next_seq=?, last_play_date=?, answered_today=?, "
            "current_streak=?, longest_streak=? WHERE user_id=?",
            (new_next, today.isoformat(), n_answered, current_streak, longest_streak, user_id),
        )

    db.commit()
    _clear_state(db, user_id)
    return {"game_no": game_no, "score": state["score"], "correct": state["correct"],
            "wrong": state["wrong"], "questions_played": n_answered,
            "time_seconds": max(0, int(time_seconds or 0)), "category_name": state["category_name"]}


def exit_without_saving(user_id):
    _clear_state(get_db(), user_id)
