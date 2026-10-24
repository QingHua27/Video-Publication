import unittest
from utils.publish_jobs import create_job,update_job,read_job,bind_job,report_stage
class ProgressTests(unittest.TestCase):
 def setUp(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from utils import publish_jobs
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
  isolated=patch.object(publish_jobs,'_store',publish_jobs.JobStore(Path(temporary.name)/'jobs.db'))
  isolated.start();self.addCleanup(isolated.stop)
 def tearDown(self):bind_job(None)
 def test_failed_retains_real_stage(self):
  jid=create_job(1);bind_job(jid);update_job(jid,'running','checking');report_stage('设置封面',70);update_job(jid,'failed','failed')
  job=read_job(jid);self.assertEqual(job['progress'],70);self.assertEqual(job['stage'],'设置封面')
 def test_completed_is_100(self):
  jid=create_job(3);update_job(jid,'completed','done');self.assertEqual(read_job(jid)['progress'],100)
 def test_queue_zero(self):
  jid=create_job(2);self.assertEqual(read_job(jid)['progress'],0)
if __name__=='__main__':unittest.main()
