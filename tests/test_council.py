import pytest

from rock.core.contracts import Model, Task
from rock.core.council import CouncilEngine
from rock.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_parallel_council() -> None:
    providers = {"a": MockProvider("a"), "b": MockProvider("b")}
    models = {
        "a:default": Model(id="a:default", provider="a", model_name="mock-a"),
        "b:default": Model(id="b:default", provider="b", model_name="mock-b"),
    }
    engine = CouncilEngine(providers, models)
    synthesis, verification, responses = await engine.run(
        Task(id="t1", prompt="hello"), ["a:default", "b:default"]
    )
    assert len(responses) == 2
    assert verification.passed
    assert "Mock response" in synthesis


@pytest.mark.asyncio
async def test_council_critique_protocol_supports_multiple_rounds() -> None:
    providers = {"a": MockProvider("a"), "b": MockProvider("b")}
    models = {
        "a:default": Model(id="a:default", provider="a", model_name="mock-a"),
        "b:default": Model(id="b:default", provider="b", model_name="mock-b"),
    }
    engine = CouncilEngine(providers, models)
    task = Task(
        id="t-rounds",
        prompt="hello",
        metadata={"council_protocol": "critique_synthesis"},
        policy={"budget": {"max_rounds": 2}},
    )

    synthesis, verification, responses = await engine.run(
        task, ["a:default", "b:default"]
    )

    assert len(responses) == 2
    assert "Mock synthesis" in synthesis
    assert verification.passed


@pytest.mark.asyncio
async def test_council_roles_can_use_different_models() -> None:
    providers = {"a": MockProvider("a"), "b": MockProvider("b")}
    models = {
        "a:default": Model(id="a:default", provider="a", model_name="mock-a"),
        "b:default": Model(id="b:default", provider="b", model_name="mock-b"),
    }
    engine = CouncilEngine(providers, models)
    task = Task(
        id="t-roles",
        prompt="hello",
        metadata={
            "council_critic_model": "b",
            "council_synthesizer_model": "a",
            "council_verifier_model": "b",
        },
    )

    synthesis, verification, responses = await engine.run(
        task, ["a:default", "b:default"]
    )

    assert len(responses) == 2
    assert "Mock synthesis from a" in synthesis
    assert verification.verifier == "b/mock-b"
    assert verification.passed


@pytest.mark.asyncio
async def test_verification_loop_can_correct_synthesis() -> None:
    from rock.core.providers import Provider
    from rock.core.contracts import Model, Response, Task

    class OneTimeReview(Provider):
        def __init__(self):
            self.calls = 0

        async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
            self.calls += 1
            text = "FAIL\ncorrectable finding" if self.calls == 1 else "PASS\ncorrected"
            return Response(provider=model.provider, model=model.model_name, content=text)

    reviewer = OneTimeReview()
    engine = CouncilEngine(
        {"writer": MockProvider("writer"), "reviewer": reviewer},
        {
            "writer:default": Model(id="writer:default", provider="writer", model_name="mock-writer"),
            "reviewer:default": Model(id="reviewer:default", provider="reviewer", model_name="mock-reviewer"),
        },
    )
    task = Task(
        id="verification-loop",
        prompt="answer reliably",
        policy={"budget": {"max_rounds": 2}},
        metadata={
            "council_synthesizer_model": "writer",
            "council_verifier_model": "reviewer",
        },
    )

    synthesis, verification, _ = await engine.run(
        task, ["writer:default", "reviewer:default"]
    )

    assert "Mock synthesis from writer" in synthesis
    assert reviewer.calls == 2
    assert verification.passed
