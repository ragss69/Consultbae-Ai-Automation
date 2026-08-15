Yes — in that case the root README should act as the **submission-level documentation**, while the individual task READMEs should contain the deeper implementation details.

So I would **not remove the Stuck Log or Data Issues Report**. I would instead consolidate the *other* sections so the root README doesn't unnecessarily duplicate all three task READMEs.

The right split is:

* **Root `README.md`** → what the assignment is, repository structure, architecture, prerequisites, setup/run instructions, task summaries, integration between tasks, validation, stuck log, data issues report, security, limitations, completion.
* **Task 1 README** → detailed matching implementation, normalization rules, schema, code-level behavior.
* **Task 2 README** → detailed n8n workflow/node configuration, Gemini prompt, Google Sheets setup.
* **Task 3 README** → detailed Streamlit implementation, audio processing, database schema, etc.
* **`DECISIONS.md`** → cross-task design decisions if you want to retain those separately.

Below is the version I would actually use as the **final root README**. I have retained your **Stuck Log essentially as-is** and the **Data Issues Report placeholder**, while reducing duplicated per-task material.

````markdown
# ConsultBae Assignment — Data Pipeline, Skill Automation & Audio Collection App

This repository contains the complete implementation of the three-part ConsultBae technical assignment:

1. **Task 1 — Data Merge Pipeline**
2. **Task 2 — No-Code Skill Categorization Automation**
3. **Task 3 — Mini Audio Collection App**

The project combines data engineering, entity resolution, no-code automation, LLM-based classification, audio processing, SQLite, and Streamlit.

The implementation prioritizes:

- reproducibility;
- explainable decisions;
- preservation of raw source data;
- conservative entity resolution;
- clear handling of malformed and ambiguous records;
- controlled use of LLMs;
- simple local execution;
- documentation of implementation decisions and stuck points.

---

# Repository Structure

```text
consultbae-assignment/
├── README.md
├── DECISIONS.md
│   # Cross-task design decisions
│
├── task1_data_pipeline/
│   ├── README.md
│   ├── requirements.txt
│   ├── src/
│   │   ├── ingest/
│   │   │   └── load_csv.py
│   │   ├── normalize.py
│   │   ├── matching/
│   │   │   ├── grouping.py
│   │   │   ├── linking.py
│   │   │   └── review.py
│   │   ├── db/
│   │   │   └── schema.sql
│   │   └── pipeline.py
│   └── data/
│       ├── raw/
│       └── processed/
│
├── task2_automation/
│   ├── README.md
│   ├── requirements.txt
│   ├── workflow/
│   │   └── consultbae_skill_categorization.json
│   ├── input/
│   └── reports/
│
└── task3_audio_app/
    ├── README.md
    ├── requirements.txt
    ├── streamlit_app.py
    ├── audio_utils.py
    ├── db.py
    ├── audio_files/
    └── tests/
````

Generated files such as the SQLite database, uploaded audio files, credentials, and local environment files should be excluded through `.gitignore`.

---

# Assignment Overview

## Task 1 — Data Merge Pipeline

The first task merges three inconsistent CSV exports:

* Naukri applicants
* Gig Workers
* CBNexus contacts

The source files do not share a common identifier. The pipeline therefore normalizes and compares strong identifiers such as email and phone while handling ambiguity conservatively.

The main output is:

```text
task1_data_pipeline/data/processed/consultbae.db
```

The database contains canonical people, source records, quarantine records, and matching decisions.

Detailed implementation and matching documentation is available in:

```text
task1_data_pipeline/README.md
```

---

## Task 2 — No-Code Skill Categorization Automation

The second task implements a no-code/low-code automation in n8n.

The workflow:

1. reads person-level records derived from Task 1;
2. sends skill information to Gemini;
3. assigns one of six fixed skill categories;
4. validates the model response;
5. writes the result to a separate Google Sheets output.

The workflow export is stored in:

```text
task2_automation/workflow/consultbae_skill_categorization.json
```

Detailed workflow configuration and setup are documented in:

```text
task2_automation/README.md
```

---

## Task 3 — Mini Audio Collection App

The third task implements a Streamlit application for collecting audio submissions.

Users can:

* enter their name and phone number;
* record or upload audio;
* submit the audio;
* view extracted audio properties;
* view previous submissions;
* play stored recordings.

Audio metadata is stored in the Task 1 SQLite database through an `audio_submissions` table.

Detailed implementation and audio-processing documentation is available in:

```text
task3_audio_app/README.md
```

---

# Overall Architecture

The intended relationship between the three tasks is:

```text
                    ┌──────────────────┐
                    │   Raw CSV Files  │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │      Task 1      │
                    │ Data Merge &     │
                    │ Entity Resolution│
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │  SQLite Database │
                    │     persons      │
                    │ source_records   │
                    │   match_log      │
                    └───────┬─────┬────┘
                            │     │
                Person Data │     │ Audio Submissions
                            ↓     ↓
                    ┌──────────┐ ┌──────────────┐
                    │  Task 2  │ │    Task 3    │
                    │   n8n +  │ │  Streamlit   │
                    │  Gemini  │ │ Audio App    │
                    └────┬─────┘ └──────┬───────┘
                         ↓              ↓
                  Google Sheets    SQLite Audio
                     Output         Metadata
