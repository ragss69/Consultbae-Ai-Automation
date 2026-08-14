## Stuck Log

- **Issue:** `sqlite3.IntegrityError` on `match_log.outcome` CHECK constraint when inserting a `needs_review` outcome from the name+city review stage.
  **Cause:** `schema.sql`'s CHECK constraint for `match_log.outcome` was written before `review.py` existed and never updated to include `'needs_review'`.
  **Fix:** Added `'needs_review'` to the CHECK constraint list.

- **Issue:** Same CHECK constraint error persisted after the first fix, for a different reason — most Naukri records (no duplicates found) were being logged with `outcome='single'`, which was never a valid value in `match_log` (nor should it be).
  **Cause:** `pipeline.py` blindly logged `cluster.outcome` for every cluster, including the common case of a single, non-duplicated record.
  **Fix:** Singles are now logged as `outcome='new_person', match_method='none'` — accurately reflecting that no duplicate match occurred, this Naukri record simply established a new person.


## Task 4 — Data Issues Report

| # | Issue Type | Example | Where Found | How Handled |
|---|---|---|---|---|
| 1 | Blank row | Fully empty row | Gig Worker CSV | Quarantined (`blank_row`), excluded from matching |
| 2 | Repeated header row | Header row repeated mid-file | CBNexus CSV | Quarantined (`repeated_header`) |
| 3 | Shifted/malformed columns | Quoted skill list caused column offset (Isha Chopra row) | Gig Worker CSV | Quarantined (`shifted_columns`) |
| 4 | Duplicate person, same identifier, alt email | Nikhil Chopra — same phone, two emails (`nikhil.chopra70@example.com` / `alt.nikhil.chopra70@...`) | Naukri CSV | Merged into one person (`duplicate_variant`) |
| 5 | Duplicate person, abbreviated name | Rohit Verma / "R. Verma" — identical email+phone, name variant | Naukri CSV | Merged into one person (`duplicate_variant`) |
| 6 | Cross-source bridge via email | Vikram Saxena — same email in Naukri & Gig Worker | Naukri ↔ Gig Worker | Linked to one person (`high_confidence_match`) |
| 7 | Cross-source bridge via phone | Vikram Saxena / Arjun Mehta — same phone in Naukri & CBNexus | Naukri ↔ CBNexus | Linked to one person (`high_confidence_match`) |
| 8 | Same name, different person (no shared identifier) | Second "Arjun Mehta" in CBNexus (different phone) and in Gig Worker (different email) | CBNexus, Gig Worker | NOT auto-merged — flagged `needs_review` / kept as separate provisional person, never guessed onto the real Arjun Mehta |
| 9 | Ambiguous phone/email formatting | Leading zeros, `+91-`, dashes/spaces in phone; mixed case in email | All 3 sources | Normalized before comparison (`normalize.py`) so formatting never causes a false non-match or false match |
| 10 | CTC unit ambiguity | Values with no unit — could be absolute INR or lakhs | Naukri CSV | Assumed-unit heuristic applied and explicitly logged in `ctc_unit_assumed`, never silently guessed without a record of the assumption |
| 11 | Phone number corrupted by spreadsheet scientific notation | `9E+09`, `9.19E+11`, `-9E+09` — original digits permanently lost | CBNexus CSV, rows 28-32 | Detected via regex, `normalized_phone` set to `None` (never guessed), flagged with `phone_parse_status='scientific_notation_corrupted'`, routed to review queue |

**Totals from a full pipeline run:**
- 102 clean records ingested across all 3 sources; 3 rows quarantined (1 blank, 1 repeated header, 1 shifted-columns)
- 54 canonical persons created
- 40 records auto-linked with `high_confidence_match` (exact email/phone bridge)
- 4 records merged as intra-source `duplicate_variant` pairs (2 pairs)
- 6 records left in the review queue (`needs_review`/`ambiguous`) — 5 of which are directly caused by the scientific-notation phone corruption (issue #11) — never auto-merged on name/city alone
