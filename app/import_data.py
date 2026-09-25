"""
Imports the three quiz datasets into the SQLite database:
  - app/data_source/categories/*.csv(.gz)          -> Normal Quiz 1 (56 categories)
  - app/data_source/normal_quiz_2*.csv(.gz)         -> Normal Quiz 2 ("Play All Quiz")
  - app/data_source/daily_quiz*.csv(.gz)            -> Daily Quiz

A dataset may ship as a single file (e.g. daily_quiz.csv.gz) or split into
several numbered parts (e.g. normal_quiz_2_part1.csv.gz,
normal_quiz_2_part2.csv.gz, ...) -- this is how the large Normal Quiz 2
dataset stays under GitHub's 100MB-per-file limit even after gzip. Parts
are read in numeric order and treated as one continuous dataset; each
part must be a complete, valid CSV with its own header row.

Safe to re-run: skips any dataset that's already populated.
Runs automatically on first app start (see app/__init__.py).
"""
import csv
import glob
import gzip
import os
import re
import sys
import sqlite3

from .categories_meta import CATEGORIES
from .config import DATA_DIR

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CORRECT_RE = re.compile(r"^\s*([ABCD])\s*[\).:-]", re.IGNORECASE)
PART_NUM_RE = re.compile(r"_part(\d+)", re.IGNORECASE)


def letter_from_correct(raw, a, b, c, d):
    if raw:
        m = CORRECT_RE.match(raw)
        if m:
            return m.group(1).upper()
        text = raw.strip().lower()
        for letter, opt in (("A", a), ("B", b), ("C", c), ("D", d)):
            if opt and opt.strip().lower() == text:
                return letter
    return "A"


def _find_dataset_parts(base_path):
    """Returns an ordered list of file(s) making up this dataset.

    Accepts either a single file -- base_path + '.csv.gz' or '.csv' -- or
    multiple numbered parts -- base_path + '_part1.csv.gz',
    '_part2.csv.gz', etc. Gzip is preferred; plain '.csv' works too (e.g.
    if someone swaps in their own uncompressed file for local testing).
    """
    for ext in (".csv.gz", ".csv"):
        single = base_path + ext
        if os.path.exists(single):
            return [single]

    for ext in (".csv.gz", ".csv"):
        parts = sorted(
            glob.glob(f"{base_path}_part*{ext}"),
            key=lambda p: int(PART_NUM_RE.search(p).group(1)) if PART_NUM_RE.search(p) else 0,
        )
        if parts:
            return parts

    return []


def _rows(paths):
    """Yields CSV rows across one or more files, in order. Each file is
    read as its own complete CSV (its own header row)."""
    for path in paths:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, mode="rt", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row