```

Task 2 and Task 3 do not modify the original raw source files.

---

# Design Principles

## Preserve Raw Data

Raw input values are preserved wherever normalization or transformation takes place.

This makes it possible to:

* audit decisions;
* reproduce results;
* investigate failed matches;
* compare normalized and original values.

## Normalize Before Comparing

Fields such as emails, phone numbers, names, cities, and dates can differ in formatting even when they refer to the same underlying value.

Comparison uses normalized values while retaining the original values.

## Prefer Safe Matches Over Maximum Matches

A false merge is more damaging than an unresolved record.

The system therefore prefers:

```text
safe match > review candidate > unresolved record > false merge
```

## Make Decisions Explainable

Important outcomes are represented explicitly rather than hiding decisions behind a single opaque score.

Examples include:

```text
matched
duplicate_variant
ambiguous
conflicting_identifier
new_person
quarantined
```

## Keep the Prototype Simple

The assignment is designed to be completed and demonstrated within a limited scope.

The implementation therefore avoids unnecessary production infrastructure such as:

* distributed queues;
* vector databases;
* agent frameworks;
* microservices;
* cloud object storage;
* unnecessary authentication systems.

The architecture is modular enough that these components could be introduced later if required.

---

# Prerequisites

The following are required:

* Python 3.10 or later
* `pip`
* SQLite, normally included with Python
* A browser for Task 3
* An n8n instance for Task 2
* Google Sheets access
* Gemini API credentials for Task 2

For Task 3, browser recording support depends on the browser and installed Streamlit version. File upload can be used when browser recording is unavailable or unreliable.

---

# Setup & Execution

Each task is independently executable, while Task 2 and Task 3 depend on outputs produced by Task 1.

---

## Task 1 Setup

Navigate to the Task 1 directory:

```bash
cd task1_data_pipeline
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Place the supplied CSV files inside:

```text
task1_data_pipeline/data/raw/
```

Run the pipeline:

```bash
python src/pipeline.py
```

The generated database will be:

```text
task1_data_pipeline/data/processed/consultbae.db
```

The database is a generated build artifact and can be regenerated from the supplied raw CSV files.

### Task 1 Processing Flow

```text
Raw CSV files
      ↓
Structural validation
      ↓
Quarantine malformed rows
      ↓
Normalize comparison fields
      ↓
Group duplicates within each source
      ↓
Link records across sources
      ↓
Detect ambiguity and conflicts
      ↓
Create canonical persons
      ↓
Write SQLite database
```

For detailed matching rules, normalization logic, schema, and data handling, see:

```text
task1_data_pipeline/README.md
```

---

## Task 2 Setup

Task 2 uses the person-level data generated from Task 1.

The input Google Sheet should contain:

```text
person_id
display_name
skills_raw
```

Optional fields can include:

```text
city
source_count
match_status
```

Create separate input and output tabs, for example:

```text
ConsultBae_Persons
ConsultBae_Persons_Tagged
```

Import the workflow:

```text
task2_automation/workflow/consultbae_skill_categorization.json
```

into n8n.

Configure:

1. Google Sheets credentials.
2. Input spreadsheet and sheet.
3. Output spreadsheet and sheet.
4. Gemini credentials.
5. Required field mappings.

Run the workflow using the Manual Trigger.

