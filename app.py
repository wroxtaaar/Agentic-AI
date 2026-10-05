import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from core.orchestrator import Orchestrator
from core.approvals import list_pending, get, set_status, create
from tools.patches import approve, apply
from tools.docker import execute_action
from tools.system import info
from tools.projects import discover
from tools.docker import list_containers

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
    return set_status(aid,'approved')

@app.post('/api/approvals/{aid}/reject')
def approval_reject(aid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    item=get(aid)
    if not item: raise HTTPException(404,'Approval not found')
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

@app.post('/api/actions/docker/{aid}/execute')
def execute_docker_action(aid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    item=get(aid)
    if not item: raise HTTPException(404,'Approval not found')
    if item.get('kind') not in {'docker_restart','docker_start','docker_stop'}:
        raise HTTPException(400,'Approval is not a Docker action')
    if item.get('status')!='approved':
        raise HTTPException(400,'Approval is not approved')
    action=item['payload'].get('action')
    container=item['payload'].get('container')
    result=execute_action(action,container)
    if not result.get('success'):
        raise HTTPException(502,result.get('stderr') or result.get('error') or 'Docker action failed')
    set_status(aid,'executed')
    return {'success':True,'approval_id':aid,'action':action,'container':container,'result':result}

@app.get('/',include_in_schema=False)
def index(): return FileResponse(Path(__file__).parent/'web'/'index.html')
