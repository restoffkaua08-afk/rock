import pytest

from rock.core.contracts import CouncilProtocol, Model, Task
from rock.core.council import CouncilEngine
from rock.core.protocols import (
    CritiqueSynthesisProtocol,
    ParallelProtocol,
    RedTeamProtocol,
    VoteProtocol,
    get_protocol,
)
from rock.providers.mock import MockProvider


def test_protocol_registry_returns_expected_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.PARALLEL), ParallelProtocol)
    assert isinstance(get_protocol(CouncilProtocol.CRITIQUE_SYNTHESIS), CritiqueSynthesisProtocol)


def test_protocol_registry_returns_red_team_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.RED_TEAM), RedTeamProtocol)


def test_protocol_registry_returns_vote_runner() -> None:
    assert isinstance(get_protocol(CouncilProtocol.VOTE), VoteProtocol)




@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("protocol", "role_key", "expected_marker"),
    [
        ("debate", "council_judge_model", "Mock judge"),
        ("red_team", "council_red_team_model", "Mock response"),
        ("vote", "council_voter_model", "Mock response"),
    ],
)
async def test_protocols_execute_through_council(protocol, role_key, expected_marker) -> None:
    providers = {"a": MockProvider("a"), "b": MockProvider("b")}
    models = {
        "a:default": Model(id="a:default", provider="a", model_name="mock-a"),
        "b:default": Model(id="b:default", provider="b", model_name="mock-b"),
    }
    metadata = {
        "council_protocol": protocol,
        role_key: "b",
        "council_synthesizer_model": "a",
        "council_verifier_model": "b",
    }
    task = Task(
        id=f"t-{protocol}",
        prompt=f"exercise {protocol}",
        metadata=metadata,
        policy={"budget": {"max_rounds": 2}},
    )

    engine = CouncilEngine(providers, models)
    synthesis, verification, responses = await engine.run(task, ["a:default", "b:default"])

    assert len(responses) == 2
    assert expected_marker in synthesis
    assert verification.passed