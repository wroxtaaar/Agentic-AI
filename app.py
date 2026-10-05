import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from core.orchestrator import Orchestrator
from core.approvals import list_pending, get, set_status, create
from tools.patches import approve, apply
from tools.system import info
from tools.projects import discover
from tools.docker import list_containers
from tools.actions import execute_approved

load_dotenv()
app=FastAPI(title='Oracle VPS Agent',version='1.0.0')

def auth(authorization: str|None=Header(default=None)):
    token=os.getenv('AGENT_API_TOKEN')
    if not token: raise HTTPException(503,'AGENT_API_TOKEN is not configured')
    if authorization!=f'Bearer {token}': raise HTTPException(401,'Unauthorized')

class Chat(BaseModel):
    message:str=Field(min_length=1,max_length=12000)
    history:list[dict]=Field(default_factory=list,max_length=20)

class RestartRequest(BaseModel):
    container:str=Field(min_length=1,max_length=200)

@app.get('/health')
def health(): return {'status':'ok','service':'oracle-vps-agent','version':app.version}

@app.get('/api/status')
def status(authorization:str|None=Header(default=None)):
    auth(authorization)
    return {'system':info(),'projects':discover(),'containers':list_containers()}

@app.post('/api/chat')
def chat(req:Chat,authorization:str|None=Header(default=None)):
    auth(authorization)
    return Orchestrator().run(req.message,req.history)

@app.get('/api/approvals')
def approvals(authorization:str|None=Header(default=None)):
    auth(authorization)
    return {'approvals':list_pending()}

@app.get('/api/approvals/{aid}')
def approval(aid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    item=get(aid)
    if not item: raise HTTPException(404,'Approval not found')
    return item

@app.post('/api/approvals/{aid}/approve')
def approval_approve(aid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    item=get(aid)
    if not item: raise HTTPException(404,'Approval not found')
    if item.get('status')!='pending': raise HTTPException(400,'Approval is not pending')
    return set_status(aid,'approved')

@app.post('/api/approvals/{aid}/reject')
def approval_reject(aid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    item=get(aid)
    if not item: raise HTTPException(404,'Approval not found')
    if item.get('status')!='pending': raise HTTPException(400,'Approval is not pending')
    return set_status(aid,'rejected')

@app.post('/api/proposals/{pid}/approve')
def proposal_approve(pid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    result=approve(pid)
    if not result.get('success',True): raise HTTPException(400,result.get('error','Approval failed'))
    return result

@app.post('/api/proposals/{pid}/apply')
def proposal_apply(pid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    result=apply(pid)
    if not result.get('success',True): raise HTTPException(400,result.get('error','Apply failed'))
    return result

@app.post('/api/actions/restart-container')
def restart_container(req:RestartRequest,authorization:str|None=Header(default=None)):
    auth(authorization)
    return create('container_restart',f'Restart Docker container {req.container}',{'container':req.container})

@app.post('/api/actions/{aid}/execute')
def execute_approved_action(aid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    result=execute_approved(aid)
    if not result.get('success'):
        error=result.get('error','Approved action failed')
        if result.get('approval_id') and result.get('verification'):
            raise HTTPException(502,result)
        raise HTTPException(400,error)
    return result

# Backward-compatible Docker endpoint for existing clients.
@app.post('/api/actions/docker/{aid}/execute')
def execute_docker_action(aid:str,authorization:str|None=Header(default=None)):
    return execute_approved_action(aid,authorization)

@app.get('/',include_in_schema=False)
def index(): return FileResponse(Path(__file__).parent/'web'/'index.html')
