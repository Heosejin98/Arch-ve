import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "arch_violations.db"


def init_db():
    """테이블 생성 (IF NOT EXISTS)"""
    with get_connection() as conn:
        conn.executescript("""
            PRAGMA journal_mode = WAL;

            CREATE TABLE IF NOT EXISTS arch_checks (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                repo                TEXT    NOT NULL,
                pr_number           INTEGER,
                branch              TEXT    NOT NULL DEFAULT 'main',
                commit_sha          TEXT,
                author              TEXT    NOT NULL,
                checked_at          TEXT    NOT NULL DEFAULT (datetime('now')),
                violation_count     INTEGER NOT NULL DEFAULT 0,
                prev_violation_count INTEGER,
                delta               INTEGER,
                total_files         INTEGER,
                total_dependencies  INTEGER,
                raw_result          TEXT
            );

            CREATE TABLE IF NOT EXISTS layer_violations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id    INTEGER NOT NULL REFERENCES arch_checks(id),
                from_layer  TEXT    NOT NULL,
                to_layer    TEXT    NOT NULL,
                from_module TEXT,
                to_module   TEXT
            );
        """)


@contextmanager
def get_connection():
    """Row factory 포함 SQLite 커넥션 반환"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
