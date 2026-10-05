import os
from pathlib import Path
from .safety import sensitive
IGNORE={'.git','.venv','venv','node_modules','__pycache__','.gradle','build','dist','.cache'}
def roots(): return [Path(x).expanduser().resolve() for x in os.getenv('AGENT_WORKSPACE_ROOTS','/home/ubuntu').split(':') if x.strip()]
def discover(limit=100,max_depth=4):
    found=[]
    for root in roots():
        if not root.is_dir() or sensitive(root):continue
        q=[(root,0)]; seen=set()
        while q and len(found)<limit:
            p,d=q.pop(0)
            if p in seen:continue
            seen.add(p)
            if (p/'.git').exists() and p!=root:
                found.append({'name':p.name,'path':str(p),'root':str(root)});continue
            if d>=max_depth:continue
            try: children=sorted(p.iterdir())
            except OSError:continue
            for c in children:
                if c.is_dir() and c.name not in IGNORE and not sensitive(c):q.append((c,d+1))
    return {'success':True,'projects':found,'count':len(found)}
def read_file(path):
    p=Path(path).expanduser().resolve()
    if sensitive(p):return {'success':False,'error':'Sensitive file blocked'}
    if not p.is_file():return {'success':False,'error':'File not found'}
    try:return {'success':True,'path':str(p),'content':__import__('tools.safety',fromlist=['redact']).redact(p.read_text(encoding='utf-8',errors='replace'))}
    except Exception as e:return {'success':False,'error':str(e)}
def structure(path):
    p=Path(path).expanduser().resolve(); important=[]; count=0
    for x in p.rglob('*'):
        if any(part in IGNORE for part in x.relative_to(p).parts):continue
        if x.is_file():
            count+=1
            if x.name in {'README.md','package.json','requirements.txt','pyproject.toml','pom.xml','build.gradle','build.gradle.kts','Dockerfile','docker-compose.yml','docker-compose.yaml'}:important.append(str(x.relative_to(p)))
    return {'success':True,'project':str(p),'file_count':count,'important_files':sorted(important)}
