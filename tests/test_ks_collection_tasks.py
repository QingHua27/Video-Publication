import unittest,tempfile,json,time
from pathlib import Path
from unittest.mock import patch
from utils import ks_collection_tasks as ks

class DeferredCollections(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.patch=patch.object(ks,'_DB',Path(self.tmp.name)/'test.db');self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def task(self):
  return ks.get(ks.create('job','private-cookie','合集','123','第一章',['10'],100,200))
 def row(self,id='11',title='第一章\n #文学',at=150000):return {'photoId':id,'title':title,'publishTime':at,'available':True}
 def test_prepared_is_not_auto_resumed(self):
  t=self.task();self.assertEqual(t['status'],'prepared')
  with patch.object(ks,'start') as start:ks.resume();start.assert_not_called()
 def test_exact_new_title_and_submission_window(self):
  t=self.task();r=self.row();self.assertEqual(ks.select_work([r],t),r)
  self.assertIsNone(ks.select_work([self.row(id='10')],t))
  self.assertIsNone(ks.select_work([self.row(title='第一章预览')],t))
  self.assertIsNone(ks.select_work([self.row(at=999000)],t))
 def test_ambiguous_title_never_guesses(self):
  with self.assertRaises(RuntimeError):ks.select_work([self.row(),self.row(id='12')],self.task())
 def test_bound_id_is_used_after_retry(self):
  t=self.task();ks.update(t['id'],photo_id='11',status='waiting');t=ks.get(t['id'])
  self.assertEqual(ks.select_work([self.row(),self.row(id='12')],t)['photoId'],'11')
 def test_public_status_has_no_cookie_or_paths(self):
  t=self.task();self.assertNotIn('cookie',ks.public(t));self.assertNotIn('baseline',ks.public(t))
 def test_already_associated_task_cannot_restart(self):
  t=self.task();ks.update(t['id'],status='completed');self.assertFalse(ks.start(t['id']))
 def test_api_recovery_and_retry_do_not_dispatch_upload(self):
  import sau_backend
  t=self.task();ks.update(t['id'],status='failed')
  client=sau_backend.app.test_client()
  with patch.object(sau_backend,'read_job',return_value=None):
   result=client.get('/publishJob?id=job')
   self.assertTrue(result.json['data']['videoSubmitted'])
   self.assertEqual(result.json['data']['collectionTask']['status'],'failed')
  with patch.object(ks,'start') as start,patch.object(sau_backend,'post_video_ks') as upload:
   self.assertEqual(client.post('/retryKuaishouCollection',json={'id':t['id']}).status_code,403)
   response=client.post('/retryKuaishouCollection',json={'id':t['id']},headers={'X-OmniPost-Local':'1','Origin':'http://127.0.0.1:5173'})
   self.assertEqual(response.status_code,200);start.assert_called_once_with(t['id']);upload.assert_not_called()
 def test_retry_worker_only_calls_association(self):
  t=self.task();ks.update(t['id'],status='waiting')
  async def done(task):return True
  with patch.object(ks,'run_once',side_effect=done):
   self.assertTrue(ks.start(t['id']))
   for _ in range(100):
    if ks.get(t['id'])['status']=='completed':break
    time.sleep(.01)
   self.assertEqual(ks.get(t['id'])['status'],'completed')

if __name__=='__main__':unittest.main()
