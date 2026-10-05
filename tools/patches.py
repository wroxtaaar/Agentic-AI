import hashlib,json,secrets
from pathlib import Path
from .safety import sensitive,within
from core.approvals import create,get,set_status
ROOT=Path(__file__).resolve().parent.parent
PROPOSALS=ROOT/'proposals'
PROPOSALS.mkdir(exist_ok=True)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def propose(project,problem,explanation,edits):
    root=Path(project).expanduser().resolve()
    if not root.is_dir(): return {'success':False,'error':'Project not found'}
    if not isinstance(edits,list) or not edits: return {'success':False,'error':'At least one exact edit required'}
    if len(edits)>20: return {'success':False,'error':'Too many edits in one proposal'}
    normalized=[]; hashes={}
    for e in edits:
        f,old,new=e.get('file'),e.get('old_text'),e.get('new_text')
        if not all(isinstance(x,str) for x in (f,old,new)): return {'success':False,'error':'Invalid edit'}
        target=(root/f).resolve()
        if not within(target,root) or sensitive(target) or not target.is_file():
            return {'success':False,'error':f'Invalid target: {f}'}
        content=target.read_text(encoding='utf-8',errors='replace')
        if content.count(old)!=1: return {'success':False,'error':f'old_text must occur exactly once: {f}'}
        hashes[f]=sha(target)
        normalized.append({'file':f,'old_text':old,'new_text':new})
    pid=secrets.token_hex(8)
    approval=create('code_patch',f'Apply coding proposal {pid}',{'proposal_id':pid})
    proposal={'id':pid,'project':str(root),'problem':problem,'explanation':explanation,'edits':normalized,'hashes':hashes,'status':'pending','approval_id':approval['id']}
    (PROPOSALS/f'{pid}.json').write_text(json.dumps(proposal,indent=2),encoding='utf-8')
    return {'success':True,'proposal':proposal,'approval':approval}

def load(pid):
    f=PROPOSALS/f'{pid}.json'
    return json.loads(f.read_text()) if f.exists() else None

def save(p):
    (PROPOSALS/f"{p['id']}.json").write_text(json.dumps(p,indent=2),encoding='utf-8')

def approve(pid):
    p=load(pid)
    if not p: return {'success':False,'error':'Proposal not found'}
    approval=get(p.get('approval_id',''))
    if not approval: return {'success':False,'error':'Approval record not found'}
    if approval.get('status')!='approved': return {'success':False,'error':'Approval must be approved through the approval queue first'}
    p['status']='approved'
    save(p)
    return p

def apply(pid):
    p=load(pid)
    if not p or p.get('status')!='approved': return {'success':False,'error':'Proposal is not approved'}
    approval=get(p.get('approval_id',''))
    if not approval or approval.get('status')!='approved': return {'success':False,'error':'Approval record is not approved'}
    for e in p['edits']:
        target=(Path(p['project'])/e['file']).resolve()
        if not target.is_file(): return {'success':False,'error':f'File missing: {e["file"]}'}
        if sha(target)!=p['hashes'][e['file']]:
            return {'success':False,'error':f'Changed since proposal: {e["file"]}'}
    backups=[]
    for e in p['edits']:
        target=(Path(p['project'])/e['file']).resolve()
        content=target.read_text(encoding='utf-8')
        backup=target.with_name(target.name+'.backup-'+secrets.token_hex(4))
        backup.write_text(content,encoding='utf-8')
        backups.append(str(backup))
        target.write_text(content.replace(e['old_text'],e['new_text']),encoding='utf-8')
    p['status']='applied'
    p['backups']=backups
    save(p)
    set_status(approval['id'],'executed')
    return {'success':True,'proposal_id':pid,'approval_id':approval['id'],'backups':backups,'verification_required':True}
