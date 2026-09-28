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

class DebateProtocol(CouncilProtocolRunner):
    protocol = CouncilProtocol.DEBATE

    async def critique_rounds(self, engine, context, critic_model, rounds, *, event_sink=None):
        participants = context.responses
        transcript: list[str] = []
        rounds = max(1, rounds)
        for round_number in range(1, rounds + 1):
            for response in participants:
                model_id = next(
                    (
                        mid for mid, model in engine.models.items()
                        if model.provider == response.provider
                        and model.model_name == response.model
                    ),
                    None,
                )
                if model_id is None:
                    continue
                previous = "\n\n".join(transcript[-6:])
                prompt = (
                    "You are a participant in Rock's multi-model debate. "
                    "Challenge weak claims, defend strong claims, and respond to "
                    "the other participants. Do not treat consensus as proof. "
                    f"Round: {round_number}/{rounds}\n\n"
                    f"Task:\n{context.task.prompt}\n\n"
                    f"Previous debate:\n{previous or 'No previous debate.'}"
                )
                result = await engine.debate_turn(
                    context.task,
                    model_id,
                    prompt,
                    event_sink=event_sink,
                )
                if result.content.strip():
                    transcript.append(
                        f"[round {round_number}][{response.provider}/{response.model}]\n"
                        f"{result.content}"
                    )

        transcript_text = "\n\n".join(transcript)
        judge_prompt = (
            "You are Rock's debate judge. Evaluate the debate transcript for "
            "contradictions, evidence quality, unsupported claims and unresolved "
            "questions. Produce a concise adjudication for the synthesis agent. "
            "Do not declare something true merely because multiple participants "
            "agree.\n\n"
            f"Task:\n{context.task.prompt}\n\n"
            f"Debate transcript:\n{transcript_text}"
        )
        return await engine.debate_turn(
            context.task,
            critic_model,
            judge_prompt,
            event_sink=event_sink,
            event_name="Judge",
        )


class RedTeamProtocol(CouncilProtocolRunner):
    protocol = CouncilProtocol.RED_TEAM

    async def critique_rounds(self, engine, context, critic_model, rounds, *, event_sink=None):
        material = "\n\n".join(
            f"[{r.provider}/{r.model}]\n{r.content}" for r in context.responses
        )
        prompt = (
            "You are Rock's red-team agent. Your job is to actively attack the "
            "candidate answers before synthesis. Find hidden assumptions, factual "
            "risks, contradictions, missing edge cases, ambiguous requirements and "
            "ways the final answer could fail. Do not merely summarize. Return "
            "specific attack findings and concrete tests or corrections.\n\n"
            f"Task:\n{context.task.prompt}\n\nCandidate answers:\n{material}"
        )
        result = await engine.debate_turn(
            context.task,
            critic_model,
            prompt,
            event_sink=event_sink,
            event_name="Red Team",
        )
        for round_number in range(2, max(1, rounds) + 1):
            follow_up = (
                "Continue the red-team attack. Re-examine your previous findings, "
                "try to disprove them, and identify any remaining failure modes. "
                f"Round: {round_number}/{rounds}\n\nPrevious findings:\n{result.content}"
            )
            result = await engine.debate_turn(
                context.task,
                critic_model,
                follow_up,
                event_sink=event_sink,
                event_name="Red Team",
            )
        return result


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
        CouncilProtocol.DEBATE: DebateProtocol(),
        CouncilProtocol.RED_TEAM: RedTeamProtocol(),
    }[protocol]
