import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from utils import publish_windows as windows
from utils.publish_jobs import bind_job, create_job, read_job

class WindowTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from utils import publish_jobs
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
  isolated=patch.object(publish_jobs,'_store',publish_jobs.JobStore(Path(temporary.name)/'jobs.db'))
  isolated.start();self.addCleanup(isolated.stop)
 async def test_publish_is_headed_offscreen_and_registered(self):
  key=create_job(1);bind_job(key)
  browser=MagicMock();session=AsyncMock();session.send.return_value={'processInfo':[{'type':'browser','id':123}]};browser.new_browser_cdp_session=AsyncMock(return_value=session)
  chromium=MagicMock();chromium.launch=AsyncMock(return_value=browser)
  try:
   with patch.object(windows.os,'name','nt'),patch.object(windows,'start_controller') as start:
    await windows.launch_browser(chromium,headless=True,channel='chrome')
    self.assertFalse(chromium.launch.call_args.kwargs['headless']);self.assertIn('--window-position=-32000,-32000',chromium.launch.call_args.kwargs['args']);start.assert_called_once_with(key,123,browser)
  finally:bind_job(None)
 async def test_login_remains_unchanged(self):
  bind_job(None);chromium=MagicMock();chromium.launch=AsyncMock()
  await windows.launch_browser(chromium,headless=True)
  chromium.launch.assert_awaited_once_with(headless=True)
 def test_missing_window_rejected(self):
  with self.assertRaises(ValueError):windows.set_visible('missing',True)

 def test_toggle_only_registered_job_and_update_status(self):
  import threading
  key=create_job(1);other=create_job(3)
  state={'pid':444,'visible':False,'stop':threading.Event()}
  with patch.dict(windows._controllers,{key:state},clear=True),patch.object(windows,'apply_visibility') as apply:
   windows.set_visible(key,True)
   apply.assert_called_once_with(444,True)
   self.assertTrue(read_job(key)['windowVisible'])
   self.assertNotIn('windowVisible',read_job(other))
   windows.set_visible(key,False)
   self.assertFalse(read_job(key)['windowVisible'])
   state['stop'].set()
   with self.assertRaises(ValueError):windows.set_visible(key,True)
