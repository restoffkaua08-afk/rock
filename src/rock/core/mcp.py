from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from rock.core.contracts import Tool


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for an MCP server discovery target."""

    id: str
    transport: str
    url: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    env: dict[str, str] | None = None


class MCPError(RuntimeError):
    pass


class MCPToolRegistry:
    """Discover MCP tools without executing them.

    V0.5 only performs protocol initialization and tool discovery. Calling a
    discovered tool is intentionally deferred to the V0.6 policy-controlled
    tool engine.
    """

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}

    async def discover(self, server: MCPServerConfig) -> list[Tool]:
        if server.transport == "streamable-http":
            if not server.url:
                raise MCPError(f"MCP server {server.id} has no URL")
            async with streamablehttp_client(server.url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await self._discover_session(server, session)

        if server.transport == "stdio":
            if not server.command:
                raise MCPError(f"MCP server {server.id} has no command")
            params = StdioServerParameters(
                command=server.command,
                args=list(server.args),
                env=server.env,
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await self._discover_session(server, session)

        raise MCPError(f"Unsupported MCP transport: {server.transport}")

    async def _discover_session(
        self,
        server: MCPServerConfig,
        session: ClientSession,
    ) -> list[Tool]:
        discovered: list[Tool] = []
        cursor: str | None = None
        while True:
            page = await session.list_tools(cursor=cursor)
            for item in page.tools:
                tool_id = f"mcp:{server.id}:{item.name}"
                tool = Tool(
                    id=tool_id,
                    name=item.name,
                    description=item.description or "",
                    input_schema=dict(item.inputSchema or {}),
                    metadata={
                        "mcp_server": server.id,
                        "transport": server.transport,
                        "title": getattr(item, "title", None),
                    },
                )
                self.tools[tool_id] = tool
                discovered.append(tool)
            if page.next_cursor is None:
                return discovered
            cursor = page.next_cursor

    def get(self, tool_id: str) -> Tool | None:
        return self.tools.get(tool_id)

    def all(self) -> list[Tool]:
        return list(self.tools.values())
