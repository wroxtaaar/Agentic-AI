import subprocess
from pathlib import Path
from .safety import redact
IGNORE={'.git','.venv','venv','node_modules','build','dist','.gradle','__pycache__'}
def python_syntax(path):
    root=Path(path).expanduser().resolve(); files=[str(x.relative_to(root)) for x in root.rglob('*.py') if not any(p in IGNORE for p in x.relative_to(root).parts)]
    if not files:return {'success':False,'error':'No Python files found'}
    r=subprocess.run(['python','-m','py_compile',*files],cwd=root,capture_output=True,text=True,timeout=60)
    return {'success':r.returncode==0,'check':'python_syntax','files':len(files),'stdout':redact(r.stdout),'stderr':redact(r.stderr),'return_code':r.returncode}
def project_markers(path):
    root=Path(path).expanduser().resolve(); markers=[]
    if any((root/x).exists() for x in ('pyproject.toml','requirements.txt','setup.py')):markers.append('python')
    if (root/'package.json').exists():markers.append('node')
    if (root/'pom.xml').exists():markers.append('maven')
    if any((root/x).exists() for x in ('build.gradle','build.gradle.kts')):markers.append('gradle')
    return {'success':True,'project_type':markers[0] if len(markers)==1 else ('mixed' if markers else 'unknown'),'markers':markers}
