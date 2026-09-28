# Policy and Tool Execution

V0.6 introduces the execution boundary for Rock tools.

## Decision flow

Agent / Workflow -> ToolCall -> PolicyEngine -> ALLOW/DENY -> ToolExecutionEngine -> handler -> result

A tool discovered through MCP is not implicitly trusted. It must have an explicit matching permission, unless an interactive policy deliberately routes the request through an approval handler.

## Limits

The execution engine enforces a maximum number of tool calls per engine instance and a timeout for each invocation.

## MCP

MCP discovery creates Rock Tool objects. V0.6 adds handlers capable of invoking discovered MCP tools, but invocation remains gated by PolicyEngine.

The policy layer is the mandatory boundary between model intent and external side effects.
