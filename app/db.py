import os
import sqlite3
from datetime import datetime

from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())
    _migrate(conn)
    conn.commit()
    conn.close()
    app.teardown_appcontext(close_db)


def _migrate(conn):
    """Add columns introduced after the initial release to any database
    file created by an earlier version of this app, so existing accounts
    (and their quiz history/progress) keep working without a reset."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "full_name" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''")
    if "gender" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT ''")


def now_iso():
    return datetime.utcnow().isoformat(sep=" ", timespec="seconds")
