from flask import Blueprint, request, jsonify, g
from .routes import login_required
from . import quiz_engine as QE

api_bp = Blueprint("api", __name__)


@api_bp.route("/quiz/start", methods=["POST"])
@login_required
def quiz_start():
    data = request.get_json(force=True) or {}
    quiz_type = data.get("type")
    category_key = data.get("category")
    ok, err = QE.start_quiz(g.user["id"], quiz_type, category_key)
    if not ok:
        return jsonify({"ok": False, "error": err}), 400
    st = QE.get_state(g.user["id"])
    return jsonify({
        "ok": True,
        "category_name": st["category_name"],
        "total": st["max_index"],           # null (JSON) => unlimited
        "max_hints": st["max_hints"],
        "question": QE.get_question(g.user["id"], 0),
    })


@api_bp.route("/quiz/question/<int:index>", methods=["GET"])
@login_required
def quiz_question(index):
    q = QE.get_question(g.user["id"], index)
    if q is None:
        return jsonify({"ok": False, "error": "No active quiz or invalid index."}), 400
    return jsonify({"ok": True, "question": q})


@api_bp.route("/quiz/answer", methods=["POST"])
@login_required
def quiz_answer():
    data = request.get_json(force=True) or {}
    index = int(data.get("index", -1))
    option = data.get("option")
    q = QE.submit_answer(g.user["id"], index, option)
    if q is None:
        return jsonify({"ok": False, "error": "No active quiz or invalid index."}), 400
    st = QE.get_state(g.user["id"])
    return jsonify({"ok": True, "question": q, "score": st["score"],
                     "correct": st["correct"], "wrong": st["wrong"]})


@api_bp.route("/quiz/hint", methods=["POST"])
@login_required
def quiz_hint():
    data = request.get_json(force=True) or {}
    index = int(data.get("index", -1))
    result = QE.use_hint(g.user["id"], index)
    if result is None:
        return jsonify({"ok": False, "error": "No active quiz."}), 400
    if "error" in result:
        return jsonify({"ok": False, "error": result["error"]}), 400
    st = QE.get_state(g.user["id"])
    return jsonify({"ok": True, "question": result,
                     "hints_remaining": st["max_hints"] - len(st["hints"])})


@api_bp.route("/quiz/finish", methods=["POST"])
@login_required
def quiz_finish():
    data = request.get_json(force=True) or {}
    time_seconds = data.get("time_seconds", 0)
    result = QE.finish_and_save(g.user["id"], time_seconds)
    if result is None:
        return jsonify({"ok": False, "error": "No active quiz."}), 400
    return jsonify({"ok": True, "result": result})


@api_bp.route("/quiz/exit", methods=["POST"])
@login_required
def quiz_exit():
    QE.exit_without_saving(g.user["id"])
    return jsonify({"ok": True})


@api_bp.route("/quiz/state", methods=["GET"])
@login_required
def quiz_state():
    st = QE.get_state(g.user["id"])
    if not st:
        return jsonify({"ok": False})
    return jsonify({"ok": True, "type": st["type"], "category_name": st["category_name"],
                     "total": st["max_index"], "score": st["score"], "correct": st["correct"],
                     "wrong": st["wrong"], "hints_used": len(st["hints"]),
                     "max_hints": st["max_hints"], "answered_count": len(st["answers"])})
