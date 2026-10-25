import sqlite3, unittest
from unittest.mock import AsyncMock
from utils.account_identity import read_username, save_account, LoginLabel, account_remarks

class IdentityTests(unittest.IsolatedAsyncioTestCase):
 async def test_reads_only_unique_visible_profile_name(self):
  page=type('Page',(),{'evaluate':AsyncMock(return_value=['Alice','Alice'])})()
  self.assertEqual(await read_username(page,2),'Alice')
 async def test_ambiguous_name_is_not_guessed(self):
  page=type('Page',(),{'evaluate':AsyncMock(return_value=['Alice','Bob'])})()
  self.assertEqual(await read_username(page,2),'')
 async def test_remark_is_separate_and_empty_is_allowed(self):
  with sqlite3.connect(':memory:') as db:
   db.execute('CREATE TABLE user_info(id INTEGER PRIMARY KEY,type INTEGER,filePath TEXT,userName TEXT,status INTEGER)')
   save_account(db,2,'cookie.json','Alice',LoginLabel('',None),1)
   self.assertEqual(db.execute('SELECT userName FROM user_info').fetchone()[0],'Alice')
   self.assertEqual(account_remarks(db),{1:''})
 async def test_relogin_updates_same_account_and_preserves_detected_name_on_failure(self):
  with sqlite3.connect(':memory:') as db:
   db.execute('CREATE TABLE user_info(id INTEGER PRIMARY KEY,type INTEGER,filePath TEXT,userName TEXT,status INTEGER)')
   save_account(db,2,'old.json','Alice',LoginLabel('工作号',None),1)
   save_account(db,2,'new.json','',LoginLabel('新备注',1),1)
   self.assertEqual(db.execute('SELECT userName,filePath FROM user_info').fetchall(),[('Alice','new.json')])
   self.assertEqual(account_remarks(db),{1:'新备注'})

 async def test_visible_profile_selector_does_not_read_content_author(self):
  import conf
  from patchright.async_api import async_playwright
  async with async_playwright() as runtime:
   browser=await runtime.chromium.launch(headless=True)
   try:
    page=await browser.new_page()
    await page.set_content('<div class="finder-nickname">实际昵称</div><div class="video-author">别人的昵称</div><div class="finder-nickname" style="display:none">隐藏昵称</div>')
    self.assertEqual(await read_username(page,2),'实际昵称')
   finally:
    await browser.close()

class AccountIdentityApiTests(unittest.TestCase):
 def test_old_account_list_and_remark_edit_roundtrip(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  import sau_backend
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'db').mkdir()
   with sqlite3.connect(root/'db/database.db') as db:
    db.execute('CREATE TABLE user_info(id INTEGER PRIMARY KEY,type INTEGER,filePath TEXT,userName TEXT,status INTEGER)')
    db.execute("INSERT INTO user_info VALUES(1,2,'demo.json','原用户名',1)")
   db.close()
   with patch.object(sau_backend,'BASE_DIR',root):
    client=sau_backend.app.test_client()
    self.assertEqual(client.get('/getAccounts').get_json()['data'][0],[1,2,'demo.json','原用户名',1,''])
    self.assertEqual(client.post('/updateUserinfo',json={'id':1,'type':2,'userName':'新昵称','remark':'工作号'}).status_code,200)
    self.assertEqual(client.get('/getAccounts').get_json()['data'][0][3:],["新昵称",1,"工作号"])
