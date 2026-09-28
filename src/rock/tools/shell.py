from __future__ import annotations

import asyncio
import os
from pathlib import Path

from rock.core.contracts import Execution, ExecutionStatus, PermissionDecision
from rock.core.policy import PermissionEngine


class ShellTool:
    """Controlled PowerShell/CMD execution. Never bypasses Rock's permission gate."""

    def __init__(self, permission_engine: PermissionEngine | None = None) -> None:
        self.permissions = permission_engine or PermissionEngine()

    async def run(self, command: str, *, task_id: str, interactive: bool = True) -> Execution:
        permission = self.permissions.classify_path(Path.cwd(), "execute")
        decision = self.permissions.decide(permission, interactive=interactive)
        execution = Execution(
            id=f"shell-{task_id}",
            task_id=task_id,
            actor="rock-shell",
            action=command,
            status=ExecutionStatus.PENDING,
        )
        if decision != PermissionDecision.ALLOW:
            execution.status = ExecutionStatus.DENIED
            execution.error = "Shell execution denied by policy."
            return execution

        execution.status = ExecutionStatus.RUNNING
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )
            stdout, stderr = await process.communicate()
            execution.status = (
                ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED
            )
            execution.output = {
                "returncode": process.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }
            return execution
        except OSError as exc:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(exc)
            return execution
