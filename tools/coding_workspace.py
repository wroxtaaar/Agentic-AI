"""Isolated coding workspaces with bounded verification and approval-gated application."""
import json
import os
import re
import secrets
import subprocess
from pathlib import Path

from core.approvals import create
from tools.projects import roots
from tools.safety import sensitive, within, redact
from tools.verify import project_verify

WORKSPACES = Path(os.getenv("AGENT_CODING_WORKSPACE_ROOT", "/home/ubuntu/.agent-workspaces")).expanduser().resolve()
MAX_FILE_BYTES = 256_000
MAX_PATCH_BYTES = 2_000_000
IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".gradle"}

def _allowed_project(path):
    return any(path == root or root in path.parents for root in roots())

def _run(args, cwd, timeout=30):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"success": p.returncode == 0, "command": " ".join(args),
                "return_code": p.returncode, "stdout": redact(p.stdout, 12000),
                "stderr": redact(p.stderr, 12000)}
    except subprocess.TimeoutExpired:
        return {"success": False, "command": " ".join(args), "error": f"Timed out after {timeout}s"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

def _meta_dir():
    path = WORKSPACES / ".metadata"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _load(workspace_id):
    if not re.fullmatch(r"[a-f0-9]{16}", str(workspace_id or "")):
        return None
    f = _meta_dir() / f"{workspace_id}.json"
    try:
        item = json.loads(f.read_text(encoding="utf-8"))
        worktree = Path(item["worktree"]).resolve()
        project = Path(item["project"]).resolve()
        if not within(worktree, WORKSPACES) or not _allowed_project(project):
            return None
        return item
    except Exception:
        return None

def create_workspace(project):
    root = Path(project).expanduser().resolve()
    if not root.is_dir() or not _allowed_project(root):
        return {"success": False, "error": "Project is outside configured workspace roots"}
    if not (root / ".git").exists() and not (root / ".git").is_file():
        return {"success": False, "error": "Project is not a Git checkout"}
    status = _run(["git", "status", "--porcelain"], root)
    if not status.get("success"):
        return {"success": False, "error": "Could not inspect Git status", "details": status}
    if status.get("stdout", "").strip():
        return {"success": False, "error": "Refusing to start from a project with uncommitted changes; commit or stash them first"}
    WORKSPACES.mkdir(parents=True, exist_ok=True)
    wid = secrets.token_hex(8)
    worktree = WORKSPACES / wid
    added = _run(["git", "worktree", "add", "--detach", str(worktree), "HEAD"], root, 60)
    if not added.get("success"):
        return {"success": False, "error": "Could not create isolated Git worktree", "details": added}
    item = {"id": wid, "project": str(root), "worktree": str(worktree), "base_commit": _run(["git", "rev-parse", "HEAD"], root).get("stdout", "").strip(), "status": "editing"}
    (_meta_dir() / f"{wid}.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
    return {"success": True, "workspace_id": wid, "project": str(root), "worktree": str(worktree), "base_commit": item["base_commit"], "note": "Only this detached worktree is editable. The original checkout is unchanged until an approval is executed."}

def read_workspace_file(workspace_id, file):
    item = _load(workspace_id)
    if not item: return {"success": False, "error": "Unknown workspace"}
    rel = Path(file)
    if rel.is_absolute() or ".." in rel.parts: return {"success": False, "error": "Invalid relative path"}
    target = (Path(item["worktree"]) / rel).resolve()
    if not within(target, Path(item["worktree"])) or sensitive(target): return {"success": False, "error": "Path is blocked"}
    if not target.is_file(): return {"success": False, "error": "File not found"}
    if target.stat().st_size > MAX_FILE_BYTES: return {"success": False, "error": "File exceeds the 256 KB read limit"}
    try: return {"success": True, "file": str(rel), "content": redact(target.read_text(encoding="utf-8", errors="replace"), MAX_FILE_BYTES)}
    except Exception as exc: return {"success": False, "error": str(exc)}

def write_workspace_file(workspace_id, file, content):
    item = _load(workspace_id)
    if not item: return {"success": False, "error": "Unknown workspace"}
    if item.get("status") != "editing": return {"success": False, "error": "Workspace is no longer editable"}
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_FILE_BYTES:
        return {"success": False, "error": "Content must be text no larger than 256 KB"}
    rel = Path(file)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts: return {"success": False, "error": "Invalid relative path"}
    target = (Path(item["worktree"]) / rel).resolve()
    if not within(target, Path(item["worktree"])) or sensitive(target): return {"success": False, "error": "Path is blocked"}
    if any(part in IGNORED for part in rel.parts): return {"success": False, "error": "Generated/dependency directories are blocked"}
    if target.exists() and not target.is_file(): return {"success": False, "error": "Target is not a regular file"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"success": True, "file": str(rel), "bytes_written": len(content.encode("utf-8")), "workspace_only": True}

def verify_workspace(workspace_id, mode="auto", timeout=180):
    item = _load(workspace_id)
    if not item: return {"success": False, "error": "Unknown workspace"}
    if item.get("status") not in {"editing", "verified"}: return {"success": False, "error": "Workspace is not available for verification"}
    result = project_verify(item["worktree"], mode=mode, timeout=max(10, min(int(timeout), 300)))
    item["last_verification"] = result
    item["status"] = "verified" if result.get("success") else "editing"
    (_meta_dir() / f"{item['id']}.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
    return {"workspace_id": item["id"], "verification": result}

def finalize_workspace(workspace_id, summary):
    item = _load(workspace_id)
    if not item: return {"success": False, "error": "Unknown workspace"}
    if item.get("status") != "verified" or not (item.get("last_verification") or {}).get("success"):
        return {"success": False, "error": "Run successful verification in this workspace before requesting application"}
    root, worktree = Path(item["project"]), Path(item["worktree"])
    # Include new files in the diff without staging their contents.
    intent = _run(["git", "add", "-N", "."], worktree, 30)
    if not intent.get("success"): return {"success": False, "error": "Could not prepare diff", "details": intent}
    patch = _run(["git", "diff", "--binary", "HEAD", "--", ".", ":(exclude)**/.env", ":(exclude)**/.env.*"], worktree, 30)
    if not patch.get("success"): return {"success": False, "error": "Could not create patch", "details": patch}
    diff = patch.get("stdout", "")
    if not diff.strip(): return {"success": False, "error": "No changes found in workspace"}
    if len(diff.encode("utf-8")) > MAX_PATCH_BYTES: return {"success": False, "error": "Patch exceeds 2 MB limit"}
    patch_path = _meta_dir() / f"{item['id']}.patch"
    patch_path.write_text(diff, encoding="utf-8")
    approval = create("workspace_patch", f"Apply verified coding workspace {item['id']}: {summary[:180]}", {
        "workspace_id": item["id"], "project": str(root), "patch_path": str(patch_path),
        "base_commit": item["base_commit"], "summary": summary[:2000]
    })
    item["status"] = "pending_approval"
    item["approval_id"] = approval["id"]
    (_meta_dir() / f"{item['id']}.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
    return {"success": True, "workspace_id": item["id"], "approval": approval,
            "summary": summary, "diff": redact(diff, 24000),
            "note": "Changes remain isolated. Approve the workspace_patch item, then execute its approval to apply this tested diff to the original checkout. Git commit/push/deploy remain separate actions."}

def apply_approved_workspace_patch(payload):
    root = Path(payload.get("project", "")).expanduser().resolve()
    patch_path = Path(payload.get("patch_path", "")).resolve()
    wid = payload.get("workspace_id", "")
    item = _load(wid)
    if not item or item.get("status") != "pending_approval" or Path(item["project"]).resolve() != root:
        return {"success": False, "error": "Workspace metadata does not match approval"}
    if not _allowed_project(root) or not within(patch_path, _meta_dir()) or not patch_path.is_file():
        return {"success": False, "error": "Project or patch path is not allowed"}
    if _run(["git", "rev-parse", "HEAD"], root).get("stdout", "").strip() != payload.get("base_commit"):
        return {"success": False, "error": "Project HEAD changed since workspace creation; recreate the workspace and rebase the task"}
    status = _run(["git", "status", "--porcelain"], root)
    if not status.get("success") or status.get("stdout", "").strip():
        return {"success": False, "error": "Project has uncommitted changes; refusing to apply patch"}
    check = _run(["git", "apply", "--check", str(patch_path)], root, 30)
    if not check.get("success"): return {"success": False, "error": "Patch no longer applies cleanly", "details": check}
    applied = _run(["git", "apply", str(patch_path)], root, 30)
    if not applied.get("success"): return {"success": False, "error": "Patch application failed", "details": applied}
    verification = project_verify(str(root), mode="auto", timeout=240)
    if not verification.get("success"):
        rollback = _run(["git", "apply", "--reverse", str(patch_path)], root, 30)
        return {"success": False, "error": "Applied patch failed post-application verification", "verification": verification, "rollback": rollback}
    item["status"] = "applied"
    (_meta_dir() / f"{wid}.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
    return {"success": True, "workspace_id": wid, "project": str(root), "verification": verification,
            "note": "Patch is applied but not committed or pushed. Review the diff and use the separate approval-gated Git commit flow when ready."}
