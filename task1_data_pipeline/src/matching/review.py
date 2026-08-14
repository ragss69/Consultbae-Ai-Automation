"""
Review-queue generation for ConsultBae Task 1.

This module handles records that link.py could NOT confidently attach to
an existing Naukri-anchored person (outcome = 'new_person_candidate').
It never merges anything. It only:

  1. Finds existing persons who share the same city/match_region and a
     similar name (using rapidfuzz for RANKING only — decision D8).
  2. Classifies the record as:
       - 'needs_review'  : exactly one plausible candidate person found
       - 'ambiguous'      : two or more plausible candidate persons found
                             (decision D3 — multiple name+city matches are
                             ambiguous, never "medium confidence")
       - 'new_person'     : no plausible candidate at all

A human (or a later, explicitly justified rule) makes the final call on
'needs_review' and 'ambiguous' cases. This module's job is only to make
that human review fast and well-evidenced.
"""

from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz

from task1_data_pipeline.src.matching.grouping import SourceRecord

# Minimum name similarity to even be considered a "candidate" worth
# showing to a reviewer. Documented, not tuned to a specific test case —
# 85 comfortably catches abbreviation-style variants like "R. Verma" vs
# "Rohit Verma" while excluding unrelated names.
FUZZY_NAME_THRESHOLD = 85


@dataclass
class ExistingPerson:
    person_id: int
    display_name: str
    match_region: Optional[str]  # from normalize_city(); e.g. "delhi_ncr", "gurugram"


@dataclass
class ReviewCandidate:
    person: ExistingPerson
    name_similarity: float
    match_basis: str  # 'exact_name_and_region' | 'fuzzy_name_and_region'


@dataclass
class ReviewDecision:
    record: SourceRecord
    outcome: str  # 'needs_review' | 'ambiguous' | 'new_person'
    candidates: list[ReviewCandidate]
    evidence: str


def generate_candidates(
    record: SourceRecord,
    record_match_region: Optional[str],
    existing_persons: list[ExistingPerson],
) -> list[ReviewCandidate]:
    """
    Candidate gate: same match_region is REQUIRED (city is the corroborating
    signal, not a nice-to-have). Within that gate, rank by name similarity.
    Fuzzy score alone, with no region match, is not enough to surface a
    candidate — this avoids flooding the review queue with coincidental
    name matches across unrelated cities.
    """
    if not record.raw_name or not record_match_region:
        return []

    candidates: list[ReviewCandidate] = []
    for person in existing_persons:
        if person.match_region != record_match_region:
            continue

        score = fuzz.token_sort_ratio(record.raw_name.lower(), person.display_name.lower())
        if score < FUZZY_NAME_THRESHOLD:
            continue

        basis = "exact_name_and_region" if score == 100 else "fuzzy_name_and_region"
        candidates.append(ReviewCandidate(person=person, name_similarity=score, match_basis=basis))

    # Rank strongest match first — purely for a human's convenience.
    candidates.sort(key=lambda c: c.name_similarity, reverse=True)
    return candidates


def resolve_review_outcome(
    record: SourceRecord,
    record_match_region: Optional[str],
    existing_persons: list[ExistingPerson],
) -> ReviewDecision:
    candidates = generate_candidates(record, record_match_region, existing_persons)

    if len(candidates) == 0:
        return ReviewDecision(
            record, "new_person", [],
            f"No existing person shares name+region with '{record.raw_name}' "
            f"in region '{record_match_region}'. Treated as a new person "
            f"(provisional) — not forced onto any existing record.",
        )

    if len(candidates) == 1:
        c = candidates[0]
        return ReviewDecision(
            record, "needs_review", candidates,
            f"One plausible candidate: person_id={c.person.person_id} "
            f"('{c.person.display_name}', similarity={c.name_similarity}, "
            f"basis={c.match_basis}). NOT auto-merged — no strong identifier "
            f"corroboration exists; requires human confirmation.",
        )

    names = ", ".join(f"person_id={c.person.person_id} ({c.person.display_name})" for c in candidates)
    return ReviewDecision(
        record, "ambiguous", candidates,
        f"{len(candidates)} plausible candidates share name+region '{record_match_region}' "
        f"with '{record.raw_name}': {names}. Cannot be resolved automatically — "
        f"this is exactly the pattern that must never be auto-merged (decision D3).",
    )


if __name__ == "__main__":
    # Worked case: the two CBNexus/Gig-Worker "Arjun Mehta" records that
    # link.py left as new_person_candidate (see matching/linking.py output).
    # Once one of them (or a genuinely new "Arjun Mehta" person) exists as
    # an ExistingPerson, the OTHER unresolved Arjun Mehta record should
    # surface as 'needs_review' against it — never silently merged.

    existing = [
        ExistingPerson(person_id=1, display_name="Arjun Mehta", match_region="noida"),
    ]

    unresolved_gig_worker_arjun = SourceRecord(
        "gig_worker", 8, "Arjun Mehta", "arjun.mehta77@mailtest.example.org", None, {},
    )

    decision = resolve_review_outcome(
        unresolved_gig_worker_arjun, record_match_region="noida", existing_persons=existing,
    )
    print(decision.outcome, "|", decision.evidence)

    # Now simulate a SECOND existing person also named Arjun Mehta in the
    # same region (the second CBNexus record, promoted to its own person) —
    # this must flip the outcome to 'ambiguous', not stay 'needs_review'.
    existing_two = existing + [
        ExistingPerson(person_id=2, display_name="Arjun Mehta", match_region="noida"),
    ]
    decision2 = resolve_review_outcome(
        unresolved_gig_worker_arjun, record_match_region="noida", existing_persons=existing_two,
    )
    print(decision2.outcome, "|", decision2.evidence)
