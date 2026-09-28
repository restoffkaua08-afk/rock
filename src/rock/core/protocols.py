from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rock.core.contracts import CouncilProtocol, Response

if TYPE_CHECKING:
    from rock.core.council import CouncilEngine
    from rock.core.contracts import Task

@dataclass(frozen=True)
class ProtocolContext:
    task: Task
    responses: list[Response]

class CouncilProtocolRunner(ABC):
    protocol: CouncilProtocol

    @abstractmethod
    async def critique_rounds(
        self,
        engine: CouncilEngine,
        context: ProtocolContext,
        critic_model: str,
        rounds: int,
        *,
        event_sink: Any = None,
    ) -> Response:
        raise NotImplementedError

class ParallelProtocol(CouncilProtocolRunner):
    protocol = CouncilProtocol.PARALLEL

    async def critique_rounds(self, engine, context, critic_model, rounds, *, event_sink=None):
        return await engine.critique(
            context.task, context.responses, critic_model, event_sink=event_sink
        )

class CritiqueSynthesisProtocol(CouncilProtocolRunner):
    protocol = CouncilProtocol.CRITIQUE_SYNTHESIS

    async def critique_rounds(self, engine, context, critic_model, rounds, *, event_sink=None):
        critique = await engine.critique(
            context.task, context.responses, critic_model, event_sink=event_sink
        )
        for round_number in range(2, rounds + 1):
            engine._emit(
                event_sink, "stage", "Critic", "running",
                f"rodada {round_number}/{rounds}",
            )
            prior = critique.content if critique.content else critique.error or ""
            augmented = context.responses + [
                Response(
                    provider="rock",
                    model="critic",
                    content=f"Previous critique:\n{prior}",
                )
            ]
            critique = await engine.critique(
                context.task, augmented, critic_model, event_sink=event_sink
            )
        return critique

def get_protocol(protocol: CouncilProtocol) -> CouncilProtocolRunner:
    return {
        CouncilProtocol.PARALLEL: ParallelProtocol(),
        CouncilProtocol.CRITIQUE_SYNTHESIS: CritiqueSynthesisProtocol(),
    }[protocol]
