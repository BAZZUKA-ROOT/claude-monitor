import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "monitor.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ts           TEXT NOT NULL,
                period_start TEXT,
                period_end   TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens  INTEGER DEFAULT 0,
                cost_usd      REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS alerts_fired (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                period     TEXT NOT NULL,
                threshold  INTEGER NOT NULL,
                fired_at   TEXT NOT NULL,
                UNIQUE(period, threshold)
            );
        """)


def save_snapshot(data: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO snapshots
              (ts, period_start, period_end, input_tokens, output_tokens, total_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            data.get("period_start"),
            data.get("period_end"),
            data.get("input_tokens", 0),
            data.get("output_tokens", 0),
            data.get("total_tokens", 0),
            data.get("cost_usd", 0.0),
        ))


def get_latest_snapshot():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_daily_history(days: int = 7):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT date(ts) as day,
                   MAX(total_tokens) as tokens,
                   MAX(cost_usd)     as cost
            FROM snapshots
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
        """, (days,)).fetchall()
        return [dict(r) for r in rows]


def alert_already_fired(period: str, threshold: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM alerts_fired WHERE period=? AND threshold=?",
            (period, threshold)
        ).fetchone()
        return row is not None


def mark_alert_fired(period: str, threshold: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO alerts_fired (period, threshold, fired_at) VALUES (?,?,?)",
            (period, threshold, datetime.utcnow().isoformat())
        )
