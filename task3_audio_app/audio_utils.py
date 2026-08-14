"""
audio_utils.py — audio validation and property extraction for Task 3.

Metrics extracted:
    - duration_sec
    - sample_rate_hz
    - bitrate_kbps (+ bitrate_method: "uncompressed_pcm" or "average_estimated")
    - loudness_dbfs (RMS-based; explicitly dBFS, not LUFS)
    - noise_estimate (bonus; a rough heuristic only, not a validated SNR score)
"""

import numpy as np
import librosa
import soundfile as sf
import hashlib

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}


class AudioValidationError(Exception):
    """Raised when an uploaded/recorded file fails validation or decoding."""


def validate_upload(file_bytes: bytes, filename: str) -> None:
    if not file_bytes:
        raise AudioValidationError("File is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise AudioValidationError(
            f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit."
        )

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AudioValidationError(
            f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def extract_properties(file_path: str, file_size_bytes: int) -> dict:
    """
    Decode the audio file and extract required properties.
    Raises AudioValidationError if the file cannot be decoded.
    """
    try:
        data, sample_rate = librosa.load(file_path, sr=None, mono=False)
    except Exception as exc:
        raise AudioValidationError(f"Could not decode audio file: {exc}") from exc

    if data.size == 0:
        raise AudioValidationError("Decoded audio contains no samples.")

    if data.ndim > 1:
        channels = data.shape[0]
        mono = data.mean(axis=0)
    else:
        channels = 1
        mono = data

    duration_sec = len(mono) / float(sample_rate)

    # --- Bitrate: label clearly, don't fake codec precision ---------------
    is_pcm = False
    bits_per_sample = 16
    try:
        info = sf.info(file_path)
        subtype = (info.subtype or "").upper()
        is_pcm = "PCM" in subtype or subtype in ("FLOAT", "DOUBLE")
        bits_per_sample = {
            "PCM_16": 16, "PCM_24": 24, "PCM_32": 32, "PCM_U8": 8,
            "FLOAT": 32, "DOUBLE": 64,
        }.get(subtype, 16)
    except Exception:
        pass  # not libsndfile-readable (e.g. mp3/webm) -> fall back below

    if is_pcm:
        bitrate_kbps = (sample_rate * bits_per_sample * channels) / 1000.0
        bitrate_method = "uncompressed_pcm"
    else:
        bitrate_kbps = (file_size_bytes * 8) / duration_sec / 1000.0
        bitrate_method = "average_estimated"

    # --- Loudness: RMS dBFS, explicitly labeled -----------------------------
    rms = float(np.sqrt(np.mean(np.square(mono))))
    loudness_dbfs = 20.0 * np.log10(rms) if rms > 0 else -120.0

    # --- Bonus: rough heuristic, NOT a validated SNR measurement -----------
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    noise_estimate = (
        round(20.0 * np.log10(peak / rms), 2) if (peak > 0 and rms > 0) else None
    )

    return {
        "duration_sec": round(duration_sec, 3),
        "sample_rate_hz": int(sample_rate),
        "bitrate_kbps": round(bitrate_kbps, 1),
        "bitrate_method": bitrate_method,
        "loudness_dbfs": round(loudness_dbfs, 2),
        "noise_estimate": noise_estimate,
    }

def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
