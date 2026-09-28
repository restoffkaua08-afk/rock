from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from rock.core.contracts import Execution, ExecutionStatus, Verification


@dataclass(frozen=True)
class VerificationAttempt:
    attempt: int
    verification: Verification
    execution: Execution | None = None


Verifier = Callable[[Any], Awaitable[Verification]]
Corrector = Callable[[Any, Verification, int], Awaitable[Any]]


class VerificationLoop:
    """Bounded verify/correct loop for tool and workflow results."""

    def __init__(self, *, max_attempts: int = 3) -> None:
        self.max_attempts = max(1, min(max_attempts, 3))

    async def run(
        self,
        artifact: Any,
        *,
        verify: Verifier,
        correct: Corrector,
    ) -> tuple[Any, Verification, list[VerificationAttempt]]:
        attempts: list[VerificationAttempt] = []
        current = artifact

        for number in range(1, self.max_attempts + 1):
            result = await verify(current)
            execution = current if isinstance(current, Execution) else None
            attempts.append(
                VerificationAttempt(
                    attempt=number,
                    verification=result,
                    execution=execution,
                )
            )
            if result.passed:
                return current, result, attempts

            if number == self.max_attempts:
                return current, result, attempts

            current = await correct(current, result, number)

        raise RuntimeError("verification loop terminated unexpectedly")


def execution_verification(execution: Execution) -> Verification:
    passed = execution.status == ExecutionStatus.SUCCESS and not execution.error
    findings = [] if passed else [execution.error or f"execution status: {execution.status.value}"]
    return Verification(
        target=execution.id,
        verifier="rock:execution",
        checks=["execution_status", "execution_error"],
        passed=passed,
        findings=findings,
        confidence=1.0 if passed else 0.0,
    )
