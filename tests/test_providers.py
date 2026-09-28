import sys
from types import SimpleNamespace

import pytest

from rock.core.contracts import Model
from rock.providers.litellm_provider import LiteLLMProvider


@pytest.mark.asyncio
async def test_litellm_provider_passes_explicit_credentials(monkeypatch) -> None:
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=5),
            _hidden_params={"response_cost": 0.0123},
        )

    fake_litellm = SimpleNamespace(acompletion=fake_acompletion)
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)

    provider = LiteLLMProvider("openai", api_key="secret", api_base="https://example.test")
    response = await provider.generate(
        "hello",
        Model(id="openai:default", provider="openai", model_name="openai/test"),
        timeout=12,
    )

    assert captured["api_key"] == "secret"
    assert captured["api_base"] == "https://example.test"
    assert response.content == "hello"
    assert response.input_tokens == 3
    assert response.output_tokens == 5
    assert response.estimated_cost == 0.0123
