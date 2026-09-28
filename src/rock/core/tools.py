from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from rock.core.contracts import Execution, ExecutionStatus, PermissionDecision, Tool
from rock.core.policy import PolicyEngine
from rock.core.verification import VerificationLoop, execution_verification


@dataclass(frozen=True)
class ToolCall:
    tool_id: str
    action: str
    input: dict


ToolHandler = Callable[[dict], Awaitable[dict]]


class ToolExecutionError(RuntimeError):
    pass


class ToolExecutionEngine:
    """Execute registered tools only after policy approval."""

    def __init__(self, policy: PolicyEngine, *, max_calls: int = 20) -> None:
        self.policy = policy
        self.max_calls = max_calls
        self.calls = 0
        self.handlers: dict[str, ToolHandler] = {}

    def register(self, tool: Tool, handler: ToolHandler) -> None:
        self.handlers[tool.id] = handler

    async def execute(
        self,
        tool: Tool,
        call: ToolCall,
        *,
        task_id: str,
        actor: str,
        timeout: float,
        interactive: bool = False,
    ) -> Execution:
        execution = Execution(
            id=f"{task_id}:tool:{self.calls + 1}",
            task_id=task_id,
            actor=actor,
            action=call.action,
            input=call.input,
            status=ExecutionStatus.RUNNING,
        )

        if call.tool_id != tool.id:
            return self._deny(execution, "tool id mismatch")

        if self.calls >= self.max_calls:
            return self._deny(execution, "maximum tool calls exceeded")

        decision = self.policy.decide(tool, call.action, interactive=interactive)
        if decision != PermissionDecision.ALLOW:
            return self._deny(execution, f"permission decision: {decision}")

        handler = self.handlers.get(tool.id)
        if handler is None:
            return self._deny(execution, "tool handler is not registered")

        self.calls += 1
        try:
            output = await asyncio.wait_for(handler(call.input), timeout=timeout)
        except asyncio.TimeoutError:
            execution.status = ExecutionStatus.TIMEOUT
            execution.error = "tool execution timed out"
            return execution
        except Exception as exc:  # noqa: BLE001
            execution.status = ExecutionStatus.FAILED
            execution.error = str(exc)
            return execution

        execution.status = ExecutionStatus.SUCCESS
        execution.output = output

        if not execution.error:
            verified, verification, attempts = await VerificationLoop(
                max_attempts=1
            ).run(
                execution,
                verify=self._verify_execution,
                correct=self._no_correction,
            )
            execution.metadata = {
                "verification_passed": verification.passed,
                "verification_attempts": len(attempts),
            }
            if not verification.passed:
                execution.status = ExecutionStatus.FAILED
                execution.error = "tool result failed verification"
            else:
                execution.output = verified.output
        return execution

    @staticmethod
    async def _verify_execution(execution: Execution):
        return execution_verification(execution)

    @staticmethod
    async def _no_correction(execution, _verification, _attempt):
        return execution

    @staticmethod
    def _deny(execution: Execution, reason: str) -> Execution:
        execution.status = ExecutionStatus.DENIED
        execution.error = reason
        return execution
