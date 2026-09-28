from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from rock.core.contracts import Permission, PermissionDecision, Policy, Tool


class PermissionEngine:
    """Central permission evaluator for side-effecting operations."""

    SAFE_READ_ACTIONS: ClassVar[set[str]] = {"read", "list", "inspect", "status"}
    WRITE_ACTIONS: ClassVar[set[str]] = {"write", "edit", "delete", "execute", "network"}

    def decide(self, permission: Permission, *, interactive: bool = False) -> PermissionDecision:
        if permission.decision == PermissionDecision.DENY:
            return PermissionDecision.DENY
        if permission.decision == PermissionDecision.ALLOW:
            return PermissionDecision.ALLOW
        if interactive:
            answer = input(
                f"Rock permission required: {permission.action} on {permission.resource}. "
                "Allow? [y/N] "
            ).strip().lower()
            return PermissionDecision.ALLOW if answer in {"y", "yes"} else PermissionDecision.DENY
        return PermissionDecision.ASK

    def classify_path(self, path: str | Path, action: str) -> Permission:
        resolved = Path(path).expanduser().resolve()
        if action in self.SAFE_READ_ACTIONS:
            return Permission(resource=str(resolved), action=action, decision=PermissionDecision.ALLOW)
        return Permission(
            resource=str(resolved),
            action=action,
            decision=PermissionDecision.ASK,
            reason="Side-effecting filesystem action requires explicit approval.",
        )


class PolicyEngine:
    """Apply task policy and tool permissions before a tool handler runs."""

    def __init__(self, policy: Policy, permission_engine: PermissionEngine | None = None) -> None:
        self.policy = policy
        self.permission_engine = permission_engine or PermissionEngine()

    def decide(self, tool: Tool, action: str, *, interactive: bool = False) -> PermissionDecision:
        if not self.policy.allow_tools:
            return PermissionDecision.DENY

        matches = [
            permission
            for permission in tool.permissions
            if permission.action in {action, "*"}
        ]
        if not matches:
            return PermissionDecision.ASK if interactive else PermissionDecision.DENY

        return self.permission_engine.decide(matches[0], interactive=interactive)
