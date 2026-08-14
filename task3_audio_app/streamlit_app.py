"""
streamlit_app.py — Task 3: audio intake and submissions viewer.
"""

import uuid
from pathlib import Path

import streamlit as st

from db import (
    init_audio_table, match_person, insert_submission,
    update_submission_status, get_all_submissions, utc_now_iso,
)
from db import find_duplicate_by_hash
from audio_utils import (
    validate_upload, extract_properties, compute_file_hash, AudioValidationError,
)

APP_DIR = Path(__file__).resolve().parent
AUDIO_DIR = APP_DIR / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="ConsultBae Audio Intake", layout="wide")
init_audio_table()

page = st.sidebar.radio("Navigate", ["Submit Audio", "All Submissions"])

# ============================== SUBMIT PAGE ==============================
if page == "Submit Audio":
    st.title("Submit Audio Sample")

    with st.form("submission_form", clear_on_submit=False):
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")

        st.write("Record audio or upload a file (one is required):")
        recorded = st.audio_input("Record audio")
        uploaded = st.file_uploader(
            "...or upload an audio file",
            type=["wav", "mp3", "m4a", "webm", "ogg"],
        )

        submitted = st.form_submit_button("Submit")

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Name is required.")
        if not phone.strip():
            errors.append("Phone number is required.")

        audio_source = recorded or uploaded
        if audio_source is None:
            errors.append("Please record or upload an audio file.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            file_bytes = audio_source.getvalue()
            original_filename = getattr(audio_source, "name", "recording.wav")

            try:
                validate_upload(file_bytes, original_filename)
            except AudioValidationError as e:
                st.error(f"Upload rejected: {e}")
            else:
                file_hash = compute_file_hash(file_bytes)
                duplicate_row = find_duplicate_by_hash(file_hash)

                if duplicate_row is not None:
                    st.warning(
                        f"⚠️ This exact audio file was already submitted by "
                        f"'{duplicate_row['submitted_name']}' on {duplicate_row['submitted_at']}. "
                        f"This submission will still be recorded separately."
                    )
                ext = ("." + original_filename.rsplit(".", 1)[-1].lower()
                       if "." in original_filename else ".wav")
                stored_filename = f"{uuid.uuid4()}{ext}"
                stored_path = AUDIO_DIR / stored_filename
                stored_path.write_bytes(file_bytes)

                match_result = match_person(name.strip(), phone.strip())

                record = {
                "person_id": match_result["person_id"],
                "submitted_name": name.strip(),
                "submitted_phone": phone.strip(),
                "normalized_phone": match_result["normalized_phone"],
                "phone_parse_status": match_result["phone_parse_status"],
                "match_status": match_result["match_status"],
                "match_method": match_result["match_method"],
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "mime_type": getattr(audio_source, "type", None),
                "file_size_bytes": len(file_bytes),
                "file_hash": file_hash,
                "is_duplicate": 1 if duplicate_row is not None else 0,
                "duplicate_of": duplicate_row["submission_id"] if duplicate_row is not None else None,
                "file_path": str(stored_path),
                "duration_sec": None,
                "sample_rate_hz": None,
                "bitrate_kbps": None,
                "bitrate_method": None,
                "loudness_dbfs": None,
                "noise_estimate": None,
                "processing_status": "processing",
                "processing_error": None,
                "submitted_at": utc_now_iso(),
            }
                submission_id = insert_submission(record)

                try:
                    props = extract_properties(str(stored_path), len(file_bytes))
                except AudioValidationError as e:
                    update_submission_status(
                        submission_id, processing_status="failed", processing_error=str(e)
                    )
                    st.error(f"Audio saved, but analysis failed: {e}")
                else:
                    update_submission_status(
                        submission_id, processing_status="completed", **props
                    )
                    st.success("Submission recorded and analyzed successfully.")

                    st.subheader("Extracted properties")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Duration (sec)", props["duration_sec"])
                    col2.metric("Sample rate (Hz)", props["sample_rate_hz"])
                    col3.metric("Bitrate (kbps)", props["bitrate_kbps"])
                    col1.metric("Loudness (dBFS)", props["loudness_dbfs"])
                    col2.caption(f"Bitrate method: {props['bitrate_method']}")
                    if props["noise_estimate"] is not None:
                        col3.metric("Noise estimate (heuristic)", props["noise_estimate"])

                    st.caption(
                        f"Match status: **{match_result['match_status']}**"
                        + (f" → person_id {match_result['person_id']}"
                           if match_result["person_id"] else "")
                    )

# ============================ LISTING PAGE ================================
else:
    st.title("All Submissions")

    rows = get_all_submissions()
    if not rows:
        st.info("No submissions yet.")
    else:
        for row in rows:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**{row['submitted_name']}** — {row['submitted_phone']}")
                    st.caption(
                        f"Status: {row['processing_status']} | "
                        f"Match: {row['match_status']} | "
                        f"Submitted: {row['submitted_at']}"
                    )
                    if row["processing_status"] == "completed":
                        st.write(
                            f"Duration: {row['duration_sec']}s | "
                            f"Sample rate: {row['sample_rate_hz']} Hz | "
                            f"Bitrate: {row['bitrate_kbps']} kbps ({row['bitrate_method']}) | "
                            f"Loudness: {row['loudness_dbfs']} dBFS"
                        )
                        if row["noise_estimate"] is not None:
                            st.caption(f"Noise estimate (heuristic): {row['noise_estimate']}")
                    elif row["processing_status"] == "failed":
                        st.warning(f"Processing failed: {row['processing_error']}")
                with c2:
                    file_path = Path(row["file_path"])
                    if file_path.exists():
                        st.audio(str(file_path))
                    else:
                        st.caption("Audio file unavailable.")
