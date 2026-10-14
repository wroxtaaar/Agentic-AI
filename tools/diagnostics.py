"""Authenticated, bounded, read-only VPS diagnostics for private API access.

These endpoints intentionally expose no shell, Docker mutation, arbitrary URL,
filesystem path, or arbitrary container selection.
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from tools.safety import redact

DEFAULT_CONTAINERS = ("home", "docker-control-bot", "agentic-ai", "agentic-monitor")
CONTAINERS = {
    item.strip()
    for item in os.getenv("DIAGNOSTICS_CONTAINERS", ",".join(DEFAULT_CONTAINERS)).split(",")
    if item.strip()
}
MAX_LOG_LINES = max(20, min(200, int(os.getenv("DIAGNOSTICS_MAX_LOG_LINES", "100"))))
MAX_LOG_CHARS = 12000
_CONTAINER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def _run_docker(args: list[str], timeout: int = 12) -> dict[str, Any]:
    """Run only internally-constructed Docker read commands; never a user command."""
    try:
        result = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "output": redact(result.stdout.strip() or result.stderr.strip(), MAX_LOG_CHARS),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "output": redact(str(exc), 1000)}


def _validate_container(name: str) -> str:
    if not _CONTAINER_RE.fullmatch(name) or name not in CONTAINERS:
        raise ValueError("Container is not in the diagnostics allowlist")
    return name


def list_diagnostics_containers() -> dict[str, Any]:
    """Return status/health/restart count for configured containers only."""
    results = []
    for name in sorted(CONTAINERS):
        result = _run_docker([
            "inspect", "--format",
            "{{.Name}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.RestartCount}}",
            name,
        ])
        if not result["success"]:
            results.append({"name": name, "available": False, "error": result["output"]})
            continue
        fields = result["output"].lstrip("/").split("|")
        if len(fields) != 4:
            results.append({"name": name, "available": False, "error": "Unexpected inspect response"})
            continue
        results.append({
            "name": name,
            "available": True,
            "status": fields[1],
            "health": fields[2],
            "restart_count": int(fields[3]) if fields[3].isdigit() else None,
        })
    return {"read_only": True, "containers": results}


def container_diagnostics(name: str) -> dict[str, Any]:
    name = _validate_container(name)
    inspect = _run_docker([
        "inspect", "--format",
        "{{.Name}}|{{.Config.Image}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.State.StartedAt}}|{{.RestartCount}}",
        name,
    ])
    stats = _run_docker([
        "stats", "--no-stream", "--format",
        "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}", name,
    ])
    if not inspect["success"]:
        return {"read_only": True, "name": name, "available": False, "error": inspect["output"]}
    fields = inspect["output"].lstrip("/").split("|")
    result: dict[str, Any] = {"read_only": True, "name": name, "available": True}
    if len(fields) == 6:
        result.update({
            "image": fields[1],
            "status": fields[2],
            "health": fields[3],
            "started_at": fields[4],
            "restart_count": int(fields[5]) if fields[5].isdigit() else None,
        })
    if stats["success"]:
        values = stats["output"].split("|")
        if len(values) == 3:
            result["resources"] = {
                "cpu_percent": values[0],
                "memory_usage": values[1],
                "memory_percent": values[2],
            }
    return result


def container_logs(name: str, lines: int = 100) -> dict[str, Any]:
    name = _validate_container(name)
    bounded_lines = max(1, min(int(lines), MAX_LOG_LINES))
    result = _run_docker([
        "logs", "--timestamps", "--tail", str(bounded_lines), name,
    ], timeout=15)
    return {
        "read_only": True,
        "name": name,
        "lines_requested": bounded_lines,
        "success": result["success"],
        "logs": redact(result["output"], MAX_LOG_CHARS),
    }
