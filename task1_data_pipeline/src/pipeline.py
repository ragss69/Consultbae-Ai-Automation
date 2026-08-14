"""
ConsultBae Task 1 — end-to-end pipeline entry point.

Run: python -m src.pipeline

Order of operations:
  1. Reset DB, load schema.
  2. Ingest all 3 CSVs, quarantine structural problems (load_csv.py).
  3. Normalize every clean row (normalize.py) -> build SourceRecord objects.
  4. Group Naukri records into intra-source clusters, detect conflicts (grouping.py).
  5. Create a person per safe Naukri cluster (the identity bridge).
  6. Link Gig Worker (by email) and CBNexus (by phone) records against those
     persons (linking.py). Anything that doesn't match a Naukri person tries
     name+city review (review.py) against persons created so far, then
     either becomes a new provisional person or is left in the review queue.
  7. Write everything to source_records, persons, match_log; write
     quarantine_records. Print a validation summary.
"""

from pathlib import Path

from task1_data_pipeline.src.normalize import (
    normalize_email, normalize_phone, normalize_city, parse_date,
    normalize_ctc, normalize_rate, normalize_status, normalize_verified,
)
from task1_data_pipeline.src.ingest.load_csv import load_all_sources
from task1_data_pipeline.src.matching.grouping import SourceRecord, group_within_source, Cluster
from task1_data_pipeline.src.matching.linking import link_by_email, link_by_phone
from task1_data_pipeline.src.matching.review import ExistingPerson, resolve_review_outcome
from task1_data_pipeline.src.db.db import (
    reset_database, insert_quarantine_record, insert_source_record,
    insert_person, link_record_to_person, insert_match_log,
)

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/processed/consultbae.db")
SCHEMA_PATH = Path("src/db/schema.sql")


# ---------------------------------------------------------------------------
# Step 1-3: ingest + normalize each source into SourceRecord objects,
# keeping the full normalized field dict alongside for DB insertion.
# ---------------------------------------------------------------------------

def build_naukri_records(rows: list[dict]) -> list[tuple[SourceRecord, dict]]:
    out = []
    for row in rows:
        email = normalize_email(row.get("Email"))
        phone, phone_parse_status = normalize_phone(row.get("Phone"))
        city_info = normalize_city(row.get("City"))
        date_info = parse_date(row.get("Applied Date"))
        ctc_info = normalize_ctc(row.get("Current CTC"))

        sr = SourceRecord(
            source_name="naukri",
            source_row_index=row["_source_row_index"],
            raw_name=row.get("Full Name"),
            normalized_email=email,
            normalized_phone=phone,
            raw=row,
        )
        db_fields = {
            "source_name": "naukri",
            "source_row_index": row["_source_row_index"],
            "raw_name": row.get("Full Name"),
            "raw_email": row.get("Email"),
            "raw_phone": row.get("Phone"),
            "raw_city": row.get("City"),
            "normalized_email": email,
            "normalized_phone": phone,
            "phone_parse_status": phone_parse_status,
            "normalized_city": city_info["normalized_city"],
            "match_region": city_info["match_region"],
            "experience_years": _to_float(row.get("Experience (Years)")),
            "ctc_raw": ctc_info["raw"],
            "ctc_normalized_inr": ctc_info["normalized_ctc_inr"],
            "ctc_unit_assumed": ctc_info["ctc_unit_assumed"],
            "applied_date_raw": date_info["raw"],
            "applied_date_normalized": date_info["normalized_date"],
            "date_parse_status": date_info["date_parse_status"],
            "skills_raw": row.get("Skills"),
        }
        out.append((sr, db_fields))
    return out


def build_gig_worker_records(rows: list[dict]) -> list[tuple[SourceRecord, dict]]:
    out = []
    for row in rows:
        email = normalize_email(row.get("email_id"))
        # This source has no phone column at all. Running None through the
        # same normalizer keeps behaviour consistent and gives an explicit
        # phone_parse_status="missing" rather than an unexplained NULL.
        _, phone_parse_status = normalize_phone(None)
        city_info = normalize_city(row.get("location"))
        rate_info = normalize_rate(row.get("rate"))

        sr = SourceRecord(
            source_name="gig_worker",
            source_row_index=row["_source_row_index"],
            raw_name=row.get("worker_name"),
            normalized_email=email,
            normalized_phone=None,   # this source has no phone field
            raw=row,
        )
        db_fields = {
            "source_name": "gig_worker",
            "source_row_index": row["_source_row_index"],
            "raw_name": row.get("worker_name"),
            "raw_email": row.get("email_id"),
            "raw_phone": None,
            "raw_city": row.get("location"),
            "normalized_email": email,
            "normalized_phone": None,
            "phone_parse_status": phone_parse_status,
            "normalized_city": city_info["normalized_city"],
            "match_region": city_info["match_region"],
            "rate_raw": rate_info["raw"],
            "rate_normalized_monthly_inr": rate_info["normalized_monthly_inr"],
            "rate_unit_assumed": rate_info["rate_unit_assumed"],
            "status_normalized": normalize_status(row.get("status")),
            "skill_tags_raw": row.get("skill_tags"),
        }
        out.append((sr, db_fields))
    return out


