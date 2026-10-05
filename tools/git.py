import subprocess
from pathlib import Path
from .safety import redact
def _run(args,path='.'):
    p=Path(path).expanduser().resolve()
    if not p.exists():return {'success':False,'error':f'Path does not exist: {p}'}
    try:
        r=subprocess.run(['git','-C',str(p),*args],capture_output=True,text=True,timeout=20)
        return {'success':r.returncode==0,'repository':str(p),'stdout':redact(r.stdout),'stderr':redact(r.stderr,5000),'return_code':r.returncode}
    except Exception as e:return {'success':False,'error':str(e)}
def status(path='.'):return _run(['status','--short','--branch'],path)
def branch(path='.'):return _run(['branch','--show-current'],path)
def log(path='.',count=10):return _run(['log',f'-{max(1,min(int(count),50))}','--oneline','--decorate'],path)
def diff(path='.'):return _run(['diff','--stat','--','.'],path)
