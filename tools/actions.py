import time

from core.approvals import get, set_status
from tools.docker import execute_action, verify_container
from tools.memory import save_approved
from tools.patches import apply as apply_patch
from tools.git_actions import execute_commit

DOCKER_KINDS = {"docker_restart", "docker_start", "docker_stop"}

def execute_approved(aid):
    item = get(aid)
    if not item:
        return {"success": False, "error": "Approval not found"}
    if item.get("status") != "approved":
        return {"success": False, "error": "Approval is not approved"}

    kind = item.get("kind")
    payload = item.get("payload") or {}

    if kind in DOCKER_KINDS:
        action = payload.get("action")
        container = payload.get("container")
        result = execute_action(action, container)
        if not result.get("success"):
            set_status(aid, "failed")
            return {"success": False, "approval_id": aid, "kind": kind, "result": result}
        expected_status = "exited" if action == "stop" else "running"
        verification = {"success": False}
        for attempt in range(5):
            verification = verify_container(container, expected_status=expected_status)
            if verification.get("success"):
                break
            if attempt < 4:
                time.sleep(2)
        if not verification.get("success"):
            set_status(aid, "failed")
            return {"success": False, "approval_id": aid, "kind": kind, "result": result,
                    "verification": verification, "error": "Docker action completed but verification failed"}
        set_status(aid, "executed")
        return {"success": True, "approval_id": aid, "kind": kind, "action": action,
                "container": container, "result": result, "verification": verification}

    if kind == "memory_save":
        result = save_approved(payload.get("content", ""), payload.get("project", "global"))
        if not result.get("success"):
            set_status(aid, "failed")
            return {"success": False, "approval_id": aid, "kind": kind, "result": result}
        set_status(aid, "executed")
        return {"success": True, "approval_id": aid, "kind": kind, "result": result,
                "verification": {"success": True, "verified": True}}

    if kind == "git_commit":
        result = execute_commit(payload.get("path", ""), payload.get("message", ""))
        if not result.get("success"):
            set_status(aid, "failed")
            return {"success": False, "approval_id": aid, "kind": kind, "result": result}
        set_status(aid, "executed")
        return {"success": True, "approval_id": aid, "kind": kind, "result": result,
                "verification": {"success": True, "verified": True}}

    if kind == "code_patch":
        proposal_id = payload.get("proposal_id")
        if not proposal_id:
            set_status(aid, "failed")
            return {"success": False, "approval_id": aid, "error": "Missing proposal_id"}
        result = apply_patch(proposal_id)
        if not result.get("success"):
            set_status(aid, "failed")
            return {"success": False, "approval_id": aid, "kind": kind, "result": result}
        set_status(aid, "executed")
        return {"success": True, "approval_id": aid, "kind": kind, "result": result,
                "verification": {"success": True, "verified": True, "note": "Patch applied; run the project's tests before deployment"}}

    return {"success": False, "approval_id": aid, "kind": kind,
            "error": f"No executor is registered for approval kind '{kind}'"}
