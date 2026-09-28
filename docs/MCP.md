# MCP in Rock

V0.5 adds MCP tool discovery without tool execution.

## Boundary

Rock can initialize a configured MCP server and discover its tool definitions and JSON schemas. The discovered definitions are normalized into Rock's `Tool` contract.

V0.5 does **not** call MCP tools. Tool execution belongs to V0.6, where every call will pass through Rock's policy/permission layer.

## Transports

Supported discovery targets:

- `stdio`: local MCP server command plus arguments.
- `streamable-http`: MCP endpoint URL.

The Python MCP SDK is used only as the protocol adapter.

## Internal flow

```text
MCP Server
   |
   v
MCPToolRegistry
   |
   v
initialize -> list_tools (with pagination)
   |
   v
Rock Tool contracts
   |
   v
Policy-controlled execution (V0.6)
```

Tool IDs are namespaced as `mcp:<server-id>:<tool-name>` so different MCP servers can expose the same tool name without silently colliding.
