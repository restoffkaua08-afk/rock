from __future__ import annotations

from collections.abc import Callable

from rock.core.contracts import Agent, AgentRun, Capability, ExecutionStatus, Response
from rock.core.providers import Provider
from rock.core.skills import SkillRegistry

EventSink = Callable[[str, str, str, str, str | None], None]


class AgentRuntime:
    """Bounded model-only agent runtime.

    V0.3 deliberately has no direct tool or OS execution. An agent can reason
    for a bounded number of turns, but every turn still goes through a Rock
    provider and the runtime owns the iteration limit.
    """

    def __init__(self, providers: dict[str, Provider], registry: SkillRegistry | None = None) -> None:
        self.providers = providers
        self.registry = registry

    @staticmethod
    def _emit(
        event_sink: EventSink | None,
        name: str,
        status: str,
        detail: str,
        error: str | None = None,
    ) -> None:
        if event_sink:
            event_sink("agent", name, status, detail, error)

    def _build_prompt(self, agent: Agent, prompt: str, history: list[Response]) -> str:
        sections = []
        if agent.system_policy.strip():
            sections.append(f"Agent policy:\n{agent.system_policy.strip()}")
        if agent.skills and self.registry:
            loaded = self.registry.select(agent.skills)
            if loaded:
                sections.append(
                    "Loaded capabilities:\n"
                    + "\n\n".join(
                        f"## {item.name}\n{item.instructions}" for item in loaded
                    )
                )
        sections.append(f"Task:\n{prompt}")
        if history:
            sections.append(
                "Previous agent turns:\n"
                + "\n\n".join(f"[turn {i}] {item.content}" for i, item in enumerate(history, 1))
            )
        return "\n\n".join(sections)

    async def execute(
        self,
        agent: Agent,
        prompt: str,
        *,
        task_id: str,
        timeout: float,
        event_sink: EventSink | None = None,
    ) -> AgentRun:
        run = AgentRun(agent_id=agent.id, task_id=task_id, status=ExecutionStatus.RUNNING)
        if agent.model is None:
            run.status = ExecutionStatus.FAILED
            run.metadata["error"] = "agent has no model"
            return run

        provider = self.providers.get(agent.model.provider)
        if provider is None:
            run.status = ExecutionStatus.FAILED
            run.metadata["error"] = "agent provider unavailable"
            return run

        if Capability.TEXT not in agent.model.capabilities:
            run.status = ExecutionStatus.FAILED
            run.metadata["error"] = "agent model does not support text"
            return run

        limit = max(1, min(agent.max_iterations, 16))
        history: list[Response] = []
        for iteration in range(1, limit + 1):
            self._emit(event_sink, agent.name, "running", f"turn {iteration}/{limit}")
            response = await provider.generate(
                self._build_prompt(agent, prompt, history),
                agent.model,
                timeout=timeout,
            )
            history.append(response)
            run.iterations = iteration
            run.responses.append(response)

            if response.error:
                run.status = ExecutionStatus.FAILED
                run.final_response = response
                self._emit(event_sink, agent.name, "failed", response.error, response.error)
                return run

            # V0.3 has no tool protocol yet. The model response is therefore
            # the terminal artifact for this turn; additional iterations are
            # explicit bounded refinement, not autonomous OS actions.
            if iteration == limit:
                run.final_response = response
                run.status = ExecutionStatus.SUCCESS
                self._emit(event_sink, agent.name, "success", f"{iteration} turn(s)")
                return run

        run.status = ExecutionStatus.FAILED
        run.metadata["error"] = "agent iteration loop terminated unexpectedly"
        return run
