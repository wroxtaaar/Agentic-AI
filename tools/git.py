import os
import subprocess
from pathlib import Path

from .safety import redact

IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}


def _is_git_repo(path):
    return path.is_dir() and (path / ".git").exists()


def _workspace_roots():
    configured = os.getenv("AGENT_WORKSPACE_ROOTS", "/home/ubuntu")
    return [Path(item).expanduser().resolve() for item in configured.split(":") if item.strip()]


def _default_repo():
    # An explicit deployment setting takes precedence.
    configured = os.getenv("AGENT_DEFAULT_PROJECT") or os.getenv("AGENT_PROJECT_PATH")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if _is_git_repo(candidate):
            return candidate
        return None, f"Configured default project is not a Git repository: {candidate}"

    # Support local development when the process is already inside a checkout.
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if _is_git_repo(candidate):
            return candidate

    # In containers, the checkout is often mounted under a workspace root while
    # the process itself runs from /app. Prefer this project's conventional name.
    found = []
    for root in _workspace_roots():
        if _is_git_repo(root):
            found.append(root)
            continue
        if not root.is_dir():
            continue
        try:
            for current, dirs, _ in os.walk(root):
                current_path = Path(current)
                depth = len(current_path.relative_to(root).parts)
                dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS) if depth < 4 else []
                if current_path != root and _is_git_repo(current_path):
                    found.append(current_path.resolve())
                    dirs[:] = []
        except OSError:
            continue

    unique = sorted(set(found), key=lambda item: str(item))
    named = [item for item in unique if item.name.lower() == "agentic-ai"]
    if len(named) == 1:
        return named[0]
    if len(unique) == 1:
        return unique[0]
    if not unique:
        return None, "No Git repository found in the current directory or AGENT_WORKSPACE_ROOTS."
    return None, "Multiple Git repositories found; pass an explicit repository path or set AGENT_DEFAULT_PROJECT."


def _resolve_repo(path=None):
    if path is None or str(path).strip() in {"", ".", "./"}:
        result = _default_repo()
        if isinstance(result, tuple):
            return result
        return result, None

    candidate = Path(path).expanduser().resolve()
    if not candidate.exists():
        return None, f"Path does not exist: {candidate}"
    # Allow a file path within a repository as well as the repository directory.
    if candidate.is_file():
        candidate = candidate.parent
    for parent in (candidate, *candidate.parents):
        if _is_git_repo(parent):
            return parent, None
    return None, f"Path is not inside a Git repository: {candidate}"


def _run(args, path=None):
    repository, error = _resolve_repo(path)
    if error:
        return {"success": False, "error": error}
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *args],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return {
            "success": result.returncode == 0,
            "repository": str(repository),
            "stdout": redact(result.stdout),
            "stderr": redact(result.stderr, 5000),
            "return_code": result.returncode,
        }
    except Exception as exc:
        return {"success": False, "repository": str(repository), "error": str(exc)}


def status(path=None):
    return _run(["status", "--short", "--branch"], path)


def branch(path=None):
    return _run(["branch", "--show-current"], path)


def log(path=None, count=10):
    return _run(["log", f"-{max(1, min(int(count), 50))}", "--oneline", "--decorate"], path)


def diff(path=None):
    return _run(["diff", "--stat", "--", "."], path)
