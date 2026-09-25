# Quiz Master

A full-stack quiz web app: Flask backend, server-rendered HTML/CSS/JS frontend,
SQLite database, session-based authentication. Built from the Quiz Master
spec (`quiz_master_details_web_site.pdf`) and the provided UI screenshots.

## Screenshots

### 🏠 Home
![Home](screenshots/home.png)
The first page after login. Shows a welcome banner, quick-start cards for
**Play All Quiz** and the **Daily Challenge**, a shortcut back into
whichever Normal Quiz 1 category you played most recently, and a
breakdown of your Normal Quiz 1 activity by category (questions played,
percentages, and your most-played category).

### 🧩 Quizzes (56 categories)
![Quizzes](screenshots/quizzes.png)
The Normal Quiz 1 hub. All 56 categories (History, Science, Python,
Cricket, and so on) are listed as searchable/filterable cards, each
showing how many questions that category has and a **Play Now** button
that jumps straight into the Quiz Playing page for it.

### 🎮 Quiz Playing
![Quiz Playing](screenshots/quiz-playing.png)
The shared gameplay screen for Normal Quiz 1 & 2. One question at a
time, four options, a live status bar (question count, timer, hints
remaining, correct/wrong/score), and instant feedback: the moment you
pick an answer, it shows whether you were right, highlights the correct
option, and reveals the explanation -- no extra click needed. Hint,
Previous/Next, Pause, Save & Finish, and Exit are all here too. Normal
Quiz 1 & 2 are unlimited-length -- you keep going until you click
**Save & Finish**.

### 📅 Daily Quiz
![Daily Quiz](screenshots/daily-quiz.png)
The same gameplay screen, but for the Daily Challenge: capped at 50
questions per calendar day, no hints, and only one attempt allowed per
day (trying again the same day is blocked with a friendly message).
Completing it builds your Daily Quiz streak, shown on your Profile page.

### 🕘 History
![History](screenshots/history.png)
A complete, searchable log of every quiz you've ever played across all
three quiz types -- date, game number, category, time spent, and score
for each one, with search, a category filter, a date-range filter, and
pagination.

### 🏆 Leaderboard
![Leaderboard](screenshots/leaderboard.png)
Ranks every player by total score, combining Normal Quiz 1, Normal Quiz
2, and Daily Quiz together. Includes All Time / This Month / This Week
/ Today filters, your own row highlighted so it's easy to find, and a
"Your Rank" summary.

### 👤 Profile
![Profile](screenshots/profile.png)
Your personal dashboard for **Normal Quiz 1 only**: account details, a
"Clear All Data" option (with a confirmation step), overall stats
(games played, accuracy, average score, personal bests), your Daily
Quiz streak (current + longest), and a per-category performance
breakdown.

### 📊 All Quiz
![All Quiz](screenshots/all-quiz.png)
The detailed stats page for **Normal Quiz 2 ("Play All Quiz") only**:
totals, personal bests, and overall performance metrics (accuracy,
average time/score/questions per game, correct vs. wrong rate).

## Quick start

```bash
cd quizmaster
pip install -r requirements.txt
python run.py
```

Open **http://localhost:5000**, register an account, and start playing.

On the very first run, the app automatically imports the three quiz
datasets from `app/data_source/` into `instance/quizmaster.db`. This
takes about 10-20 seconds (there are ~713,000 questions total across all
three datasets, shipped gzip-compressed). Every run after that is instant.

## Putting this on GitHub

**Upload everything in this folder as-is, with one exception: never
upload the `instance/` folder** (delete it first if it exists locally --
`python run.py` recreates it automatically). The provided `.gitignore`
already excludes it, along with `__pycache__/` and stray `.pyc` files,
so if you commit normally none of that will be included.

Concretely, here's what should end up in the repo:

