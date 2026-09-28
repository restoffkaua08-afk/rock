import pytest

from rock.core.contracts import Permission, PermissionDecision, Policy, Tool
from rock.core.policy import PolicyEngine
from rock.core.tools import ToolCall, ToolExecutionEngine


@pytest.mark.asyncio
async def test_tool_execution_requires_explicit_permission() -> None:
    tool = Tool(
        id="demo:write",
        name="write",
        permissions=[
            Permission(
                resource="demo",
                action="write",
                decision=PermissionDecision.ALLOW,
            )
        ],
    )
    engine = ToolExecutionEngine(PolicyEngine(Policy()))
    called = False

    async def handler(data: dict) -> dict:
        nonlocal called
        called = True
        return {"ok": True, "value": data["value"]}

    engine.register(tool, handler)
    result = await engine.execute(
        tool,
        ToolCall("demo:write", "write", {"value": 7}),
        task_id="task-1",
        actor="agent-1",
        timeout=1,
    )

    assert result.status.value == "success"
    assert called
    assert result.output["value"] == 7


@pytest.mark.asyncio
async def test_tool_execution_denies_without_permission() -> None:
    tool = Tool(id="demo:read", name="read")
    engine = ToolExecutionEngine(PolicyEngine(Policy()))

    async def handler(_: dict) -> dict:
        raise AssertionError("handler must not run")

    engine.register(tool, handler)
    result = await engine.execute(
        tool,
        ToolCall("demo:read", "read", {}),
        task_id="task-2",
        actor="agent-1",
        timeout=1,
    )

    assert result.status.value == "denied"
    assert "permission" in (result.error or "")


@pytest.mark.asyncio
async def test_tool_execution_enforces_call_budget() -> None:
    tool = Tool(
        id="demo:read",
        name="read",
        permissions=[Permission(resource="demo", action="read", decision=PermissionDecision.ALLOW)],
    )
    engine = ToolExecutionEngine(PolicyEngine(Policy()), max_calls=1)

    async def handler(_: dict) -> dict:
        return {"ok": True}

    engine.register(tool, handler)
    first = await engine.execute(
        tool, ToolCall("demo:read", "read", {}), task_id="task-3", actor="a", timeout=1
    )
    second = await engine.execute(
        tool, ToolCall("demo:read", "read", {}), task_id="task-3", actor="a", timeout=1
    )

    assert first.status.value == "success"
    assert second.status.value == "denied"
    assert "maximum tool calls" in (second.error or "")
