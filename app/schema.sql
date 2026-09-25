CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    location TEXT DEFAULT '',
    dark_mode INTEGER DEFAULT 0,
    joined_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '❓',
    question_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS questions_nq1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
    correct TEXT,
    explanation TEXT,
    subcategory TEXT
);
CREATE INDEX IF NOT EXISTS idx_nq1_cat_seq ON questions_nq1(category_id, seq);

CREATE TABLE IF NOT EXISTS questions_nq2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
    correct TEXT,
    explanation TEXT,
    category TEXT,
    subcategory TEXT
);
CREATE INDEX IF NOT EXISTS idx_nq2_seq ON questions_nq2(seq);

CREATE TABLE IF NOT EXISTS questions_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
    correct TEXT,
    explanation TEXT,
    category TEXT,
    subcategory TEXT
);
CREATE INDEX IF NOT EXISTS idx_daily_seq ON questions_daily(seq);

CREATE TABLE IF NOT EXISTS category_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    next_seq INTEGER DEFAULT 0,
    completed_count INTEGER DEFAULT 0,
    UNIQUE(user_id, category_id)
);

CREATE TABLE IF NOT EXISTS nq2_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    next_seq INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    next_seq INTEGER DEFAULT 0,
    last_play_date TEXT,
    answered_today INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0
);

-- Holds the in-progress quiz game (server-side, not a browser cookie) so
-- a session can grow to any number of answered questions without ever
-- hitting a browser cookie-size limit. One row per user; replaced on
-- each /api/quiz/start and deleted on finish/exit.
CREATE TABLE IF NOT EXISTS active_quiz (
    user_id INTEGER PRIMARY KEY,
    state_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quiz_type TEXT NOT NULL,
    category_name TEXT,
    game_no INTEGER,
    played_at TEXT NOT NULL,
    questions_played INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    wrong INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    time_seconds INTEGER DEFAULT 0,
    hints_used INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_history_user ON game_history(user_id, played_at);
