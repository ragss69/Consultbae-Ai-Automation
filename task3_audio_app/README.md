# Task 3 — Audio Intake & Analysis App

A Streamlit app that lets a person submit their name, phone number, and an
audio sample (recorded in-browser or uploaded), automatically extracts audio
properties, matches the submission to an existing person from the Task 1
database where possible, and stores everything for later review and playback.

---

## What it does

1. Collects **name**, **phone number**, and **audio** (record or upload).
2. Validates the upload (non-empty, size limit, allowed format).
3. Saves the audio file with a safe, unique generated filename.
4. Attempts to match the submission to an existing person in the Task 1
   `persons` table, using the same phone-normalization logic as Task 1.
5. Extracts and stores:
   - Duration (seconds)
   - Sample rate (Hz)
   - Bitrate (kbps) — labeled with the method used
   - Loudness (dBFS, RMS-based)
   - A rough noise/quality heuristic (bonus, not a validated SNR score)
6. Writes one row per submission into a new `audio_submissions` table inside
   the **same** SQLite database used by Task 1 (`consultbae.db`).
7. Provides a second page listing all submissions with playback and status.

---

## Setup

From the repo root:

```bash
cd task3_audio_app
pip install -r requirements.txt
