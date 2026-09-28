import pytest

from rock.core.contracts import Model, Response, Task
from rock.core.council import CouncilEngine
from rock.core.providers import Provider, ProviderError
from rock.providers.mock import MockProvider


class FailingProvider(Provider):
    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        raise RuntimeError("provider unavailable")


@pytest.mark.asyncio
async def test_council_keeps_working_when_one_provider_fails() -> None:
    providers = {"ok": MockProvider("ok"), "down": FailingProvider()}
    models = {
        "ok:default": Model(id="ok:default", provider="ok", model_name="mock-ok"),
        "down:default": Model(id="down:default", provider="down", model_name="mock-down"),
    }
    engine = CouncilEngine(providers, models)

    synthesis, verification, responses = await engine.run(
        Task(id="t-failure", prompt="hello"),
        ["ok:default", "down:default"],
    )

    assert len(responses) == 2
    assert responses[1].error == "provider unavailable"
    assert "Mock synthesis" in synthesis
    assert verification.passed


def test_task_budget_can_carry_cost_limit() -> None:
    task = Task(
        id="t-budget",
        prompt="hello",
        policy={
            "budget": {
                "max_cost": 0.50,
                "max_parallel": 2,
            }
        },
    )

    assert task.policy.budget.max_cost == 0.50
    assert task.policy.budget.max_parallel == 2


@pytest.mark.asyncio
async def test_council_uses_healthy_provider_for_control_stages() -> None:
    providers = {"down": FailingProvider(), "ok": MockProvider("ok")}
    models = {
        "down:default": Model(id="down:default", provider="down", model_name="mock-down"),
        "ok:default": Model(id="ok:default", provider="ok", model_name="mock-ok"),
    }
    engine = CouncilEngine(providers, models)

    synthesis, verification, responses = await engine.run(
        Task(id="t-control-fallback", prompt="hello"),
        ["down:default", "ok:default"],
    )

    assert responses[0].error == "provider unavailable"
    assert "Mock synthesis" in synthesis
    assert verification.passed


class AuthFailProvider(Provider):
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        self.calls += 1
        raise ProviderError("authentication", "invalid API key")


@pytest.mark.asyncio
async def test_council_does_not_retry_authentication_failure() -> None:
    provider = AuthFailProvider()
    engine = CouncilEngine(
        {"auth": provider},
        {"auth:default": Model(id="auth:default", provider="auth", model_name="mock-auth")},
    )

    responses = await engine.collect(
        Task(
            id="t-auth",
            prompt="hello",
            policy={"max_retries": 3},
        ),
        ["auth:default"],
    )

    assert provider.calls == 1
    assert responses[0].error == "authentication: invalid API key"
