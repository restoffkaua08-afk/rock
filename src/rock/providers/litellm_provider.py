from __future__ import annotations

from rock.core.contracts import Capability, Model, Response
from rock.core.providers import Provider


class LiteLLMProvider(Provider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        import litellm

        result = await litellm.acompletion(
            model=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )
        choice = result.choices[0]
        content = choice.message.content or ""
        usage = getattr(result, "usage", None)
        return Response(
            provider=self.provider_name,
            model=model.model_name,
            content=content,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )

    def capabilities(self) -> set[Capability]:
        return {Capability.TEXT, Capability.STREAMING, Capability.STRUCTURED_OUTPUT}
