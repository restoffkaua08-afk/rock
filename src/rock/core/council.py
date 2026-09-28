from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from rock.core.contracts import Model, Response, Task, Verification
from rock.core.providers import Provider


class CouncilEngine:
    def __init__(self, providers: dict[str, Provider], models: dict[str, Model]) -> None:
        self.providers = providers
        self.models = models

    async def collect(self, task: Task, model_ids: list[str]) -> list[Response]:
        semaphore = asyncio.Semaphore(task.policy.budget.max_parallel)

        async def one(model_id: str) -> Response:
            model = self.models[model_id]
            provider = self.providers[model.provider]
            started = time.perf_counter()
            async with semaphore:
                try:
                    response = await asyncio.wait_for(
                        provider.generate(task.prompt, model, timeout=task.policy.timeout_seconds),
                        timeout=task.policy.timeout_seconds,
                    )
                    response.latency_ms = (time.perf_counter() - started) * 1000
                    return response
                except asyncio.TimeoutError:
                    return Response(
                        provider=model.provider,
                        model=model.model_name,
                        content="",
                        error="timeout",
                        latency_ms=(time.perf_counter() - started) * 1000,
                    )
                except Exception as exc:
                    return Response(
                        provider=model.provider,
                        model=model.model_name,
                        content="",
                        error=str(exc),
                        latency_ms=(time.perf_counter() - started) * 1000,
                    )

        return await asyncio.gather(*(one(model_id) for model_id in model_ids))

    @staticmethod
    def normalize(responses: list[Response]) -> list[Response]:
        return [response for response in responses if response.content.strip()]

    @staticmethod
    def critique(responses: list[Response]) -> str:
        if not responses:
            return "No successful model responses were available for critique."
        providers = ", ".join(r.provider for r in responses)
        return (
            f"Critique stage received {len(responses)} independent responses "
            f"from: {providers}. Agreement is not treated as proof of correctness."
        )

    @staticmethod
    def synthesize(task: Task, responses: list[Response], critique: str) -> str:
        if not responses:
            return "Rock could not produce a synthesis because all providers failed."
        joined = "\n\n".join(
            f"[{r.provider}/{r.model}]\n{r.content}" for r in responses
        )
        return (
            f"Rock synthesis for: {task.prompt}\n\n"
            f"{joined}\n\n"
            f"Council critique: {critique}"
        )

    @staticmethod
    def verify(synthesis: str, responses: list[Response]) -> Verification:
        passed = bool(synthesis.strip()) and bool(responses)
        findings = [] if passed else ["Synthesis is empty or has no supporting responses."]
        return Verification(
            target="synthesis",
            verifier="rock-v0.1-verifier",
            checks=["non_empty_synthesis", "supporting_responses"],
            passed=passed,
            findings=findings,
            confidence=0.5 if passed else 0.0,
        )

    async def run(self, task: Task, model_ids: list[str]) -> tuple[str, Verification, list[Response]]:
        responses = await self.collect(task, model_ids)
        usable = self.normalize(responses)
        critique = self.critique(usable)
        synthesis = self.synthesize(task, usable, critique)
        verification = self.verify(synthesis, usable)
        return synthesis, verification, responses
