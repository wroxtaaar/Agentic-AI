import json, os, secrets
from pathlib import Path
from datetime import datetime, timezone

DB = Path(os.getenv("AGENT_APPROVAL_DB", "/data/approvals.json"))

def _load():
    if not DB.exists():
        return {}
    try:
        return json.loads(DB.read_text())
    except Exception:
        return {}

def _save(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def create(kind, description, payload):
    data = _load()
    aid = secrets.token_hex(8)
    data[aid] = {"id": aid, "kind": kind, "description": description, "payload": payload, "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()}
    _save(data)
    return data[aid]

def get(aid):
    return _load().get(aid)

def list_pending():
    return [x for x in _load().values() if x["status"] == "pending"]

def set_status(aid, status):
    data = _load()
    if aid not in data:
        return None
    data[aid]["status"] = status
    data[aid]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(data)
    return data[aid]