### Task 2 Categories

The workflow classifies skills into one of:

| Category                | Description                                                                    |
| ----------------------- | ------------------------------------------------------------------------------ |
| `Web Development`       | Frontend, backend, APIs, web frameworks, and application development           |
| `Data / Analytics`      | SQL, Python data tools, statistics, reporting, analytics, and data engineering |
| `Automation / AI`       | n8n, Zapier, workflow automation, AI, machine learning, and LangChain          |
| `Design`                | UI/UX, Figma, Adobe, visual design, and branding                               |
| `Sales / Ops / Support` | Sales, customer support, CRM, recruiting, and operations                       |
| `Other`                 | Insufficient, unclear, or unrelated evidence                                   |

Missing skills are handled deterministically without an unnecessary Gemini call.

The Gemini response is validated against the allowed categories before being written to the output.

For detailed workflow configuration, node behavior, Google Sheets setup, and Gemini configuration, see:

```text
task2_automation/README.md
```

---

## Task 3 Setup

Task 3 requires the Task 1 SQLite database.

If it has not already been generated:

```bash
cd task1_data_pipeline
python src/pipeline.py
```

Then install Task 3 dependencies:

```bash
cd ../task3_audio_app
pip install -r requirements.txt
```

Start the Streamlit application:

```bash
streamlit run streamlit_app.py
```

Open the local URL shown by Streamlit, normally:

```text
http://localhost:8501
```

The application allows the user to:

1. enter name and phone;
2. record or upload audio;
3. submit the recording;
4. process the audio;
5. view extracted properties;
6. view previous submissions;
7. play stored audio.

For detailed audio-processing logic, database schema, validation, and application behavior, see:

```text
task3_audio_app/README.md
```

---

# Generated Outputs

The primary generated artifacts are:

```text
task1_data_pipeline/data/processed/consultbae.db
task2_automation/reports/sample_tagged_output.csv
task3_audio_app/audio_files/
```

Task 2's live classification output is written to Google Sheets.

Task 3 stores submission metadata in the shared SQLite database under:

```text
audio_submissions
```

Generated artifacts should not be committed unless explicitly required by the assignment.

---

# Database Relationship

Task 1 provides the canonical person identity used by the downstream tasks.

The primary relationship is:

```text
persons
   │
   ├── source_records
   │
   ├── match_log
   │
   └── audio_submissions
```

`person_id` is also retained in the Task 2 output so that skill classifications can be traced back to the canonical person.

---

# Validation Checklist

## Task 1

* [ ] All three CSV files can be ingested.
* [ ] Structurally malformed rows are quarantined.
* [ ] Raw values are preserved.
* [ ] Normalized comparison values are generated.
* [ ] Within-source duplicates are grouped safely.
* [ ] Cross-source matches use exact normalized identifiers.
* [ ] RapidFuzz is used only as documented secondary corroboration/review support.
* [ ] Name and city alone never force a merge.
* [ ] Conflicts are recorded.
* [ ] SQLite database is generated successfully.
* [ ] Matching outcomes can be inspected.

## Task 2

* [ ] n8n workflow JSON is imported successfully.
* [ ] Workflow reads Task 1 person-level data.
* [ ] Gemini is configured with the fixed category list.
* [ ] Missing skills are handled without an unnecessary model call.
* [ ] Invalid model output is detected.
* [ ] `person_id` is preserved.
* [ ] Results are written to a separate output sheet.
* [ ] Rerunning does not silently create duplicate rows.
* [ ] Credentials are not committed.

## Task 3

* [ ] Streamlit application starts successfully.
* [ ] Name and phone can be entered.
* [ ] Audio can be recorded or uploaded.
* [ ] Audio is stored safely.
* [ ] Duration is extracted.
* [ ] Sample rate is extracted.
* [ ] Bitrate is extracted or estimated with the documented method.
* [ ] Loudness is extracted using the documented definition.
* [ ] Submission is written to SQLite.
* [ ] Unmatched submissions are still accepted.
* [ ] Submissions are listed.
* [ ] Stored audio can be played.
* [ ] Processing failures are visible.

---

# Testing & Verification

The project should be tested at three levels.

## Unit-Level Testing

Individual functions should be tested for:

