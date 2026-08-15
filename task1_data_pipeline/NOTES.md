# ConsultBae Assignment — Design Decisions & Trade-offs

Purpose: a running log of every non-trivial decision made during this task,
why it was made, what was rejected, and where real friction occurred.

---

## Task 1 — Data Merge

### D1. Source 1 (Naukri) as the identity bridge, not a universal anchor
**Decision:** Use Source 1 (has both email + phone) to link Source 2 (email-only)
and Source 3 (phone-only). Records from Source 2/3 with no safe Source-1 match
become their own new-person or ambiguous records — never force-matched.
**Why:** No file has all 3 identity fields; Source 1 is the only overlap point.
**Rejected alternative:** Treating name+city as a fallback universal key — rejected
because the dataset contains a real name+city collision (two "Arjun Mehta" in Noida)
that would produce a false merge.

### D2. Auto-merge only on exact, exclusive, uncontradicted identifier match
**Decision:** Merge automatically only when a normalized email or phone matches
exactly one existing person AND no other field materially contradicts it.
Categories used: high-confidence match, duplicate/formatting variant, ambiguous,
conflicting identifier, new person, quarantined record.
**Why:** A bare "email OR phone matches" rule risks unsafe transitive merges
(A–B share email, B–C share phone, but A and C share nothing) and ignores cases
where a shared identifier co-occurs with a contradicting name.
**Rejected alternative:** A single numeric confidence score (e.g. email=1.0,
phone=0.9, name+city=0.5) — rejected because it implies false precision I can't
defend ("why 0.5 and not 0.4?"). Categorical outcomes are more explainable.

### D3. Name + city is candidate-generation/review evidence only — never a merge trigger
**Decision:** name+city can surface candidates and support a merge only when a
strong identifier is also present. On its own it always resolves to "ambiguous."
**Why:** The dataset has two CBNexus "Arjun Mehta" records in Noida with different
phones — proof that name+city alone is not reliable enough to merge on.
**Worked test case:** Arjun Mehta —
  - Naukri: arjun.mehta9@example.in / 9000000131 / Noida
  - CBNexus record A: phone 9000000131 (normalized) → matches Naukri exactly →
    **high-confidence match**, merged.
  - CBNexus record B: phone 9000000272 → no corroboration anywhere →
    **ambiguous / unresolved new person**, NOT merged into A.
  - Gig Worker: arjun.mehta77@mailtest.example.org — email doesn't match Naukri's
    email at all → name+city overlap only → **ambiguous**, NOT merged.
  This is the central proof-of-correctness case for the whole matching design.

### D4. Intra-source duplicate detection requires internal consistency, not just a shared field
**Decision:** Before collapsing a group of rows sharing an identifier into one
person, check all group members agree on other identifiers too. If not, split
the group and quarantine the conflicting row instead of merging everything.
**Why:** Naive connected-components merging on "shares email OR phone" can chain
together unrelated people through a middle record (A-B-C conflict pattern).
**Example handled correctly:** Nikhil Chopra — two rows, same phone
(09000000103), same city/experience/CTC/skills, different email
(nikhil.chopra70@... vs alt.nikhil.chopra70@...) → duplicate/formatting variant,
both emails retained as observed values for one person.

### D5. Structural row problems are quarantined before entity resolution, not repaired by guesswork
**Decision:** Blank rows, the repeated CBNexus header row, and the shifted Gig
Worker row (Isha Chopra's skills/email/name columns offset by one) are detected
at ingestion and routed to a `quarantine_records` table — never passed into
matching logic.
**Why:** The shifted row could be "repaired" by shifting values back, but that's
a guess about *why* it's shifted, not a deterministically justified fix — and it
duplicates a clean Isha Chopra row already present in the same file. Quarantining
with full raw text + row number preserves the evidence without inventing a fix.
**Rejected alternative:** Auto-repairing the shifted row — rejected as
undocumented guesswork for a case where the "correct" version already exists
elsewhere in the file.

### D6. Unified `source_records` table instead of 3 source-specific tables
**Decision:** One `source_records` table with a `source_name` column and a mix
of shared + nullable source-specific columns, instead of `naukri_records`,
`gig_worker_records`, `cbnexus_records` as separate tables.
**Why:** Cuts schema boilerplate roughly by half, and extends cleanly to Task 3
(audio submissions can be `source_name = 'audio_submission'` in the same table)
without adding a 4th table.
**Rejected alternative:** Fully generic EAV/key-value schema — rejected as
enterprise-grade over-engineering for a 10–14 hour assignment.

### D7. City normalization: derive-then-hardcode, two-tier (canonical vs. matching-region)
**Decision:** First profile all distinct raw city values (trimmed, lowercased,
frequency-counted) from the actual data, then hand-write a small documented
alias map only for what's observed (e.g. gurgaon→gurugram, bangalore→bengaluru).
Delhi / New Delhi / Delhi NCR are normalized to a broader `delhi_ncr` value used
only for candidate generation — not claimed as identical canonical cities.
**Why:** Avoids guessing aliases that don't exist in the data, and avoids
silently treating "Delhi" and "Delhi NCR" as definitely-identical when they may
not be for reporting purposes.
**Rejected alternative:** Automatic string-similarity clustering of cities —
rejected as unnecessary and less explainable than a short hand-reviewed map.

### D8. Fuzzy matching (rapidfuzz) is review-ranking only, never a merge trigger
**Decision:** Use rapidfuzz purely to rank/prioritize name-based review
candidates (e.g. surfacing "R. Verma" as a likely match for "Rohit Verma" for a
human to confirm) — it never independently causes a merge.
**Why:** Keeps every actual merge traceable to a deterministic identifier match,
which is what's defensible in an interview.

### D9. Date parsing: deterministic rules + explicit ambiguity flag, not quarantine
**Decision:**
  - ISO (`2026-08-08`) and textual (`7 Jul 2026`) dates parsed directly.
  - Slash/hyphen dates where one component > 12 are parsed unambiguously
    (e.g. `07/13/2026` → MM/DD/YYYY, since 13 can't be a month).
  - Remaining ambiguous cases (both components ≤ 12, e.g. `01-08-2026`) default
    to DD-MM-YYYY (India-context assumption), flagged with
    `date_parse_status = 'ambiguous_default'`.
  - Raw string always preserved alongside the normalized value.
**Why:** Applied Date isn't an identity field, so quarantining every ambiguous
date would remove valid records for no matching benefit. Flagging preserves
honesty about the assumption without breaking the pipeline.
**Explicitly not used as entity-matching evidence.**

### D10. Generated SQLite file is gitignored, not committed
**Decision:** `.gitignore` the `.db` file; it's rebuilt by running `pipeline.py`

### CTC threshold of 1000 — worth stating explicitly in the report: it's a heuristic based on the observed gap between the two clusters (all lakh-values < 20, all absolute values > 300,000), not a general-purpose rule. Fine for this dataset, would need revisiting for a different one.
### 176 hrs/month assumption for rate normalization — purely for reporting comparability; I've deliberately kept it out of any matching logic per your instruction that dates/rates aren't identity evidence.
### normalize_city returns two values — normalized_city (your best-guess canonical form, shown to users/reports) and match_region (a broader bucket like delhi_ncr used only inside the matching candidate-generation step) — this directly implements your "don't claim they're identical, but group them for candidate generation" instruction.
