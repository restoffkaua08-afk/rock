from __future__ import annotations

import re

from rock.core.contracts import Claim, Conflict, Evidence, Response


class EvidenceEngine:
    """Builds traceable evidence records and conservative conflicts from responses."""

    @staticmethod
    def collect(responses: list[Response]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for index, response in enumerate(responses, 1):
            if response.error or not response.content.strip():
                continue
            evidence_id = f"response-{index}"
            source = f"{response.provider}/{response.model}"
            statements = _extract_claims(response.content)
            claims = [
                Claim(
                    id=f"{evidence_id}-claim-{claim_index}",
                    statement=statement,
                    source=source,
                    evidence_id=evidence_id,
                    polarity=_claim_polarity(statement),
                    metadata={"kind": "model_claim"},
                )
                for claim_index, statement in enumerate(statements, 1)
            ]
            evidence.append(
                Evidence(
                    id=evidence_id,
                    source=source,
                    content=response.content.strip(),
                    provider=response.provider,
                    claims=claims,
                    metadata={"kind": "model_response", "model": response.model},
                )
            )
        return evidence

    @staticmethod
    def detect_conflicts(evidence: list[Evidence]) -> list[Conflict]:
        conflicts: list[Conflict] = []

        for left_index, left in enumerate(evidence):
            for right in evidence[left_index + 1 :]:
                conflicting_pairs = []

                for left_claim in left.claims:
                    for right_claim in right.claims:
                        overlap = _key_terms(left_claim.statement) & _key_terms(right_claim.statement)
                        similarity = _claim_similarity(left_claim.statement, right_claim.statement)
                        markers = _contradiction_markers(
                            left_claim.statement,
                            right_claim.statement,
                        )
                        if not overlap or (similarity < 0.35 and not markers):
                            continue

                        if markers:
                            conflicting_pairs.append(
                                (left_claim, right_claim, overlap, markers)
                            )

                if not conflicting_pairs:
                    continue

                claim_map: dict[str, str] = {}
                overlaps: set[str] = set()
                markers: list[str] = []

                for left_claim, right_claim, overlap, pair_markers in conflicting_pairs:
                    claim_map[left_claim.id] = left_claim.statement
                    claim_map[right_claim.id] = right_claim.statement
                    overlaps.update(overlap)
                    markers.extend(pair_markers)

                unique_markers = list(dict.fromkeys(markers))
                severity = min(1.0, 0.5 + 0.1 * len(unique_markers))
                conflicts.append(
                    Conflict(
                        id=f"conflict-{len(conflicts) + 1}",
                        topic="claim contradiction",
                        claims=list(claim_map.values()),
                        claim_ids=list(claim_map),
                        claim_statements=claim_map,
                        sources=[left.source, right.source],
                        severity=severity,
                        metadata={
                            "overlap_terms": sorted(overlaps),
                            "markers": unique_markers,
                            "pair_count": len(conflicting_pairs),
                            "similarity_threshold": 0.35,
                        },
                    )
                )

        return conflicts


def _key_terms(text: str) -> set[str]:
    words = {word.strip(".,:;!?()[]{}'\"").lower() for word in text.split()}
    return {word for word in words if len(word) >= 5}


def _claim_similarity(left: str, right: str) -> float:
    left_terms = _semantic_terms(left)
    right_terms = _semantic_terms(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def _semantic_terms(text: str) -> set[str]:
    stopwords = {
        "about", "after", "also", "because", "being", "could", "from",
        "have", "into", "more", "most", "only", "should", "that", "their",
        "there", "these", "this", "those", "under", "using", "with", "would",
        "feature", "system", "the", "and", "for", "are", "was",
    }
    return {term for term in _key_terms(text) if term not in stopwords}


def _claim_polarity(text: str) -> str | None:
    lowered = text.lower()
    positive = re.search(r"\b(required|mandatory|always|true|yes|supports)\b", lowered)
    negative = re.search(r"\b(optional|never|false|no|unsupported|does not support)\b", lowered)
    if positive and negative:
        return "mixed"
    if positive:
        return "positive"
    if negative:
        return "negative"
    return None


def _contradiction_markers(left: str, right: str) -> list[str]:
    markers = []
    pairs = (
        ("yes", "no"),
        ("true", "false"),
        ("always", "never"),
        ("required", "optional"),
        ("supports", "does not support"),
        ("supports", "unsupported"),
    )
    a = left.lower()
    b = right.lower()
    for first, second in pairs:
        if (first in a and second in b) or (second in a and first in b):
            markers.append(f"{first}/{second}")

    left_polarity = _claim_polarity(left)
    right_polarity = _claim_polarity(right)
    if {left_polarity, right_polarity} == {"positive", "negative"}:
        markers.append("polarity/positive-negative")

    return list(dict.fromkeys(markers))


def _extract_claims(text: str) -> list[str]:
    """Extract conservative claim-sized statements while preserving list structure."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    statements: list[str] = []

    for line in normalized.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Markdown/list prefixes are presentation, not part of the claim.
        while line.startswith(("- ", "* ", "+ ")):
            line = line[2:].strip()
        if line and line[:2].isdigit() and line[2:3] in {".", ")"}:
            line = line[3:].strip()

        # Split ordinary prose into sentences, but keep abbreviations/decimal-like
        # fragments conservative by requiring a meaningful trailing sentence.
        parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9])", line)
        for part in parts:
            statement = part.strip()
            if len(statement) < 12:
                continue
            if statement[-1] not in ".!?":
                statement += "."
            statements.append(statement)

    return statements or [normalized.strip()]
