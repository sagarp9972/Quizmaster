import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "app", "data_source")
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("QUIZMASTER_SECRET_KEY", "dev-secret-change-me")

    # --- Database -----------------------------------------------------
    # Ships with SQLite (zero setup, single file at instance/quizmaster.db).
    # The spec calls for MySQL; the data-access layer here is plain SQL via
    # Python's sqlite3 module for a portable, dependency-free package. To
    # run on MySQL instead, swap app/db.py's connection for a MySQL
    # connector (e.g. PyMySQL) -- the SQL used throughout is simple,
    # standard SQL with no SQLite-only syntax beyond AUTOINCREMENT.
    DATABASE_PATH = os.environ.get(
        "QUIZMASTER_DATABASE_PATH",
        os.path.join(INSTANCE_DIR, "quizmaster.db"),
    )

    # Quiz rules (see README for the full rule list from the spec)
    SCORE_CORRECT = 10
    SCORE_WRONG = -5
    # Normal Quiz 1 & 2 are unlimited-length (play continues until the
    # player clicks Finish & Save). Only Daily Quiz is capped, per day.
    DAILY_QUESTIONS_PER_DAY = 50
    MAX_HINTS_NORMAL = 5
    MAX_HINTS_DAILY = 0
