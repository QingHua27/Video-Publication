"""One browser session for Channels across publishing, checks and manual use."""
import threading,asyncio
from contextlib import contextmanager
from functools import wraps

_lock=threading.Lock()
_owner=None
class SessionBusy(RuntimeError):pass

def session_owner():
 return dict(_owner) if _owner else None

@contextmanager
def channels_session(cookie,purpose):
 global _owner
 try:task=asyncio.current_task()
 except RuntimeError:task=None
 identity=(threading.get_ident(),task)
 if _owner and _owner.get('_identity')==identity:
  yield;return
 if not _lock.acquire(blocking=False):
  owner=session_owner() or {}
  raise SessionBusy('视频号正在'+owner.get('purpose','使用')+'，请先关闭后台页面或等待当前操作结束，避免登录状态互相覆盖')
 try:
  from utils.publish_jobs import current_job_id
  _owner={'cookie':str(cookie),'purpose':purpose,'jobId':current_job_id(),'_identity':identity}
  yield
 finally:
  _owner=None;_lock.release()

def exclusive_channels(purpose,cookie_arg=0):
 def decorate(fn):
  @wraps(fn)
  async def wrapped(*args,**kwargs):
   value=args[cookie_arg] if len(args)>cookie_arg else kwargs.get('account_file','')
   if hasattr(value,'account_file'):value=value.account_file
   with channels_session(value,purpose):return await fn(*args,**kwargs)
  return wrapped
 return decorate
