from __future__ import annotations

from rock.core.contracts import Adjudication, AdjudicationStatus, Conflict, Model, Response, Task


class AdjudicationEngine:
    """Uses a dedicated model to resolve conflicts conservatively."""

    async def adjudicate(
        self,
        engine,
        task: Task,
        conflict: Conflict,
        model_id: str,
        *,
        event_sink=None,
    ) -> Adjudication:
        model: Model = engine.models[model_id]
        prompt = (
            "You are Rock's adjudication agent. Resolve the conflict below using only "
            "the supplied claims and sources. Do not decide by majority. If the evidence "
            "is insufficient, return INCONCLUSIVE. If the conflict requires external "
            "evidence unavailable here, return ESCALATE. Return exactly one status on "
            "the first line: RESOLVED, INCONCLUSIVE, or ESCALATE. Then provide a decision, "
            "brief rationale, supporting sources, rejected sources, and confidence from "
            "0 to 1.\n\n"
            f"TASK:\n{task.prompt}\n\n"
            f"CONFLICT ID: {conflict.id}\n"
            f"TOPIC: {conflict.topic}\n"
            f"SOURCES: {', '.join(conflict.sources)}\n\n"
            "CLAIMS:\n"
            + "\n\n".join(f"- {claim}" for claim in conflict.claims)
        )
        response = await engine.debate_turn(
            task,
            model_id,
            prompt,
            event_sink=event_sink,
            event_name="Adjudicator",
        )
        return self.parse(conflict, response)

    @staticmethod
    def parse(conflict: Conflict, response: Response) -> Adjudication:
        lines = [line.strip() for line in response.content.splitlines() if line.strip()]
        status_line = lines[0].upper() if lines else ""
        if status_line.startswith("RESOLVED"):
            status = AdjudicationStatus.RESOLVED
        elif status_line.startswith("ESCALATE"):
            status = AdjudicationStatus.ESCALATE
        else:
            status = AdjudicationStatus.INCONCLUSIVE

        body = "\n".join(lines[1:]) if len(lines) > 1 else response.content.strip()
        confidence = 0.0
        for line in lines:
            if "confidence" in line.lower():
                try:
                    confidence = float(line.split(":")[-1].strip().rstrip("%")) / (
                        100 if "%" in line else 1
                    )
                except ValueError:
                    pass
                break

        return Adjudication(
            conflict_id=conflict.id,
            status=status,
            decision=body or "No adjudication decision was returned.",
            rationale=body,
            supporting_sources=[],
            rejected_sources=[],
            confidence=max(0.0, min(1.0, confidence)),
        )