def import_nq1(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] > 0:
        return
    cat_dir = os.path.join(DATA_DIR, "categories")
    for key, name, icon in CATEGORIES:
        paths = _find_dataset_parts(os.path.join(cat_dir, key))
        if not paths:
            continue
        cur.execute("INSERT INTO categories (key, name, icon, question_count) VALUES (?,?,?,0)",
                    (key, name, icon))
        cat_id = cur.lastrowid

        buf = []
        seq = 0
        for row in _rows(paths):
            q = (row.get("Question") or "").strip()
            if not q:
                continue
            a, b, c, d = (row.get("Option A", ""), row.get("Option B", ""),
                          row.get("Option C", ""), row.get("Option D", ""))
            correct = letter_from_correct(row.get("Correct Answer", ""), a, b, c, d)
            buf.append((cat_id, seq, q, a, b, c, d, correct,
                        row.get("Solution/Explanation", ""), row.get("Subcategory", "")))
            seq += 1
            if len(buf) >= 1000:
                cur.executemany(
                    "INSERT INTO questions_nq1 (category_id, seq, question, option_a, option_b, "
                    "option_c, option_d, correct, explanation, subcategory) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    buf)
                buf = []
        if buf:
            cur.executemany(
                "INSERT INTO questions_nq1 (category_id, seq, question, option_a, option_b, "
                "option_c, option_d, correct, explanation, subcategory) VALUES (?,?,?,?,?,?,?,?,?,?)",
                buf)
        cur.execute("UPDATE categories SET question_count=? WHERE id=?", (seq, cat_id))
        conn.commit()
        print(f"  NQ1 [{name}]: {seq} questions")


def import_nq2(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM questions_nq2")
    if cur.fetchone()[0] > 0:
        return
    paths = _find_dataset_parts(os.path.join(DATA_DIR, "normal_quiz_2"))
    if not paths:
        return
    if len(paths) > 1:
        print(f"  NQ2: reading {len(paths)} parts: {[os.path.basename(p) for p in paths]}")
    buf, seq = [], 0
    for row in _rows(paths):
        q = (row.get("Question") or "").strip()
        if not q:
            continue
        a, b, c, d = (row.get("Option A", ""), row.get("Option B", ""),
                      row.get("Option C", ""), row.get("Option D", ""))
        correct = letter_from_correct(row.get("Correct Answer", ""), a, b, c, d)
        buf.append((seq, q, a, b, c, d, correct, row.get("Solution/Explanation", ""),
                    row.get("Category", ""), row.get("Subcategory", "")))
        seq += 1
        if len(buf) >= 2000:
            cur.executemany(
                "INSERT INTO questions_nq2 (seq, question, option_a, option_b, option_c, option_d, "
                "correct, explanation, category, subcategory) VALUES (?,?,?,?,?,?,?,?,?,?)", buf)
            conn.commit()
            buf = []
            if seq % 20000 == 0:
                print(f"  NQ2: {seq} imported so far...")
    if buf:
        cur.executemany(
            "INSERT INTO questions_nq2 (seq, question, option_a, option_b, option_c, option_d, "
            "correct, explanation, category, subcategory) VALUES (?,?,?,?,?,?,?,?,?,?)", buf)
        conn.commit()
    print(f"  NQ2 total: {seq} questions")


def import_daily(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM questions_daily")
    if cur.fetchone()[0] > 0:
        return
    paths = _find_dataset_parts(os.path.join(DATA_DIR, "daily_quiz"))
    if not paths:
        return
    buf, seq = [], 0
    for row in _rows(paths):
        q = (row.get("Question") or "").strip()
        if not q:
            continue
        a, b, c, d = (row.get("Option A", ""), row.get("Option B", ""),
                      row.get("Option C", ""), row.get("Option D", ""))
        correct = letter_from_correct(row.get("Correct Answer", ""), a, b, c, d)
        buf.append((seq, q, a, b, c, d, correct, row.get("Solution/Explanation", ""),
                    row.get("Category", ""), row.get("Subcategory", "")))
        seq += 1
        if len(buf) >= 2000:
            cur.executemany(
                "INSERT INTO questions_daily (seq, question, option_a, option_b, option_c, option_d, "
                "correct, explanation, category, subcategory) VALUES (?,?,?,?,?,?,?,?,?,?)", buf)
            conn.commit()
            buf = []
            if seq % 20000 == 0:
                print(f"  Daily: {seq} imported so far...")
    if buf:
        cur.executemany(
            "INSERT INTO questions_daily (seq, question, option_a, option_b, option_c, option_d, "
            "correct, explanation, category, subcategory) VALUES (?,?,?,?,?,?,?,?,?,?)", buf)
        conn.commit()
    print(f"  Daily total: {seq} questions")


def run_import(db_path):
    conn = sqlite3.connect(db_path)
    print("Importing Normal Quiz 1 (56 categories)...")
    import_nq1(conn)
    print("Importing Normal Quiz 2 dataset...")
    import_nq2(conn)
    print("Importing Daily Quiz dataset...")
    import_daily(conn)
    conn.close()
    print("Import complete.")
