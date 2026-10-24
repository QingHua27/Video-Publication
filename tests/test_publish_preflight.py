import json,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from PIL import Image
from utils.publish_preflight import preflight_publish
from utils import publish_history
class PreflightTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  for name in ('db','videoFile','cookiesFile'):(self.root/name).mkdir()
  with closing(sqlite3.connect(self.root/'db/database.db')) as db:
   db.execute('CREATE TABLE user_info(id INTEGER PRIMARY KEY,type INTEGER,filePath TEXT)');db.execute("INSERT INTO user_info VALUES(1,1,'xhs.json')")
   db.execute('CREATE TABLE file_records(id INTEGER PRIMARY KEY,filename TEXT,file_path TEXT,section_id INTEGER)');db.commit()
  self.video=self.root/'videoFile/第25章.mp4';self.video.write_bytes(b'nonempty-video')
  self.cover=self.root/'videoFile/第25章_3比4.png';Image.new('RGB',(300,400)).save(self.cover)
  (self.root/'cookiesFile/xhs.json').write_text(json.dumps({'cookies':[],'origins':[]}))
  self.payload={'type':1,'fileList':[self.video.name],'accountList':['xhs.json'],'thumbnail':self.cover.name,'title':'外婆第25章'}
 def test_valid_inputs_do_not_create_or_reserve_publication_records(self):
  result=preflight_publish(self.root,self.payload)
  self.assertTrue(result['ok'],result)
  with closing(sqlite3.connect(self.root/'db/database.db')) as db:
   self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='publish_history'").fetchone())
 def test_collects_missing_video_corrupt_cookie_and_cover_episode_mismatch(self):
  (self.root/'cookiesFile/xhs.json').write_text('broken json')
  other=self.root/'videoFile/第26章_3比4.png';Image.new('RGB',(300,400)).save(other)
  result=preflight_publish(self.root,{**self.payload,'fileList':['missing.mp4',self.video.name],'thumbnail':other.name})
  self.assertFalse(result['ok']);text=' '.join(result['errors'])
  self.assertIn('视频',text);self.assertIn('登录文件',text);self.assertIn('集数',text)
 def test_wrong_cover_orientation_blocks_but_unknown_login_does_not_claim_online_validity(self):
  Image.new('RGB',(400,300)).save(self.cover)
  result=preflight_publish(self.root,self.payload);self.assertFalse(result['ok']);self.assertIn('竖版',' '.join(result['errors']))
 def test_duplicate_is_warning_without_mutation_and_active_job_cannot_be_overridden(self):
  publish_history.reserve(self.root,1,['xhs.json'],[self.video.name],'标题','old-job',manual=True)
  before=publish_history.list_records(self.root)
  report=preflight_publish(self.root,self.payload)
  self.assertTrue(report['ok']);self.assertTrue(report['confirmRepeatRequired']);self.assertTrue(report['warnings'])
  self.assertEqual(publish_history.list_records(self.root),before)
  active=preflight_publish(self.root,{**self.payload,'confirmRepeat':True},job_reader=lambda _: {'status':'running'})
  self.assertFalse(active['ok']);self.assertIn('执行',' '.join(active['errors']))
 def test_manual_xhs_does_not_require_cookie_but_still_checks_assets_and_account(self):
  (self.root/'cookiesFile/xhs.json').unlink()
  self.assertTrue(preflight_publish(self.root,self.payload,manual=True)['ok'])
  self.assertFalse(preflight_publish(self.root,self.payload)['ok'])
  self.video.unlink();self.assertFalse(preflight_publish(self.root,self.payload,manual=True)['ok'])

 def test_api_preflight_is_local_only_and_direct_submission_cannot_bypass_errors(self):
  from unittest.mock import patch
  import sau_backend
  from utils import publish_jobs
  with patch.object(sau_backend,'BASE_DIR',self.root),patch.object(publish_jobs,'_store',publish_jobs.JobStore(self.root/'db/jobs-test.db')),patch.object(sau_backend,'post_video_xhs') as upload,patch.object(sau_backend.threading,'Thread') as thread:
   client=sau_backend.app.test_client();headers={'X-OmniPost-Local':'1','Origin':'http://127.0.0.1:5173'}
   self.assertEqual(client.post('/publishPreflight',json=self.payload).status_code,403)
   checked=client.post('/publishPreflight',json=self.payload,headers=headers)
   self.assertTrue(checked.json['data']['ok'],checked.json)
   self.assertEqual(publish_jobs.list_jobs(),[])
   self.video.unlink()
   failed=client.post('/postVideo',json=self.payload)
   self.assertEqual(failed.status_code,422,failed.json);upload.assert_not_called();thread.assert_not_called()
   self.assertFalse(failed.json['data']['preflight']['ok'])
