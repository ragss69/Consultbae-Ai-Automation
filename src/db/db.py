"""
Thin SQLite access layer for ConsultBae Task 1.

Deliberately minimal — no ORM. The schema is small enough that plain SQL via
sqlite3 is easier to read, test, and defend than adding an ORM dependency.
"""

import sqlite3
from pathlib import Path


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def reset_database(db_path: Path, schema_path: Path) -> sqlite3.Connection:
    """Deletes any existing DB file and rebuilds from schema.sql. Used at the
    start of pipeline.py so every run is fully reproducible from data/raw/."""
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(db_path)
    init_schema(conn, schema_path)
    return conn


# --- Insert helpers -----------------------------------------------------

def insert_quarantine_record(conn: sqlite3.Connection, *, source_name: str,
                              source_row_index: int, raw_row_text: str, reason: str) -> int:
    cur = conn.execute(
        """INSERT INTO quarantine_records (source_name, source_row_index, raw_row_text, reason)
           VALUES (?, ?, ?, ?)""",
        (source_name, source_row_index, raw_row_text, reason),
    )
    return cur.lastrowid


def insert_source_record(conn: sqlite3.Connection, fields: dict) -> int:
    """fields keys must be a subset of source_records columns (excluding record_id)."""
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO source_records ({columns}) VALUES ({placeholders})",
        tuple(fields.values()),
    )
    return cur.lastrowid


def insert_person(conn: sqlite3.Connection, *, display_name: str, primary_email: str | None,
                   primary_phone: str | None, city: str | None, match_region: str | None,
                   resolution_status: str) -> int:
    cur = conn.execute(
        """INSERT INTO persons (display_name, primary_email, primary_phone, city, match_region, resolution_status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (display_name, primary_email, primary_phone, city, match_region, resolution_status),
    )
    return cur.lastrowid


def link_record_to_person(conn: sqlite3.Connection, record_id: int, person_id: int) -> None:
    conn.execute("UPDATE source_records SET person_id = ? WHERE record_id = ?", (person_id, record_id))


def insert_match_log(conn: sqlite3.Connection, *, record_id: int, candidate_person_id: int | None,
                      match_method: str, outcome: str, evidence: str, reviewed: int = 0) -> int:
    cur = conn.execute(
        """INSERT INTO match_log (record_id, candidate_person_id, match_method, outcome, evidence, reviewed)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (record_id, candidate_person_id, match_method, outcome, evidence, reviewed),
    )
    return cur.lastrowid
