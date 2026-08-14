"""
Normalization functions for ConsultBae Task 1.

Design principle: every function takes a raw value and returns a normalized
value PLUS enough metadata to explain what was assumed. Raw values are never
discarded by this module — callers are responsible for storing both raw and
normalized values (see db/schema.sql).

No entity-matching decisions happen here. This module only cleans fields.
"""

import re
from datetime import date


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def normalize_email(raw_email: str | None) -> str | None:
    """Lowercase + strip whitespace. Does not validate email format —
    the assignment's data doesn't contain malformed emails, only casing
    differences (e.g. ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG)."""
    if raw_email is None:
        return None
    cleaned = raw_email.strip().lower()
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

def normalize_phone(raw_phone: str | None) -> str | None:
    """
    Normalize to a bare 10-digit Indian mobile number.

    Observed raw formats in the data:
      +919000000254   -> 9000000254
      919000000231    -> 9000000231
      09000000287     -> 9000000287
      9000000237      -> 9000000237
      +91-9000000131  -> 9000000131

    Rule: strip all non-digit characters, then strip a leading '91' country
    code (if the result would still be >10 digits) or a leading '0'
    (trunk prefix), then take the last 10 digits.
    """
    if raw_phone is None:
        return None
    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        return None
    # Strip a single leading trunk '0'
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    # Strip country code '91' if present and result is still 12 digits
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    # Final safety: keep only the last 10 digits
    return digits[-10:] if len(digits) >= 10 else digits


# ---------------------------------------------------------------------------
# City
# ---------------------------------------------------------------------------

# Derived from profiling ALL distinct raw city values across the 3 files
# (documented in docs/DECISIONS.md, decision D7). Small and explicit —
# not auto-clustered.
CITY_ALIAS_MAP = {
    "gurgaon": "gurugram",
    "bangalore": "bengaluru",
}

# Broader grouping used ONLY for candidate generation in matching —
# never claimed as canonically identical cities in the persons table.
DELHI_NCR_VARIANTS = {"delhi", "new delhi", "delhi ncr"}


def normalize_city(raw_city: str | None) -> dict:
    """
    Returns a dict:
      {
        "normalized_city": <cleaned, alias-applied city name>,
        "match_region": <broader grouping used only for candidate generation>
      }

    Example:
      "GURGAON"   -> {"normalized_city": "gurugram", "match_region": "gurugram"}
      "New Delhi" -> {"normalized_city": "new delhi", "match_region": "delhi_ncr"}
      "Delhi NCR" -> {"normalized_city": "delhi ncr", "match_region": "delhi_ncr"}
    """
    if raw_city is None:
        return {"normalized_city": None, "match_region": None}

    cleaned = raw_city.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)  # collapse internal double spaces

    normalized = CITY_ALIAS_MAP.get(cleaned, cleaned)

    if cleaned in DELHI_NCR_VARIANTS:
        match_region = "delhi_ncr"
    else:
        match_region = normalized

    return {"normalized_city": normalized, "match_region": match_region}


# ---------------------------------------------------------------------------
# Date (Naukri "Applied Date")
# ---------------------------------------------------------------------------

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(raw_date: str | None) -> dict:
    """
    Returns:
      {
        "raw": <original string>,
        "normalized_date": <YYYY-MM-DD string or None if unparseable>,
        "date_parse_status": "unambiguous" | "ambiguous_default" | "unparseable"
      }

    Handles the 4 formats actually observed in Source 1:
      - ISO:            2026-08-08
      - Textual:        7 Jul 2026
      - Slash/hyphen ambiguous between DD-MM and MM-DD:
                         01-08-2026, 07/03/2026  -> default DD-MM-YYYY (India context)
                         07/13/2026, 08/19/2026  -> unambiguous MM/DD (day > 12)
    """
    if raw_date is None:
        return {"raw": raw_date, "normalized_date": None, "date_parse_status": "unparseable"}

    text = raw_date.strip()
    if not text:
        return {"raw": raw_date, "normalized_date": None, "date_parse_status": "unparseable"}

    # ISO: YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if m:
        y, mo, d = map(int, m.groups())
        return _result(raw_date, y, mo, d, "unambiguous")

    # Textual: "7 Jul 2026"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$", text)
    if m:
        d, mon_str, y = m.groups()
        mon = MONTH_NAMES.get(mon_str.lower())
        if mon:
            return _result(raw_date, int(y), mon, int(d), "unambiguous")

    # Slash or hyphen numeric: A-B-YYYY or A/B/YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", text)
    if m:
        a, b, y = map(int, m.groups())
        if a > 12 and b <= 12:
            # a must be the day -> A/B/YYYY is DD-MM-YYYY... but wait, need
            # to check which convention the file uses per-value.
            # a>12 means a can't be a month -> a is day, b is month.
            return _result(raw_date, y, b, a, "unambiguous")
        if b > 12 and a <= 12:
            # b can't be a month -> b is day, a is month (MM/DD/YYYY)
            return _result(raw_date, y, a, b, "unambiguous")
        if a <= 12 and b <= 12:
            # Genuinely ambiguous. Documented default: DD-MM-YYYY (India context).
            return _result(raw_date, y, b, a, "ambiguous_default")

    return {"raw": raw_date, "normalized_date": None, "date_parse_status": "unparseable"}