* email normalization;
* phone normalization;
* city normalization;
* date parsing;
* entity-resolution logic;
* audio duration extraction;
* sample-rate extraction;
* loudness calculation;
* bitrate calculation.

## Integration Testing

The main end-to-end flows are:

```text
Raw CSV → SQLite
Malformed row → Quarantine
Task 1 person data → n8n
n8n → Categorized Google Sheet
Audio submission → SQLite
Audio submission → Playback
```

## Manual Demonstration

The final screen recording should demonstrate:

1. Task 1 pipeline execution or generated database.
2. Task 2 n8n workflow execution.
3. Task 2 categorized Google Sheet output.
4. Task 3 Streamlit application.
5. Audio submission.
6. Extracted audio metrics.
7. All Submissions view.
8. Audio playback.

---

# Error Handling

The implementation handles errors conservatively.

### Task 1

* malformed rows are quarantined;
* repeated headers are excluded;
* conflicting identifiers are flagged;
* ambiguous people are not automatically merged;
* raw evidence is retained.

### Task 2

* missing skills receive a deterministic result;
* invalid model output is flagged;
* source identifiers are preserved;
* reruns are controlled to avoid unexplained duplicates.

### Task 3

* invalid input is rejected with a visible message;
* unsupported/corrupt audio is handled as a controlled processing error;
* audio analysis errors are recorded;
* unsafe filenames are not trusted;
* unmatched people are accepted with a nullable `person_id`.

---

# Security & Privacy Considerations

Although this is an assignment prototype:

* credentials and API keys are not committed;
* user-provided filenames are not used directly as storage paths;
* generated filenames are unique;
* raw and normalized values are separated;
* uploaded audio is stored locally;
* database files and uploaded audio are gitignored;
* person matching does not rely on name alone;
* ambiguous identity matches are not force-resolved.

A production deployment would additionally require:

* authentication;
* authorization;
* encrypted storage;
* HTTPS;
* access-controlled audio;
* retention and deletion policies;
* database access controls;
* upload scanning;
* audit logging.

---

# Known Limitations

## Task 1

* Conservative matching may leave some records unresolved.
* The city alias map covers observed dataset variants rather than every possible spelling.
* Name and city are not sufficient for automatic merging.
* Ambiguous dates require a documented default.
* Compensation values may use different units across sources.
* The source data is assignment data rather than a production data feed.

## Task 2

* The workflow is manually triggered.
* The input Google Sheet is populated from Task 1 output rather than automatically ingesting every new CSV.
* LLM classification can be imperfect for overlapping skills.
* Only one dominant category is stored.
* The workflow is designed for a small batch rather than high-volume production processing.
* Rate-limit and retry handling are limited.

## Task 3

* Audio is stored on the local filesystem.
* SQLite is appropriate for this prototype but not high-concurrency production traffic.
* Supported audio formats depend on installed decoder libraries.
* Bitrate may be estimated for some formats.
* RMS dBFS is not the same as LUFS.
* The noise estimate, if present, is heuristic.
* There is no authentication or user-account system.
* Local Streamlit deployment is not designed for large-scale concurrent usage.

---

# Data Issues Report

The final data issues report should be completed after the final pipeline execution using the actual generated results.

It should include:

* source-level row counts;
* accepted and quarantined row counts;
* malformed-row details;
* duplicate identifiers;
* missing-value patterns;
* city variants;
* date parsing issues;
* compensation-unit issues;
* match outcomes;
* ambiguous records;
* conflicting identifiers;
* final canonical-person counts.

> **Important:** This section should be populated with actual run results rather than estimated values.

---

# Stuck Log

The following entries document the main implementation difficulties and how they were resolved.

---

## 1. Learning n8n and Debugging Data Flow Between Nodes

### Problem

This was my first time working with n8n, so one of the initial challenges was understanding how nodes pass data to each other and how the JSON output of one node becomes the input of the next.

I initially assumed that fields available earlier in the workflow, such as `person_id` and `name`, would continue to be available after every subsequent node. This assumption caused an issue when I introduced the Gemini node.

After the Gemini node, the generated result was available downstream, but some of the original fields I needed, particularly `person_id` and `name`, were no longer present in the output in the form I expected.

This meant that the final step did not have enough information to associate the generated result with the correct person.

### Investigation

I inspected the execution data for the individual nodes and compared:

* the input entering the Gemini node;
* the output produced by Gemini;
* the data available to the downstream node.

