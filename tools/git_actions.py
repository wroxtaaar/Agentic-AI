import os
import subprocess
from pathlib import Path
from core.approvals import create
from .safety import redact

def _roots():
    return [Path(x).expanduser().resolve() for x in os.getenv("AGENT_WORKSPACE_ROOTS","/home/ubuntu").split(":") if x.strip()]

def _allowed(root):
    return any(root == base or base in root.parents for base in _roots())

def propose_commit(path, message):
    root=Path(path).expanduser().resolve()
    if not _allowed(root):
        return {'success':False,'error':'Git path is outside configured workspace'}
    if not (root/'.git').exists():
        return {'success':False,'error':'Not a Git repository'}
    message=message.strip()
    if not message or len(message)>200:
        return {'success':False,'error':'Commit message must be 1-200 characters'}
    approval=create('git_commit',f'Create Git commit in {root}',{'path':str(root),'message':message})
    return {'success':True,'approval':approval}

def execute_commit(path, message):
    root=Path(path).expanduser().resolve()
    if not _allowed(root):
        return {'success':False,'error':'Git path is outside configured workspace'}
    try:
        r=subprocess.run(['git','-C',str(root),'commit','-m',message],capture_output=True,text=True,timeout=60)
        return {'success':r.returncode==0,'stdout':redact(r.stdout),'stderr':redact(r.stderr,5000),'return_code':r.returncode}
    except Exception as e: return {'success':False,'error':str(e)}
