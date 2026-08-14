"""
ConsultBae Task 1 — report/export script.

Run: python -m src.report

Produces, under data/processed/reports/:
  - persons_merged.csv       (one row per canonical person — the "ONE record
                               per person" deliverable, human-readable)
  - quarantine_report.csv    (every structurally rejected row + reason)
  - review_queue.csv         (every unresolved record: needs_review,
                               ambiguous, conflicting_identifier — with
                               evidence, ready for a human to act on)
  - summary.txt              (counts for the Task 4 report / video)

This script only READS the database — it makes no matching decisions.
It exists purely to turn pipeline.py's output into evidence.
"""

import csv
from pathlib import Path

from src.db.db import get_connection

DB_PATH = Path("data/processed/consultbae.db")
OUT_DIR = Path("data/processed/reports")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def export_persons_merged(conn) -> int:
    rows = [dict(r) for r in conn.execute("SELECT * FROM person_merged_view ORDER BY person_id")]
    _write_csv(OUT_DIR / "persons_merged.csv", rows)
    return len(rows)


def export_quarantine(conn) -> int:
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM quarantine_records ORDER BY source_name, source_row_index"
    )]
    _write_csv(OUT_DIR / "quarantine_report.csv", rows)
    return len(rows)


def export_review_queue(conn) -> int:
    query = """
        SELECT
            ml.match_id, sr.source_name, sr.source_row_index, sr.raw_name,
            sr.raw_email, sr.raw_phone, sr.raw_city,
            ml.outcome, ml.match_method, ml.evidence
        FROM match_log ml
        JOIN source_records sr ON sr.record_id = ml.record_id
        WHERE ml.outcome IN ('needs_review', 'ambiguous', 'conflicting_identifier')
        ORDER BY ml.outcome, sr.source_name, sr.source_row_index
    """
    rows = [dict(r) for r in conn.execute(query)]
    _write_csv(OUT_DIR / "review_queue.csv", rows)
    return len(rows)


def write_summary(conn, counts: dict) -> None:
    lines = ["=== ConsultBae Task 1 — Final Report Summary ===", ""]

    lines.append("--- Source ingestion ---")
    for row in conn.execute(
        "SELECT source_name, COUNT(*) as n FROM source_records GROUP BY source_name"
    ):
        lines.append(f"{row['source_name']}: {row['n']} clean records loaded")
    lines.append(f"quarantined rows total: {counts['quarantine']}")
    lines.append("")

    lines.append("--- Quarantine breakdown by reason ---")
    for row in conn.execute(
        "SELECT reason, COUNT(*) as n FROM quarantine_records GROUP BY reason"
    ):
        lines.append(f"{row['reason']}: {row['n']}")
    lines.append("")

    lines.append("--- Match outcome breakdown ---")
    for row in conn.execute(
        "SELECT outcome, COUNT(*) as n FROM match_log GROUP BY outcome ORDER BY n DESC"
    ):
        lines.append(f"{row['outcome']}: {row['n']}")
    lines.append("")

    lines.append(f"Total canonical persons: {counts['persons']}")
    lines.append(f"Records still needing human review: {counts['review_queue']}")
    lines.append("")

    lines.append("--- Cross-source bridge check (people found in 2+ sources) ---")
    for row in conn.execute(
        "SELECT display_name, sources_present, total_source_records "
        "FROM person_merged_view WHERE sources_present LIKE '%,%' ORDER BY display_name"
    ):
        lines.append(f"{row['display_name']}: {row['sources_present']} ({row['total_source_records']} records)")

    (OUT_DIR / "summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection(DB_PATH)

    n_persons_exported = export_persons_merged(conn)
    n_quarantine = export_quarantine(conn)
    n_review = export_review_queue(conn)

    total_persons = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]

    write_summary(conn, {
        "persons": total_persons,
        "quarantine": n_quarantine,
        "review_queue": n_review,
    })

    print(f"\nWritten to {OUT_DIR.resolve()}:")
    print(f"  persons_merged.csv   ({n_persons_exported} rows)")
    print(f"  quarantine_report.csv ({n_quarantine} rows)")
    print(f"  review_queue.csv     ({n_review} rows)")
    print(f"  summary.txt")

    conn.close()


if __name__ == "__main__":
    run()
