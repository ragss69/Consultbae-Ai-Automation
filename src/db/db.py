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


def insert_source_record(conn, fields: dict) -> int:
    """
    Insert one row into source_records. `fields` is the db_fields dict built
    by pipeline.py's build_naukri_records / build_gig_worker_records /
    build_cbnexus_records. Since each source only populates a subset of
    columns (e.g. Naukri has no rate_raw, Gig Worker has no ctc_raw),
    every column is pulled with .get(...) so missing ones are stored as
    NULL rather than raising a KeyError.

    Returns the new record_id (needed by pipeline.py to build record_id_map
    for later match_log inserts).
    """
    columns = [
        "source_name", "source_row_index",
        "raw_name", "raw_email", "raw_phone", "raw_city",
        "normalized_email", "normalized_phone", "phone_parse_status",
        "normalized_city", "match_region",
        "experience_years",
        "ctc_raw", "ctc_normalized_inr", "ctc_unit_assumed",
        "applied_date_raw", "applied_date_normalized", "date_parse_status",
        "skills_raw",
        "rate_raw", "rate_normalized_monthly_inr", "rate_unit_assumed",
        "status_normalized", "skill_tags_raw",
        "verified_normalized", "projects_completed",
    ]

    values = [fields.get(col) for col in columns]
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)

    cursor = conn.execute(
        f"INSERT INTO source_records ({column_list}) VALUES ({placeholders})",
        values,
    )
    return cursor.lastrowid



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
