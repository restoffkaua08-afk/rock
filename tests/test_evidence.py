from rock.core.contracts import Response
from rock.core.evidence import EvidenceEngine


def response(provider: str, content: str) -> Response:
    return Response(provider=provider, model="mock", content=content)


def test_collect_builds_traceable_evidence() -> None:
    evidence = EvidenceEngine.collect(
        [response("a", "The system supports feature X."), response("b", "Feature X is optional.")]
    )
    assert len(evidence) == 2
    assert evidence[0].source == "a/mock"
    assert evidence[1].metadata["kind"] == "model_response"


def test_detect_conflicts_flags_explicit_contradiction() -> None:
    conflicts = EvidenceEngine.detect_conflicts(
        [
            response("a", "Feature X is required and always enabled."),
            response("b", "Feature X is optional and never enabled."),
        ]
    )
    assert len(conflicts) == 1
    assert conflicts[0].resolved is False
    assert conflicts[0].severity > 0.5


def test_detect_conflicts_does_not_flag_unrelated_answers() -> None:
    conflicts = EvidenceEngine.detect_conflicts(
        [response("a", "Python is useful for automation."), response("b", "Rust is useful for systems.")]
    )
    assert conflicts == []



def test_adjudication_parse_keeps_inconclusive_status() -> None:
    from rock.core.adjudication import AdjudicationEngine
    from rock.core.contracts import AdjudicationStatus, Conflict

    conflict = Conflict(
        id="c1",
        topic="feature",
        claims=["Feature is required.", "Feature is optional."],
        sources=["a/mock", "b/mock"],
    )
    result = AdjudicationEngine.parse(
        conflict,
        Response(
            provider="judge",
            model="mock",
            content="INCONCLUSIVE\nThe supplied claims do not establish which condition is correct.\nConfidence: 0.4",
        ),
    )
    assert result.status is AdjudicationStatus.INCONCLUSIVE
    assert result.confidence == 0.4



def test_collect_extracts_traceable_claims() -> None:
    evidence = EvidenceEngine.collect(
        [response("a", "Python supports automation. Python is widely used.")]
    )
    assert len(evidence) == 1
    assert len(evidence[0].claims) == 2
    assert evidence[0].claims[0].evidence_id == evidence[0].id
    assert evidence[0].claims[0].source == "a/mock"


def test_conflict_contains_claim_ids() -> None:
    conflicts = EvidenceEngine.detect_conflicts(
        [
            response("a", "Feature X is required."),
            response("b", "Feature X is optional."),
        ]
    )
    assert len(conflicts) == 1
    assert len(conflicts[0].claim_ids) == 2



def test_adjudication_preserves_conflict_claim_ids() -> None:
    from rock.core.adjudication import AdjudicationEngine

    conflict = __import__("rock.core.contracts", fromlist=["Conflict"]).Conflict(
        id="c-claims",
        topic="feature",
        claims=["required", "optional"],
        claim_ids=["response-1-claim-1", "response-2-claim-1"],
        sources=["a/mock", "b/mock"],
    )
    result = AdjudicationEngine.parse(
        conflict,
        Response(
            provider="judge",
            model="mock",
            content="RESOLVED\nClaim one is supported.\nConfidence: 0.9",
        ),
    )
    assert result.claim_ids == conflict.claim_ids


def test_conflict_contains_only_contradictory_claims() -> None:
    conflicts = EvidenceEngine.detect_conflicts(
        [
            response("a", "Feature X is required. Python is useful for automation."),
            response("b", "Feature X is optional. Rust is useful for systems."),
        ]
    )
    assert len(conflicts) == 1
    assert set(conflicts[0].claim_statements.values()) == {
        "Feature X is required.",
        "Feature X is optional.",
    }


def test_conflict_does_not_pair_unrelated_claims_with_global_markers() -> None:
    conflicts = EvidenceEngine.detect_conflicts(
        [
            response("a", "Feature X is required. The sky is blue."),
            response("b", "Feature X is optional. This is not a statement about the sky."),
        ]
    )
    assert len(conflicts) == 1
    assert all("sky" not in claim.lower() for claim in conflicts[0].claim_statements.values())
