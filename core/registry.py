from tools.system import info
from tools.shell import run
from tools.projects import discover,read_file,read_files,structure
from tools.audit import audit_project
from tools.docker import list_containers,logs,inspect,stats,propose_restart,propose_start,propose_stop
from tools.git import status,branch,log,diff
from tools.git_actions import propose_commit
from tools.patches import propose
from tools.memory import save as memory_save, search as memory_search
from tools.verify import python_syntax, project_markers, project_verify

def build_tools():
    def t(name,desc,fn,props=None,required=None):
        return {'name':name,'description':desc,'function':fn,'schema':{'type':'object','properties':props or {},'required':required or [],'additionalProperties':False}}
    return [
      t('system_info','Get VPS system information.',info),
      t('discover_projects','Find Git repositories under configured workspace roots.',discover,{'limit':{'type':'integer'},'max_depth':{'type':'integer'}}),
      t('project_audit','Build an evidence-based audit of one project: project type, important files, Git state, scripts and wrappers. Read-only.',audit_project,{'path':{'type':'string'}},['path']),
      t('project_structure','Inspect a project without modifying it.',structure,{'path':{'type':'string'}},['path']),
      t('read_file','Read a non-secret project file with redaction.',read_file,{'path':{'type':'string'}},['path']),
      t('read_files','Read up to 12 non-secret project files in one call. Prefer this over repeated read_file calls.',read_files,{'paths':{'type':'array','items':{'type':'string'}}},['paths']),
      t('shell_readonly','Run an allowlisted read-only shell command.',run,{'command':{'type':'string'}},['command']),
      t('docker_list','List running Docker containers.',list_containers),
      t('docker_logs','Read recent container logs.',logs,{'container':{'type':'string'},'lines':{'type':'integer'}},['container']),
      t('docker_inspect','Inspect one Docker container.',inspect,{'container':{'type':'string'}},['container']),
      t('docker_stats','Read one-shot Docker resource usage.',stats,{'container':{'type':'string'}},['container']),
      t('docker_restart','PROPOSAL ONLY: request approval to restart a Docker container. Does not restart it.',propose_restart,{'container':{'type':'string'}},['container']),
      t('docker_start','PROPOSAL ONLY: request approval to start a Docker container. Does not start it.',propose_start,{'container':{'type':'string'}},['container']),
      t('docker_stop','PROPOSAL ONLY: request approval to stop a Docker container. Does not stop it.',propose_stop,{'container':{'type':'string'}},['container']),
      t('git_status','Show repository status.',status,{'path':{'type':'string'}},['path']),
      t('git_branch','Show current branch.',branch,{'path':{'type':'string'}},['path']),
      t('git_log','Show recent commits.',log,{'path':{'type':'string'},'count':{'type':'integer'}},['path']),
      t('git_diff','Show unstaged diff statistics.',diff,{'path':{'type':'string'}},['path']),
      t('git_commit','PROPOSAL ONLY: request approval to create a local Git commit. Does not commit.',propose_commit,{'path':{'type':'string'},'message':{'type':'string'}},['path','message']),
      t('memory_save','PROPOSAL ONLY: request approval to save durable non-secret project memory.',memory_save,{'content':{'type':'string'},'project':{'type':'string'}},['content']),
      t('memory_search','Search durable project memory.',memory_search,{'query':{'type':'string'},'project':{'type':'string'}},['query']),
      t('verify_python','Run Python syntax verification after an approved change.',python_syntax,{'path':{'type':'string'}},['path']),
      t('verify_project','Run a bounded, project-aware verification check. Read-only; auto selects syntax/tests/build checks based on project type.',project_verify,{'path':{'type':'string'},'mode':{'type':'string','enum':['auto','syntax','test','build']},'timeout':{'type':'integer'}},['path']),
      t('project_type','Detect basic project type.',project_markers,{'path':{'type':'string'}},['path']),
      t('create_patch_proposal','Create an exact coding proposal. Does not edit source.',propose,{'project':{'type':'string'},'problem':{'type':'string'},'explanation':{'type':'string'},'edits':{'type':'array','items':{'type':'object'}}},['project','problem','explanation','edits']),
    ]
