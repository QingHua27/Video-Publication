import sqlite3
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from utils import publish_history as history


class PublishHistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.root=Path(self.directory.name)
        (self.root/'db').mkdir()
        with closing(sqlite3.connect(self.root/'db/database.db')) as db:
            db.execute('CREATE TABLE file_records(filename TEXT,file_path TEXT,section_id INTEGER)')
            db.execute('CREATE TABLE material_sections(id INTEGER,name TEXT)')
            db.executemany('INSERT INTO material_sections VALUES(?,?)',[(1,'剧A'),(2,'剧B')])
            db.executemany('INSERT INTO file_records VALUES(?,?,?)',[
                ('第二集.mp4','a.mp4',1),('第2集_预览.mp4','alternate.mp4',1),('第二集.mp4','b.mp4',2)])
            db.commit()

    def tearDown(self):self.directory.cleanup()

    def reserve(self,**kwargs):
        values=dict(root=self.root,platform=3,accounts=['account'],files=['a.mp4'],title='标题',job_id='job')
        values.update(kwargs);return history.reserve(**values)

    def test_same_episode_versions_block_but_series_accounts_and_platforms_are_independent(self):
        self.reserve()
        with self.assertRaises(history.DuplicatePublication):self.reserve(files=['alternate.mp4'])
        self.reserve(files=['b.mp4']);self.reserve(platform=4);self.reserve(accounts=['other'])
        self.assertEqual(len(history.list_records(self.root)),4)

    def test_submitted_and_manual_publication_remain_blocked_after_reopen(self):
        ids=self.reserve();history.finish(self.root,ids,'submitted','待核对')
        with self.assertRaises(history.DuplicatePublication):self.reserve()
        history.reconcile(self.root,ids[0],'published',lambda job:None)
        with self.assertRaises(history.DuplicatePublication):self.reserve()
        history.reconcile(self.root,ids[0],'cleared',lambda job:None)
        self.reserve(manual=True)
        self.assertEqual(history.list_records(self.root)[0]['status'],'published')

    def test_only_one_concurrent_submission_reserves_episode(self):
        # Initialize schema before racing two independent connections.
        history.list_records(self.root)
        def reserve_once(n):
            try:self.reserve(job_id=str(n));return True
            except history.DuplicatePublication:return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(reserve_once,[1,2])),1)

    def test_active_task_cannot_be_unblocked(self):
        ids=self.reserve()
        with self.assertRaisesRegex(ValueError,'仍在执行'):
            history.reconcile(self.root,ids[0],'cleared',lambda job:{'status':'running'})
        self.assertEqual(history.list_records(self.root)[0]['status'],'pending')

    def test_explicit_repeat_confirmation_allows_retry_but_not_active_task(self):
        ids=self.reserve();history.finish(self.root,ids,'needs_review','已取消')
        with self.assertRaises(history.DuplicatePublication):self.reserve()
        new_ids=self.reserve(allow_repeat=True,job_reader=lambda job:None)
        self.assertEqual(history.list_records(self.root)[0]['id'],new_ids[0])
        with self.assertRaisesRegex(ValueError,'仍在执行'):
            self.reserve(allow_repeat=True,job_reader=lambda job:{'status':'running'})

    def test_duplicate_rolls_back_entire_batch(self):
        self.reserve(accounts=['second'])
        with self.assertRaises(history.DuplicatePublication):self.reserve(accounts=['first','second'])
        self.assertEqual(len(history.list_records(self.root)),1)

    def test_unknown_series_does_not_confuse_different_files_numbered_episode_one(self):
        self.reserve(files=['第一集-A.mp4'])
        self.reserve(files=['第一集-B.mp4'])
        with self.assertRaises(history.DuplicatePublication):self.reserve(files=['第一集-A.mp4'])


class PublishHistoryApiTests(unittest.TestCase):
    def setUp(self):
        PublishHistoryTests.setUp(self)
        import sau_backend
        self.backend=sau_backend
        (self.root/'videoFile').mkdir();(self.root/'cookiesFile').mkdir()
        (self.root/'videoFile/a.mp4').write_bytes(b'fixture-video')
        for cookie in ('account','ks'):(self.root/'cookiesFile'/cookie).write_text('{}')
        from utils import publish_jobs
        self.jobs_patch=patch.object(publish_jobs,'_store',publish_jobs.JobStore(self.root/'db/jobs-test.db'));self.jobs_patch.start()

        with closing(sqlite3.connect(self.root/'db/database.db')) as db:
            db.execute('CREATE TABLE user_info(id INTEGER,type INTEGER,filePath TEXT)')
            db.executemany('INSERT INTO user_info VALUES(?,?,?)',[(3,3,'account'),(4,4,'ks')]);db.commit()
        self.base_patch=patch.object(sau_backend,'BASE_DIR',self.root);self.base_patch.start()
        class InlineThread:
            def __init__(self,target,**kwargs):self.target=target
            def start(self):self.target()
        self.thread_patch=patch.object(sau_backend.threading,'Thread',InlineThread);self.thread_patch.start()
        self.client=sau_backend.app.test_client()

    def tearDown(self):
        self.thread_patch.stop();self.base_patch.stop();self.jobs_patch.stop();PublishHistoryTests.tearDown(self)

    def payload(self):
        return dict(type=3,fileList=['a.mp4'],accountList=['account'],title='剧A-第二集',tags=[],
                    videosPerDay=1,dailyTimes=['10:00'],startDays=0,enableTimer=0)

    def test_real_submission_blocks_duplicates_but_preview_does_not_write(self):
        payload=self.payload()
        with patch.object(self.backend,'post_video_DouYin') as uploader:
            response=self.client.post('/postVideo',json={**payload,'dryRun':True})
            self.assertEqual(response.status_code,200)
            self.assertEqual(history.list_records(self.root),[])
            self.assertEqual(self.client.post('/postVideo',json=payload).status_code,200)
            self.assertEqual(history.list_records(self.root)[0]['status'],'submitted')
            self.assertEqual(self.client.post('/postVideo',json=payload).status_code,409)
            self.assertEqual(uploader.call_count,2)

    def test_unknown_failure_requires_reconciliation_before_retry(self):
        with patch.object(self.backend,'post_video_DouYin',side_effect=RuntimeError('提交结果不确定')):
            self.client.post('/postVideo',json=self.payload())
        row=history.list_records(self.root)[0]
        self.assertEqual(row['status'],'needs_review')
        self.assertEqual(self.client.post('/postVideo',json=self.payload()).status_code,409)
        response=self.client.post('/publishHistory',json={'id':row['id'],'status':'cleared'},
                                  headers={'Origin':'http://127.0.0.1:5173','X-OmniPost-Local':'1'})
        self.assertEqual(response.status_code,200,response.json)
        with patch.object(self.backend,'post_video_DouYin'):
            self.assertEqual(self.client.post('/postVideo',json=self.payload()).status_code,200)

    def test_manual_publication_blocks_only_selected_account(self):
        response=self.client.post('/publishHistory',json={'action':'manual','accountId':4,'fileList':['a.mp4']},
                                  headers={'Origin':'http://127.0.0.1:5173','X-OmniPost-Local':'1'})
        self.assertEqual(response.status_code,200,response.json)
        payload={**self.payload(),'type':4,'accountList':['ks']}
        self.assertEqual(self.client.post('/postVideo',json=payload).status_code,409)
        with patch.object(self.backend,'post_video_DouYin'):
            self.assertEqual(self.client.post('/postVideo',json=self.payload()).status_code,200)
