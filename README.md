# ConsultBae Assignment — Data Pipeline, Skill Automation & Audio Collection App

This repository contains the complete implementation of the five-part ConsultBae technical assignment:

1. **Task 1 — Data Merge Pipeline**
2. **Task 2 — No-Code Skill Categorization Automation**
3. **Task 3 — Mini Audio Collection App**
4. **Task 4 - Data Issues Report**
5. **Task 5 - Scaling Stretch**

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
├── task5_scaling.md
│── requirements.txt  
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

Generated files such as the SQLite database, uploaded audio files, credentials, and local environment files are excluded through `.gitignore`.

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

## Additional Reporting Outputs

The assignment requires a data issues report in the README. In addition, the
repository includes `src/report.py`, which exports the pipeline results into
human-readable evidence files:

- `persons_merged.csv` — canonical person-level output;
- `quarantine_report.csv` — structurally rejected rows and reasons;
- `review_queue.csv` — unresolved, ambiguous, or conflicting records;
- `summary.txt` — validation and outcome counts.

These files are additional reporting outputs and are generated from the SQLite
database after the pipeline completes, by running the command:
```text
cd task1_data_pipeline
python -m src.report
```

The detailed reasoning behind the entity-resolution architecture, including alternatives considered and rejected, is documented separately:

task1/TASK_1_DECISIONS.md

This document covers decisions such as:

why Source 1 (Naukri) is used as the identity bridge;
why automatic merges require exact, exclusive and uncontradicted identifiers;
why name + city is not used as a universal identity key;
why a single numeric confidence score was rejected;
how ambiguous and conflicting records are handled.

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
python src/report.py   (optional)
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

# Validation Checklist

## Task 1

* [ ] All three CSV files can be ingested.
* [ ] Structurally malformed rows are quarantined.
* [ ] Raw values are preserved.
* [ ] Normalized comparison values are generated.
* [ ] Within-source duplicates are grouped safely.
* [ ] Cross-source matches use exact normalized identifiers.
* [ ] Conflicts are recorded.
* [ ] SQLite database is generated successfully.
* [ ] Matching outcomes can be inspected.

## Task 2

* [ ] n8n workflow JSON is imported successfully.
* [ ] Workflow reads Task 1 person-level data.
* [ ] Gemini is configured with the fixed category list.
* [ ] Missing skills are handled without an unnecessary model call.
* [ ] Invalid model output is detected.
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

# Task 4: Data Quality Report

## Overview

This document lists every data quality issue I found while building the matching pipeline across the three source files (Naukri, Gig Worker, CBNexus), along with the row-level evidence for each and exactly how the pipeline handles it. I've tried to back every claim below with an actual row from the data rather than a general description.

---

## 1. Source-level row counts

| Source | Total rows | Clean (ingested) | Quarantined |
|---|---|---|---|
| Naukri | 42 | 42 | 0 |
| Gig Worker | 32 | 30 | 2 |
| CBNexus | 31 | 30 | 1 |
| **Total** | **105** | **102** | **3** |

---

## 2. Malformed rows (quarantined)

**Blank row — Gig Worker.**
A completely empty row (`,,,,,`) sitting between the Tanvi Gupta and Varun Saxena rows. Nothing to recover here hence it was dropped.

**Repeated header — CBNexus.**
The header line (`Name,Phone Number,City,Verified,Projects Completed`) appears a second time part-way through the file, right before the Isha Kapoor block starts. Looks like two exports got concatenated without stripping the second file's header. Quarantined so it doesn't get read in as a data row.

**Shifted/malformed columns — Gig Worker, Isha Chopra.**
```
"react, javascript, mysql",ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG,Isha Chopra,1406/hr,Pune,active
```
Her skills list ended up in the email column, and everything after it shifted by one position. I quarantined this row rather than trying to shift it back into place, mainly because a correctly-formatted duplicate of the same person already exists elsewhere in the same file, so nothing was actually lost by dropping the broken one.

---

## 3. Duplicate identifiers

**Nikhil Chopra.** Two rows, identical phone (`09000000103`), identical city, experience, CTC, applied date, and skills. Only the email differs — `nikhil.chopra70@example.com` vs `alt.nikhil.chopra70@example.com`. Reads like someone re-applying using an alternate email address. Merged on the shared phone number.

**Rohit Verma / "R. Verma".** Two rows, identical email (`rohit.verma13@mailtest.example.org`) and identical phone (`9000000294`). Only the name string is abbreviated in one of them. Merged on the shared email + phone.

