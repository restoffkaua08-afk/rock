import pytest

from rock.core.contracts import Model, Task
from rock.core.council import CouncilEngine
from rock.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_debate_protocol_uses_separate_judge_role() -> None:
    providers = {"a": MockProvider("a"), "b": MockProvider("b")}
    models = {
        "a:default": Model(id="a:default", provider="a", model_name="mock-a"),
        "b:default": Model(id="b:default", provider="b", model_name="mock-b"),
    }
    engine = CouncilEngine(providers, models)
    task = Task(
        id="t-debate",
        prompt="compare two approaches",
        metadata={
            "council_protocol": "debate",
            "council_judge_model": "b",
            "council_synthesizer_model": "a",
            "council_verifier_model": "b",
        },
        policy={"budget": {"max_rounds": 2}},
    )

    synthesis, verification, responses = await engine.run(
        task, ["a:default", "b:default"]
    )

    assert len(responses) == 2
    assert "Mock synthesis from a" in synthesis
    assert verification.verifier == "b/mock-b"
    assert verification.passed
