import os
import sqlite3
from pathlib import Path
from .safety import redact
from core.approvals import create

DB=Path(os.getenv('AGENT_MEMORY_DB','/data/memory.db'))

def _ensure(con):
    con.execute('CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY, project TEXT, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')

def propose(content, project='global'):
    content=redact(content.strip(),5000)
    if not content:
        return {'success':False,'error':'Memory content is empty'}
    approval=create('memory_save',f'Save durable memory for {project}',{'content':content,'project':project})
    return {'success':True,'approval':approval}

def save_approved(content, project='global'):
    content=redact(content.strip(),5000)
    DB.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(DB)
    _ensure(con)
    cur=con.execute('INSERT INTO memory(project,content) VALUES(?,?)',(project,content))
    con.commit(); con.close()
    return {'success':True,'memory_id':cur.lastrowid,'project':project}

def search(query,project=''):
    DB.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(DB)
    _ensure(con)
    if project:
        rows=con.execute('SELECT id,project,content,created_at FROM memory WHERE project=? AND content LIKE ? ORDER BY id DESC LIMIT 20',(project,f'%{query}%')).fetchall()
    else:
        rows=con.execute('SELECT id,project,content,created_at FROM memory WHERE content LIKE ? ORDER BY id DESC LIMIT 20',(f'%{query}%')).fetchall()
    con.close()
    return {'success':True,'memories':[{'id':r[0],'project':r[1],'content':r[2],'created_at':r[3]} for r in rows]}

save = propose
