import sqlite3
from pathlib import Path
from .safety import redact
DB=Path(__file__).resolve().parent.parent/'memory.db'
def save(content, project='global'):
    content=redact(content.strip(),5000)
    con=sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY, project TEXT, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cur=con.execute('INSERT INTO memory(project,content) VALUES(?,?)',(project,content))
    con.commit(); con.close()
    return {'success':True,'memory_id':cur.lastrowid,'project':project}
def search(query,project=''):
    con=sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY, project TEXT, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    if project:
        rows=con.execute('SELECT id,project,content,created_at FROM memory WHERE project=? AND content LIKE ? ORDER BY id DESC LIMIT 20',(project,f'%{query}%')).fetchall()
    else:
        rows=con.execute('SELECT id,project,content,created_at FROM memory WHERE content LIKE ? ORDER BY id DESC LIMIT 20',(f'%{query}%',)).fetchall()
    con.close()
    return {'success':True,'memories':[{'id':r[0],'project':r[1],'content':r[2],'created_at':r[3]} for r in rows]}
