"""
Within-source strong-identifier grouping for ConsultBae Task 1.

Groups records belonging to the SAME source file into clusters based on
shared normalized email or phone. This step deliberately avoids a naive
connected-components merge (see docs/DECISIONS.md, decision D4):

    Record A: email X, phone 1
    Record B: email X, phone 2
    Record C: email Y, phone 2

Plain union-find would connect A-B (via email X) and B-C (via phone 2),
collapsing {A, B, C} into one person — even though A and C share nothing,
and their OTHER identifier disagrees through the "hub" record B. This
module treats that pattern as a CONFLICT, not a duplicate cluster.

Rule:
  For each connected component (built via shared email OR shared phone):
    - If every member's normalized_email agrees (or is null), OR every
      member's normalized_phone agrees (or is null) -> there is one
      consistent "anchor" identifier holding the group together safely.
      -> outcome: 'exact_duplicate' (if every raw field also matches) or
                  'duplicate_variant' (minor differences in other fields,
                  e.g. two emails for the same phone).
    - If BOTH fields show more than one distinct non-null value across
      the component -> the group only holds together by chaining through
      different identifier types (the hub problem).
      -> outcome: 'conflicting_identifier' — never merged automatically.

Name-only duplicates (no shared strong identifier at all) never form a
multi-member component here in the first place — they are handled later,
in matching/review.py, as candidate-generation evidence only.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceRecord:
    source_name: str
    source_row_index: int
    raw_name: Optional[str]
    normalized_email: Optional[str]
    normalized_phone: Optional[str]
    raw: dict  # full original row, kept for provenance/logging/exact-dup check


@dataclass
class Cluster:
    records: list[SourceRecord]
    outcome: str                       # 'single' | 'exact_duplicate' |
                                         # 'duplicate_variant' | 'conflicting_identifier'
    anchor_field: Optional[str]        # 'email' | 'phone' | None
    anchor_value: Optional[str]
    evidence: str


class _DisjointSet:
    def __init__(self):
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry


def _raw_matches_ignoring_row_index(a: dict, b: dict) -> bool:
    keys = set(a) | set(b)
    keys.discard("_source_row_index")
    return all(a.get(k) == b.get(k) for k in keys)


def group_within_source(records: list[SourceRecord]) -> list[Cluster]:
    """Groups records from ONE source into clusters, with conflict detection."""
    n = len(records)
    ds = _DisjointSet()
    for i in range(n):
        ds.find(i)

    email_index: dict[str, list[int]] = {}
    phone_index: dict[str, list[int]] = {}
    for i, r in enumerate(records):
        if r.normalized_email:
            email_index.setdefault(r.normalized_email, []).append(i)
        if r.normalized_phone:
            phone_index.setdefault(r.normalized_phone, []).append(i)

    for group in email_index.values():
        for i in group[1:]:
            ds.union(group[0], i)
    for group in phone_index.values():
        for i in group[1:]:
            ds.union(group[0], i)

    components: dict[int, list[int]] = {}
    for i in range(n):
        components.setdefault(ds.find(i), []).append(i)

    clusters: list[Cluster] = []
    for indices in components.values():
        members = [records[i] for i in indices]

        if len(members) == 1:
            clusters.append(Cluster(
                records=members, outcome="single",
                anchor_field=None, anchor_value=None,
                evidence="Only record with these identifiers in this source.",
            ))
            continue

        distinct_emails = {m.normalized_email for m in members if m.normalized_email}
        distinct_phones = {m.normalized_phone for m in members if m.normalized_phone}
        email_consistent = len(distinct_emails) <= 1
        phone_consistent = len(distinct_phones) <= 1

        row_refs = ", ".join(f"row {m.source_row_index}" for m in members)

        if not email_consistent and not phone_consistent:
            # Both fields disagree within the group -> only connected via
            # chaining through different identifiers. Classic hub problem.
            detail = ", ".join(
                f"row {m.source_row_index} (email={m.normalized_email}, phone={m.normalized_phone})"
                for m in members
            )
            clusters.append(Cluster(
                records=members, outcome="conflicting_identifier",
                anchor_field=None, anchor_value=None,
                evidence=f"Connected only by chaining through different identifiers; "
                         f"both email and phone disagree across the group: {detail}. "
                         f"Not merged automatically — quarantined for review.",
            ))
            continue

        anchor_field = "email" if distinct_emails else "phone" if distinct_phones else None
        anchor_value = next(iter(distinct_emails), None) or next(iter(distinct_phones), None)

        if all(_raw_matches_ignoring_row_index(members[0].raw, m.raw) for m in members[1:]):
            outcome = "exact_duplicate"
        else:
            outcome = "duplicate_variant"

        clusters.append(Cluster(
            records=members, outcome=outcome,
            anchor_field=anchor_field, anchor_value=anchor_value,
            evidence=f"Consistent shared {anchor_field} ({anchor_value}) across {row_refs}.",
        ))

    return clusters


if __name__ == "__main__":
    # Smoke test against the two patterns this module must get right.

    # Case 1: Nikhil Chopra pair — same phone, two emails -> duplicate_variant
    nikhil_a = SourceRecord("naukri", 10, "Nikhil Chopra", "nikhil.chopra70@example.com",
                             "9000000103", {"City": "Pune"})
    nikhil_b = SourceRecord("naukri", 11, "Nikhil Chopra", "alt.nikhil.chopra70@example.com",
                             "9000000103", {"City": "Pune"})

    # Case 2: the A/B/C conflict pattern
    rec_a = SourceRecord("test", 1, "A", "X", "1", {})
    rec_b = SourceRecord("test", 2, "B", "X", "2", {})
    rec_c = SourceRecord("test", 3, "C", "Y", "2", {})

    for cluster in group_within_source([nikhil_a, nikhil_b, rec_a, rec_b, rec_c]):
        print(cluster.outcome, "->", [r.source_row_index for r in cluster.records], "|", cluster.evidence)
