from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from rock.core.contracts import Model, Response, Task, Verification
from rock.core.providers import Provider


EventSink = Callable[[str, str, str, str, str | None], None]


class CouncilEngine:
    def __init__(self, providers: dict[str, Provider], models: dict[str, Model]) -> None:
        self.providers = providers
        self.models = models

    @staticmethod
    def _emit(
        event_sink: EventSink | None,
        kind: str,
        name: str,
        status: str,
        detail: str,
        error: str | None = None,
    ) -> None:
        if event_sink:
            event_sink(kind, name, status, detail, error)

    async def _call(
        self,
        provider: Provider,
        model: Model,
        prompt: str,
        task: Task,
        *,
        event_sink: EventSink | None = None,
        event_kind: str = "model",
        event_name: str | None = None,
    ) -> Response:
        name = event_name or model.model_name
        last: Response | None = None
        total_attempts = task.policy.max_retries + 1
        self._emit(event_sink, event_kind, name, "running", f"tentativa 1/{total_attempts}")

        for attempt in range(total_attempts):
            try:
                response = await asyncio.wait_for(
                    provider.generate(prompt, model, timeout=task.policy.timeout_seconds),
                    timeout=task.policy.timeout_seconds,
                )
                if response.error:
                    last = response
                else:
                    self._emit(event_sink, event_kind, name, "success", "concluído")
                    return response
            except TimeoutError:
                last = Response(
                    provider=model.provider,
                    model=model.model_name,
                    content="",
                    error="timeout",
                )
            except Exception as exc:  # noqa: BLE001
                last = Response(
                    provider=model.provider,
                    model=model.model_name,
                    content="",
                    error=str(exc),
                )

            if attempt < task.policy.max_retries:
                next_attempt = attempt + 2
                self._emit(
                    event_sink,
                    event_kind,
                    name,
                    "running",
                    f"tentativa {next_attempt}/{total_attempts}",
                    last.error if last else None,
                )
                await asyncio.sleep(min(2**attempt, 4))

        failure_status = "timeout" if last and last.error == "timeout" else "failed"
        self._emit(
            event_sink,
            event_kind,
            name,
            failure_status,
            last.error if last else "falha desconhecida",
            last.error if last else None,
        )
        return last or Response(
            provider=model.provider,
            model=model.model_name,
            content="",
            error="unknown failure",
        )

    async def collect(
        self,
        task: Task,
        model_ids: list[str],
        *,
        event_sink: EventSink | None = None,
    ) -> list[Response]:
        semaphore = asyncio.Semaphore(max(1, task.policy.budget.max_parallel))

        async def one(model_id: str) -> Response:
            model = self.models[model_id]
            provider = self.providers[model.provider]
            started = time.perf_counter()
            response = await self._call(
                provider,
                model,
                task.prompt,
                task,
                event_sink=event_sink,
                event_kind="model",
                event_name=model.model_name,
            )
            response.latency_ms = (time.perf_counter() - started) * 1000
            return response

        async def limited(model_id: str) -> Response:
            async with semaphore:
                return await one(model_id)

        return await asyncio.gather(*(limited(model_id) for model_id in model_ids))

    @staticmethod
    def normalize(responses: list[Response]) -> list[Response]:
        return [r for r in responses if r.content.strip() and not r.error]

    async def critique(
        self,
        task: Task,
        responses: list[Response],
        model_id: str,
        *,
        event_sink: EventSink | None = None,
    ) -> Response:
        if not responses:
            return Response(
                provider="rock",
                model="critic",
                content="",
                error="no responses to critique",
            )
        model = self.models[model_id]
        provider = self.providers[model.provider]
        material = "\n\n".join(f"[{r.provider}/{r.model}]\n{r.content}" for r in responses)
        prompt = (
            "You are Rock's critical reviewer. Analyze the independent answers below. "
            "Identify agreements, contradictions, unsupported claims, missing evidence and "
            "specific corrections. Do not choose an answer merely because it is popular. "
            "Return a concise review with actionable findings.\n\n"
            f"USER TASK:\n{task.prompt}\n\nANSWERS:\n{material}"
        )
        return await self._call(
            provider,
            model,
            prompt,
            task,
            event_sink=event_sink,
            event_kind="stage",
            event_name="Critic",
        )

    async def synthesize(
        self,
        task: Task,
        responses: list[Response],
        critique: Response,
        model_id: str,
        *,
        event_sink: EventSink | None = None,
    ) -> Response:
        model = self.models[model_id]
        provider = self.providers[model.provider]
        material = "\n\n".join(f"[{r.provider}/{r.model}]\n{r.content}" for r in responses)
        prompt = (
            "You are Rock's synthesis agent. Produce the final answer to the user's task. "
            "Use the independent answers as evidence, incorporate valid critique findings, "
            "resolve contradictions explicitly, and never claim verification that did not occur. "
            "Answer the user directly and clearly.\n\n"
            f"USER TASK:\n{task.prompt}\n\nANSWERS:\n{material}\n\n"
            f"CRITIQUE:\n{critique.content}"
        )
        return await self._call(
            provider,
            model,
            prompt,
            task,
            event_sink=event_sink,
            event_kind="stage",
            event_name="Synthesizer",
        )

    async def verify(
        self,
        task: Task,
        synthesis: Response,
        responses: list[Response],
        model_id: str,
        *,
        event_sink: EventSink | None = None,
    ) -> Verification:
        model = self.models[model_id]
        provider = self.providers[model.provider]
        prompt = (
            "You are Rock's verification agent. Check the proposed synthesis against the "
            "available independent answers. Look for factual contradictions, unsupported "
            "claims, omissions and internal inconsistency. Return PASS or FAIL first, then "
            "brief findings. Do not invent external evidence.\n\n"
            f"TASK:\n{task.prompt}\n\nSYNTHESIS:\n{synthesis.content}\n\n"
            "SOURCE ANSWERS:\n"
            + "\n\n".join(r.content for r in responses)
        )
        result = await self._call(
            provider,
            model,
            prompt,
            task,
            event_sink=event_sink,
            event_kind="stage",
            event_name="Verifier",
        )
        text = result.content.strip()
        passed = bool(text) and text.upper().startswith("PASS")
        self._emit(
            event_sink,
            "stage",
            "Verifier",
            "success" if passed else "failed",
            "pass" if passed else "revisar achados",
            None if passed else (text or result.error),
        )
        return Verification(
            target="synthesis",
            verifier=f"{model.provider}/{model.model_name}",
            checks=["model_cross_check", "source_consistency", "non_empty_synthesis"],
            passed=passed,
            findings=[text] if text else [result.error or "verification failed"],
            confidence=0.85 if passed else 0.25,
        )

    async def run(
        self,
        task: Task,
        model_ids: list[str],
        *,
        event_sink: EventSink | None = None,
    ) -> tuple[str, Verification, list[Response]]:
        self._emit(event_sink, "stage", "Models", "running", "consultando em paralelo")
        responses = await self.collect(task, model_ids, event_sink=event_sink)
        self._emit(event_sink, "stage", "Models", "success", "respostas recebidas")

        usable = self.normalize(responses)
        if not usable:
            verification = Verification(
                target="synthesis",
                verifier="rock",
                checks=["providers"],
                passed=False,
                findings=["All configured providers failed or returned empty responses."],
                confidence=0.0,
            )
            return (
                "Rock could not produce a synthesis because all providers failed.",
                verification,
                responses,
            )

        usable_providers = {response.provider for response in usable}
        control_model = next(
            model_id
            for model_id in model_ids
            if self.models[model_id].provider in usable_providers
        )
        critique = await self.critique(task, usable, control_model, event_sink=event_sink)
        synthesis = await self.synthesize(
            task,
            usable,
            critique,
            control_model,
            event_sink=event_sink,
        )
        verification = await self.verify(
            task,
            synthesis,
            usable,
            control_model,
            event_sink=event_sink,
        )
        return synthesis.content, verification, responses