def _result(raw, y, mo, d, status):
    try:
        normalized = date(y, mo, d).isoformat()
    except ValueError:
        return {"raw": raw, "normalized_date": None, "date_parse_status": "unparseable"}
    return {"raw": raw, "normalized_date": normalized, "date_parse_status": status}


# ---------------------------------------------------------------------------
# CTC (Naukri "Current CTC") — mixed absolute-rupee and lakh values
# ---------------------------------------------------------------------------

# Threshold derived from actual data: all "lakh-scale" values observed are
# < 20 (e.g. 4.2, 8.3, 11.9); all absolute-rupee values are > 300,000.
# There is a clean, wide gap between the two clusters, so a threshold of
# 1000 is a safe, documented separator.
CTC_LAKH_THRESHOLD = 1000


def normalize_ctc(raw_ctc: str | None) -> dict:
    """
    Returns:
      {
        "raw": <original string>,
        "normalized_ctc_inr": <float, always in absolute INR>,
        "ctc_unit_assumed": "absolute_inr" | "lakhs_inr"
      }
    """
    if raw_ctc is None:
        return {"raw": raw_ctc, "normalized_ctc_inr": None, "ctc_unit_assumed": None}
    try:
        value = float(str(raw_ctc).strip())
    except ValueError:
        return {"raw": raw_ctc, "normalized_ctc_inr": None, "ctc_unit_assumed": None}

    if value < CTC_LAKH_THRESHOLD:
        return {"raw": raw_ctc, "normalized_ctc_inr": value * 100_000, "ctc_unit_assumed": "lakhs_inr"}
    return {"raw": raw_ctc, "normalized_ctc_inr": value, "ctc_unit_assumed": "absolute_inr"}


# ---------------------------------------------------------------------------
# Rate (Gig Workers) — "/hr" vs "k/month"
# ---------------------------------------------------------------------------

# Documented assumption: 8 hours/day, 22 working days/month = 176 hrs/month.
# Used only to compare hourly and monthly rates on a common basis for
# reporting; NEVER used as entity-matching evidence.
ASSUMED_HOURS_PER_MONTH = 176


def normalize_rate(raw_rate: str | None) -> dict:
    """
    Returns:
      {
        "raw": <original string>,
        "normalized_monthly_inr": <float>,
        "rate_unit_assumed": "hourly" | "monthly"
      }
    """
    if raw_rate is None:
        return {"raw": raw_rate, "normalized_monthly_inr": None, "rate_unit_assumed": None}

    text = raw_rate.strip().lower()

    m = re.match(r"^(\d+(\.\d+)?)/hr$", text)
    if m:
        hourly = float(m.group(1))
        return {"raw": raw_rate, "normalized_monthly_inr": hourly * ASSUMED_HOURS_PER_MONTH,
                 "rate_unit_assumed": "hourly"}

    m = re.match(r"^(\d+(\.\d+)?)k/month$", text)
    if m:
        monthly = float(m.group(1)) * 1000
        return {"raw": raw_rate, "normalized_monthly_inr": monthly, "rate_unit_assumed": "monthly"}

    return {"raw": raw_rate, "normalized_monthly_inr": None, "rate_unit_assumed": None}


# ---------------------------------------------------------------------------
# Status (Gig Workers) — Active/Inactive/paused
# ---------------------------------------------------------------------------

def normalize_status(raw_status: str | None) -> str | None:
    """
    Casing collapsed for 'active'/'inactive'. 'paused' is kept as its own
    distinct value — it is NOT the same as 'inactive' in this dataset.
    """
    if raw_status is None:
        return None
    cleaned = raw_status.strip().lower()
    if cleaned in ("active", "inactive", "paused"):
        return cleaned
    return cleaned or None  # preserve unexpected values rather than silently dropping


# ---------------------------------------------------------------------------
# Verified (CBNexus) — Y/N, Yes/No
# ---------------------------------------------------------------------------

def normalize_verified(raw_verified: str | None) -> bool | None:
    if raw_verified is None:
        return None
    cleaned = raw_verified.strip().lower()
    if cleaned in ("y", "yes"):
        return True
    if cleaned in ("n", "no"):
        return False
    return None


import re

_SCI_NOTATION_RE = re.compile(r'^-?\d+(\.\d+)?[eE][+-]?\d+$')

def normalize_phone(raw: str | None) -> str | None:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None

    if _SCI_NOTATION_RE.match(raw):
        # Phone number was corrupted into scientific notation -- almost
        # certainly Excel auto-formatting a long digit string as a number.
        # The original digits are IRRECOVERABLE (e.g. "9E+09" could be any
        # ~10-digit number starting with 9). Do not attempt to reconstruct
        # digits from this: doing so risks fabricating a phone number that
        # could coincidentally collide with someone else's real number.
        return None

    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10:
        return None
    return digits[-10:]
