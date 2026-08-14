Task 3 — Audio Submission App
Collects a gig worker's name, phone, and voice recording (upload or in-browser), validates and stores the audio, extracts basic audio properties, matches the submitter against Task 1's persons table by normalized phone, and stores everything in the shared SQLite database. Includes a listing view with playback.

Built as a single Streamlit app (not a FastAPI + Streamlit split) to keep local setup and demoing simple — one process, no backend URL/CORS to manage.

Setup
bash


cd task3_audio_app
pip install -r requirements.txt
python -m streamlit run streamlit_app.py
Open the local URL Streamlit prints (usually http://localhost:8501).

Structure


task3_audio_app/
├── streamlit_app.py    # UI + submission flow
├── db.py               # DB access, matching, schema
├── audio_utils.py       # Validation, property extraction, hashing
├── audio_files/          # Runtime-generated, not committed
└── requirements.txt
Key decisions
Matches submissions to Task 1 people by normalized phone, not name — unique match required; ambiguous or conflicting matches are left unlinked rather than guessed. person_id is nullable; audio is always accepted even if unmatched.
Every submission has a processing_status (processing/completed/failed) — analysis failures are recorded with the error, never silently dropped or misreported.
Files are stored under generated UUID names; the original filename is kept as metadata only.
Duplicate files (by SHA-256 hash) are flagged, not blocked — full history is preserved.
Bitrate is a calculated average (labelled via bitrate_method), not the true encoded bitrate. Loudness uses one consistent metric: RMS dBFS.
Known limitations
Bitrate is an estimate, not the actual encoded bitrate.
Duplicate detection is exact-match only.
Single-process, local-only — not built for concurrent production load (see TASK5_SCALING.md).
Noise estimate (if present) is a rough heuristic, not a validated SNR score.