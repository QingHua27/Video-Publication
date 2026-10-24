import concurrent.futures,tempfile,unittest
from pathlib import Path
from utils import publish_jobs
class DurableJobTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'jobs.db'
 def tearDown(self):self.temp.cleanup()
 def test_restart_keeps_material_stage_and_marks_active_result_uncertain(self):
  first=publish_jobs.JobStore(self.path)
  key,created=first.claim(1,{'title':'外婆第25章','fileList':['episode25.mp4'],'accounts':['xhs.json']},'request-1','digest')
  first.update(key,status='running',message='上传中',stage='设置封面',progress=45,windowAvailable=True)
  completed,_=first.claim(3,{'title':'已完成'})
  first.update(completed,status='completed',message='流程结束',progress=100)
  restarted=publish_jobs.JobStore(self.path)
  job=restarted.get(key)
  self.assertEqual(job['title'],'外婆第25章');self.assertEqual(job['progress'],45);self.assertEqual(job['stage'],'设置封面')
  self.assertEqual(job['status'],'failed');self.assertTrue(job['resultUncertain']);self.assertFalse(job['windowAvailable'])
  self.assertEqual(restarted.get(completed)['status'],'completed')
  existing,new=restarted.claim(1,{'title':'外婆第25章'},'request-1','digest');self.assertEqual(existing,key);self.assertFalse(new)
 def test_concurrent_identical_requests_have_one_job_and_mismatched_reuse_is_rejected(self):
  store=publish_jobs.JobStore(self.path)
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   results=list(pool.map(lambda _:store.claim(1,{},'same','digest'),range(20)))
  self.assertEqual(len({key for key,_ in results}),1);self.assertEqual(sum(created for _,created in results),1)
  with self.assertRaises(ValueError):store.claim(3,{},'same','other')
 def test_updates_and_history_are_copied_and_persisted(self):
  store=publish_jobs.JobStore(self.path);key,_=store.claim(4,{'fileList':['first.mp4']})
  store.update(key,status='failed',message='封面不存在',stage='检查素材',progress=5)
  job=store.get(key);job['fileList'][0]='changed.mp4'
  self.assertEqual(store.get(key)['fileList'],['first.mp4'])
  self.assertEqual(publish_jobs.JobStore(self.path).list()[0]['message'],'封面不存在')