This showed that the issue was not that the original data had disappeared from the workflow entirely. Rather, the Gemini node's output did not contain all of the upstream fields I had expected to be carried forward.

### Research

I researched:

* n8n node input and output behavior;
* JSON data flow;
* n8n expressions;
* referencing data from previous nodes;
* inspecting execution data;
* Loop Over Items behavior.

I also used AI tools to help interpret the execution output and compare possible expression patterns. I verified the suggestions against the actual n8n execution data.

### Approaches Considered

I considered:

1. continuing to reference everything from `$json` after the Gemini node;
2. changing the Gemini output structure;
3. adding a transformation step to reconstruct the original fields;
4. explicitly referencing the original fields from the earlier node.

The first approach was rejected because it assumed that the Gemini node would preserve the complete input object.

### Final Solution

I explicitly referenced `person_id`, `name`, and the other required source fields from the earlier node where they were available, while taking the generated classification result from the Gemini node.

Conceptually:

```text
Original record
      │
      ├──────────────→ person_id / name / skills
      │
      ↓
   Gemini
      │
      └──────────────→ generated category
                         │
                         ↓
                  Output Google Sheet
```

I then tested the workflow with a small number of rows and verified that:

* the correct `person_id` was retained;
* the original name and skills were preserved;
* the Gemini result was written to the correct output column;
* the number of output rows matched the expected input rows.

### What I Learned

The main lesson was not to assume that all upstream fields automatically propagate through every n8n node.

When a field is missing, inspecting execution data is more effective than guessing about expressions. I also gained a practical understanding of n8n's node-based execution model and JSON data flow.

---

## 2. Learning Audio Processing in an Unfamiliar Technical Domain

### Problem

I had not worked with audio processing before this assignment.

The application needed to extract:

* duration;
* sample rate;
* bitrate;
* loudness.

Initially, I assumed these would all be simple metadata fields. During research, I found that they represent different types of information.

Duration and sample rate can commonly be obtained from decoded audio information. Bitrate depends on the format and encoding. Loudness requires analysing the audio signal rather than simply reading a file header.

### Investigation

I researched:

* sample rate;
* bitrate;
* audio duration;
* amplitude;
* decibels;
* RMS measurements;
* audio containers;
* codecs;
* compressed and uncompressed audio.

I compared Python libraries that could decode audio and provide the required metrics.

### Libraries Used

The implementation uses:

* `librosa` for loading and decoding audio;
* `soundfile` for audio information such as subtype;
* `numpy` for RMS, peak, and logarithmic calculations;
* `hashlib` for SHA-256 file hashing and duplicate detection.

I avoided adding more dependencies than necessary for the assignment.

### Audio Processing Flow

```text
Audio input
    ↓
Validate submission
    ↓
Save file
    ↓
Decode audio
    ↓
Extract sample rate and duration
    ↓
Determine bitrate
    ↓
Calculate loudness
    ↓
Calculate optional noise estimate
    ↓
Store metadata and processing result
```

### Browser Recording

The application supports browser recording and file upload.

Browser-recorded audio can use formats or codecs that are not decoded identically by every Python library. I therefore wrapped the decoding process so that a failure becomes a controlled application error rather than an unhandled exception.

This was important because successfully creating an audio file in the browser does not guarantee that every downstream Python library can decode it.

### Final Solution

I chose a clear measurement definition for each metric and stored the extracted values with the submission record.

The loudness field is represented as:

```text
loudness_dbfs
```

because the implementation uses an RMS-based dBFS calculation rather than LUFS.

Bitrate is stored together with its calculation method.

### What I Learned

Audio processing involves several layers:

```text
File/container metadata
        +
Codec and format compatibility
        +
Signal-level analysis
```

Understanding this distinction helped me choose appropriate libraries and make the processing pipeline more defensive.

---

## 3. Handling Bitrate Differences Across Audio Formats

### Problem

Bitrate was not equally straightforward for every audio format.

For uncompressed PCM audio, the bitrate can be derived from sample rate, bits per sample, and number of channels. For other formats, the available metadata may not expose an exact encoded bitrate.

This made it unsafe to populate a bitrate field without also documenting how the value had been obtained.

### Investigation

I compared bitrate information across the audio files used during testing.

I considered:

