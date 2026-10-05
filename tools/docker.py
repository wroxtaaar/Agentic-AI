import subprocess
import time
from .safety import redact
from core.approvals import create

def _run(args, timeout=20):
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
        return {"success": r.returncode == 0, "stdout": redact(r.stdout), "stderr": redact(r.stderr, 5000), "return_code": r.returncode}
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_containers():
    return _run(["ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"])

def logs(container, lines=100):
    return _run(["logs", "--tail", str(max(1, min(int(lines), 500))), container])

def inspect(container):
    return _run(["inspect", "--format", "Name={{.Name}}\nImage={{.Config.Image}}\nStatus={{.State.Status}}\nHealth={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}\nStartedAt={{.State.StartedAt}}\nRestartCount={{.RestartCount}}", container])

def stats(container):
    return _run(["stats", "--no-stream", "--format", "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}", container])

def _action(action, container):
    container = container.strip()
    if not container or any(c in container for c in " ;|&$"):
        return {"success": False, "error": "Invalid container name"}
    if action not in {"restart", "start", "stop"}:
        return {"success": False, "error": "Unsupported Docker action"}
    descriptions = {"restart": f"Restart Docker container {container}", "start": f"Start Docker container {container}", "stop": f"Stop Docker container {container}"}
    return create(f"docker_{action}", descriptions[action], {"action": action, "container": container})

def propose_restart(container):
    return _action("restart", container)

def propose_start(container):
    return _action("start", container)

def propose_stop(container):
    return _action("stop", container)

def verify_container(container):
    container = container.strip()
    if not container or any(c in container for c in " ;|&$"):
        return {"success": False, "error": "Invalid container name"}

    result = _run([
        "inspect", "--format",
        "Status={{.State.Status}}\nHealth={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}\nRestartCount={{.RestartCount}}",
        container,
    ])

    if not result.get("success"):
        return result

    values = {}
    for line in result.get("stdout", "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip()

    status = values.get("Status", "")
    health = values.get("Health", "none")
    running = status == "running"

    # A container without a Docker HEALTHCHECK is still valid when running.
    healthy = health in {"none", "healthy"}
    if not running or not healthy:
        return {
            "success": False,
            "status": status,
            "health": health,
            "restart_count": values.get("RestartCount"),
            "error": "Container is not running/healthy after the approved action",
        }

    return {
        "success": True,
        "status": status,
        "health": health,
        "restart_count": values.get("RestartCount"),
        "verified": True,
    }

def execute_action(action, container):
    if action == "verify":
        return verify_container(container)
    if action not in {"restart", "start", "stop"}:
        return {"success": False, "error": "Unsupported Docker action"}
    return _run([action, container], 30)
