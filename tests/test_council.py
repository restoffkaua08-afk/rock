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