| Path | Upload? | Why |
|---|---|---|
| `app/` (all `.py` files, `templates/`, `static/`) | ✅ Yes | the application code |
| `app/data_source/*.csv.gz`, `app/data_source/categories/*.csv.gz` | ✅ Yes | the 3 datasets, gzip-compressed. Every file is under GitHub's 100MB limit this way (the largest is ~33MB) |
| `app/schema.sql` | ✅ Yes | database schema |
| `requirements.txt` | ✅ Yes | Python dependencies |
| `Procfile` | ✅ Yes | tells most hosting platforms how to start the app |
| `run.py`, `README.md`, `.gitignore` | ✅ Yes | entry point + docs |
| `instance/` (and `instance/quizmaster.db` if present) | ❌ **No** | this is the generated database -- it can contain real user data/password hashes from your own local testing, and it gets rebuilt automatically on first run anyway |
| `__pycache__/`, `*.pyc` | ❌ No | compiled Python cache, regenerated automatically |
| Any plain `*.csv` you may have decompressed locally for testing | ❌ No | already gitignored; keep only the `.csv.gz` versions in the repo |

If you're using the GitHub website's drag-and-drop uploader or
GitHub Desktop, just uploading the entire `quizmaster` folder is fine as
long as `instance/` isn't inside it when you drag it in. If you're using
git on the command line, `git add .` from inside the `quizmaster/`
folder will correctly respect `.gitignore` and do the right thing.

## Deploying: the one thing that matters most

**This app needs a persistent disk.** Everything -- every registered
account, every quiz history entry, every score, Daily Quiz streaks --
lives in the single SQLite file at `instance/quizmaster.db`. That's
completely fine on a normal server or VM, but it is a real problem on
hosting platforms whose filesystem is **ephemeral** (wiped on every
restart or redeploy): on those, your entire database -- including every
user's account and quiz history -- would vanish the next time the app
restarts, which can happen automatically at any time (crashes, scaling
events, routine maintenance), not just when you redeploy.

Before you pick a host, confirm it gives you a **persistent volume/disk**
mounted at a path you control, and point the app at it:

```
QUIZMASTER_DATABASE_PATH=/var/data/quizmaster.db   (or wherever your persistent volume is mounted)
```

Platforms known to need extra care here:
- **Render / Railway / Heroku free or basic web-service tiers** --
  typically ephemeral by default. Render and Railway both offer an
  add-on "persistent disk/volume" (sometimes paid) -- attach one and set
  `QUIZMASTER_DATABASE_PATH` to a file inside it. Without that add-on,
  don't use these for anything beyond a demo.
- **PythonAnywhere, a small VPS (DigitalOcean/Linode/EC2), or any host
  with a normal persistent filesystem** -- works with zero extra setup,
  the default `instance/` folder is fine.

If you'd rather not think about this at all, the more robust long-term
fix is swapping SQLite for a managed hosted database (e.g. your host's
managed Postgres/MySQL) -- ask if you'd like that change made.

## Required environment variables in production

| Variable | Required? | Purpose |
|---|---|---|
| `QUIZMASTER_SECRET_KEY` | **Yes** | signs login sessions; the app prints a warning on startup if you skip this and still uses an insecure default |
| `QUIZMASTER_DATABASE_PATH` | Recommended | absolute path to your persistent volume (see above); defaults to `instance/quizmaster.db` next to the app |
| `PORT` | Usually set automatically by your host | which port to bind to |

Start command for platforms that read a `Procfile` (Render, Railway,
Heroku) is already provided:
```
web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```
If your platform instead wants an explicit start command, use the same
line. The `--timeout 120` gives the first-boot dataset import (10-20s)
comfortable headroom so the platform doesn't kill the worker as
unresponsive during that first startup.

## After you deploy: how to verify everything works

I can't reach your live URL myself (I have no network access once this
conversation ends), so please run through this checklist on the
deployed site once it's up -- it exercises every feature end to end:

1. **Register** a brand-new account (unique username/email) -- confirm
   the Gender pills, password eye-toggle, and confirm-password
   validation all work, and that it logs you straight in.
