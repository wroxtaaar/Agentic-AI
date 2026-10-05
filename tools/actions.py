import time

from core.approvals import get, set_status
from tools.docker import execute_action


DOCKER_KINDS = {"docker_restart", "docker_start", "docker_stop"}


def execute_approved(aid):
    item = get(aid)
    if not item:
        return {"success": False, "error": "Approval not found"}

    if item.get("status") != "approved":
        return {"success": False, "error": "Approval is not approved"}

    kind = item.get("kind")
    if kind in DOCKER_KINDS:
        payload = item.get("payload") or {}
        action = payload.get("action")
        container = payload.get("container")

        result = execute_action(action, container)
        if not result.get("success"):
            return {
                "success": False,
                "approval_id": aid,
                "kind": kind,
                "action": action,
                "container": container,
                "result": result,
            }

        # Give Docker a moment to finish a restart/start before verification.
        time.sleep(2)
        verification = execute_action("verify", container)

        if not verification.get("success"):
            set_status(aid, "failed")
            return {
                "success": False,
                "approval_id": aid,
                "kind": kind,
                "action": action,
                "container": container,
                "result": result,
                "verification": verification,
                "error": "Docker action completed but post-action verification failed",
            }

        set_status(aid, "executed")
        return {
            "success": True,
            "approval_id": aid,
            "kind": kind,
            "action": action,
            "container": container,
            "result": result,
            "verification": verification,
        }

    return {
        "success": False,
        "approval_id": aid,
        "kind": kind,
        "error": f"No executor is registered for approval kind '{kind}'",
    }