* reading bitrate directly from metadata;
* calculating PCM bitrate from audio properties;
* estimating average bitrate from file size and duration;
* returning no value when bitrate could not be determined.

I also reviewed library documentation and used AI tools to compare the trade-offs between exact metadata and estimated values.

### Final Solution

The implementation uses two explicit methods:

```text
uncompressed_pcm
average_estimated
```

For uncompressed PCM:

```text
bitrate =
sample rate × bits per sample × number of channels
```

For other formats, the estimate is approximately:

```text
bitrate =
file size × 8 / duration
```

The calculation method is stored alongside the bitrate.

This prevents an estimated value from being presented as though it were an exact codec bitrate.

### What I Learned

A field can be technically populated while still being semantically misleading.

The method used to derive a value is part of the data and should be preserved when different records may have different levels of precision.

---

## 4. Designing Conservative Entity Resolution for Messy People Data

### Problem

Task 1 required records from three different source systems to be consolidated into one canonical person table.

The sources did not have a shared ID, and fields such as names, phones, emails, and cities varied in formatting.

The central challenge was avoiding false-positive merges.

### Investigation

I profiled:

* missing values;
* duplicate emails;
* duplicate phones;
* formatting differences;
* city variants;
* source-specific fields;
* possible cross-source links;
* contradictory identifiers.

I normalized identifiers before attempting matching.

### Matching Decision

I considered using one overall fuzzy score, but rejected it because arbitrary weights and thresholds would be difficult to defend.

The final strategy used:

```text
Normalize identifiers
        ↓
Group within source
        ↓
Find exact identifiers
        ↓
Check uniqueness
        ↓
Use secondary name corroboration where required
        ↓
Detect conflicts
        ↓
Match / review / unresolved
```

RapidFuzz was used with `fuzz.token_sort_ratio` and the configured name threshold of `70` as a secondary corroboration check after an exact phone match.

It was not used as unrestricted name-only matching.

### Malformed Record

The malformed record was in the Gig Workers CSV:

```csv
"react, javascript, mysql",ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG,Isha Chopra,1406/hr,Pune,active
```

The row was structurally displaced relative to:

```text
email_id, worker_name, rate, location, status, skill_tags
```

I considered:

1. automatically shifting the values;
2. dropping the row;
3. quarantining it.

I quarantined the row and preserved the raw data, source, row number, and reason.

### Why

The correct repair could not be proven safely. A clean Isha Chopra record already existed elsewhere, so automatically repairing the malformed row introduced more risk than value.

### What I Learned

Entity resolution should not maximize the number of matches at any cost.

A good system distinguishes between:

```text
Strong evidence
     ↓
Safe match

Weak evidence
     ↓
Review or unresolved

Conflicting evidence
     ↓
Do not automatically merge
```

Preserving provenance and explaining why a match was made is as important as producing the final merged database.

---

# Future Improvements

## Task 1

* Add a configurable review interface for ambiguous matches.
* Add stronger phone validation.
* Support more international phone formats.
* Improve date parsing with source-specific metadata.
* Add automated regression tests for known entity-resolution cases.
* Export review and quarantine reports as CSV files.

## Task 2

* Add automatic ingestion from Google Drive.
* Add incremental upsert behavior using `person_id`.
* Add retry logic for transient model errors.
* Add rate-limit handling.
* Add human review for invalid or uncertain classifications.
* Store classification history and prompt version.

## Task 3

* Move audio files to object storage.
* Replace SQLite with PostgreSQL for concurrent use.
* Add background audio processing.
* Add authentication and access control.
* Add audio duration limits.
* Add upload scanning.
* Add idempotency and retry handling.
* Add monitoring and structured logs.

These improvements are intentionally outside the current assignment scope.

---

# Documentation

The repository contains detailed task-specific documentation:

| Document                        | Purpose                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| `README.md`                     | Overall assignment, architecture, setup, execution, validation, issues, and stuck log |
| `DECISIONS.md`                  | Cross-task implementation decisions                                                   |
| `task1_data_pipeline/README.md` | Detailed data pipeline and entity-resolution documentation                            |
| `task2_automation/README.md`    | Detailed n8n workflow and Gemini automation documentation                             |
| `task3_audio_app/README.md`     | Detailed Streamlit and audio-processing documentation                                 |


---


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
