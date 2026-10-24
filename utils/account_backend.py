"""Account-isolated creator windows; browser automation stays on its owner thread."""
import asyncio,json,os,threading
from pathlib import Path
from contextlib import nullcontext
from utils.channels_session import channels_session,session_owner,SessionBusy
from utils.collection_catalog import browser_storage_state

URLS={1:'https://creator.xiaohongshu.com/',2:'https://channels.weixin.qq.com/platform',3:'https://creator.douyin.com/',4:'https://cp.kuaishou.com/',5:'https://baijiahao.baidu.com/builder/rc/home',6:'https://member.bilibili.com/platform/home',7:'https://mp.toutiao.com/profile_v4/index',8:'https://mp.sohu.com/mpfe/v4/contentManagement/news',9:'https://www.zhihu.com/creator'}
_lock=threading.Lock();_windows={}

def cookie_path(root,filename):
 base=(Path(root)/'cookiesFile').resolve();path=(base/filename).resolve()
 if path.parent!=base:raise ValueError('账号登录文件路径无效')
 if not path.is_file():raise ValueError('登录文件不存在，请先重新登录该账号')
 return path

def save_browser_state(path,platform,state):
 if platform==6:
  original=json.loads(path.read_text(encoding='utf-8'))
  if 'cookie_info' in original:
   cookies=[c for c in state.get('cookies',[]) if c.get('domain','').lstrip('.').endswith('bilibili.com')]
   original['cookie_info']['cookies']=cookies;state=original
 temp=path.with_name(path.name+'.backend.tmp')
 temp.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8');os.replace(temp,path)

def open_backend(root,account_id,platform,filename):
 if platform not in URLS:raise ValueError('该平台暂不支持打开后台')
 path=cookie_path(root,filename);key=str(path)
 with _lock:
  existing=_windows.get(key)
  if existing:
   existing['focus'].set();state=existing
  else:
   if platform==2:
    owner=session_owner()
    if owner:
     if owner.get('cookie')==key and owner.get('jobId'):
      from utils.publish_windows import set_visible
      set_visible(owner['jobId'],True)
      return {'reused':True,'message':'已显示视频号当前发布页面，请勿同时进入其他发布页'}
     raise SessionBusy('视频号正在'+owner.get('purpose','使用')+'，请等待结束后再打开后台')
   state={'ready':threading.Event(),'focus':threading.Event(),'error':None,'path':path,'platform':platform}
   _windows[key]=state
   threading.Thread(target=_run,args=(key,state),daemon=True).start()
 if not state['ready'].wait(25):raise RuntimeError('后台页面仍在打开，请稍后再点；重复点击会复用原窗口')
 if state['error']:raise RuntimeError(state['error'])
 return {'reused':existing is not None,'message':'已显示已有后台窗口' if existing else '已使用保存的登录状态打开后台；使用结束请关闭窗口'}

def _run(key,state):
 try:
  with channels_session(key,'手动后台') if state['platform']==2 else nullcontext():
   asyncio.run(_browse(state))
 except Exception as problem:
  # Do not include cookies or browser diagnostics in API responses.
  state['error']=str(problem) if isinstance(problem,(ValueError,SessionBusy)) else '打开后台失败，请检查浏览器和账号登录文件'
 finally:
  state['ready'].set()
  with _lock:
   if _windows.get(key) is state:_windows.pop(key,None)

async def _browse(state):
 from playwright.async_api import async_playwright
 from conf import LOCAL_CHROME_PATH
 path=state['path'];platform=state['platform'];storage=browser_storage_state(platform,path)
 stamp=path.stat().st_mtime_ns
 async with async_playwright() as p:
  options={'headless':False}
  if LOCAL_CHROME_PATH:options['executable_path']=LOCAL_CHROME_PATH
  else:options['channel']='chrome'
  browser=await p.chromium.launch(**options)
  try:
   context=await browser.new_context(storage_state=storage)
   page=await context.new_page()
   if platform==2:
    async def block_extra(extra):
     if extra!=page:await extra.close()
    context.on('page',block_extra)
   await page.goto(URLS[platform],wait_until='domcontentloaded',timeout=20000)
   ticks=0
   async def save():
    nonlocal stamp
    # Cookie imports/relogins win; never overwrite a newer external state.
    if path.exists() and path.stat().st_mtime_ns==stamp:
     saved=await context.storage_state();save_browser_state(path,platform,saved);stamp=path.stat().st_mtime_ns
   await save()
   state['ready'].set()
   while browser.is_connected() and context.pages:
    if state['focus'].is_set():
     state['focus'].clear()
     await context.pages[0].bring_to_front()
    await asyncio.sleep(.25);ticks+=1
    if ticks%4==0:await save()
   if browser.is_connected():await save()
  finally:
   await browser.close()
