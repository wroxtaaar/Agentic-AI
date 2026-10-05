import subprocess
from .safety import redact
def _run(args,timeout=20):
    try:
        r=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout)
        return {'success':r.returncode==0,'stdout':redact(r.stdout),'stderr':redact(r.stderr,5000),'return_code':r.returncode}
    except Exception as e:return {'success':False,'error':str(e)}
def list_containers(): return _run(['ps','--format','table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'])
def logs(container,lines=100): return _run(['logs','--tail',str(max(1,min(int(lines),500))),container])
def inspect(container): return _run(['inspect','--format','Name={{.Name}}\nImage={{.Config.Image}}\nStatus={{.State.Status}}\nStartedAt={{.State.StartedAt}}\nRestartCount={{.RestartCount}}',container])
def stats(container): return _run(['stats','--no-stream','--format','table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}',container])
def restart(container): return _run(['restart',container],30)
