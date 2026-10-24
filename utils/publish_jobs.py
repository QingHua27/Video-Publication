"""Durable task stages and request deduplication; interrupted work is never replayed."""
import json
import sqlite3
import threading
import time
import uuid
from contextlib import closing, contextmanager
from contextvars import ContextVar
from pathlib import Path
from conf import BASE_DIR

class JobStore:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with closing(self.connect()) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS publish_job_records(id TEXT PRIMARY KEY, request_key TEXT UNIQUE, request_digest TEXT, updated REAL NOT NULL, payload TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS publish_job_updated ON publish_job_records(updated DESC)')
            for key,payload in db.execute('SELECT id,payload FROM publish_job_records').fetchall():
                job=json.loads(payload)
                if job['status'] in ('queued','running'):
                    stage=job.get('stage') or '等待执行'
                    job.update(status='failed',resultUncertain=True,interrupted=True,windowAvailable=False,windowVisible=False,uploadWaiting=False,updatedAt=time.time(),message=f'上次服务退出时任务停在「{stage}」，执行结果待核对；未自动重新发布。请先到平台核对。')
                    for phase in job.get('phases',{}).values():
                        if phase.get('status') in ('running','waiting'):phase['status']='interrupted'
                    self.write(db,job)
            db.commit()
    def connect(self):
        return sqlite3.connect(self.path,timeout=15)
    @staticmethod
    def write(db,job):
        db.execute('UPDATE publish_job_records SET updated=?,payload=? WHERE id=?',(job['updatedAt'],json.dumps(job,ensure_ascii=False),job['id']))
    def claim(self,platform,metadata=None,request_key=None,request_digest=None):
        if request_key is not None and (not isinstance(request_key,str) or not 1<=len(request_key)<=100):
            raise ValueError('提交标识无效，请刷新后重试')
        with self.lock,closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if request_key:
                row=db.execute('SELECT id,request_digest FROM publish_job_records WHERE request_key=?',(request_key,)).fetchone()
                if row:
                    if row[1]!=request_digest:raise ValueError('同一提交标识对应的内容已改变，请重新提交')
                    return row[0],False
            now=time.time();key=uuid.uuid4().hex
            job={**(metadata or {}),'id':key,'platform':platform,'status':'queued','message':'任务已提交','createdAt':now,'updatedAt':now,'progress':0,'stage':'等待执行'}
            db.execute('INSERT INTO publish_job_records VALUES(?,?,?,?,?)',(key,request_key,request_digest,now,json.dumps(job,ensure_ascii=False)))
            db.commit()
            return key,True
    def update(self,key,**fields):
        with self.lock,closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM publish_job_records WHERE id=?',(key,)).fetchone()
            if not row:return
            job=json.loads(row[0]);job.update(fields,updatedAt=time.time());self.write(db,job);db.commit()
    def get(self,key):
        with closing(self.connect()) as db:
            row=db.execute('SELECT payload FROM publish_job_records WHERE id=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def list(self,limit=100):
        with closing(self.connect()) as db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM publish_job_records ORDER BY updated DESC LIMIT ?',(min(500,max(1,int(limit))),))]

_lock=threading.RLock()
_store=None
_context=threading.local()
_phase_context=ContextVar('publish_phase',default=None)
def job_store():
    global _store
    with _lock:
        if _store is None:_store=JobStore(Path(BASE_DIR)/'db'/'publish-jobs.db')
        return _store

def claim_job(platform,metadata=None,request_key=None,request_digest=None):
    return job_store().claim(platform,metadata,request_key,request_digest)
def create_job(platform,metadata=None):
    return claim_job(platform,metadata)[0]
def update_job(job_id,status,message,**extra):
    with _lock:
        job=read_job(job_id)
        if not job:return
        fields={'status':status,'message':message}
        phases=job.get('phases',{})
        if status=='completed':
            fields.update(progress=100,stage='流程结束',uploadWaiting=False)
            for phase in phases.values():
                if phase.get('status')=='running':phase.update(status='completed',updatedAt=time.time())
        elif status=='running':fields.update(progress=5,stage='检查账号与素材')
        elif status in ('failed','cancelled'):
            fields['uploadWaiting']=False
            active=[(name,phase) for name,phase in phases.items() if phase.get('status')=='running']
            if active and not any(phase.get('status')=='failed' for phase in phases.values()):
                name,phase=max(active,key=lambda item:_phase_priority.get(item[0],0))
                phase.update(status='failed' if status=='failed' else 'cancelled',error=message)
            for phase in phases.values():
                if phase.get('status') in ('running','waiting'):phase['status']='cancelled'
        if phases:fields['phases']=phases
        job_store().update(job_id,**fields,**extra)

def read_job(job_id):return job_store().get(job_id)
def list_jobs(limit=100):return job_store().list(limit)
def bind_job(job_id):_context.job_id=job_id
def current_job_id():return getattr(_context,'job_id',None)
_NO_PROGRESS=object()
_phase_priority={'precheck':0,'preparation':1,'upload':2,'metadata':3,'cover':4,'collection':5,'submission':6}

@contextmanager
def phase_scope(name):
    token=_phase_context.set(name)
    try:yield
    finally:_phase_context.reset(token)

def _phase_stage(phases,fallback):
    for statuses in ({'failed'},{'running'},{'waiting'}):
        matching=[(name,phase) for name,phase in phases.items() if phase.get('status') in statuses]
        if matching:return max(matching,key=lambda item:_phase_priority.get(item[0],0))[1]['message']
    return fallback

def report_phase(name,status,message,progress=_NO_PROGRESS,*,overall_progress=None):
    key=current_job_id()
    if not key:return
    with _lock:
        job=read_job(key)
        if not job or job['status'] in ('completed','failed','cancelled'):return
        phases=job.get('phases',{})
        phase={**phases.get(name,{}),'status':status,'message':str(message),'updatedAt':time.time()}
        if progress is not _NO_PROGRESS:phase['progress']=progress
        phases[name]=phase
        upload=phases.get('upload',{})
        fields={'phases':phases,'stage':_phase_stage(phases,str(message)),'uploadWaiting':upload.get('status') in ('running','waiting'),'uploadPercent':upload.get('progress')}
        if overall_progress is not None:fields['progress']=max(job.get('progress',0),min(95,int(overall_progress)))
        job_store().update(key,**fields)

def report_stage(stage,progress):
    name=_phase_context.get()
    if name is None:
        if '均已就绪' in stage or '均已准备' in stage:name='preparation'
        elif '封面' in stage:name='cover'
        elif '合集' in stage:name='collection'
        elif '发布' in stage or '验证' in stage or progress>=85:name='submission'
        elif '上传' in stage:name='upload'
        else:name='metadata'
    report_phase(name,'completed' if name=='preparation' else 'running',stage,overall_progress=progress)

def set_window_state(job_id,available,visible):job_store().update(job_id,windowAvailable=available,windowVisible=visible)

def report_upload_progress(percent=None):
    key=current_job_id()
    if not key:return
    with _lock:
        job=read_job(key)
        if not job or job['status'] in ('completed','failed','cancelled'):return
        now=time.time();started=job.get('uploadStartedAt',now);elapsed=int(now-started)
        job_store().update(key,uploadStartedAt=started)
        report_phase('upload','running',f'视频上传中 · 已等待{elapsed//60}分{elapsed%60}秒',percent,overall_progress=35 if percent is None else int(35+percent*.3))


def record_preflight(job_id,report):
    with _lock:
        job=read_job(job_id)
        if not job:return
        phases=job.get('phases',{})
        phases['precheck']={'status':'completed' if report['ok'] else 'failed','message':'本地预检通过（未联网验证登录状态）' if report['ok'] else '；'.join(report['errors']),'updatedAt':time.time()}
        job_store().update(job_id,phases=phases,preflight=report,stage='本地预检通过，等待执行' if report['ok'] else '发布前检查未通过')