2. **Logout**, then **Login** again with that same account -- confirm
   the eye-toggle shows/hides the password there too.
3. **Home page**: confirm the welcome message shows your username and
   the layout matches (Play All Quiz, Daily Challenge cards, etc.).
4. **Quizzes page**: search for a category (e.g. "Python"), confirm
   filtering works, then click Play Now on any category.
5. **Play a Normal Quiz 1 game**: answer a few questions, confirm the
   correct/wrong result + explanation appear immediately (no separate
   click needed), try a Hint, click Previous/Next, then **Finish & Save**.
6. **History page**: confirm that game just appears at the top with the
   right category, score, and time.
7. **Profile page**: confirm the stats updated, and try **Clear All
   Data** -- confirm the confirmation modal appears, and after
   confirming, your history/stats reset to zero.
8. **Play All Quiz** (Normal Quiz 2) from the Home page, finish it, then
   check the **All Quiz** page reflects it (and Profile does *not*,
   since Profile is Normal-Quiz-1-only).
9. **Daily Challenge**: play it once, confirm it blocks a second
   attempt the same day, and check the streak shows on Profile.
10. **Leaderboard**: confirm your account appears with the right totals,
    and that the time-period filters (Today/Week/Month/All Time) work.
11. **Dark mode toggle**: confirm it switches theme and persists across
    a page reload/re-login.
12. **Open the same account from a second browser/device** and confirm
    your data (history, scores, progress) is identical -- this proves
    the persistent-disk setup from the section above is actually
    working. If it *isn't* persisting, that's the #1 thing to check
    first (see "Deploying" section above).

If anything in that list misbehaves on the live site, tell me exactly
which step and what you saw (a screenshot helps a lot, like before) and
I'll fix it.

## What's included

- **Normal Quiz 1** — all 56 categories from `quiz_dataset_56_categories.zip`,
  each played independently, browsable/searchable on the Quizzes page.
- **Normal Quiz 2** ("Play All Quiz") — its own dataset
  (`all_quiz_category_is_normal_quiz_2.csv`), started from the Home page.
- **Daily Quiz** — its own dataset (`daily_quiz.csv`), 50 questions/day,
  one attempt per calendar day, no hints.
- Scoring: +10 correct / −5 wrong (never below 0 within a single game),
  hints don't affect score, max 5 hints per game for Normal Quiz 1 & 2,
  0 hints for Daily Quiz.
- Sequential, non-repeating question delivery per category/dataset per
  user, wrapping back to the start once a dataset is exhausted.
- Pages: Home, Quizzes (56 categories), History, Leaderboard, Profile
  (Normal Quiz 1 stats + Daily Quiz streak), All Quiz (Normal Quiz 2
  stats), Quiz Playing page (shared by Normal Quiz 1 & 2), Daily Quiz
  Playing page, Login, Register.
- Dark mode (persisted per account), left sidebar nav matching the
  provided screenshots, logout confirmation modal.

## Data scope per page (as specified)

Each page pulls from a different slice of your quiz data on purpose --
here's exactly what feeds each one:

**Profile** — draws from **Normal Quiz 1 only**. Every stat here (games
played, accuracy, personal bests, category-by-category performance) is
calculated purely from your Normal Quiz 1 history. The one exception is
the Streak card, which comes from your Daily Quiz activity (consecutive
calendar days completed).

**All Quiz** — draws from **Normal Quiz 2 only** (the "Play All Quiz"
mode). Same kind of stats as Profile, but scoped entirely to your Play
All Quiz games instead.

**History** — draws from **all 3 quiz types combined**: Normal Quiz 1,
Normal Quiz 2, and Daily Quiz all show up here as one searchable,
filterable log, since History's job is just to be your complete personal
record of every game you've ever played.

**Leaderboard** — draws from **all 3 quiz types combined, across every
user account**. Your total score/questions/games/time here is the sum
of everything you've played in any mode, ranked against everyone else's
same combined total.

