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
