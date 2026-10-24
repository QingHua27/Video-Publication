"""Temporarily reveal only the native Chromium window owned by a publishing job."""
import ctypes
import os
import threading
from utils.publish_jobs import current_job_id, set_window_state

_lock=threading.Lock()
_controllers={}


def native_windows(pid):
 from ctypes import wintypes
 user=ctypes.windll.user32
 callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
 user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
 user.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
 result=[]
 @callback_type
 def visit(hwnd,_):
  owner=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
  if owner.value==pid:
   name=ctypes.create_unicode_buffer(256);user.GetClassNameW(hwnd,name,256)
   if name.value=='Chrome_WidgetWin_1':result.append(hwnd)
  return True
 user.EnumWindows(visit,0)
 return result


def apply_visibility(pid,visible):
 from ctypes import wintypes
 user=ctypes.windll.user32
 user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
 user.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_uint]
 user.SetForegroundWindow.argtypes=[wintypes.HWND]
 for hwnd in native_windows(pid):
  if visible:
   user.SetWindowPos(hwnd,None,100,70,1200,800,0x0014)
   user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd)
  else:user.ShowWindow(hwnd,0)


def start_controller(job_id,pid,browser):
 state={'pid':pid,'visible':False,'stop':threading.Event()}
 with _lock:_controllers[job_id]=state
 set_window_state(job_id,True,False)
 def closed(*_):
  state['stop'].set()
  with _lock:
   if _controllers.get(job_id) is state:_controllers.pop(job_id,None)
  set_window_state(job_id,False,False)
 browser.on('disconnected',closed)
 def watch():
  while not state['stop'].wait(.05):
   with _lock:
    if _controllers.get(job_id) is not state:return
    if not state['visible']:apply_visibility(pid,False)
 threading.Thread(target=watch,daemon=True).start()


def set_visible(job_id,visible):
 with _lock:
  state=_controllers.get(job_id)
  if not state or state['stop'].is_set():raise ValueError('该任务没有可显示的页面，旧任务需结束后重新执行')
  apply_visibility(state['pid'],visible)
  state['visible']=visible
 set_window_state(job_id,True,visible)


async def launch_browser(chromium,**options):
 job_id=current_job_id()
 if os.name!='nt' or not job_id or not options.get('headless'):
  return await chromium.launch(**options)
 options=dict(options,headless=False,args=[*options.get('args',[]),'--window-position=-32000,-32000','--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding'])
 browser=await chromium.launch(**options)
 try:
  session=await browser.new_browser_cdp_session()
  processes=await session.send('SystemInfo.getProcessInfo')
  pid=next(int(p['id']) for p in processes['processInfo'] if p['type']=='browser')
  await session.detach()
  start_controller(job_id,pid,browser)
 except Exception:
  await browser.close()
  raise
 return browser
