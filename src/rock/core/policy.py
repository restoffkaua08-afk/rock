from __future__ import annotations

from pathlib import Path

from rock.core.contracts import Permission, PermissionDecision


class PermissionEngine:
    """Central policy gate for all future tool/agent side effects."""

    SAFE_READ_ACTIONS = {"read", "list", "inspect", "status"}
    WRITE_ACTIONS = {"write", "edit", "delete", "execute", "network"}

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