**Home** — draws from your **Normal Quiz 1** activity for the category
breakdown and "most played category" widgets, plus quick-launch
shortcuts into Play All Quiz (Normal Quiz 2) and the Daily Challenge.

## Design decisions & how the spec was interpreted

The spec (80-page doc) was occasionally ambiguous or internally
inconsistent (e.g. it says "38 categories" in one place but lists — and
the ZIP contains — 56; example question counts in the mockups don't
match the real datasets). Where that happened, this build:

- Uses the **real counts** from your datasets, not the mockup's example
  numbers (e.g. Science has ~6,600 questions, not 250 — the design
  *layout* is unchanged, only the live numbers differ).
- Shows **all 56 categories** on the Quizzes page (the ZIP's actual
  contents), since the spec's full category list (spread across a few
  pages) enumerates exactly 56 names matching the 56 CSV files.
- Implements **Normal Quiz 1 & 2 games as 15 questions**, and **Daily
  Quiz as up to 50 questions/day**, per the spec's explicit examples.
- "Category" column for Normal Quiz 2 history rows reads **"Over All"**
  (spec's literal wording) since that mode isn't tied to one category.
- **Finish & Save** persists exactly what was answered so far (so an
  early save never silently skips unanswered questions in future games);
  **Exit** discards the whole in-progress game, matching the spec.

## Database: SQLite (with a note on MySQL)

The spec asks for MySQL. This package uses **SQLite via Python's
built-in `sqlite3` module** instead, for one practical reason: it makes
the whole project runnable with just `pip install -r requirements.txt`
and no external database server to install/configure — genuinely
"unzip and run" (see the "Deploying" section above for the one caveat
this brings: it needs a persistent disk in production).

All the SQL in `app/db.py`, `app/quiz_engine.py`, `app/stats.py`,
`app/auth.py`, and `app/import_data.py` is plain, portable SQL (no
SQLite-only features beyond `AUTOINCREMENT`). To run this on MySQL
instead:

1. `pip install pymysql`
2. Swap the `sqlite3.connect(...)` calls in `app/db.py` for a PyMySQL
   connection (and adjust `?` placeholders to `%s`).
3. Point it at a MySQL server via connection settings of your choice.

## Cross-device sync

Because all quiz progress, scores, history, and settings are written to
the server-side database (not local storage), logging into the same
account from a different device/browser picks up exactly where you left
off — this is inherent to the server-backed design, no extra code
needed.

## Project structure

```
quizmaster/
  run.py                  # entry point: python run.py (local) / gunicorn run:app (prod)
  Procfile                # start command for Render/Railway/Heroku-style platforms
  requirements.txt
  app/
    __init__.py            # app factory, auto-imports data on first run
    config.py
    db.py                  # sqlite3 connection helper
    schema.sql              # database schema
    categories_meta.py      # the 56 categories: key, display name, icon
    import_data.py          # CSV(.gz) -> database importer
    quiz_engine.py           # gameplay logic: scoring, hints, sessions
    stats.py                 # aggregation for Profile/All Quiz/Leaderboard/Home
    auth.py                  # register/login/logout
    routes.py                # page routes
    api.py                   # JSON API used by the quiz-playing page
    data_source/              # the 3 datasets, gzip-compressed (*.csv.gz)
    static/
      css/style.css
      js/app.js               # dark mode + logout modal
      js/auth.js               # password show/hide toggle
      js/quiz.js               # quiz-playing page logic
      img/logo.png
    templates/                 # all HTML pages
  instance/                    # quizmaster.db is created here on first run (gitignored)
```

## Notes / things you may want to adjust

- The Quiz Playing page's timer/pause is client-side JavaScript; the
  final time is sent to the server only when you click Finish & Save.
- "Clear All Data" on the Profile page wipes only the logged-in
  account's own quiz history/progress/scores after a confirmation
  prompt; login, profile info, and other accounts are never touched.
