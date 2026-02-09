"""
SQLite storage for detection events, triggers, and alert history.
"""
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime

# DB path next to this package
_BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE, "analytics.db")
_local = threading.local()


def _conn():
    if not getattr(_local, "conn", None):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


@contextmanager
def cursor():
    c = _conn().cursor()
    try:
        yield c
        _conn().commit()
    except Exception:
        _conn().rollback()
        raise
    finally:
        c.close()


def init_db():
    with cursor() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS detection_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id TEXT NOT NULL,
                rtsp_url TEXT,
                class_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                ts REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_det_ts ON detection_events(ts)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_det_stream ON detection_events(stream_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_det_class ON detection_events(class_name)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                stream_id TEXT,
                rule_type TEXT NOT NULL,
                rule_config TEXT NOT NULL,
                cooldown_sec INTEGER DEFAULT 300,
                notify_email INTEGER DEFAULT 0,
                notify_sms INTEGER DEFAULT 0,
                notify_whatsapp INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            c.execute("ALTER TABLE triggers ADD COLUMN notify_whatsapp INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # column already exists (migration from older DB)

        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER NOT NULL,
                message TEXT,
                channel TEXT NOT NULL,
                sent_at REAL NOT NULL,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_trigger ON alerts_sent(trigger_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_sent_at ON alerts_sent(sent_at)")


def insert_detection(stream_id: str, rtsp_url: str, class_name: str, confidence: float, ts: float = None):
    if ts is None:
        ts = time.time()
    with cursor() as c:
        c.execute(
            "INSERT INTO detection_events (stream_id, rtsp_url, class_name, confidence, ts) VALUES (?,?,?,?,?)",
            (stream_id, rtsp_url, class_name, confidence, ts),
        )
        return c.lastrowid


def get_detections(stream_id=None, class_name=None, from_ts=None, to_ts=None, limit=5000):
    with cursor() as c:
        q = "SELECT * FROM detection_events WHERE 1=1"
        params = []
        if stream_id:
            q += " AND stream_id = ?"
            params.append(stream_id)
        if class_name:
            q += " AND class_name = ?"
            params.append(class_name)
        if from_ts is not None:
            q += " AND ts >= ?"
            params.append(from_ts)
        if to_ts is not None:
            q += " AND ts <= ?"
            params.append(to_ts)
        q += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]


def get_summary(from_ts, to_ts, stream_id=None, group_by="class"):
    """group_by: 'class' | 'hour' | 'day'"""
    with cursor() as c:
        if group_by == "class":
            q = """
                SELECT class_name AS key, COUNT(*) AS count
                FROM detection_events WHERE ts >= ? AND ts <= ?
            """
            params = [from_ts, to_ts]
            if stream_id:
                q += " AND stream_id = ?"
                params.append(stream_id)
            q += " GROUP BY class_name ORDER BY count DESC"
        elif group_by == "hour":
            q = """
                SELECT strftime('%Y-%m-%d %H:00', datetime(ts, 'unixepoch', 'localtime')) AS key, COUNT(*) AS count
                FROM detection_events WHERE ts >= ? AND ts <= ?
            """
            params = [from_ts, to_ts]
            if stream_id:
                q += " AND stream_id = ?"
                params.append(stream_id)
            q += " GROUP BY key ORDER BY key"
        else:  # day
            q = """
                SELECT strftime('%Y-%m-%d', datetime(ts, 'unixepoch', 'localtime')) AS key, COUNT(*) AS count
                FROM detection_events WHERE ts >= ? AND ts <= ?
            """
            params = [from_ts, to_ts]
            if stream_id:
                q += " AND stream_id = ?"
                params.append(stream_id)
            q += " GROUP BY key ORDER BY key"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]


def get_triggers(enabled_only=True):
    with cursor() as c:
        q = "SELECT * FROM triggers"
        if enabled_only:
            q += " WHERE enabled = 1"
        q += " ORDER BY id"
        c.execute(q)
        return [dict(r) for r in c.fetchall()]


def add_trigger(name, stream_id, rule_type, rule_config, cooldown_sec=300, notify_email=False, notify_sms=False, notify_whatsapp=False):
    with cursor() as c:
        c.execute(
            """INSERT INTO triggers (name, stream_id, rule_type, rule_config, cooldown_sec, notify_email, notify_sms, notify_whatsapp)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, stream_id, rule_type, rule_config, cooldown_sec, 1 if notify_email else 0, 1 if notify_sms else 0, 1 if notify_whatsapp else 0),
        )
        return c.lastrowid


def delete_trigger(trigger_id):
    with cursor() as c:
        c.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))


def toggle_trigger(trigger_id, enabled: bool):
    with cursor() as c:
        c.execute("UPDATE triggers SET enabled = ? WHERE id = ?", (1 if enabled else 0, trigger_id))


def last_alert_time(trigger_id):
    with cursor() as c:
        c.execute("SELECT MAX(sent_at) AS t FROM alerts_sent WHERE trigger_id = ?", (trigger_id,))
        r = c.fetchone()
        return r["t"] if r and r["t"] is not None else 0


def record_alert_sent(trigger_id, message, channel):
    with cursor() as c:
        c.execute(
            "INSERT INTO alerts_sent (trigger_id, message, channel, sent_at) VALUES (?,?,?,?)",
            (trigger_id, message, channel, time.time()),
        )
