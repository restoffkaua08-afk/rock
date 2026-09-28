from types import SimpleNamespace

import pytest

from rock.core.contracts import Tool
from rock.core.mcp import MCPError, MCPServerConfig, MCPToolRegistry


class FakeSession:
    def __init__(self) -> None:
        self.calls = 0

    async def list_tools(self, cursor=None):
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="read_file",
                        title="Read file",
                        description="Reads a file.",
                        inputSchema={"type": "object", "properties": {"path": {"type": "string"}}},
                    )
                ],
                next_cursor="next",
            )
        return SimpleNamespace(tools=[], next_cursor=None)


@pytest.mark.asyncio
async def test_mcp_registry_normalizes_tool_pages() -> None:
    registry = MCPToolRegistry()
    server = MCPServerConfig(id="demo", transport="stdio", command="demo")

    tools = await registry._discover_session(server, FakeSession())

    assert len(tools) == 1
    assert isinstance(tools[0], Tool)
    assert tools[0].id == "mcp:demo:read_file"
    assert tools[0].input_schema["properties"]["path"]["type"] == "string"
    assert registry.get("mcp:demo:read_file") is tools[0]


@pytest.mark.asyncio
async def test_mcp_registry_rejects_missing_stdio_command() -> None:
    registry = MCPToolRegistry()

    with pytest.raises(MCPError, match="no command"):
        await registry.discover(MCPServerConfig(id="demo", transport="stdio"))


@pytest.mark.asyncio
async def test_mcp_registry_rejects_unknown_transport() -> None:
    registry = MCPToolRegistry()

    with pytest.raises(MCPError, match="Unsupported MCP transport"):
        await registry.discover(MCPServerConfig(id="demo", transport="unknown"))
