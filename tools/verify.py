import json
import subprocess
from pathlib import Path

from .safety import redact


IGNORE={'.git','.venv','venv','node_modules','build','dist','.gradle','__pycache__'}


def python_syntax(path):
    root=Path(path).expanduser().resolve()
    files=[str(x.relative_to(root)) for x in root.rglob('*.py')
           if not any(p in IGNORE for p in x.relative_to(root).parts)]
    if not files:
        return {'success':False,'error':'No Python files found'}
    r=subprocess.run(['python','-m','py_compile',*files],cwd=root,capture_output=True,text=True,timeout=60)
    return {'success':r.returncode==0,'check':'python_syntax','files':len(files),
            'stdout':redact(r.stdout),'stderr':redact(r.stderr),'return_code':r.returncode}


def project_markers(path):
    root=Path(path).expanduser().resolve()
    markers=[]
    if any((root/x).exists() for x in ('pyproject.toml','requirements.txt','setup.py')): markers.append('python')
    if (root/'package.json').exists(): markers.append('node')
    if (root/'pom.xml').exists(): markers.append('maven')
    if any((root/x).exists() for x in ('build.gradle','build.gradle.kts')): markers.append('gradle')
    return {'success':True,'project_type':markers[0] if len(markers)==1 else ('mixed' if markers else 'unknown'),'markers':markers}


def _run(root, command, timeout):
    try:
        r=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=timeout)
        return {'success':r.returncode==0,'command':' '.join(command),
                'stdout':redact(r.stdout,12000),'stderr':redact(r.stderr,12000),
                'return_code':r.returncode}
    except subprocess.TimeoutExpired:
        return {'success':False,'command':' '.join(command),'error':f'Command timed out after {timeout}s'}
    except Exception as exc:
        return {'success':False,'command':' '.join(command),'error':str(exc)}


def project_verify(path, mode='auto', timeout=180):
    root=Path(path).expanduser().resolve()
    if not root.is_dir(): return {'success':False,'error':'Project directory not found'}
    timeout=max(10,min(int(timeout),600))
    if mode not in {'auto','syntax','test','build'}:
        return {'success':False,'error':'Unsupported verification mode'}

    results=[]
    types=[]
    if (root/'package.json').exists(): types.append('node')
    if (root/'pom.xml').exists(): types.append('maven')
    if (root/'build.gradle').exists() or (root/'build.gradle.kts').exists() or (root/'gradlew').exists(): types.append('gradle')
    if any((root/x).exists() for x in ('pyproject.toml','requirements.txt','setup.py')) or list(root.rglob('*.py')): types.append('python')

    if mode in {'auto','syntax'} and 'python' in types:
        results.append(python_syntax(str(root)))
        if mode=='syntax':
            return {'success':all(x.get('success') for x in results),'mode':mode,'results':results}

    if mode in {'auto','test','build'} and 'node' in types:
        try:
            package=json.loads((root/'package.json').read_text(encoding='utf-8'))
            scripts=package.get('scripts',{})
            script='test' if mode!='build' and 'test' in scripts else ('build' if 'build' in scripts else None)
            if mode=='test' and 'test' not in scripts:
                return {'success':False,'mode':mode,'error':'Node project has no test script','types':types}
            if mode=='build' and 'build' not in scripts:
                return {'success':False,'mode':mode,'error':'Node project has no build script','types':types}
            if script:
                results.append(_run(root,['npm','run',script],timeout))
        except Exception as exc:
            return {'success':False,'mode':mode,'error':f'Invalid package.json: {exc}','types':types}

    if mode in {'auto','test','build'} and 'maven' in types:
        wrapper=root/'mvnw'
        command=[str(wrapper),'test'] if wrapper.exists() else ['mvn','test']
        if mode=='build':
            command=[str(wrapper),'package','-DskipTests'] if wrapper.exists() else ['mvn','package','-DskipTests']
        results.append(_run(root,command,timeout))

    if mode in {'auto','test','build'} and 'gradle' in types:
        wrapper=root/'gradlew'
        command=[str(wrapper),'test'] if wrapper.exists() else ['gradle','test']
        if mode=='build':
            command=[str(wrapper),'build','-x','test'] if wrapper.exists() else ['gradle','build','-x','test']
        results.append(_run(root,command,timeout))

    if not results:
        return {'success':False,'mode':mode,'types':types,'error':'No supported verification check was found'}
    return {'success':all(x.get('success') for x in results),'mode':mode,'types':types,'results':results}
