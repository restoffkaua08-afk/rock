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
    ("protocol", "role_key", "expected_event"),
    [
        ("debate", "council_judge_model", "Judge"),
        ("red_team", "council_red_team_model", "Red Team"),
        ("vote", "council_voter_model", "Vote"),
    ],
)
async def test_protocols_execute_through_council(protocol, role_key, expected_event) -> None:
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
    events = []

    def sink(kind, name, status, detail, error=None):
        events.append((kind, name, status, detail, error))

    synthesis, verification, responses = await engine.run(
        task, ["a:default", "b:default"], event_sink=sink
    )

    assert len(responses) == 2
    assert synthesis
    assert verification.passed
    assert any(name == expected_event and status == "success" for _, name, status, _, _ in events)