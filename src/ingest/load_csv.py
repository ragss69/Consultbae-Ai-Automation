"""
CSV ingestion for ConsultBae Task 1.

This module does ONLY structural triage:
  - detects blank rows
  - detects repeated/duplicated header rows
  - detects shifted/malformed rows (source-specific heuristic)

None of these rows are repaired or passed into normalization/matching.
They are routed to a quarantine list with the original raw values and
the 1-based row index as it would appear if you opened the CSV in a
spreadsheet (header = row 1, first data row = row 2), so quarantine
reports are easy to cross-check against the source file by hand.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class QuarantinedRow:
    source_name: str
    source_row_index: int
    raw_row: list[str]
    reason: str  # 'blank_row' | 'repeated_header' | 'shifted_columns'


@dataclass
class LoadResult:
    source_name: str
    header: list[str]
    clean_rows: list[dict]              # header-mapped dict + _source_row_index
    quarantined: list[QuarantinedRow] = field(default_factory=list)


def _is_blank_row(row: list[str]) -> bool:
    """A row is blank if every cell is empty after stripping whitespace."""
    return all(cell.strip() == "" for cell in row)


def _is_repeated_header(row: list[str], header: list[str]) -> bool:
    """
    Detects a header row that reappears mid-file (observed in
    cbnexus_contacts.csv, where the file is a concatenation of two
    exports and the second export's header wasn't stripped).
    """
    return [c.strip() for c in row] == [h.strip() for h in header]


def _looks_shifted_gig_worker_row(row: list[str]) -> bool:
    """
    Deterministic heuristic specific to the Gig Workers column order
    (email_id, worker_name, rate, location, status, skill_tags):

    The first column (email_id) should always contain '@'. If it
    doesn't, but a LATER column does, the row's values are very likely
    misaligned/shifted rather than just a missing email — the '@'
    should exist somewhere on a normal row, just not where it's expected.

    Observed once in the data: skill_tags text ("react, javascript,
    mysql") sitting in the email_id position, with every other value
    shifted out of place, for what appears to be a corrupted duplicate
    of an already-present, well-formed Isha Chopra row.

    This function only DETECTS the anomaly. It intentionally does not
    attempt to un-shift the columns — see docs/DECISIONS.md (D5) for why
    an automatic repair was rejected as undocumented guesswork.
    """
    if len(row) < 2:
        return False
    email_field = row[0].strip()
    if "@" in email_field:
        return False
    return any("@" in cell for cell in row[1:])


def load_csv(
    path: Path,
    source_name: str,
    malformed_row_check: Optional[Callable[[list[str]], bool]] = None,
) -> LoadResult:
    """
    Reads a raw CSV and splits its rows into clean_rows (dicts keyed by
    the original header) and quarantined rows (structural problems).

    malformed_row_check is an optional, source-specific function for
    detecting shifted/corrupted rows. It is deliberately not a generic
    "detect any malformed CSV" rule — that would be unjustifiably broad
    for a 10-14 hour assignment. Pass it only for sources where such a
    pattern has actually been observed (currently: gig_workers).
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    if not reader:
        return LoadResult(source_name=source_name, header=[], clean_rows=[], quarantined=[])

    header = reader[0]
    clean_rows: list[dict] = []
    quarantined: list[QuarantinedRow] = []

    # source_row_index starts at 2: header is row 1, first data row is row 2 —
    # matches what you'd see opening the file in Excel/Sheets.
    for idx, row in enumerate(reader[1:], start=2):
        if _is_blank_row(row):
            quarantined.append(QuarantinedRow(source_name, idx, row, "blank_row"))
            continue

        if _is_repeated_header(row, header):
            quarantined.append(QuarantinedRow(source_name, idx, row, "repeated_header"))
            continue

        if malformed_row_check and malformed_row_check(row):
            quarantined.append(QuarantinedRow(source_name, idx, row, "shifted_columns"))
            continue

        record = dict(zip(header, row))
        record["_source_row_index"] = idx
        clean_rows.append(record)

    return LoadResult(source_name=source_name, header=header, clean_rows=clean_rows, quarantined=quarantined)


def load_all_sources(raw_dir: Path) -> dict[str, LoadResult]:
    """
    Loads all three ConsultBae source files with their appropriate
    source-specific structural checks.
    """
    return {
        "naukri": load_csv(
            raw_dir / "source1_naukri_applicants.csv",
            source_name="naukri",
        ),
        "gig_worker": load_csv(
            raw_dir / "source2_gig_workers.csv",
            source_name="gig_worker",
            malformed_row_check=_looks_shifted_gig_worker_row,
        ),
        "cbnexus": load_csv(
            raw_dir / "source3_cbnexus_contacts.csv",
            source_name="cbnexus",
        ),
    }


if __name__ == "__main__":
    # Quick manual smoke test — prints counts, not full data.
    # Run: python -m src.ingest.load_csv
    results = load_all_sources(Path("data/raw"))
    for name, result in results.items():
        print(f"[{name}] clean={len(result.clean_rows)} quarantined={len(result.quarantined)}")
        for q in result.quarantined:
            print(f"   row {q.source_row_index}: {q.reason} -> {q.raw_row}")
