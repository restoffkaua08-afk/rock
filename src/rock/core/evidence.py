from __future__ import annotations

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
    def detect_conflicts(responses: list[Response]) -> list[Conflict]:
        usable = [r for r in responses if not r.error and r.content.strip()]
        conflicts: list[Conflict] = []
        response_claims = {
            index: _response_claims(response, index)
            for index, response in enumerate(usable, 1)
        }

        for left_index, left in enumerate(usable, 1):
            for right_index, right in enumerate(usable[left_index:], left_index + 1):
                left_claims = response_claims[left_index]
                right_claims = response_claims[right_index]
                conflicting_pairs = []

                for left_id, left_claim in left_claims.items():
                    for right_id, right_claim in right_claims.items():
                        overlap = _key_terms(left_claim) & _key_terms(right_claim)
                        if not overlap:
                            continue
                        markers = _contradiction_markers(left_claim, right_claim)
                        if markers:
                            conflicting_pairs.append(
                                (left_id, left_claim, right_id, right_claim, overlap, markers)
                            )

                if not conflicting_pairs:
                    continue

                claim_map: dict[str, str] = {}
                overlaps: set[str] = set()
                markers: list[str] = []
                for left_id, left_claim, right_id, right_claim, overlap, pair_markers in conflicting_pairs:
                    claim_map[left_id] = left_claim
                    claim_map[right_id] = right_claim
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
                        sources=[
                            f"{left.provider}/{left.model}",
                            f"{right.provider}/{right.model}",
                        ],
                        severity=severity,
                        metadata={
                            "overlap_terms": sorted(overlaps),
                            "markers": unique_markers,
                            "pair_count": len(conflicting_pairs),
                        },
                    )
                )
        return conflicts


def _key_terms(text: str) -> set[str]:
    words = {word.strip(".,:;!?()[]{}'\"").lower() for word in text.split()}
    return {word for word in words if len(word) >= 5}


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
    return markers


def _extract_claims(text: str) -> list[str]:
    """Extract coarse, sentence-level claims without pretending to prove them."""
    statements = []
    for part in text.replace("\n", " ").split("."):
        statement = part.strip()
        if len(statement) >= 12:
            statements.append(statement + ".")
    return statements or [text.strip()]


def _response_claims(response: Response, response_index: int) -> dict[str, str]:
    return {
        f"response-{response_index}-claim-{claim_index}": statement
        for claim_index, statement in enumerate(_extract_claims(response.content), 1)
    }
