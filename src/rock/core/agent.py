from __future__ import annotations

from rock.core.contracts import Agent, Response
from rock.core.providers import Provider


class AgentRuntime:
    def __init__(self, providers: dict[str, Provider]) -> None:
        self.providers = providers

    async def execute(self, agent: Agent, prompt: str, *, timeout: float) -> Response:
        if agent.model is None:
            return Response(provider="rock", model="agent", content="", error="agent has no model")
        provider = self.providers.get(agent.model.provider)
        if provider is None:
            return Response(
                provider=agent.model.provider,
                model=agent.model.model_name,
                content="",
                error="agent provider unavailable",
            )
        system = agent.system_policy.strip()
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        return await provider.generate(full_prompt, agent.model, timeout=timeout)
