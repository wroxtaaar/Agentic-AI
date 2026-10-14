"""Private, read-only MCP bridge for the VPS diagnostics API.

This service is intended to be reachable only on the Docker Compose network.
Use OpenAI Secure MCP Tunnel for ChatGPT access; do not publish port 8788.
"""
import os

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

AGENT_BASE_URL = os.getenv("DIAGNOSTICS_AGENT_URL", "http://agent:8787").rstrip("/")
AGENT_API_TOKEN = os.environ["AGENT_API_TOKEN"]
ALLOWED_CONTAINERS = frozenset(
    name.strip()
    for name in os.getenv(
        "DIAGNOSTICS_MCP_CONTAINERS",
        "home,docker-control-bot,agentic-ai,agentic-monitor",
    ).split(",")
    if name.strip()
)

mcp = FastMCP("Oracle VPS Read-only Diagnostics")
mcp.settings.host = "0.0.0.0"
mcp.settings.port = int(os.getenv("DIAGNOSTICS_MCP_PORT", "8788"))
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


async def _get(path: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {AGENT_API_TOKEN}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{AGENT_BASE_URL}{path}", headers=headers, params=params
        )
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Diagnostics API returned an unexpected response")
    return data


@mcp.tool(annotations=READ_ONLY)
async def list_containers() -> dict:
    """List status, health, and restart counts for the fixed VPS diagnostics allowlist."""
    return await _get("/api/diagnostics/containers")


@mcp.tool(annotations=READ_ONLY)
async def get_container_details(name: str) -> dict:
    """Get health, image, restart count, and CPU/memory snapshot for an allowlisted container."""
    if name not in ALLOWED_CONTAINERS:
        raise ValueError("Container is not in the MCP diagnostics allowlist")
    return await _get(f"/api/diagnostics/containers/{name}")


@mcp.tool(annotations=READ_ONLY)
async def get_container_logs(name: str, lines: int = 80) -> dict:
    """Read recent redacted logs; requests are bounded to 1–200 lines by this bridge."""
    if name not in ALLOWED_CONTAINERS:
        raise ValueError("Container is not in the MCP diagnostics allowlist")
    bounded_lines = max(1, min(int(lines), 200))
    return await _get(
        f"/api/diagnostics/containers/{name}/logs",
        params={"lines": bounded_lines},
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
