import sqlite3
import json
from datetime import datetime
from pathlib import Path
from backend.config import DB_PATH


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                module      TEXT NOT NULL,
                question    TEXT NOT NULL,
                answer      TEXT,
                sources     TEXT,
                duration_ms INTEGER
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON query_logs(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_module ON query_logs(module)
        """)
        conn.commit()


def log_query(
    module: str,
    question: str,
    answer: str = "",
    sources: list[str] | None = None,
    duration_ms: int = 0,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO query_logs
               (timestamp, module, question, answer, sources, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                module,
                question,
                answer[:2000],
                json.dumps(sources or [], ensure_ascii=False),
                duration_ms,
            ),
        )
        conn.commit()


def get_top_questions(limit: int = 20, module: str = "all") -> list[dict]:
    with _get_conn() as conn:
        if module == "all":
            rows = conn.execute(
                """SELECT question, COUNT(*) as cnt
                   FROM query_logs
                   GROUP BY question
                   ORDER BY cnt DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT question, COUNT(*) as cnt
                   FROM query_logs
                   WHERE module = ?
                   GROUP BY question
                   ORDER BY cnt DESC
                   LIMIT ?""",
                (module, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def get_daily_stats(days: int = 30) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT substr(timestamp, 1, 10) as date,
                      COUNT(*) as total,
                      COUNT(DISTINCT module) as modules_used
               FROM query_logs
               WHERE timestamp >= date('now', ?)
               GROUP BY date
               ORDER BY date""",
            (f"-{days} days",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_module_stats() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT module, COUNT(*) as cnt
               FROM query_logs
               GROUP BY module
               ORDER BY cnt DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_logs(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT id, timestamp, module, question, duration_ms
               FROM query_logs
               ORDER BY id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_total_count() -> int:
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()
    return row[0] if row else 0


init_db()
