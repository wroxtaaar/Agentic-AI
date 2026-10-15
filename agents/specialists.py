from dataclasses import dataclass

@dataclass(frozen=True)
class Specialist:
    name:str
    mission:str
    triggers:tuple[str,...]

SPECIALISTS=(
 Specialist('project','Own repository discovery, architecture, project inventory and context.',('project','repo','repository','codebase','all my projects')),
 Specialist('research','Gather evidence from project documentation, configuration and available local sources; compare options without inventing external facts.',('research','compare','comparison','investigate','documentation','docs','evaluate','alternatives','trade-off','tradeoff')),
 Specialist('coding','Own source diagnosis, exact patch proposals and implementation planning.',('fix','bug','crash','error','code','implement','change','refactor')),
 Specialist('devops','Own Docker, services, resource usage and operational state.',('docker','container','service','cpu','memory','ram','disk','deploy','server','vps')),
 Specialist('git','Own branches, commits, diffs and repository state.',('git','commit','branch','diff','merge','history')),
 Specialist('debugger','Correlate runtime logs, source and configuration to identify root cause.',('debug','logs','failing','failure','broken','why')),
 Specialist('security','Review requested operations for secret exposure, unsafe scope and least privilege.',('security','secret','token','permission','credential','safe')),
 Specialist('verifier','Act as QA: own post-change verification, test coverage, regression risks and evidence of success.',('test','verify','verification','health','check','qa','regression','coverage')),
)
