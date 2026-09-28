from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from rock.core.contracts import CouncilProtocol, Model, Response, Task, Verification
from rock.core.providers import Provider, ProviderError
from rock.core.protocols import ProtocolContext, get_protocol


EventSink = Callable[[str, str, str, str, str | None], None]

class CostBudget:
    def __init__(self, limit: float | None) -> None:
        self.limit = limit
        self.total = 0.0
        self._lock = asyncio.Lock()

    async def can_spend(self) -> bool:
        async with self._lock:
            return self.limit is None or self.total < self.limit

    async def record(self, amount: float | None) -> None:
        if amount is None or amount < 0:
            return
        async with self._lock:
            self.total += amount



class CouncilEngine:
    def __init__(self, providers: dict[str, Provider], models: dict[str, Model]) -> None:
        self.providers = providers
        self.models = models
        self._cost_budget: CostBudget | None = None

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
        cost_budget: CostBudget | None = None,
    ) -> Response:
        name = event_name or model.model_name
        last: Response | None = None
        total_attempts = task.policy.max_retries + 1
        self._emit(event_sink, event_kind, name, "running", f"tentativa 1/{total_attempts}")

        if cost_budget is not None and not await cost_budget.can_spend():
            return Response(provider=model.provider, model=model.model_name, content="", error="budget_exceeded: cost limit reached")

        for attempt in range(total_attempts):
            try:
                response = await asyncio.wait_for(
                    provider.generate(prompt, model, timeout=task.policy.timeout_seconds),
                    timeout=task.policy.timeout_seconds,
                )
                if response.error:
                    last = response
                else:
                    if cost_budget is not None:
                        await cost_budget.record(response.estimated_cost)
                    self._emit(event_sink, event_kind, name, "success", "concluído")
                    return response
            except TimeoutError:
                last = Response(
                    provider=model.provider,
                    model=model.model_name,
                    content="",
                    error="timeout: provider request timed out",
                )
            except ProviderError as exc:
                last = Response(
                    provider=model.provider,
                    model=model.model_name,
                    content="",
                    error=f"{exc.code}: {exc.message}",
                )
                if exc.code in {"authentication", "model_invalid"}:
                    break
            except Exception as exc:  # noqa: BLE001
                last = Response(
                    provider=model.provider,
                    model=model.model_name,
                    content="",
                    error=f"unavailable: {exc}",
                )

            retryable = last is not None and not last.error.startswith(
                ("authentication:", "model_invalid:")
            )
            if attempt < task.policy.max_retries and retryable:
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
        cost_budget = CostBudget(task.policy.budget.max_cost)
        self._cost_budget = cost_budget

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
                cost_budget=cost_budget,
            )
            response.latency_ms = (time.perf_counter() - started) * 1000
            return response

        async def limited(model_id: str) -> Response:
            async with semaphore:
                return await one(model_id)

        return await asyncio.gather(*(limited(model_id) for model_id in model_ids))

    def _resolve_role_model(
        self,
        requested: str | None,
        fallback: str,
        available_model_ids: list[str],
    ) -> str:
        if requested:
            normalized = requested.strip().lower()
            for model_id in available_model_ids:
                model = self.models[model_id]
                if normalized in {model_id.lower(), model.provider.lower(), model.model_name.lower()}:
                    return model_id
        return fallback

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
            cost_budget=self._cost_budget,
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
            cost_budget=self._cost_budget,
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
            cost_budget=self._cost_budget,
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
        protocol_name = str(task.metadata.get("council_protocol", CouncilProtocol.PARALLEL.value)).lower()
        try:
            protocol = CouncilProtocol(protocol_name)
        except ValueError:
            protocol = CouncilProtocol.PARALLEL

        protocol_runner = None
        rounds = max(1, min(task.policy.budget.max_rounds, 5))
        critic_model = self._resolve_role_model(
            task.metadata.get("council_critic_model"), control_model, model_ids
        )
        synthesizer_model = self._resolve_role_model(
            task.metadata.get("council_synthesizer_model"), control_model, model_ids
        )
        verifier_model = self._resolve_role_model(
            task.metadata.get("council_verifier_model"), control_model, model_ids
        )
        protocol_runner = get_protocol(protocol)
        critique = await protocol_runner.critique_rounds(
            self,
            ProtocolContext(task=task, responses=usable),
            critic_model,
            rounds,
            event_sink=event_sink,
        )
        synthesis = await self.synthesize(
            task,
            usable,
            critique,
            synthesizer_model,
            event_sink=event_sink,
        )
        if synthesis.error:
            verification = Verification(
                target="synthesis",
                verifier=f"{self.models[synthesizer_model].provider}/{self.models[synthesizer_model].model_name}",
                checks=["cost_budget"],
                passed=False,
                findings=[synthesis.error],
                confidence=0.0,
            )
            return (
                "Rock stopped before synthesis because the task budget was exhausted.",
                verification,
                responses,
            )
        verification = await self.verify(
            task,
            synthesis,
            usable,
            verifier_model,
            event_sink=event_sink,
        )
        return synthesis.content, verification, responses
