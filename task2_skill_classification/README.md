# Task 2 — No-Code Skill Categorization Automation

This task implements a **no-code skill categorization workflow using n8n**.

The workflow takes the consolidated person-level data generated in Task 1, classifies each person's skills into **one fixed business category using Gemini**, validates the model output, and writes the results to a separate Google Sheets tab.

## Workflow Overview

```text
Task 1 person export
        ↓
Google Sheets input
        ↓
n8n Manual Trigger
        ↓
Read people
        ↓
Validate input & handle missing skills
        ↓
Classify skills with Gemini
        ↓
Validate category
        ↓
Write tagged results to Google Sheets
```

The exported n8n workflow is the primary deliverable:

```text
workflow/
└── consultbae_skill_categorization.json
```

![n8n workflow](images/Screenshot%202026-08-16%20224437.jpg)

---

## Why Use an LLM?

The Task 1 output contains heterogeneous skill combinations, for example:

* `n8n, LangChain, REST APIs, MongoDB, SQL`
* `SQL, Python, JavaScript, Docker`

Rule-based keyword matching would require many overlapping conditions because individual skills can belong to multiple categories.

Gemini is therefore used as a **constrained classification step**. The model must select exactly one category from a predefined list.

> **Important:** The LLM is used only for skill categorization. Person identity is inherited from Task 1 through `person_id`.

---

## Categories

Each person is assigned exactly **one dominant category**.

| Category                  | Description                                                           |
| ------------------------- | --------------------------------------------------------------------- |
| **Web Development**       | Frontend, backend, APIs, web frameworks, and application development  |
| **Data / Analytics**      | SQL, Pandas, statistics, reporting, analytics, and data engineering   |
| **Automation / AI**       | Workflow automation, n8n, Zapier, AI, machine learning, and LangChain |
| **Design**                | UI/UX, Figma, Adobe, visual design, branding, and related skills      |
| **Sales / Ops / Support** | Sales, customer support, CRM, recruiting, and business operations     |
| **Other**                 | Insufficient, unclear, or unrelated skill evidence                    |

The model is instructed to choose the **dominant category**, rather than returning multiple categories.

---

## Project Structure

```text
task2_automation/
├── input/
│   └── persons_for_task2.csv
│       └── Task 1 person-level input
│
├── workflow/
│   └── consultbae_skill_categorization.json
│       └── Exported n8n workflow
│
├── reports/
│   └── sample_tagged_output.csv
│       └── Sample/exported output
│
├── README.md
└── DECISIONS.md
```

The **n8n workflow JSON is the source of truth** for the automation.

---

## Input Contract

The workflow reads the Task 1 person-level export from Google Sheets.

### Required fields

| Field          | Purpose                                            |
| -------------- | -------------------------------------------------- |
| `person_id`    | Stable canonical identifier from Task 1            |
| `display_name` | Human-readable name                                |
| `skills_raw`   | Combined skill information used for classification |

Optional fields such as `city`, `match_status`, and `source_count` may also be present.

The workflow assumes Task 1 has already consolidated records so that there is **at most one row per `person_id`**.

---

## Google Sheets Setup

Create a Google Sheets file with two tabs.

### Input

**Tab:** `ConsultBae_Persons`

Minimum headers:

```text
person_id
display_name
skills_raw
```

Populate this tab using the Task 1 person-level export.

### Output

**Tab:** `ConsultBae_Persons_Tagged`

Recommended headers:

```text
person_id
display_name
skills_raw
skill_category
classification_status
classified_at
workflow_run_id
model_name
prompt_version
```

Keeping the output separate ensures that the original Task 1 data remains unchanged and auditable.

---

## Workflow Steps

### 1. Manual Trigger

The workflow starts with an n8n **Manual Trigger**.

This was chosen because it is:

* Simple and reliable for a batch assignment
* Easy to demonstrate during a screen recording
* Free from unnecessary webhook or scheduling configuration

A Schedule Trigger could be added for periodic execution in a production version.

### 2. Read Input

The Google Sheets node reads records from:

```text
ConsultBae_Persons
```

Each person is processed individually.

### 3. Validate Input

The workflow checks for:

* `person_id`
* `display_name`
* `skills_raw`

If `skills_raw` is missing, the record **does not call Gemini**.

Instead:

```text
skill_category = Other
classification_status = missing_skills
```

This avoids unnecessary LLM calls when there is no classification evidence.

### 4. Gemini Classification

Gemini receives the person's skill information and is instructed to:

1. Select exactly one allowed category.
2. Use the predefined category definitions.
3. Select the dominant category.
4. Return only the exact category name.
5. Return `Other` when there is insufficient evidence.

The original identity fields are preserved alongside the model output.

### 5. Validate Model Output

