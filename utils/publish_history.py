"""Persistent per-account duplicate protection. Submission is not publication."""
import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from utils.material_classification import classify_material


class DuplicatePublication(ValueError):
    pass


@contextmanager
def database(root):
    db=sqlite3.connect(Path(root)/'db/database.db',timeout=15)
    db.row_factory=sqlite3.Row
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS publish_history(
            id INTEGER PRIMARY KEY,platform INTEGER NOT NULL,account TEXT NOT NULL,
            identity TEXT NOT NULL,series TEXT NOT NULL,episode INTEGER,filename TEXT NOT NULL,
            source_path TEXT NOT NULL,title TEXT NOT NULL,status TEXT NOT NULL,
            job_id TEXT NOT NULL DEFAULT '',message TEXT NOT NULL DEFAULT '',updated_at REAL NOT NULL,
            UNIQUE(platform,account,identity))''')
        db.commit()
        yield db
    finally:db.close()


def describe(db,source,title=''):
    source=str(source)
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    row=None
    if 'file_records' in tables:
        row=db.execute('SELECT * FROM file_records WHERE file_path=? COLLATE NOCASE',(source,)).fetchone()
    name=row['filename'] if row else Path(source).name
    classification=classify_material(name)
    number=classification['episode_number']
    section=row['section_id'] if row and 'section_id' in row.keys() else 0
    if section and 'material_sections' in tables:
        section_row=db.execute('SELECT name FROM material_sections WHERE id=?',(section,)).fetchone()
        series=section_row[0] if section_row else f'分区{section}'
        scope=f'section:{section}'
    else:
        parent=str(Path(source).parent)
        series=Path(parent).name if parent!='.' else '未分区'
        scope=f'path:{parent.casefold()}'
    # Distinct versions of the same episode in the same section share a key.
    has_series=bool(section) or str(Path(source).parent)!='.'
    key=[scope,number] if number is not None and has_series else ['file',str(Path(source)).casefold()]
    if classification['episode_unit']=='章' and number is not None and has_series:key=[scope,'chapter',number]
    return dict(identity=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest(),
                series=series,episode=number,filename=name,source_path=source,title=str(title or ''))


def reserve(root,platform,accounts,files,title,job_id,manual=False,allow_repeat=False,job_reader=None):
    if not accounts or not files:raise ValueError('请选择账号和视频素材')
    ids=[]
    with database(root) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            for account in dict.fromkeys(accounts):
                for source in dict.fromkeys(files):
                    item=describe(db,source,title)
                    old=db.execute('SELECT * FROM publish_history WHERE platform=? AND account=? AND identity=?',
                                   (platform,account,item['identity'])).fetchone()
                    if not old and classify_material(item['filename'])['episode_unit']=='章':
                        old=db.execute('SELECT * FROM publish_history WHERE platform=? AND account=? AND source_path=? COLLATE NOCASE ORDER BY updated_at DESC LIMIT 1',(platform,account,item['source_path'])).fetchone()
                    if old and old['status'] not in ('failed','cleared'):
                        label=classify_material(item['filename'])['folder_name'] if item['episode'] else item['filename']
                        active=job_reader(old['job_id']) if job_reader and old['job_id'] else None
                        if active and active['status'] in ('queued','running'):
                            raise ValueError(f'{label}的任务仍在执行，请等待结束后再提交')
                        if not allow_repeat:
                            raise DuplicatePublication(f"{item['series']} · {label}已有发布或待核对记录，继续上传可能重复发布。是否继续？")
                    values=(platform,account,item['identity'],item['series'],item['episode'],item['filename'],
                            item['source_path'],item['title'],'published' if manual else 'pending',job_id,
                            '手动补记已发布' if manual else '任务已预留，禁止重复提交',time.time())
                    if old:
                        db.execute('DELETE FROM publish_history WHERE id=?',(old['id'],))
                    cursor=db.execute('''INSERT INTO publish_history(platform,account,identity,series,episode,filename,
                        source_path,title,status,job_id,message,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',values)
                    ids.append(cursor.lastrowid)
            db.commit()
        except Exception:
            db.rollback();raise
    return ids


def finish(root,ids,status,message):
    with database(root) as db:
        db.executemany('UPDATE publish_history SET status=?,message=?,updated_at=? WHERE id=?',
                       [(status,str(message)[:500],time.time(),key) for key in ids])
        db.commit()


def list_records(root):
    with database(root) as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM publish_history ORDER BY updated_at DESC LIMIT 1000')]
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'file_records' in tables and 'section_id' in {r[1] for r in db.execute('PRAGMA table_info(file_records)')}:
            for row in rows:
                source = db.execute('SELECT section_id FROM file_records WHERE file_path=? COLLATE NOCASE',(row['source_path'],)).fetchone()
                row['material_section_id'] = source[0] if source else None
        return rows


def reconcile(root,key,status,job_reader):
    if status not in ('published','cleared'):raise ValueError('不支持的记录状态')
    with database(root) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM publish_history WHERE id=?',(key,)).fetchone()
        if not row:raise ValueError('发布记录不存在')
        job=job_reader(row['job_id']) if row['job_id'] else None
        if job and job['status'] in ('queued','running'):raise ValueError('该任务仍在执行，请结束后再核对')
        db.execute('UPDATE publish_history SET status=?,message=?,updated_at=? WHERE id=?',
                   (status,'用户确认已发布' if status=='published' else '用户确认未发布，允许重新提交',time.time(),key))
        db.commit()
