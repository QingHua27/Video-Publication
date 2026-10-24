import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from utils import publish_jobs as jobs
class PhaseTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  store=jobs.JobStore(Path(self.temp.name)/'jobs.db');mock=patch.object(jobs,'_store',store);mock.start();self.addCleanup(mock.stop)
  self.key=jobs.create_job(1);jobs.bind_job(self.key);self.addCleanup(lambda:jobs.bind_job(None));jobs.update_job(self.key,'running','start')
 def test_upload_observer_cannot_replace_active_cover_or_collection(self):
  jobs.report_upload_progress(42)
  with jobs.phase_scope('cover'):jobs.report_stage('设置封面',35)
  jobs.report_upload_progress(67)
  state=jobs.read_job(self.key)
  self.assertEqual(state['stage'],'设置封面');self.assertEqual(state['phases']['upload']['progress'],67)
  self.assertEqual(state['phases']['cover']['status'],'running');self.assertTrue(state['uploadWaiting'])
  jobs.report_phase('cover','completed','封面已完成')
  with jobs.phase_scope('collection'):jobs.report_stage('读取合集',75)
  jobs.report_upload_progress(80)
  self.assertEqual(jobs.read_job(self.key)['stage'],'读取合集')
 def test_terminal_task_stays_failed_even_if_observer_reports_late(self):
  jobs.report_phase('cover','failed','封面保存失败')
  jobs.update_job(self.key,'failed','封面保存失败')
  jobs.report_upload_progress(99)
  state=jobs.read_job(self.key)
  self.assertEqual(state['stage'],'封面保存失败');self.assertEqual(state['phases']['cover']['status'],'failed')
 def test_phase_state_is_preserved_after_restart(self):
  jobs.report_phase('cover','running','等待封面编辑器')
  recovered=jobs.JobStore(jobs.job_store().path).get(self.key)
  self.assertEqual(recovered['phases']['cover']['status'],'interrupted');self.assertTrue(recovered['resultUncertain'])

 def test_concurrent_video_observer_keeps_its_own_phase_scope(self):
  import asyncio
  from utils.early_video_cover import prepare_video_and_cover
  async def check():
   cover_started=asyncio.Event();observer_reported=asyncio.Event();cover_done=asyncio.Event()
   async def upload():
    await cover_started.wait();jobs.report_stage('等待视频上传完成',35);jobs.report_upload_progress(64);observer_reported.set();await cover_done.wait()
   async def ready():return True
   async def cover():
    jobs.report_stage('正在确认封面',35);cover_started.set();await observer_reported.wait()
    state=jobs.read_job(self.key);self.assertEqual(state['stage'],'正在确认封面');self.assertEqual(state['phases']['upload']['progress'],64)
    cover_done.set()
   await prepare_video_and_cover(upload,ready,cover,poll_interval=.001)
   state=jobs.read_job(self.key);self.assertEqual(state['phases']['upload']['status'],'completed');self.assertEqual(state['phases']['cover']['status'],'completed')
  asyncio.run(check())
