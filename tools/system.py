import os, platform
def info(): return {'hostname':platform.node(),'os':f'{platform.system()} {platform.release()}','arch':platform.machine(),'python':platform.python_version(),'user':os.getenv('USER','unknown')}
