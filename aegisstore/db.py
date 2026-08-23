"""
db.py — SQLite storage for AegisStore.
Tables:
  usage_history : disk-usage snapshots over time (for growth prediction)
  candidates    : files identified as optimization candidates + their context
  decisions     : risk score + action tier assigned to each candidate
  audit_log     : every action AegisStore actually took (quarantine, undo, etc.)
"""
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "aegisstore.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS usage_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL,
        path TEXT,
        used_bytes INTEGER,
        total_bytes INTEGER
    );

    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_time REAL,
        path TEXT,
        size_bytes INTEGER,
        last_accessed REAL,
        duplicate_of TEXT,
        classification TEXT,
        confidence REAL
    );

    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER,
        decision_time REAL,
        active_process INTEGER,
        package_owned INTEGER,
        git_tracked INTEGER,
        cpu_percent REAL,
        io_wait_percent REAL,
        risk_tier TEXT,
        action TEXT,
        reason TEXT,
        FOREIGN KEY(candidate_id) REFERENCES candidates(id)
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_time REAL,
        path TEXT,
        action TEXT,
        detail TEXT,
        quarantine_path TEXT,
        reversible INTEGER
    );
    """)
    conn.commit()
    conn.close()


def log_usage(path, used_bytes, total_bytes):
    conn = get_conn()
    conn.execute(
        "INSERT INTO usage_history (timestamp, path, used_bytes, total_bytes) VALUES (?,?,?,?)",
        (time.time(), str(path), used_bytes, total_bytes),
    )
    conn.commit()
    conn.close()


def save_candidate(c):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO candidates (scan_time, path, size_bytes, last_accessed, duplicate_of, classification, confidence)
           VALUES (?,?,?,?,?,?,?)""",
        (time.time(), str(c["path"]), c["size_bytes"], c["last_accessed"],
         c.get("duplicate_of"), c["classification"], c["confidence"]),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def save_decision(candidate_id, d):
    conn = get_conn()
    conn.execute(
        """INSERT INTO decisions (candidate_id, decision_time, active_process, package_owned, git_tracked,
           cpu_percent, io_wait_percent, risk_tier, action, reason)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (candidate_id, time.time(), int(d["active_process"]), int(d["package_owned"]), int(d["git_tracked"]),
         d["cpu_percent"], d["io_wait_percent"], d["risk_tier"], d["action"], d["reason"]),
    )
    conn.commit()
    conn.close()


def log_action(path, action, detail, quarantine_path=None, reversible=True):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log (event_time, path, action, detail, quarantine_path, reversible) VALUES (?,?,?,?,?,?)",
        (time.time(), str(path), action, detail, str(quarantine_path) if quarantine_path else None, int(reversible)),
    )
    conn.commit()
    conn.close()


def recent_audit(limit=20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def usage_series(path):
    conn = get_conn()
    rows = conn.execute(
        "SELECT timestamp, used_bytes, total_bytes FROM usage_history WHERE path=? ORDER BY timestamp", (str(path),)
    ).fetchall()
    conn.close()
    return rows
