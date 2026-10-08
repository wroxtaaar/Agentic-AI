import os
import subprocess
from pathlib import Path

from .projects import roots, IGNORE
from .safety import redact, sensitive


def _inside_workspace(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(resolved == root or root in resolved.parents for root in roots())


def _git(root: Path, args):
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return {
            "success": r.returncode == 0,
            "stdout": redact(r.stdout),
            "stderr": redact(r.stderr, 5000),
            "return_code": r.returncode,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _has(root: Path, *names):
    return [name for name in names if (root / name).exists()]


def audit_project(path):
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {"success": False, "error": "Project directory not found"}
    if sensitive(root) or not _inside_workspace(root):
        return {"success": False, "error": "Project is outside the configured workspace"}

    marker_map = {
        "python": ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile"),
        "node": ("package.json",),
        "maven": ("pom.xml",),
        "gradle": ("build.gradle", "build.gradle.kts", "gradlew"),
        "docker": ("docker-compose.yml", "docker-compose.yaml", "Dockerfile"),
    }
    markers = {kind: _has(root, *names) for kind, names in marker_map.items()}
    detected = [kind for kind, files in markers.items() if files]

    result = {
        "success": True,
        "project": str(root),
        "name": root.name,
        "types": detected,
        "markers": markers,
    }

    git_dir = root / ".git"
    if git_dir.exists():
        status = _git(root, ["status", "--short", "--branch"])
        branch = _git(root, ["branch", "--show-current"])
        commits = _git(root, ["log", "-5", "--oneline", "--decorate"])
        result["git"] = {
            "status": status,
            "branch": branch,
            "recent_commits": commits,
            "dirty": bool(status.get("stdout", "").splitlines()[1:]),
        }
    else:
        result["git"] = {"success": False, "error": "Not a Git repository"}

    try:
        files = []
        for item in root.rglob("*"):
            rel = item.relative_to(root)
            if any(part in IGNORE for part in rel.parts):
                continue
            if item.is_file():
                files.append(str(rel))
        result["file_count"] = len(files)
        result["important_files"] = [
            f for f in files
            if Path(f).name in {
                "README.md", "package.json", "requirements.txt", "pyproject.toml",
                "pom.xml", "build.gradle", "build.gradle.kts", "gradlew",
                "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            }
        ][:100]
    except OSError as exc:
        result["file_scan_error"] = str(exc)

    if (root / "package.json").is_file():
        try:
            import json
            package = json.loads((root / "package.json").read_text(encoding="utf-8"))
            scripts = package.get("scripts", {})
            result["node"] = {
                "package_name": package.get("name"),
                "package_version": package.get("version"),
                "scripts": sorted(scripts.keys()),
                "has_lockfile": any((root / x).exists() for x in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")),
            }
        except Exception as exc:
            result["node"] = {"error": str(exc)}

    if (root / "pom.xml").exists():
        result["maven"] = {"wrapper": (root / "mvnw").exists()}

    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        result["gradle"] = {"wrapper": (root / "gradlew").exists()}

    return result
