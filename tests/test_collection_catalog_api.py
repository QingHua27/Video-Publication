import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import AsyncMock,patch
import sau_backend

class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'db').mkdir();(self.root/'cookiesFile').mkdir()
        conn=sqlite3.connect(self.root/'db/database.db')
        conn.execute('CREATE TABLE user_info(id INTEGER PRIMARY KEY,type INTEGER,filePath TEXT)')
        conn.executemany('INSERT INTO user_info VALUES(?,?,?)',[(1,3,'a.json'),(2,6,'b.json')]);conn.commit();conn.close()
        for name in ('a.json','b.json'):(self.root/'cookiesFile'/name).write_text('{}')
        self.base=patch.object(sau_backend,'BASE_DIR',self.root);self.base.start()
        sau_backend._collection_cache.clear();self.client=sau_backend.app.test_client()
    def tearDown(self):
        self.base.stop();self.temp.cleanup()
    def test_cache_is_per_account_and_refresh_reloads(self):
        mock=AsyncMock(return_value={'status':'ready','items':[{'id':'5','name':'测试合集','value':'测试合集'}],'message':'ok'})
        with patch.object(sau_backend,'discover_collections',mock):
            first=self.client.get('/accountCollections?accountId=1')
            second=self.client.get('/accountCollections?accountId=1')
            self.assertEqual(mock.await_count,1)
            self.assertEqual(first.json['data']['accountId'],1)
            self.client.get('/accountCollections?accountId=2')
            self.assertEqual(mock.await_count,2)
            self.client.get('/accountCollections?accountId=1&refresh=1')
            self.assertEqual(mock.await_count,3)
    def test_unknown_account_never_opens_browser(self):
        with patch.object(sau_backend,'discover_collections',new=AsyncMock()) as mock:
            self.assertEqual(self.client.get('/accountCollections?accountId=999').status_code,404)
            mock.assert_not_called()
    def test_failure_is_not_reported_as_empty(self):
        with patch.object(sau_backend,'discover_collections',new=AsyncMock(side_effect=RuntimeError('do not expose credentials'))):
            result=self.client.get('/accountCollections?accountId=1').json['data']
        self.assertEqual(result['status'],'unavailable')
        self.assertNotIn('credentials',result['message'])
    def test_duplicate_names_on_browser_platform_are_disabled(self):
        data={'status':'ready','items':[{'id':str(n),'name':'同名合集','value':'同名合集'} for n in (1,2)],'message':'ok'}
        with patch.object(sau_backend,'discover_collections',new=AsyncMock(return_value=data)):
            result=self.client.get('/accountCollections?accountId=1').json['data']
        self.assertTrue(all(item['disabled'] for item in result['items']))


    def test_pending_collection_is_disabled_and_stops_before_video_upload(self):
        import sqlite3
        with closing(sqlite3.connect(self.root/'db/database.db')) as db:db.execute("INSERT INTO user_info VALUES(3,4,'ks.json')");db.commit()
        (self.root/'cookiesFile/ks.json').write_text('{}')
        data={'status':'ready','items':[{'id':'1','name':'新合集','value':'新合集','disabled':True,'unavailableReason':'有效剧集数不足，不公开展示'}],'message':'ok'}
        with patch.object(sau_backend,'discover_collections',new=AsyncMock(return_value=data)):
            response=self.client.get('/accountCollections?accountId=3').json['data']
        self.assertTrue(response['items'][0]['disabled'])
        with patch.object(sau_backend,'post_video_ks') as upload:
            result=self.client.post('/postVideo',json={'type':4,'title':'测试','fileList':['fixture.mp4'],'accountList':['ks.json'],'collectionName':'新合集'})
            self.assertEqual(result.status_code,400);self.assertIn('有效剧集数不足',result.json['msg']);upload.assert_not_called()

if __name__=='__main__':unittest.main()