The model response is normalized and checked against the six allowed categories.

Valid responses are accepted.

Unexpected responses are marked:

```text
classification_status = invalid_model_output
```

The invalid response is retained rather than silently converting it to `Other`, making the workflow auditable.

### 6. Write Results

The final records are written to:

```text
ConsultBae_Persons_Tagged
```

Each output row contains the classification and relevant execution metadata.

`person_id` maintains the connection between the Task 1 canonical person and the Task 2 classification.

---

## Rerun Behavior

The workflow uses a **full-refresh approach**.

Before a new classification run, the output is cleared/rebuilt so that rerunning the workflow does not append duplicate results.

This ensures:

* Task 1 input remains untouched.
* Task 2 always represents the latest complete run.
* Repeated executions do not create duplicate classifications.

If this is later converted to an incremental workflow, `person_id` should be used as the logical key for upserts.

---

## Running the Workflow

### 1. Prepare the Input

Import the Task 1 export into:

```text
ConsultBae_Persons
```

Ensure these columns exist:

```text
person_id
display_name
skills_raw
```

### 2. Prepare the Output

Create:

```text
ConsultBae_Persons_Tagged
```

Add the required output headers.

### 3. Import the Workflow

Open n8n and import:

```text
workflow/consultbae_skill_categorization.json
```

Then configure:

* Google Sheets credentials
* Input spreadsheet/tab
* Output spreadsheet/tab
* Gemini credentials

**Credentials and API keys are not committed to the repository.**

### 4. Execute

Run the workflow using the **Manual Trigger**.

Verify that:

* Input rows are read correctly.
* People with skills are sent to Gemini.
* Missing skills are handled without an LLM call.
* Gemini responses are validated.
* Output rows are written successfully.
* `person_id` is preserved.

---

## Example Output

| person_id | display_name | skills_raw                      | skill_category   | classification_status |
| --------- | ------------ | ------------------------------- | ---------------- | --------------------- |
| `p001`    | Tanvi Gupta  | n8n, LangChain, REST APIs, SQL  | Automation / AI  | valid                 |
| `p002`    | Amit Agarwal | SQL, Python, JavaScript, Docker | Data / Analytics | valid                 |
| `p003`    | Example User | —                               | Other            | missing_skills        |

The exact classification depends on the skills present in the input.

---

## Key Design Decisions

* **Fixed schema:** The workflow relies on standardized fields such as `person_id`, `display_name`, and `skills_raw`.
* **Pre-merged skills:** `skills_raw` is already consolidated across sources by Task 1; Task 2 only performs classification.
* **Constrained LLM:** Gemini can only select from six predefined categories.
* **No blind trust in model output:** Responses are validated before being written.
* **Deterministic missing-data handling:** Empty `skills_raw` skips Gemini and receives `Other / missing_skills`.
* **Full-refresh execution:** The output is rebuilt on each run to prevent duplicate classifications.
* **Auditability:** Classification metadata such as `classified_at`, `workflow_run_id`, `model_name`, and `prompt_version` can be retained for traceability.
* **Google Sheets as an adapter:** The sheet is manually populated from Task 1 rather than acting as an automated file-ingestion pipeline.
* **LLM for practicality:** Gemini is used because skill categorization can involve ambiguous and overlapping skills; this is not a claim that an LLM is universally more accurate than rules.

---

## Validation Checklist

Before submission, verify:

* [ ] Workflow is implemented in n8n.
* [ ] Workflow JSON is exported and committed.
* [ ] Input comes from the Task 1 person-level output.
* [ ] `person_id` is preserved.
* [ ] Only the six allowed categories can be returned.
* [ ] Missing skills are handled without an LLM call.
* [ ] Invalid model outputs are detected.
* [ ] Rerunning does not create duplicate rows.
* [ ] Results are written to a separate output sheet.
* [ ] Workflow execution is demonstrated in the screen recording.
* [ ] Credentials/API keys are excluded from the repository.

---

## Known Limitations

* Category boundaries can be ambiguous for people with broad skill sets.
* Classification quality depends on the LLM's judgment.
* Invalid model outputs require manual review.
* Only one dominant category is stored per person.
* The workflow is manually triggered rather than a live ingestion pipeline.
* It is designed for a small batch and does not include production-scale queueing or rate-limit orchestration.
* New people require the input sheet to be updated and the workflow to be run again.

---

## Future Improvements

A production version could add:

* Automated Google Drive or webhook triggers
* Incremental processing
* Upserts based on `person_id`
* Retry handling for transient Gemini failures
* Rate-limit management
* Human review for uncertain classifications
* Classification history
* Confidence scores and supporting skill evidence

These features were intentionally excluded to keep the assignment **simple, explainable, and focused on the core automation**.