In both cases the merge happened because a real identifier (phone or email) matched exactly, the similar-looking name was never the thing that triggered the merge on its own.

---

## 4. Cross-source matches

**Vikram Saxena.** The strongest match in the whole dataset. His email links Naukri and Gig Worker together, and separately, his phone number links Naukri and CBNexus. Two independent identifiers, agreeing independently, across all three files.

**Arjun Mehta (person_id 19).** Naukri's phone `09000000131` and CBNexus's `+91-9000000131` normalize to the same number. Clean, confident match.

---

## 5. Ambiguous records and conflicting identifiers

This is the part of the review queue I think is worth walking through carefully, because it shows the pipeline's refusal-to-guess rule being applied consistently across two different situations.

**Case A — same anchor person, missing corroboration, two separate records.**

| Row | Name | Phone given | City | Candidate | Why it wasn't merged |
|---|---|---|---|---|---|
| CBNexus row 28 | Arjun Mehta | 9000000272 | Noida | person_id 19 (100% name+city match) | Phone doesn't match anything on file for person_id 19 |
| Gig Worker row 18 | Arjun Mehta | (none given) | Noida | person_id 19 (100% name+city match) | No phone field at all to check against |

Both records look, by name and city, exactly like the confirmed Arjun Mehta from section 4. But one of them has a phone number that flatly contradicts his known number, and the other has no phone at all to check. Neither gets auto-merged — both sit in `needs_review` as their own provisional entries rather than being folded onto the real person just because the name matches.

**Case B — same pattern, four other people.**

| Row | Name | Phone given | City | Candidate | Why it wasn't merged |
|---|---|---|---|---|---|
| CBNexus row 29 | Manish Bhatia | 919000000161 | Noida | person_id 41 | Phone conflicts with the one on record |
| CBNexus row 30 | Divya Chopra | 9000000111 | Noida | person_id 42 | Phone conflicts with the one on record |
| CBNexus row 31 | Karan Chopra | 919000000245 | Pune | person_id 43 | Phone conflicts with the one on record |
| CBNexus row 32 | Vikram Mehta | +91-9000000261 | Pune | person_id 44 | Phone conflicts with the one on record |

All four parsed fine (`phone_parse_status = ok`) — the number just isn't the one already stored for that person. That could mean the same person has a second SIM or a work number, or it could mean two different people happen to share a name and a city. There's genuinely no way to tell from the data alone, which is exactly why it's a human call and not something the pipeline should be deciding on its own.

That's six `needs_review` rows in total, matching the pipeline summary exactly.

---

## 6. Missing-value patterns

The clearest missing-value case is structural rather than incidental: the Gig Worker file has no phone column at all, which is why the Arjun Mehta and other Gig Worker rows in the review queue show `phone_parse_status = missing` rather than a parse failure. There was simply nothing to parse. This isn't a data entry gap, it's a schema difference between sources, and it's part of why some cross-source links can only ever be attempted through email, never phone, for Gig Worker records.

---

## 7. City variants

- **Case differences:** `NOIDA` / `Noida` / `noida`, `PUNE` / `Pune` / `pune`
- **Trailing whitespace:** values like `"gurugram "` with a stray trailing space
- **Genuinely different strings for arguably the same place:** `Gurgaon` vs `Gurugram` vs `gurugram` — not just a casing issue, an actual naming inconsistency
- **Ambiguous compound names:** `Delhi`, `New Delhi`, `Delhi NCR` — whether these should collapse to one canonical city is a judgment call, and I've documented it as one rather than silently deciding it inside the normalizer

---

## 8. Date parsing issues

