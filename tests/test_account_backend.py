import asyncio,tempfile,unittest,json
from contextlib import closing
from pathlib import Path
from utils.account_backend import cookie_path,save_browser_state
from utils.channels_session import channels_session,SessionBusy,session_owner

class AccountBackendTests(unittest.TestCase):
 def test_cookie_path_rejects_escape(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'cookiesFile').mkdir()
   with self.assertRaises(ValueError):cookie_path(root,'../outside.json')
 def test_channels_exclusive_and_release(self):
  with channels_session('cookie.json','后台'):
   self.assertEqual(session_owner()['purpose'],'后台')
   async def contender():
    with channels_session('cookie.json','检测'):pass
   with self.assertRaises(SessionBusy):asyncio.run(contender())
  self.assertIsNone(session_owner())
 def test_bilibili_save_preserves_cli_format(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'cookie.json';path.write_text(json.dumps({'cookie_info':{'cookies':[{'name':'SESSDATA','value':'old'}]},'token_info':{'key':'keep'}}))
   save_browser_state(path,6,{'cookies':[{'name':'SESSDATA','value':'new','domain':'.bilibili.com','path':'/'}],'origins':[]})
   state=json.loads(path.read_text());self.assertEqual(state['token_info'],{'key':'keep'});self.assertEqual(state['cookie_info']['cookies'][0]['value'],'new')

 def test_repeated_open_reuses_one_thread_and_one_channels_session(self):
  import threading,time
  from unittest.mock import patch
  from utils import account_backend as manager
  stop=threading.Event();opened=[]
  async def fake_browse(state):
   opened.append(state);state['ready'].set()
   while not stop.is_set():await asyncio.sleep(.01)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'cookiesFile').mkdir();(root/'cookiesFile/a.json').write_text('{}')
   with patch.object(manager,'_browse',fake_browse):
    try:
     self.assertFalse(manager.open_backend(root,1,2,'a.json')['reused'])
     self.assertTrue(manager.open_backend(root,1,2,'a.json')['reused'])
     self.assertEqual(len(opened),1)
     self.assertTrue(opened[0]['focus'].is_set())
     async def contender():
      with channels_session('other.json','检测'):pass
     with self.assertRaises(SessionBusy):asyncio.run(contender())
    finally:
     stop.set()
     for _ in range(100):
      if session_owner() is None:break
      time.sleep(.01)
   self.assertIsNone(session_owner())

 def test_endpoint_local_only_and_database_account_lookup(self):
  import sqlite3
  from unittest.mock import patch
  import sau_backend
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'db').mkdir()
   with closing(sqlite3.connect(root/'db/database.db')) as db:
    db.execute('CREATE TABLE user_info(id INTEGER,type INTEGER,filePath TEXT)');db.execute("INSERT INTO user_info VALUES(1,2,'a.json')");db.commit()
   with patch.object(sau_backend,'BASE_DIR',root),patch('utils.account_backend.open_backend',return_value={'reused':False,'message':'opened'}) as opened:
    client=sau_backend.app.test_client()
    self.assertEqual(client.post('/account/openBackend',json={'accountId':1}).status_code,403)
    response=client.post('/account/openBackend',json={'accountId':1,'url':'https://untrusted.example'},headers={'X-OmniPost-Local':'1','Origin':'http://127.0.0.1:5173'})
    self.assertEqual(response.status_code,200);opened.assert_called_once_with(root,1,2,'a.json')

 def test_channels_busy_preflight_blocks_without_a_new_browser(self):
  from unittest.mock import patch
  from utils.publish_preflight import preflight_publish
  with tempfile.TemporaryDirectory() as temp,patch('utils.channels_session.session_owner',return_value={'purpose':'手动后台'}):
   report=preflight_publish(Path(temp),{'type':2,'accountList':[],'fileList':[]})
   self.assertFalse(report['ok']);self.assertTrue(report['activeTask'])
   self.assertTrue(any('手动后台' in e for e in report['errors']))

 def test_saved_state_loaded_and_refreshed_without_publishing(self):
  import threading
  from unittest.mock import AsyncMock,Mock,patch
  from utils import account_backend as manager
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'cookie.json';path.write_text('{"cookies":[],"origins":[]}',encoding='utf-8')
   context=Mock();page=Mock();context.pages=[]
   page.goto=AsyncMock();context.new_page=AsyncMock(return_value=page)
   updated={'cookies':[{'name':'token','value':'fixture','domain':'.example.test','path':'/'}],'origins':[]}
   context.storage_state=AsyncMock(return_value=updated)
   browser=Mock();browser.new_context=AsyncMock(return_value=context);browser.is_connected.return_value=True;browser.close=AsyncMock()
   runtime=Mock();runtime.chromium.launch=AsyncMock(return_value=browser)
   enter=Mock();enter.__aenter__=AsyncMock(return_value=runtime);enter.__aexit__=AsyncMock(return_value=False)
   state={'path':path,'platform':2,'ready':threading.Event(),'focus':threading.Event()}
   with patch('playwright.async_api.async_playwright',return_value=enter):asyncio.run(manager._browse(state))
   self.assertEqual(browser.new_context.call_args.kwargs['storage_state'],{'cookies':[],'origins':[]})
   self.assertEqual(page.goto.call_args.args[0],manager.URLS[2])
   self.assertEqual(json.loads(path.read_text()),updated)
   context.new_page.assert_awaited_once();browser.close.assert_awaited_once()

 def test_open_during_publish_reveals_existing_window(self):
  from unittest.mock import patch
  from utils.account_backend import open_backend
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);folder=root/'cookiesFile';folder.mkdir();cookie=folder/'a.json';cookie.write_text('{}')
   owner={'cookie':str(cookie.resolve()),'purpose':'发布任务','jobId':'fixture-job'}
   with patch('utils.account_backend.session_owner',return_value=owner),patch('utils.publish_windows.set_visible') as visible,patch('utils.account_backend.threading.Thread') as thread:
    self.assertTrue(open_backend(root,1,2,'a.json')['reused'])
    visible.assert_called_once_with('fixture-job',True);thread.assert_not_called()

 def test_busy_blocks_auth_upload_and_collection_before_browser_launch(self):
  from unittest.mock import patch,Mock
  from myUtils.auth import cookie_auth_tencent
  from uploader.tencent_uploader.main import TencentVideo
  from utils.collection_catalog import discover_collections,CollectionCatalogError
  with channels_session('a.json','手动后台'),patch('myUtils.auth.async_playwright') as auth_browser,patch('uploader.tencent_uploader.main.launch_browser') as publish_browser:
   with self.assertRaises(SessionBusy):asyncio.run(cookie_auth_tencent(Path('a.json')))
   with self.assertRaises(SessionBusy):asyncio.run(TencentVideo.upload(Mock(account_file='a.json'),Mock()))
   with self.assertRaises(CollectionCatalogError):asyncio.run(discover_collections(2,Path('a.json')))
   auth_browser.assert_not_called();publish_browser.assert_not_called()
