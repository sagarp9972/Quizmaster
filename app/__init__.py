import sqlite3
from flask import Flask, session, g

from .config import Config
from .db import init_db, get_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config["SECRET_KEY"] == "dev-secret-change-me":
        print("WARNING: Using the default SECRET_KEY. Set the QUIZMASTER_SECRET_KEY "
              "environment variable before deploying publicly (see README.md).")

    init_db(app)

    with app.app_context():
        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        cur = conn.execute("SELECT COUNT(*) FROM categories")
        needs_import = cur.fetchone()[0] == 0
        conn.close()
        if needs_import:
            from .import_data import run_import
            print("First run detected: importing quiz datasets (this can take a minute)...")
            run_import(app.config["DATABASE_PATH"])

    from .auth import auth_bp
    from .routes import main_bp
    from .api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.before_request
    def load_user():
        g.user = None
        uid = session.get("user_id")
        if uid:
            db = get_db()
            g.user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    @app.context_processor
    def inject_globals():
        return {"current_user": g.get("user")}

    return app