At least four different date formats coexist in the same column:
- ISO: `2026-08-08`
- DD-MM-YYYY: `24-07-2026`
- Day-Month-name-Year: `7 Jul 2026`
- MM/DD/YYYY: `08/21/2026` (only unambiguous because 21 can't be a month)

The genuinely tricky one is `07/03/2026` — both "3rd July" and "7th March" are valid readings of the same string, and there's no way to tell which is correct without an external rule. The pipeline applies a documented assumption for this case rather than guessing silently, which matters because getting this wrong would misplace someone's application date by four months.

---

## 9. Compensation-unit issues

**Naukri `Current CTC` column.** Some values are clearly absolute rupee amounts (`417964`, `332456`), others are small decimals that only make sense if read as lakhs (`4.2`, `6.1`, `11.9`). There's no unit column anywhere in the file to disambiguate, so the pipeline applies an assumed-unit rule and explicitly logs that assumption per row rather than converting silently.

**Gig Worker `rate` column** — a second, separate unit problem: values mix `/hr` (`1415/hr`, `1406/hr`) with `/month` (`15k/month`, `72k/month`, `28k/month`) in the same field. This is a different ambiguity from the CTC one and needed its own normalization step.

---

## 10. Normalization actually required before any matching could happen

**Phone.** At least five different input formats show up across the three files: bare 10-digit, leading zero (`09000000...`), `+91` with no separator, `+91-` with a dash, and bare `91` prefix with no symbol at all. All of these had to collapse to one canonical form before comparison — without it, the Vikram Saxena and Arjun Mehta cross-source matches in section 4 simply wouldn't have fired, since the raw strings never match character-for-character.

**Email.** Case had to be normalized too — several Gig Worker emails are stored fully uppercase (e.g. `ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG`) while the matching Naukri record for the same person is lowercase. Comparing these case-sensitively would have missed real matches.

**Name.** Deliberately *not* used to trigger a merge on its own — only used to rank candidates in the review queue. The whole Arjun Mehta situation in section 5 is the clearest proof of why: several people share a name and city with someone already in the system, but without a matching identifier, name similarity alone stays a suggestion, never a merge.

---

## 11. Match outcomes and final canonical-person count

| Outcome | Count |
|---|---|
| `new_person` | 52 |
| `high_confidence_match` | 40 |
| `duplicate_variant` | 4 (2 merged pairs) |
| `needs_review` | 6 |
| **Total canonical persons** | **54** |

The gap between 52 new persons and 54 total persons comes from two of the six `needs_review` records (the CBNexus and Gig Worker Arjun Mehta rows from section 5, Case A) ending up as standalone provisional persons rather than staying fully unresolved — they couldn't be merged into the existing Arjun Mehta, but they still needed a person record of their own. The remaining four `needs_review` rows (Case B) are left unassigned pending manual confirmation, exactly as they should be.

**Totals from a full pipeline run:**
- 102 clean records ingested across all 3 sources; 3 rows quarantined (1 blank, 1 repeated header, 1 shifted-columns)
- 54 canonical persons created
- 40 records auto-linked with `high_confidence_match` (exact email/phone bridge)
- 4 records merged as intra-source `duplicate_variant` pairs (2 pairs)
- 6 records left in the review queue (`needs_review`/`ambiguous`) — 5 of which are directly caused by the scientific-notation phone corruption (issue #11) — never auto-merged on name/city alone

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

How I approached it

I started by searching for how Python libraries handle:

audio duration + sample rate + bitrate + loudness
RMS vs dBFS vs LUFS
PCM vs compressed audio
Python audio decoding

I compared librosa, soundfile, pydub and FFmpeg-based approaches.

### Library Investigation and Tradeoffs

Since audio processing was new to me, I first researched a few different Python-based approaches using documentation, examples, and LLM-assisted research. I compared them based on what I actually needed for this assignment: decoding uploaded/recorded audio, accessing the raw samples, extracting basic properties, calculating loudness, and keeping the implementation reasonably lightweight.

| Library / Approach | Why it was relevant | Why it did / didn't fit my use case | Decision |
|---|---|---|---|
| **librosa** | High-level audio loading and analysis; gives access to decoded samples and sample rate and works well with NumPy | More than a simple metadata reader, but the access to actual audio samples was useful for calculating RMS-based loudness | **Chosen as the main audio loading/analysis library** |
| **soundfile** | Lightweight audio I/O and useful file information such as sample rate, channels and subtype | Doesn't provide the higher-level analysis I needed by itself, but complemented `librosa` well | **Used alongside librosa** |
| **pydub** | Simple API for loading, converting and manipulating audio files | Useful for general audio manipulation, but I wasn't building an editing/conversion application. It would also add another layer around FFmpeg | **Considered, then rejected** |
| **FFmpeg** | Very broad codec and format support and useful when dealing with browser-generated audio | Strong option for decoding/conversion, but using it as the entire processing layer would introduce more system-level complexity than I needed for this prototype | **Used as supporting dependency rather than primary API** |
| **NumPy** | Directly works with numerical audio samples and provides everything needed for RMS and logarithmic calculations | Cannot decode audio files itself, so it needs to be used after the audio has been loaded | **Used for signal calculations** |
| **Mutagen / metadata-focused libraries** | Useful for reading metadata such as duration and bitrate from supported formats | Didn't solve the main problem of accessing decoded samples for the loudness calculation, and metadata availability varies across formats | **Not used** |

The final responsibility split was therefore:

```text
librosa
    → load/decode audio and obtain samples + sample rate

soundfile
    → inspect audio information/subtype

NumPy
    → RMS and dBFS calculations

FFmpeg
    → supporting codec/format handling

hashlib
    → SHA-256 hashing for duplicate detection

The main tradeoff I was trying to make was between format compatibility, implementation complexity, and having enough control over the actual audio signal. I initially looked for a single library that could handle everything, but the combination of librosa, soundfile and NumPy gave me clearer separation of responsibilities without adding libraries that I didn't actually need.

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

## 3. Learning Audio Processing in an Unfamiliar Technical Domain

Audio processing was probably the least familiar part of the assignment for me. I had worked with Python/data processing before, but I had not previously had to deal with audio codecs, sampling rates, RMS, bitrate, etc.

### How I approached it

I first broke down the requirement instead of trying to find one library that did everything. I searched things like:

```text
Python extract audio duration sample rate bitrate
librosa vs pydub vs soundfile Python
what is sample rate vs bitrate audio
RMS loudness dBFS Python
LUFS vs dBFS
PCM bitrate calculation
```

I also asked AI questions such as:

> "For a small Streamlit audio collection app, which Python library would you use to extract duration, sample rate, bitrate and loudness, and what are the tradeoffs?"

and then followed up with more specific questions when I didn't understand something rather than copying the first implementation.

One thing I discovered from the `librosa` documentation was that `librosa.load()` normally resamples audio to 22050 Hz, but `sr=None` preserves the file's native sampling rate. That was important for this assignment because I needed to **report the submitted file's sample rate**, not silently analyse a resampled version. ([Librosa][1])

That led me to use:

```python
librosa.load(file_path, sr=None, mono=False)
```

rather than accepting the default.

### Library investigation

I compared a few approaches before settling on the current combination:

| Option        | What I found                                                                                                                          | Decision                   |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **librosa**   | Convenient way to decode audio into samples and get the native sample rate; also gives me the signal needed for loudness calculations | **Chosen**                 |
| **soundfile** | Useful for inspecting audio properties/subtypes and particularly useful for identifying PCM formats                                   | **Used alongside librosa** |
| **pydub**     | Good high-level API for manipulation/conversion, but I didn't need its editing functionality for the required metrics                 | **Not needed**             |
| **FFmpeg**    | Much broader format/codec support, but adds a system dependency and I didn't want it to become the main analysis API                  | **Supporting dependency**  |
| **NumPy**     | Doesn't decode audio, but is ideal once I have the samples for RMS/peak calculations                                                  | **Used for calculations**  |

The main reason I didn't try to make one library responsible for everything was that the requirements were actually different types of problems: decoding, metadata inspection and signal analysis.

### The part that initially confused me: loudness

I initially thought "loudness" meant I just needed another metadata field. While researching it, I came across **RMS, dBFS and LUFS**, which made me realize that I needed to define exactly what my application meant by loudness.

For this prototype I decided to use RMS-based dBFS rather than trying to implement a full LUFS measurement.

The implementation therefore does:

```text
audio samples
     ↓
RMS
     ↓
20 × log10(RMS)
     ↓
loudness_dbfs
```

I explicitly named the database field `loudness_dbfs` rather than `loudness_lufs` so that the measurement isn't overstated.

### Bitrate was a separate decision

Bitrate was where I spent the most time because I initially assumed it would be available directly from the file.

I found that this isn't something I could safely treat identically for every format. I researched PCM bitrate and the difference between **uncompressed bitrate** and the average bitrate of compressed files.

I considered:

* reading bitrate from metadata where available;
* calculating it from sample rate, bit depth and channels;
* estimating it from file size and duration;
* leaving it blank when an exact value wasn't available.

I ended up making the calculation format-aware:

```text
PCM
 ↓
sample rate × bits/sample × channels
 ↓
uncompressed_pcm
```

For other formats where I couldn't establish an exact PCM bitrate:

```text
file size × 8 / duration
 ↓
average_estimated
```

I also store the calculation method in `bitrate_method`. This was important because I didn't want an estimated value to look like an exact codec bitrate.

The main thing I took away from this was that I couldn't treat "audio properties" as one problem. I had to understand **what information came from the file, what required decoding, and what required analysing the actual signal** before choosing the implementation.

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