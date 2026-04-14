import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pyq_questions.db")


# -----------------------------
# CONNECTION (SAFE MODE)
# -----------------------------
def _get_conn():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False  # important for Flask
    )
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# INIT DB (PRODUCTION SAFE)
# -----------------------------
def init_db():
    with _get_conn() as conn:
        # Enable WAL mode (important for performance + concurrency)
        conn.execute("PRAGMA journal_mode=WAL;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                options TEXT,
                answer TEXT,
                chapter TEXT
            )
        """)
        conn.commit()


# -----------------------------
# INSERT QUESTION
# -----------------------------
def insert_question(data: dict) -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO questions (question, options, answer, chapter)
            VALUES (?, ?, ?, ?)
            """,
            (
                data.get("question", ""),
                data.get("options", "[]"),
                data.get("answer", ""),
                data.get("chapter", "Unknown"),
            ),
        )
        conn.commit()
        return cursor.lastrowid


# -----------------------------
# CHAPTER STATS
# -----------------------------
def get_chapter_stats() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT chapter, COUNT(*) AS count
            FROM questions
            GROUP BY chapter
            ORDER BY count DESC
        """).fetchall()

    return [
        {
            "chapter": row["chapter"],
            "count": row["count"]
        }
        for row in rows
    ]
