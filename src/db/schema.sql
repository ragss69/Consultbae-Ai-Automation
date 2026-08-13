-- ConsultBae Task 1 — SQLite schema
-- Design: minimal tables that still separate canonical people, raw+normalized
-- source data, structural quarantine, and a full audit trail of every match
-- decision. See docs/DECISIONS.md (D6) for why this is one unified
-- source_records table instead of three source-specific tables.

PRAGMA foreign_keys = ON;

-- Canonical people. Populated as entity resolution runs; a person can exist
-- even before all of their source records are linked (resolution_status
-- tracks how settled the record is).
CREATE TABLE persons (
    person_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name        TEXT NOT NULL,
    primary_email       TEXT,               -- best-known value, convenience only
    primary_phone       TEXT,
    city                TEXT,
    match_region        TEXT,               -- broader grouping (e.g. delhi_ncr), candidate-gen only
    resolution_status   TEXT NOT NULL DEFAULT 'provisional_new'
                            CHECK (resolution_status IN ('resolved', 'provisional_new', 'needs_review')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One row per original CSV data row that passed structural triage
-- (i.e. NOT blank / repeated-header / shifted — those go to quarantine_records).
-- person_id is nullable until entity resolution assigns/creates one.
CREATE TABLE source_records (
    record_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name             TEXT NOT NULL CHECK (source_name IN ('naukri', 'gig_worker', 'cbnexus')),
    source_row_index        INTEGER NOT NULL,     -- 1-based, matches spreadsheet view of raw CSV
    person_id               INTEGER REFERENCES persons(person_id),

    -- Raw values, untouched, always preserved
    raw_name                TEXT,
    raw_email               TEXT,
    raw_phone               TEXT,
    raw_city                TEXT,

    -- Normalized values (see src/normalize.py)
    normalized_email        TEXT,
    normalized_phone         TEXT,
    normalized_city          TEXT,
    match_region             TEXT,

    -- Naukri-specific (nullable for other sources)
    experience_years         REAL,
    ctc_raw                  TEXT,
    ctc_normalized_inr       REAL,
    ctc_unit_assumed         TEXT,             -- 'absolute_inr' | 'lakhs_inr'
    applied_date_raw         TEXT,
    applied_date_normalized  TEXT,             -- YYYY-MM-DD
    date_parse_status        TEXT,             -- 'unambiguous' | 'ambiguous_default' | 'unparseable'
    skills_raw               TEXT,

    -- Gig Worker-specific (nullable for other sources)
    rate_raw                 TEXT,
    rate_normalized_monthly_inr REAL,
    rate_unit_assumed        TEXT,             -- 'hourly' | 'monthly'
    status_normalized         TEXT,             -- 'active' | 'inactive' | 'paused'
    skill_tags_raw            TEXT,

    -- CBNexus-specific (nullable for other sources)
    verified_normalized        INTEGER,          -- 0/1 boolean, SQLite has no bool type
    projects_completed         INTEGER,

    created_at                TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_source_records_email ON source_records(normalized_email);
CREATE INDEX idx_source_records_phone ON source_records(normalized_phone);
CREATE INDEX idx_source_records_person ON source_records(person_id);

-- Rows that failed structural triage (blank row, repeated header,
-- shifted/malformed columns). Never entered entity resolution at all.
CREATE TABLE quarantine_records (
    quarantine_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name         TEXT NOT NULL,
    source_row_index    INTEGER NOT NULL,
    raw_row_text        TEXT NOT NULL,          -- verbatim original row (joined columns)
    reason              TEXT NOT NULL CHECK (reason IN ('blank_row', 'repeated_header', 'shifted_columns')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Full audit trail: every decision made about every source_record during
-- grouping, linking, and review. This is the table you walk an evaluator
-- through to defend "why did/didn't this merge happen."
CREATE TABLE match_log (
    match_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id            INTEGER REFERENCES source_records(record_id),
    candidate_person_id  INTEGER REFERENCES persons(person_id),
    match_method         TEXT NOT NULL CHECK (match_method IN
                              ('exact_email', 'exact_phone', 'name_city_candidate', 'none')),
    outcome               TEXT NOT NULL CHECK (outcome IN
                              ('high_confidence_match', 'duplicate_variant', 'exact_duplicate',
                               'ambiguous', 'conflicting_identifier', 'new_person', 'needs_review')),
    evidence               TEXT NOT NULL,
    reviewed                INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);


CREATE INDEX idx_match_log_record ON match_log(record_id);
CREATE INDEX idx_match_log_outcome ON match_log(outcome);

-- One flattened row per canonical person — satisfies the assignment's
-- "same person across files becomes ONE record" requirement for display
-- and export purposes. Underlying source of truth remains source_records
-- (raw + normalized, per source, with provenance) and match_log (why each
-- merge/non-merge happened). See docs/DECISIONS.md for the reasoning.
--
-- Caveat: if a person has genuinely conflicting values for the same field
-- across multiple rows of the same source (rare, but possible), MAX()
-- picks one arbitrarily for display. That is a display-layer simplification
-- only — source_records still holds every observed value untouched.
CREATE VIEW person_merged_view AS
SELECT
    p.person_id,
    p.display_name,
    p.primary_email,
    p.primary_phone,
    p.city,
    p.resolution_status,
    MAX(CASE WHEN sr.source_name = 'naukri' THEN sr.experience_years END)                 AS experience_years,
    MAX(CASE WHEN sr.source_name = 'naukri' THEN sr.ctc_normalized_inr END)               AS ctc_inr,
    MAX(CASE WHEN sr.source_name = 'naukri' THEN sr.applied_date_normalized END)          AS applied_date,
    MAX(CASE WHEN sr.source_name = 'naukri' THEN sr.skills_raw END)                       AS naukri_skills,
    MAX(CASE WHEN sr.source_name = 'gig_worker' THEN sr.rate_normalized_monthly_inr END)  AS gig_rate_monthly_inr,
    MAX(CASE WHEN sr.source_name = 'gig_worker' THEN sr.status_normalized END)            AS gig_status,
    MAX(CASE WHEN sr.source_name = 'gig_worker' THEN sr.skill_tags_raw END)               AS gig_skill_tags,
    MAX(CASE WHEN sr.source_name = 'cbnexus' THEN sr.verified_normalized END)             AS cbnexus_verified,
    MAX(CASE WHEN sr.source_name = 'cbnexus' THEN sr.projects_completed END)              AS cbnexus_projects_completed,
    GROUP_CONCAT(DISTINCT sr.source_name)                                                  AS sources_present,
    COUNT(DISTINCT sr.record_id)                                                           AS total_source_records
FROM persons p
LEFT JOIN source_records sr ON sr.person_id = p.person_id
GROUP BY p.person_id;

