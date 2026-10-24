import unittest
from unittest.mock import MagicMock,AsyncMock
from utils.publish_jobs import create_job,bind_job,read_job,report_stage
from utils.upload_progress import report_upload_wait
class UploadProgressTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from utils import publish_jobs
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
  isolated=patch.object(publish_jobs,'_store',publish_jobs.JobStore(Path(temporary.name)/'jobs.db'))
  isolated.start();self.addCleanup(isolated.stop)
 def tearDown(self):bind_job(None)
 async def test_real_percent_and_non_upload_stage(self):
  job=create_job(3);bind_job(job);page=MagicMock();page.locator.return_value.evaluate_all=AsyncMock(return_value=[{'value':None,'text':'视频上传 67%'}])
  await report_upload_wait(page);state=read_job(job)
  self.assertEqual(state['uploadPercent'],67);self.assertEqual(state['progress'],55);self.assertTrue(state['uploadWaiting'])
  report_stage('设置封面',70);self.assertTrue(read_job(job)['uploadWaiting']);self.assertEqual(read_job(job)['uploadPercent'],67);self.assertEqual(read_job(job)['stage'],'设置封面')
 async def test_no_platform_percent_is_not_invented(self):
  job=create_job(4);bind_job(job);page=MagicMock();page.locator.return_value.evaluate_all=AsyncMock(return_value=[])
  await report_upload_wait(page);state=read_job(job)
  self.assertIsNone(state['uploadPercent']);self.assertIn('已等待',state['stage']);self.assertEqual(state['progress'],35)
