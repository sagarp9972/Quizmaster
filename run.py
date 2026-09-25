"""
Run the Quiz Master app locally:

    pip install -r requirements.txt
    python run.py

Then open http://localhost:5000

On first run this will automatically import the quiz datasets from
app/data_source/ into the database -- this takes about 10-20 seconds.
Subsequent runs are instant.

For a real deployment, don't run this file directly -- use a production
WSGI server instead, e.g.:

    gunicorn run:app --bind 0.0.0.0:$PORT

(this module exposes the `app` object gunicorn/uWSGI need). See the
Procfile and README.md for platform-specific notes.
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
