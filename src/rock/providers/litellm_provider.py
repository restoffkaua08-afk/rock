from __future__ import annotations

from rock.core.contracts import Capability, Model, Response
from rock.core.providers import Provider, ProviderError


class LiteLLMProvider(Provider):
    def __init__(
        self,
        provider_name: str,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.api_key = api_key
        self.api_base = api_base

    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        import litellm

        kwargs = {
            "model": model.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": timeout,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        try:
            result = await litellm.acompletion(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise self._normalize_error(exc) from exc
        choice = result.choices[0]
        content = choice.message.content or ""
        usage = getattr(result, "usage", None)
        hidden_params = getattr(result, "_hidden_params", {}) or {}
        response_cost = hidden_params.get("response_cost")
        return Response(
            provider=self.provider_name,
            model=model.model_name,
            content=content,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            estimated_cost=response_cost,
        )

    @staticmethod
    def _normalize_error(exc: Exception) -> ProviderError:
        status = getattr(exc, "status_code", None)
        message = str(exc).strip() or exc.__class__.__name__
        lowered = message.lower()
        if status in {401, 403} or "authentication" in lowered or "api key" in lowered:
            code = "authentication"
        elif status == 429 or "rate limit" in lowered or "too many requests" in lowered:
            code = "rate_limit"
        elif isinstance(exc, TimeoutError) or "timeout" in lowered or "timed out" in lowered:
            code = "timeout"
        elif status in {400, 404} or ("model" in lowered and ("not found" in lowered or "invalid" in lowered)):
            code = "model_invalid"
        else:
            code = "unavailable"
        return ProviderError(code, message)

    def capabilities(self) -> set[Capability]:
        return {Capability.TEXT, Capability.STREAMING, Capability.STRUCTURED_OUTPUT}
