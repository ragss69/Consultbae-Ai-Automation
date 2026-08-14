"""
db.py — SQLite access layer for Task 3 audio submissions.

Reuses the Task 1 database (consultbae.db) and adds an
`audio_submissions` table. Matches submitted phone numbers against
the existing `persons` table using Task 1's normalize_phone() logic.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from rapidfuzz import fuzz

import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NORMALIZE_PATH = BASE_DIR / "task1_data_pipeline" / "src" / "normalize.py"

spec = importlib.util.spec_from_file_location("task1_normalize", NORMALIZE_PATH)
_normalize_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_normalize_module)
normalize_phone = _normalize_module.normalize_phone


DB_PATH = BASE_DIR / "task1_data_pipeline" / "Data" / "processed" / "consultbae.db"

NAME_MATCH_THRESHOLD = 70  # rapidfuzz token_sort_ratio, 0-100


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_audio_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audio_submissions (
                submission_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id          INTEGER,
                submitted_name     TEXT NOT NULL,
                submitted_phone    TEXT NOT NULL,
                normalized_phone   TEXT,
                phone_parse_status TEXT,
                match_status       TEXT NOT NULL,
                match_method       TEXT,
                original_filename  TEXT,
                stored_filename    TEXT NOT NULL,
                mime_type          TEXT,
                file_size_bytes    INTEGER,
                file_hash          TEXT,
                is_duplicate       INTEGER NOT NULL DEFAULT 0,
                duplicate_of       INTEGER,
                file_path          TEXT NOT NULL,
                duration_sec       REAL,
                sample_rate_hz     INTEGER,
                bitrate_kbps       REAL,
                bitrate_method     TEXT,
                loudness_dbfs      REAL,
                noise_estimate     REAL,
                processing_status  TEXT NOT NULL DEFAULT 'processing'
                                    CHECK (processing_status IN
                                        ('processing', 'completed', 'failed', 'rejected')),
                processing_error   TEXT,
                submitted_at       TEXT NOT NULL,
                FOREIGN KEY (person_id) REFERENCES persons(person_id),
                FOREIGN KEY (duplicate_of) REFERENCES audio_submissions(submission_id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def find_duplicate_by_hash(file_hash: str) -> "sqlite3.Row | None":
    """Return the earliest existing submission with the same file hash, if any."""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT submission_id, submitted_name, submitted_at
            FROM audio_submissions
            WHERE file_hash = ?
            ORDER BY submitted_at ASC
            LIMIT 1
            """,
            (file_hash,),
        ).fetchone()
    finally:
        conn.close()


def match_person(submitted_name: str, submitted_phone: str) -> dict:
    """
    Attempt to match a submission to an existing person via normalized phone.

    Never blocks submission — always returns a result dict, even on
    unmatched/ambiguous/conflict/unparseable phone numbers.
    """
    normalized, parse_status = normalize_phone(submitted_phone)

    if normalized is None:
        return {
            "person_id": None,
            "normalized_phone": None,
            "phone_parse_status": parse_status,
            "match_status": "unparseable",
            "match_method": None,
        }

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT person_id, display_name, primary_phone FROM persons"
        ).fetchall()
    finally:
        conn.close()

    candidates = []
    for row in rows:
        row_norm, row_status = normalize_phone(row["primary_phone"])
        if row_status == "ok" and row_norm == normalized:
            candidates.append(row)

    if len(candidates) == 0:
        return {
            "person_id": None,
            "normalized_phone": normalized,
            "phone_parse_status": parse_status,
            "match_status": "unmatched",
            "match_method": None,
        }

    if len(candidates) > 1:
        return {
            "person_id": None,
            "normalized_phone": normalized,
            "phone_parse_status": parse_status,
            "match_status": "ambiguous",
            "match_method": "normalized_phone",
        }

    candidate = candidates[0]
    name_score = fuzz.token_sort_ratio(
        (submitted_name or "").lower().strip(),
        (candidate["display_name"] or "").lower().strip(),
    )

    if name_score >= NAME_MATCH_THRESHOLD:
        return {
            "person_id": candidate["person_id"],
            "normalized_phone": normalized,
            "phone_parse_status": parse_status,
            "match_status": "matched",
            "match_method": "normalized_phone",
        }

    return {
        "person_id": None,
        "normalized_phone": normalized,
        "phone_parse_status": parse_status,
        "match_status": "conflict",
        "match_method": "normalized_phone",
    }


def insert_submission(record: dict) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO audio_submissions (
                person_id, submitted_name, submitted_phone, normalized_phone,
                phone_parse_status, match_status, match_method,
                original_filename, stored_filename, mime_type, file_size_bytes,
                file_hash, is_duplicate, duplicate_of,
                file_path, duration_sec, sample_rate_hz, bitrate_kbps,
                bitrate_method, loudness_dbfs, noise_estimate,
                processing_status, processing_error, submitted_at
            ) VALUES (
                :person_id, :submitted_name, :submitted_phone, :normalized_phone,
                :phone_parse_status, :match_status, :match_method,
                :original_filename, :stored_filename, :mime_type, :file_size_bytes,
                :file_hash, :is_duplicate, :duplicate_of,
                :file_path, :duration_sec, :sample_rate_hz, :bitrate_kbps,
                :bitrate_method, :loudness_dbfs, :noise_estimate,
                :processing_status, :processing_error, :submitted_at
            )
            """,
            record,
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_submission_status(submission_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{key} = :{key}" for key in fields)
    fields["submission_id"] = submission_id
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE audio_submissions SET {set_clause} WHERE submission_id = :submission_id",
            fields,
        )
        conn.commit()
    finally:
        conn.close()


def get_all_submissions() -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM audio_submissions ORDER BY submitted_at DESC"
        ).fetchall()
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
