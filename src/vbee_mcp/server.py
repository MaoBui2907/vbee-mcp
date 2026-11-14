"""MCP stdio server entrypoint. Starts without credentials; tools check env at call time."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import tools

mcp = FastMCP(
    "vbee-mcp",
    instructions=(
        "Unofficial MCP server for vbee.vn. Requires VBEE_APP_ID and VBEE_TOKEN "
        "in the environment before any tool will work. TTS text limits: 300 chars "
        "(realtime) / 100,000 chars (batch). STT accepts WAV only."
    ),
)

tools.register(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
