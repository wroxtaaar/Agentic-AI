import re
from pathlib import Path
SENSITIVE_NAMES={'.env','.env.local','.env.production','.env.development','.git-credentials','credentials','credentials.json','secrets.json','secret.json','id_rsa','id_ed25519','id_ecdsa'}
SENSITIVE_EXTENSIONS={'.pem','.key','.p12','.pfx','.jks'}
SENSITIVE_PARTS={'.ssh','.aws','.gnupg'}
PATTERNS=[(re.compile(r'(?im)^([ \t]*(?:export[ \t]+)?[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|PASSWORD|SECRET|PRIVATE[_-]?KEY|CLIENT[_-]?SECRET)[A-Z0-9_]*[ \t]*=[ \t]*)(.+)$'),r'\1[REDACTED]'),(re.compile(r'(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+'),r'\1[REDACTED]'),(re.compile(r'(?is)(-----BEGIN [A-Z ]*PRIVATE KEY-----).*?(-----END [A-Z ]*PRIVATE KEY-----)'),r'\1[REDACTED]\2')]
def resolve(p): return Path(p).expanduser().resolve()
def sensitive(p):
    p=resolve(p); return p.name.lower() in SENSITIVE_NAMES or p.suffix.lower() in SENSITIVE_EXTENSIONS or any(x.lower() in SENSITIVE_PARTS for x in p.parts)
def redact(s, limit=12000):
    for pattern,repl in PATTERNS: s=pattern.sub(repl,s)
    return s[:limit] + ('...[TRUNCATED]' if len(s)>limit else '')
def within(p,root):
    try: resolve(p).relative_to(resolve(root)); return True
    except ValueError: return False
