"""
Cross-source linking for ConsultBae Task 1 — the Source 1 "bridge" logic.

Source 1 (Naukri) is the only file with BOTH email and phone. This module
links Source 2 (email-only) and Source 3 (phone-only) records against
already-formed Source 1 clusters (from matching/grouping.py).

Core rule (decision D2, D7 in docs/DECISIONS.md):
  A cross-source record links to a Source 1 cluster ONLY if:
    1. its normalized identifier (email for Source 2, phone for Source 3)
       matches EXACTLY ONE existing Source 1 cluster, AND
    2. nothing else on the record materially contradicts that cluster
       (e.g. no wildly different name suggesting a coincidental identifier
       collision — not expected in this dataset, but checked defensively).

  If the identifier matches ZERO clusters -> candidate for a new person
  (or ambiguous, if name+city overlaps with an existing person — see
  matching/review.py).

  If the identifier matches MORE THAN ONE cluster -> ambiguous, never
  auto-linked (this should not happen with a clean anchor value, but is
  guarded against explicitly rather than assumed away).

Name+city is NEVER used in this module to trigger a link. It is only used
downstream (matching/review.py) to rank/prioritize unresolved records for
human review.
"""

from dataclasses import dataclass
from typing import Optional

from task1_data_pipeline.src.matching.grouping import Cluster, SourceRecord


@dataclass
class LinkDecision:
    record: SourceRecord
    outcome: str                 # 'high_confidence_match' | 'ambiguous' | 'new_person_candidate'
    matched_cluster: Optional[Cluster]
    match_method: str            # 'exact_email' | 'exact_phone' | 'none'
    evidence: str


def _valid_anchor_clusters(clusters: list[Cluster]) -> list[Cluster]:
    """
    Only clusters that are safe to link against: not conflicting_identifier
    (those are quarantined at the grouping stage and must never be linked
    into by other sources).
    """
    return [c for c in clusters if c.outcome != "conflicting_identifier"]


def _clusters_matching_email(clusters: list[Cluster], email: str) -> list[Cluster]:
    return [
        c for c in clusters
        if any(r.normalized_email == email for r in c.records)
    ]


def _clusters_matching_phone(clusters: list[Cluster], phone: str) -> list[Cluster]:
    return [
        c for c in clusters
        if any(r.normalized_phone == phone for r in c.records)
    ]


def link_by_email(record: SourceRecord, naukri_clusters: list[Cluster]) -> LinkDecision:
    """Used for Source 2 (Gig Worker) records — email is their only strong identifier."""
    if not record.normalized_email:
        return LinkDecision(record, "new_person_candidate", None, "none",
                             "No email present; no identifier to link on.")

    safe_clusters = _valid_anchor_clusters(naukri_clusters)
    matches = _clusters_matching_email(safe_clusters, record.normalized_email)

    if len(matches) == 1:
        return LinkDecision(
            record, "high_confidence_match", matches[0], "exact_email",
            f"Normalized email '{record.normalized_email}' matches exactly one "
            f"Naukri cluster (row {matches[0].records[0].source_row_index}).",
        )
    if len(matches) > 1:
        return LinkDecision(
            record, "ambiguous", None, "exact_email",
            f"Normalized email '{record.normalized_email}' matches {len(matches)} "
            f"distinct Naukri clusters — should not happen with a clean anchor; "
            f"flagged for manual review rather than guessed.",
        )
    return LinkDecision(
        record, "new_person_candidate", None, "none",
        f"No Naukri record shares email '{record.normalized_email}'. "
        f"No safe bridge match — becomes a new person or goes to name+city review.",
    )


def link_by_phone(record: SourceRecord, naukri_clusters: list[Cluster]) -> LinkDecision:
    """Used for Source 3 (CBNexus) records — phone is their only strong identifier."""
    if not record.normalized_phone:
        return LinkDecision(record, "new_person_candidate", None, "none",
                             "No phone present; no identifier to link on.")

    safe_clusters = _valid_anchor_clusters(naukri_clusters)
    matches = _clusters_matching_phone(safe_clusters, record.normalized_phone)

    if len(matches) == 1:
        return LinkDecision(
            record, "high_confidence_match", matches[0], "exact_phone",
            f"Normalized phone '{record.normalized_phone}' matches exactly one "
            f"Naukri cluster (row {matches[0].records[0].source_row_index}).",
        )
    if len(matches) > 1:
        return LinkDecision(
            record, "ambiguous", None, "exact_phone",
            f"Normalized phone '{record.normalized_phone}' matches {len(matches)} "
            f"distinct Naukri clusters — flagged for manual review rather than guessed.",
        )
    return LinkDecision(
        record, "new_person_candidate", None, "none",
        f"No Naukri record shares phone '{record.normalized_phone}'. "
        f"No safe bridge match — this record does NOT get forced onto an "
        f"existing person on name/city alone (decision D7).",
    )


if __name__ == "__main__":
    # Worked test case: Arjun Mehta (see docs/DECISIONS.md, decision D3)

    naukri_arjun = SourceRecord(
        "naukri", 5, "Arjun Mehta", "arjun.mehta9@example.in", "9000000131", {},
    )
    naukri_cluster = Cluster(
        records=[naukri_arjun], outcome="single", anchor_field=None,
        anchor_value=None, evidence="Only Naukri record for this identifier.",
    )

    cbnexus_arjun_match = SourceRecord(
        "cbnexus", 20, "Arjun Mehta", None, "9000000131", {},
    )
    cbnexus_arjun_no_match = SourceRecord(
        "cbnexus", 33, "Arjun Mehta", None, "9000000272", {},
    )
    gig_arjun_no_match = SourceRecord(
        "gig_worker", 8, "Arjun Mehta", "arjun.mehta77@mailtest.example.org", None, {},
    )

    for rec in [cbnexus_arjun_match, cbnexus_arjun_no_match]:
        decision = link_by_phone(rec, [naukri_cluster])
        print(f"[cbnexus row {rec.source_row_index}] {decision.outcome} | {decision.evidence}")

    decision = link_by_email(gig_arjun_no_match, [naukri_cluster])
    print(f"[gig_worker row {decision.record.source_row_index}] {decision.outcome} | {decision.evidence}")
