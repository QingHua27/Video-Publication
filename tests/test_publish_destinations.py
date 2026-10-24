import json
import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import sau_backend
from myUtils.postVideo import post_video_bilibili
from utils.publish_collections import CollectionSelectionError


class InlineThread:
    def __init__(self, target, **kwargs):
        self.target = target
    def start(self):
        self.target()


class PublishDestinationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / 'db').mkdir()
        (self.root/'videoFile').mkdir();(self.root/'cookiesFile').mkdir()
        (self.root/'videoFile/demo.mp4').write_bytes(b'fixture-video')
        from PIL import Image
        Image.new('RGB',(160,90)).save(self.root/'videoFile/wide.jpg')
        Image.new('RGB',(90,120)).save(self.root/'videoFile/tall.jpg')
        for n in range(1,7):(self.root/f'cookiesFile/{n}.json').write_text('{}')

        conn = sqlite3.connect(self.root / 'db/database.db')
        conn.execute('CREATE TABLE user_info (id INTEGER PRIMARY KEY, type INTEGER, filePath TEXT)')
        conn.executemany('INSERT INTO user_info VALUES(?,?,?)', [(n,n,f'{n}.json') for n in range(1,7)])
        conn.commit(); conn.close()
        self.stack = ExitStack()
        from utils import publish_jobs
        self.stack.enter_context(patch.object(publish_jobs,'_store',publish_jobs.JobStore(self.root/'db/jobs-test.db')))
        self.stack.enter_context(patch.object(sau_backend, 'BASE_DIR', self.root))
        self.stack.enter_context(patch.object(sau_backend.threading, 'Thread', InlineThread))
        self.client = sau_backend.app.test_client()

    def tearDown(self):
        self.stack.close()
        # sqlite transaction contexts in upstream code do not close connections.
        import gc
        gc.collect()
        self.directory.cleanup()

    def payload(self, platform):
        return dict(type=platform, fileList=['demo.mp4'],accountList=[f'{platform}.json'],title='测试视频',tags=[],
                    videosPerDay=1,dailyTimes=['10:00'],startDays=0,enableTimer=0,dryRun=True,
                    collectionName='123' if platform==6 else '准确合集名')

    def test_identical_request_is_dispatched_once_and_history_survives_service_restart(self):
        payload={**self.payload(1),'requestId':'same-request','materialLabel':'外婆 · 第25章','accountLabel':'小红书 · 测试账号'}
        with patch.object(sau_backend,'post_video_xhs') as publish:
            one=self.client.post('/postVideo',json=payload)
            two=self.client.post('/postVideo',json=payload)
            self.assertEqual(one.status_code,200,one.json);self.assertEqual(two.status_code,200,two.json)
            self.assertEqual(one.json['data']['jobId'],two.json['data']['jobId']);publish.assert_called_once()
            conflict=self.client.post('/postVideo',json={**payload,'title':'changed'})
            self.assertEqual(conflict.status_code,409)
        from utils import publish_jobs
        with patch.object(publish_jobs,'_store',publish_jobs.JobStore(self.root/'db/jobs-test.db')):
            history=self.client.get('/publishJobs',headers={'Origin':'http://127.0.0.1:5173'})
            self.assertEqual(history.status_code,200,history.json)
            self.assertEqual(history.json['data'][0]['materialLabel'],'外婆 · 第25章')
            self.assertEqual(history.json['data'][0]['accountLabel'],'小红书 · 测试账号')
            self.assertEqual(history.json['data'][0]['status'],'completed')
            self.assertEqual(self.client.get('/publishJobs',headers={'Origin':'https://example.com'}).status_code,403)

    def test_all_six_platforms_receive_their_collection_and_job_id(self):
        targets={1:'post_video_xhs',2:'post_video_tencent',3:'post_video_DouYin',4:'post_video_ks',5:'post_video_baijiahao',6:'post_video_bilibili'}
        for platform, function in targets.items():
            with self.subTest(platform=platform), patch.object(sau_backend,function) as publish:
                response=self.client.post('/postVideo',json=self.payload(platform))
                self.assertEqual(response.status_code,200,response.json)
                self.assertEqual(publish.call_args.kwargs['collection_name'],self.payload(platform)['collectionName'])
                job=self.client.get('/publishJob',query_string={'id':response.json['data']['jobId']})
                self.assertEqual(job.json['data']['status'],'completed')
                self.assertIn('未发布',job.json['data']['message'])

    def test_account_of_other_platform_is_rejected_before_dispatch(self):
        data=self.payload(3);data['accountList']=['6.json']
        with patch.object(sau_backend,'post_video_DouYin') as publish:
            self.assertEqual(self.client.post('/postVideo',json=data).status_code,400)
            publish.assert_not_called()

    def test_cover_fields_reach_each_video_uploader(self):
        targets={1:'post_video_xhs',2:'post_video_tencent',3:'post_video_DouYin',4:'post_video_ks',5:'post_video_baijiahao',6:'post_video_bilibili'}
        for platform,function in targets.items():
            data=self.payload(platform);data.update(thumbnail='tall.jpg' if platform in (1,2,4) else 'wide.jpg',portraitCover='tall.jpg' if platform==3 else '')
            with self.subTest(platform=platform),patch.object(sau_backend,function) as publish:
                self.assertEqual(self.client.post('/postVideo',json=data).status_code,200)
                if platform==3:
                    self.assertEqual(publish.call_args.kwargs['portrait_cover'],'tall.jpg')
                    self.assertIn('wide.jpg',publish.call_args.args)
                else:
                    self.assertEqual(publish.call_args.kwargs['thumbnail_path'],data['thumbnail'])

    def test_invalid_bilibili_collection_is_not_submitted(self):
        data=self.payload(6);data['collectionName']='名称不是ID'
        with patch.object(sau_backend,'post_video_bilibili') as publish:
            self.assertEqual(self.client.post('/postVideo',json=data).status_code,400)
            publish.assert_not_called()

    def test_collection_failure_is_exposed_as_failed_job(self):
        with patch.object(sau_backend,'post_video_ks',side_effect=CollectionSelectionError('找不到合集，已停止发布')):
            response=self.client.post('/postVideo',json=self.payload(4))
        job=self.client.get('/publishJob',query_string={'id':response.json['data']['jobId']})
        self.assertEqual(job.json['data']['status'],'failed')
        self.assertIn('找不到合集',job.json['data']['message'])

    def test_bilibili_merges_collection_and_creation_statement_in_web_submit(self):
        for directory in ('videoFile','cookiesFile'):
            (self.root/directory).mkdir(exist_ok=True)
        (self.root/'videoFile/demo.mp4').write_bytes(b'fixture')
        (self.root/'videoFile/cover.jpg').write_bytes(b'image-fixture')
        (self.root/'cookiesFile/6.json').write_text('{}')
        with patch('myUtils.postVideo.BASE_DIR',self.root), patch('myUtils.postVideo.run_biliup_command',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')) as command:
            post_video_bilibili('title',['demo.mp4'],[],['6.json'],creation_statement=1,collection_name='123',thumbnail_path='cover.jpg')
        args=command.call_args.args[0]
        self.assertEqual(args[args.index('--line')+1],'tx')
        fields=json.loads(args[args.index('--extra-fields')+1])
        self.assertEqual(fields,{'season_id':123,'creation_statement':{'id':1}})
        self.assertEqual(args[args.index('--submit')+1],'web')
        self.assertEqual(args[args.index('--cover')+1],str((self.root/'videoFile/cover.jpg').resolve()))

if __name__=='__main__':
    unittest.main()