def build_cbnexus_records(rows: list[dict]) -> list[tuple[SourceRecord, dict]]:
    out = []
    for row in rows:
        phone, phone_parse_status = normalize_phone(row.get("Phone Number"))
        city_info = normalize_city(row.get("City"))

        sr = SourceRecord(
            source_name="cbnexus",
            source_row_index=row["_source_row_index"],
            raw_name=row.get("Name"),
            normalized_email=None,   # this source has no email field
            normalized_phone=phone,
            raw=row,
        )
        db_fields = {
            "source_name": "cbnexus",
            "source_row_index": row["_source_row_index"],
            "raw_name": row.get("Name"),
            "raw_email": None,
            "raw_phone": row.get("Phone Number"),
            "raw_city": row.get("City"),
            "normalized_email": None,
            "normalized_phone": phone,
            "phone_parse_status": phone_parse_status,
            "normalized_city": city_info["normalized_city"],
            "match_region": city_info["match_region"],
            "verified_normalized": _bool_to_int(normalize_verified(row.get("Verified"))),
            "projects_completed": _to_int(row.get("Projects Completed")),
        }
        out.append((sr, db_fields))
    return out


def _to_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _to_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _bool_to_int(value):
    return None if value is None else int(value)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run():
    conn = reset_database(DB_PATH, SCHEMA_PATH)

    loaded = load_all_sources(RAW_DIR)

    for source_name, result in loaded.items():
        for q in result.quarantined:
            insert_quarantine_record(
                conn, source_name=source_name, source_row_index=q.source_row_index,
                raw_row_text=",".join(q.raw_row), reason=q.reason,
            )

    naukri_pairs = build_naukri_records(loaded["naukri"].clean_rows)
    gig_pairs = build_gig_worker_records(loaded["gig_worker"].clean_rows)
    cbnexus_pairs = build_cbnexus_records(loaded["cbnexus"].clean_rows)

    # Insert all source_records now (record_id needed for match_log FK).
    # Keep a map from SourceRecord identity (source_name, source_row_index) -> record_id.
    record_id_map: dict[tuple[str, int], int] = {}
    for sr, db_fields in naukri_pairs + gig_pairs + cbnexus_pairs:
        rid = insert_source_record(conn, db_fields)
        record_id_map[(sr.source_name, sr.source_row_index)] = rid

    def rid_of(sr: SourceRecord) -> int:
        return record_id_map[(sr.source_name, sr.source_row_index)]

    # --- Step 4-5: cluster Naukri records, create one person per safe cluster ---
    naukri_records = [sr for sr, _ in naukri_pairs]
    naukri_clusters = group_within_source(naukri_records)

    person_of_cluster: dict[int, int] = {}  # id(cluster) -> person_id
    existing_persons: list[ExistingPerson] = []

    for cluster in naukri_clusters:
        anchor = cluster.records[0]
        city_info = normalize_city(anchor.raw.get("City"))

        if cluster.outcome == "conflicting_identifier":
            # Do not create one merged person. Each member becomes its own
            # provisional person, and the conflict is logged for review.
            for rec in cluster.records:
                pid = insert_person(
                    conn, display_name=rec.raw_name, primary_email=rec.normalized_email,
                    primary_phone=rec.normalized_phone, city=city_info["normalized_city"],
                    match_region=city_info["match_region"], resolution_status="needs_review",
                )
                insert_match_log(
                    conn, record_id=rid_of(rec), candidate_person_id=pid,
                    match_method="none", outcome="conflicting_identifier", evidence=cluster.evidence,
                    reviewed=0,
                )
                existing_persons.append(ExistingPerson(pid, rec.raw_name, city_info["match_region"]))
            continue

        pid = insert_person(
            conn, display_name=anchor.raw_name, primary_email=anchor.normalized_email,
            primary_phone=anchor.normalized_phone, city=city_info["normalized_city"],
            match_region=city_info["match_region"], resolution_status="resolved",
        )
        person_of_cluster[id(cluster)] = pid
        existing_persons.append(ExistingPerson(pid, anchor.raw_name, city_info["match_region"]))

        # A 'single' cluster (no duplicates found) isn't really a "match" —
        # it's this Naukri record establishing a new person on its own.
        # Log it as 'new_person' so match_log's CHECK constraint (and its
        # semantics) stay meaningful; only real duplicate clusters use
        # exact_email/exact_phone as the match_method.
        if cluster.outcome == "single":
            log_outcome = "new_person"
            log_method = "none"
        else:
            log_outcome = cluster.outcome
            log_method = "exact_email" if cluster.anchor_field == "email" else "exact_phone"

        for rec in cluster.records:
            link_record_to_person(conn, rid_of(rec), pid)
            insert_match_log(
                conn, record_id=rid_of(rec), candidate_person_id=pid,
                match_method=log_method,
                outcome=log_outcome, evidence=cluster.evidence, reviewed=1,
            )

    naukri_clusters_safe = [c for c in naukri_clusters if c.outcome != "conflicting_identifier"]

    # --- Step 6: link Gig Worker (by email) and CBNexus (by phone) ---
    def process_cross_source(pairs, link_fn):
        for sr, _ in pairs:
            decision = link_fn(sr, naukri_clusters_safe)
            rid = rid_of(sr)

            if decision.outcome == "high_confidence_match":
                pid = person_of_cluster[id(decision.matched_cluster)]
                link_record_to_person(conn, rid, pid)
                insert_match_log(
                    conn, record_id=rid, candidate_person_id=pid,
                    match_method=decision.match_method, outcome=decision.outcome,
                    evidence=decision.evidence, reviewed=1,
                )
                continue

            if decision.outcome == "ambiguous":
                insert_match_log(
                    conn, record_id=rid, candidate_person_id=None,
                    match_method=decision.match_method, outcome="ambiguous",
                    evidence=decision.evidence, reviewed=0,
                )
                continue

            # new_person_candidate -> try name+city review against persons so far
            city_info = normalize_city(sr.raw.get("location") or sr.raw.get("City"))
            review = resolve_review_outcome(sr, city_info["match_region"], existing_persons)

            if review.outcome == "new_person":
                pid = insert_person(
                    conn, display_name=sr.raw_name, primary_email=sr.normalized_email,
                    primary_phone=sr.normalized_phone, city=city_info["normalized_city"],
                    match_region=city_info["match_region"], resolution_status="provisional_new",
                )
                link_record_to_person(conn, rid, pid)
                existing_persons.append(ExistingPerson(pid, sr.raw_name, city_info["match_region"]))
                insert_match_log(
                    conn, record_id=rid, candidate_person_id=pid,
                    match_method="none", outcome="new_person", evidence=review.evidence, reviewed=1,
                )
            else:
                # needs_review or ambiguous -> do not assign person_id yet
                insert_match_log(
                    conn, record_id=rid, candidate_person_id=None,
                    match_method="name_city_candidate", outcome=review.outcome,
                    evidence=review.evidence, reviewed=0,
                )

    process_cross_source(gig_pairs, link_by_email)
    process_cross_source(cbnexus_pairs, link_by_phone)

    conn.commit()
    _print_summary(conn, loaded)
    conn.close()


def _print_summary(conn, loaded):
    print("\n=== ConsultBae Task 1 — Pipeline Summary ===")
    for source_name, result in loaded.items():
        print(f"[{source_name}] clean_rows={len(result.clean_rows)} quarantined={len(result.quarantined)}")

    total_persons = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    unresolved = conn.execute(
        "SELECT COUNT(*) FROM source_records WHERE person_id IS NULL"
    ).fetchone()[0]
    print(f"\nTotal persons created: {total_persons}")
    print(f"Source records left unresolved (needs_review/ambiguous): {unresolved}")

    print("\nMatch outcome breakdown:")
    for row in conn.execute("SELECT outcome, COUNT(*) as n FROM match_log GROUP BY outcome ORDER BY n DESC"):
        print(f"  {row['outcome']}: {row['n']}")


if __name__ == "__main__":
    run()
