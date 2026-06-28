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