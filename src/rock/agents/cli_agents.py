from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass

from rock.core.contracts import Execution, ExecutionStatus


@dataclass(frozen=True)
class ExternalAgent:
    name: str
    executable: str
    args: tuple[str, ...]
    description: str


DEFAULT_AGENTS = (
    ExternalAgent(
        "codex",
        "codex",
        ("exec", "--full-auto", "{prompt}"),
        "OpenAI Codex non-interactive agent",
    ),
    ExternalAgent(
        "claude",
        "claude",
        ("-p", "{prompt}"),
        "Claude Code print-mode agent",
    ),
)


class ExternalAgentRunner:
    def __init__(self, agents: tuple[ExternalAgent, ...] = DEFAULT_AGENTS) -> None:
        self.agents = agents

    def available(self) -> list[ExternalAgent]:
        return [agent for agent in self.agents if shutil.which(agent.executable)]

    async def run(
        self,
        name: str,
        prompt: str,
        *,
        task_id: str,
        cwd: str | None = None,
        timeout: float = 1800,
    ) -> Execution:
        agent = next((a for a in self.agents if a.name == name), None)
        execution = Execution(
            id=f"agent-{task_id}",
            task_id=task_id,
            actor=name,
            action=prompt,
            status=ExecutionStatus.PENDING,
        )
        if agent is None:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Unknown external agent: {name}"
            return execution
        if not shutil.which(agent.executable):
            execution.status = ExecutionStatus.FAILED
            execution.error = f"Agent executable not found: {agent.executable}"
            return execution

        args = [arg.format(prompt=prompt) for arg in agent.args]
        execution.status = ExecutionStatus.RUNNING
        try:
            process = await asyncio.create_subprocess_exec(
                agent.executable,
                *args,
                cwd=cwd or os.getcwd(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            execution.status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED
            execution.output = {
                "returncode": process.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }
            if process.returncode != 0:
                execution.error = f"{name} exited with code {process.returncode}"
            return execution
        except asyncio.TimeoutError:
            process.kill()
            execution.status = ExecutionStatus.TIMEOUT
            execution.error = f"{name} timed out after {timeout}s"
            return execution
        except Exception as exc:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(exc)
            return execution
