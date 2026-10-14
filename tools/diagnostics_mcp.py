"""Private, read-only MCP bridge for the VPS diagnostics API.

Intended to be reachable only through OpenAI Secure MCP Tunnel. It exposes
fixed diagnostics tools and does not provide arbitrary commands or mutations.
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


def _validate_container(name: str) -> None:
    if name not in ALLOWED_CONTAINERS:
        raise ValueError("Container is not in the MCP diagnostics allowlist")


@mcp.tool(annotations=READ_ONLY)
async def list_containers() -> dict:
    """List status, health, and restart counts for the fixed VPS diagnostics allowlist."""
    return await _get("/api/diagnostics/containers")


@mcp.tool(annotations=READ_ONLY)
async def get_container_details(name: str) -> dict:
    """Get health, image, restart count, and CPU/memory snapshot for an allowlisted container."""
    _validate_container(name)
    return await _get(f"/api/diagnostics/containers/{name}")


@mcp.tool(annotations=READ_ONLY)
async def get_container_logs(name: str, lines: int = 100) -> dict:
    """Read recent redacted logs, bounded to 1–200 lines (API configured for up to 200)."""
    _validate_container(name)
    bounded_lines = max(1, min(int(lines), 200))
    return await _get(
        f"/api/diagnostics/containers/{name}/logs",
        params={"lines": bounded_lines},
    )


@mcp.tool(annotations=READ_ONLY)
async def search_container_logs(
    name: str,
    terms: str = "cache,ott,favourites,classics,poster,watchmode,tmdb,429,error,warn",
    lines: int = 200,
) -> dict:
    """Search recent redacted logs for comma-separated literal terms; never runs commands.

    Reads at most 200 recent log lines from an allowlisted container, then filters
    them locally. Terms are literal case-insensitive substrings, not regex patterns.
    """
    _validate_container(name)
    bounded_lines = max(1, min(int(lines), 200))
    parsed_terms = [term.strip().casefold() for term in terms.split(",") if term.strip()]
    if not parsed_terms:
        raise ValueError("Provide at least one comma-separated search term")
    if len(parsed_terms) > 12 or any(len(term) > 64 for term in parsed_terms):
        raise ValueError("Use at most 12 terms, each no longer than 64 characters")
    result = await _get(
        f"/api/diagnostics/containers/{name}/logs",
        params={"lines": bounded_lines},
    )
    raw_logs = str(result.get("logs", ""))
    matches = [
        line for line in raw_logs.splitlines()
        if any(term in line.casefold() for term in parsed_terms)
    ]
    return {
        "read_only": True,
        "name": name,
        "lines_requested": bounded_lines,
        "terms": parsed_terms,
        "matched_lines": len(matches),
        "logs": "\n".join(matches)[-12000:],
        "source_lines_scanned": len(raw_logs.splitlines()),
        "note": "Search covers only the recent bounded log tail returned by the diagnostics API.",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
