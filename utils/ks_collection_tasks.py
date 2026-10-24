"""Kuaishou post-publication collection association. Never uploads a video."""
import asyncio
import json
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit
from conf import BASE_DIR

_DB = BASE_DIR / 'db/database.db'
_active = set()
_lock = threading.Lock()
_browser_slot = threading.Semaphore(1)

def connect():
    conn = sqlite3.connect(_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS ks_collection_tasks (
      id TEXT PRIMARY KEY, job_id TEXT, cookie TEXT, collection_name TEXT,
      collection_id TEXT, title TEXT, baseline TEXT, started REAL, submitted REAL,
      photo_id TEXT, status TEXT, message TEXT, updated REAL)''')
    conn.commit()
    return conn

def create(job_id, cookie, name, collection_id, title, baseline, started, submitted):
    task_id = uuid.uuid4().hex
    with closing(connect()) as db:
        db.execute('INSERT INTO ks_collection_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (task_id,job_id,str(cookie),name,str(collection_id),title,json.dumps(list(baseline)),started,submitted,'','prepared','视频已提交，等待平台作品可用后加入合集',time.time()))
        db.commit()
    return task_id

def get(task_id=None, job_id=None):
    with closing(connect()) as db:
        row=db.execute('SELECT * FROM ks_collection_tasks WHERE '+('id=?' if task_id else 'job_id=?')+' ORDER BY updated DESC LIMIT 1',(task_id or job_id,)).fetchone()
    return dict(row) if row else None

def update(task_id, **fields):
    allowed={'photo_id','status','message','submitted'}
    if not fields or not set(fields)<=allowed:raise ValueError('Invalid task fields')
    with closing(connect()) as db:
        db.execute('UPDATE ks_collection_tasks SET '+','.join(f'{k}=?' for k in fields)+',updated=? WHERE id=?',(*fields.values(),time.time(),task_id));db.commit()

def public(task):
    return {k:task[k] for k in ('id','status','message','photo_id')} if task else None

def select_work(rows, task):
    """Require a unique new work, exact title, and bounded submission time."""
    if task.get('photo_id'):
        return next((r for r in rows if str(r.get('photoId'))==task['photo_id']),None)
    baseline=set(json.loads(task['baseline']))
    matches=[]
    for row in rows:
        title=str(row.get('title','')).split('#')[0].strip()
        timestamp=float(row.get('publishTime') or 0)/1000
        if (str(row.get('photoId')) not in baseline and title==task['title'].strip()
                and task['started']-2 <= timestamp <= task['submitted']+120):
            matches.append(row)
    if len(matches)>1:raise RuntimeError('发现多个同名新作品，无法安全识别本次作品，请到快手核对；不会重新上传')
    return matches[0] if matches else None

async def open_content_management(page,timeout=45000):
    from patchright.async_api import TimeoutError as BrowserTimeoutError
    from utils.publish_jobs import report_stage
    report_stage('读取快手合集资料，等待管理页面加载',75)
    try:
        menu=page.locator('.el-submenu__title').filter(has_text='内容管理').first
        await menu.wait_for(state='visible',timeout=timeout)
        await page.locator('.el-loading-mask.is-fullscreen:visible,.el-loading-mask.loading-h5:visible').first.wait_for(state='hidden',timeout=timeout)
        await menu.click(timeout=timeout)
    except BrowserTimeoutError as error:
        from utils.publish_diagnostics import capture_editor_failure
        path=await capture_editor_failure(page,'kuaishou','collection-loading')
        raise RuntimeError(f'快手合集页面加载超时，加载遮罩或内容管理菜单尚未就绪；请稍后重试。页面截图：{path}') from error


async def open_collection(context, name, collection_id=None):
    page=await context.new_page()
    info={};rows={};catalog=[]
    async def response_handler(response):
        path=urlsplit(response.url).path
        if path not in ('/rest/cp/works/v2/collection/list','/rest/cp/works/v2/collection/info','/rest/cp/works/v2/collection/unrecorded/list/v2'):return
        try:
            payload=await response.json()
            if payload.get('result')!=1:return
            data=payload.get('data') or {}
            if path.endswith('/collection/list'):catalog.extend(data.get('list',[]))
            elif path.endswith('/collection/info'):info.update(data)
            else:
                for row in data.get('list',[]):rows[str(row['photoId'])]=row
        except Exception:pass
    page.on('response',response_handler)
    try:
        await page.goto('https://cp.kuaishou.com/article/publish/video',wait_until='domcontentloaded',timeout=60000)
        await open_content_management(page)
        async with page.expect_response(lambda r:urlsplit(r.url).path.endswith('/collection/list')):
            await page.get_by_text('合集管理',exact=True).first.click()
        await page.wait_for_timeout(300)
        matches=[r for r in catalog if r.get('title')==name and (not collection_id or str(r.get('collectionId'))==str(collection_id))]
        if len(matches)!=1:raise RuntimeError('合集不存在或名称不唯一，请刷新合集后核对')
        target=matches[0]
        async with page.expect_response(lambda r:urlsplit(r.url).path.endswith('/collection/info')):
            await page.get_by_text(name,exact=True).first.click()
        await page.wait_for_timeout(300)
        if str(info.get('collectionId'))!=str(target['collectionId']):raise RuntimeError('合集身份校验失败')
        trigger=page.locator('.continue-add-btn')
        if not await trigger.count():trigger=page.get_by_text('上传视频',exact=True)
        async with page.expect_response(lambda r:urlsplit(r.url).path.endswith('/collection/unrecorded/list/v2')):
            await trigger.first.click()
        await page.wait_for_timeout(300)
        return page,info,rows
    except Exception:
        await page.close();raise

async def prepare(context, name):
    page,info,rows=await open_collection(context,name)
    try:
        from utils.publish_jobs import report_phase
        report_phase('collection','completed','合集资料已读取，发布后关联结果另行跟踪')
        return str(info['collectionId']),set(rows)|{str(x) for x in info.get('photoIdList',[])}
    finally:await page.close()

async def associate(context, task):
    page,info,rows=await open_collection(context,task['collection_name'],task['collection_id'])
    try:
        existing={str(x) for x in info.get('photoIdList',[])}
        if task.get('photo_id') in existing:return True
        # Scroll the actual official picker so requests retain the platform's signing.
        for _ in range(50):
            before=len(rows)
            await page.locator('.video-drawer-list').evaluate('el=>{el.scrollTop=el.scrollHeight}')
            await page.wait_for_timeout(800)
            if len(rows)==before:break
        else:raise RuntimeError('作品列表过长，无法安全确认本次作品，请到快手核对')
        work=select_work(list(rows.values()),task)
        if not work:return False
        photo_id=str(work['photoId'])
        update(task['id'],photo_id=photo_id)
        if photo_id in existing:return True
        if not work.get('available'):return False
        # The server's unique photo ID binds to its unique cover URL in this picker.
        cards=page.locator('.video-list-drawer .video-item')
        indexes=await cards.evaluate_all('(els,src)=>els.map((el,i)=>el.querySelector(".video-item__cover img")?.src===src?i:-1).filter(i=>i>=0)',work.get('coverUrl'))
        if len(indexes)!=1:raise RuntimeError('无法唯一定位本次作品，已停止加入合集；不会重新上传')
        card=cards.nth(indexes[0])
        if 'video-item--disabled' in (await card.get_attribute('class') or ''):return False
        await card.locator('.video-item__control__add-btn').click()
        # Click the drawer backdrop, never a work thumbnail (which opens playback).
        await page.locator('.video-list-drawer').click(position={'x':2,'y':2})
        async with page.expect_response(lambda r:urlsplit(r.url).path.endswith('/collection/update')) as saved:
            await page.get_by_role('button',name='修改',exact=True).click()
        result=await (await saved.value).json()
        if result.get('result')!=1:raise RuntimeError('平台未确认合集保存成功，请稍后重试加入合集')
    finally:await page.close()
    check,verified,_=await open_collection(context,task['collection_name'],task['collection_id'])
    try:
        if photo_id not in {str(x) for x in verified.get('photoIdList',[])}:return False
        if not existing.issubset({str(x) for x in verified.get('photoIdList',[])}):raise RuntimeError('合集原有作品发生变化，请到快手核对')
        return True
    finally:await check.close()

async def run_once(task):
    from uploader.ks_uploader.main import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            context=await browser.new_context(storage_state=task['cookie'])
            return await associate(context,task)
        finally:await browser.close()

def start(task_id):
    with _lock:
        if task_id in _active:return False
        task=get(task_id)
        if not task or task['status'] in ('completed','prepared'):return False
        _active.add(task_id)
    def worker():
        try:
            for attempt in range(6):
                task=get(task_id)
                update(task_id,status='running',message='视频已提交，正在检查作品并加入合集；不会重新上传')
                try:
                    with _browser_slot:
                        completed=asyncio.run(run_once(task))
                    if completed:
                        update(task_id,status='completed',message='视频已加入所选合集');return
                    update(task_id,status='waiting',message='视频已提交，作品审核中或尚不可加入合集，稍后自动重试')
                except RuntimeError as error:
                    update(task_id,status='failed',message=str(error));return
                except Exception:
                    update(task_id,status='waiting',message='视频已提交，暂未确认加入合集，稍后重试；不会重新上传')
                if attempt<5:time.sleep(30)
            update(task_id,status='failed',message='视频已提交，加入合集暂未完成；可仅重试加入合集，请勿重新上传视频')
        finally:
            with _lock:_active.discard(task_id)
    threading.Thread(target=worker,daemon=True,name='ks-collection-'+task_id[:8]).start()
    return True

def resume():
    with closing(connect()) as db:ids=[r[0] for r in db.execute("SELECT id FROM ks_collection_tasks WHERE status IN ('waiting','running')")]
    for task_id in ids:start(task_id)
