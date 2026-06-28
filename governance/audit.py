import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit_log.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            note_hash TEXT,
            note_preview TEXT,
            codes_returned TEXT,
            total_codes INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            note_preview TEXT,
            entity TEXT,
            code TEXT,
            action TEXT,
            corrected_code TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS code_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT,
            code TEXT,
            accept_count INTEGER DEFAULT 0,
            reject_count INTEGER DEFAULT 0,
            weight REAL DEFAULT 1.0,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_request(note, suggested_codes):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO audit_log 
        (timestamp, note_hash, note_preview, codes_returned, total_codes)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        str(hash(note)),
        note[:100],
        json.dumps([s["primary_code"] for s in suggested_codes]),
        len(suggested_codes)
    ))
    conn.commit()
    conn.close()


def log_feedback(note, entity, code, action, corrected_code=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)

    # Check if feedback already exists for this note+code
    existing_feedback = conn.execute("""
        SELECT id, action FROM feedback
        WHERE note_preview = ? AND code = ?
    """, (note[:100], code)).fetchone()

    if existing_feedback:
        # Update existing feedback instead of adding new
        conn.execute("""
            UPDATE feedback
            SET action=?, timestamp=?, corrected_code=?
            WHERE id=?
        """, (action, datetime.now().isoformat(), corrected_code, existing_feedback[0]))
    else:
        # Insert new feedback
        conn.execute("""
            INSERT INTO feedback
            (timestamp, note_preview, entity, code, action, corrected_code)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            note[:100],
            entity,
            code,
            action,
            corrected_code
        ))

    # Recalculate weights from scratch based on all feedback
    all_feedback = conn.execute("""
        SELECT action FROM feedback WHERE code = ?
    """, (code,)).fetchall()

    accept_count = sum(1 for f in all_feedback if f[0] == "accept")
    reject_count = sum(1 for f in all_feedback if f[0] == "reject")
    total = accept_count + reject_count
    weight = round((accept_count / total) * 2.0, 4) if total > 0 else 1.0

    existing_weight = conn.execute("""
        SELECT id FROM code_weights WHERE entity = ? AND code = ?
    """, (entity, code)).fetchone()

    if existing_weight:
        conn.execute("""
            UPDATE code_weights
            SET accept_count=?, reject_count=?, weight=?, last_updated=?
            WHERE id=?
        """, (accept_count, reject_count, weight, datetime.now().isoformat(), existing_weight[0]))
    else:
        conn.execute("""
            INSERT INTO code_weights
            (entity, code, accept_count, reject_count, weight, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entity, code, accept_count, reject_count, weight, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_code_weight(entity, code):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    result = conn.execute("""
        SELECT weight FROM code_weights
        WHERE entity = ? AND code = ?
    """, (entity, code)).fetchone()
    conn.close()
    return result[0] if result else 1.0


def get_feedback_stats():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    accepts = conn.execute("SELECT COUNT(*) FROM feedback WHERE action='accept'").fetchone()[0]
    rejects = conn.execute("SELECT COUNT(*) FROM feedback WHERE action='reject'").fetchone()[0]
    conn.close()
    return {"total": total, "accepts": accepts, "rejects": rejects}