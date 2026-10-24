import unittest,tempfile
from pathlib import Path
from unittest.mock import AsyncMock,MagicMock,patch
import conf
from patchright.async_api import async_playwright
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
class PublishFailureRegression(unittest.IsolatedAsyncioTestCase):
 async def test_kuaishou_collection_uses_select_instead_of_label(self):
  from utils.publish_collections import apply_video_collection
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page()
    await page.set_content('''<div>加入合集</div><div><span id="trigger" onclick="document.querySelector('.ant-select-dropdown').style.display='block'">选择要加入到的合集</span></div><div class="ant-select-dropdown" style="display:none"><div onclick="document.querySelector('#trigger').innerText='米格尔街';this.parentNode.style.display='none'">米格尔街</div></div><button onclick="document.body.dataset.published=1">发布</button>''')
    await apply_video_collection(page,4,'米格尔街')
    self.assertEqual(await page.locator('#trigger').inner_text(),'米格尔街')
    self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await browser.close()
 async def test_baijiahao_result_reports_verification_and_unknown(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();app=object.__new__(BaiJiaHaoVideo)
    with patch('utils.publish_diagnostics.capture_editor_failure',new=AsyncMock(return_value='evidence.png')):
     await page.set_content('<div>百度安全验证</div>')
     with self.assertRaisesRegex(RuntimeError,'安全验证'):await app.wait_for_publish_result(page,attempts=1)
     await page.set_content('<div>发布成功</div>')
     await app.wait_for_publish_result(page,attempts=1)
     await page.set_content('<div>作品管理：草稿</div>')
     with self.assertRaisesRegex(RuntimeError,'未确认提交结果'):await app.wait_for_publish_result(page,attempts=1)
   finally:await browser.close()
 async def test_baijiahao_publish_does_not_match_schedule_button(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page()
    await page.set_content('''<button onclick="document.body.dataset.scheduled=1">定时发布</button><button onclick="document.body.dataset.published=1"><span>发布</span></button>''')
    app=object.__new__(BaiJiaHaoVideo)
    await app.publish_video(page,0)
    self.assertEqual(await page.evaluate('document.body.dataset.published'),'1')
    self.assertIsNone(await page.evaluate('document.body.dataset.scheduled'))
   finally:await browser.close()
 async def test_unselected_original_does_not_touch_page(self):
  app=object.__new__(TencentVideo);app.category=0;page=MagicMock()
  await app.apply_original_statement(page);page.locator.assert_not_called();page.get_by_label.assert_not_called()
 async def test_empty_browser_path_uses_bundled_browser(self):
  app=object.__new__(BaiJiaHaoVideo);app.headless=True;app.proxy_setting=None;app.local_executable_path=''
  runtime=MagicMock();runtime.chromium.launch=AsyncMock(side_effect=RuntimeError('launch intercepted'))
  with patch('uploader.baijiahao_uploader.main.LOCAL_CHROME_PATH',''):
   with self.assertRaisesRegex(RuntimeError,'launch intercepted'):await app.upload(runtime)
  self.assertNotIn('executable_path',runtime.chromium.launch.call_args.kwargs)
 async def test_cover_new_confirm_buttons(self):
  with tempfile.TemporaryDirectory() as folder:
   image=Path(folder)/'cover.png';image.write_bytes(b'fixture')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     for label in ['确定','完成','保存封面']:
      await page.set_content('''<div class="cover-plugin-preview"><div class="cover-plugin-title">设置封面</div><div class="cover"><div class="default" onclick="document.querySelector('.d-modal').style.display='block'">选择封面</div></div></div><div class="d-modal cover-modal" style="display:none"><input type="file" accept=".png,.jpg"><button onclick="this.parentNode.style.display='none'">'''+label+'''</button></div><button onclick="document.body.dataset.published=1">发布</button>''')
      app=object.__new__(XiaoHongShuVideo);await app.set_thumbnail(page,str(image))
      self.assertEqual(await page.locator('input').evaluate('(x)=>x.files[0].name'),'cover.png')
      self.assertIsNone(await page.evaluate('document.body.dataset.published'))
    finally:await browser.close()
 async def test_douyin_collection_name_with_count_and_delayed_options(self):
  from utils.publish_collections import apply_video_collection
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page()
    await page.set_content('''<div><button id="trigger" onclick="setTimeout(()=>document.querySelector('#options').style.display='block',100)">选择合集</button></div><div id="options" style="display:none"><div class="semi-select-option" role="option" onclick="document.querySelector('#trigger').innerText='米格尔街';this.setAttribute('aria-selected','true')"><span>米格尔街</span><small>17个作品</small></div></div><button onclick="document.body.dataset.published=1">发布</button>''')
    await apply_video_collection(page,3,'米格尔街')
    self.assertEqual(await page.locator('#trigger').inner_text(),'米格尔街')
    self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await browser.close()
 async def test_tencent_upload_readiness_and_timeout(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();app=object.__new__(TencentVideo)
    await page.set_content('<button>发表</button>')
    await app.wait_for_upload_complete(page)
    await page.set_content('<div>没有可用发布按钮</div>')
    with patch('uploader.tencent_uploader.main.asyncio.sleep',new=AsyncMock()):
     with self.assertRaisesRegex(RuntimeError,'未执行发布'):await app.wait_for_upload_complete(page)
   finally:await browser.close()
 async def test_douyin_title_placeholder_without_legacy_layout(self):
  from uploader.douyin_uploader.main import DouYinVideo
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<input placeholder="填写标题"><div contenteditable="true"></div><button onclick="document.body.dataset.published=1">发布</button>')
    app=object.__new__(DouYinVideo)
    await app.fill_title_and_description(page,'新标题','新描述',[])
    self.assertEqual(await page.locator('input').input_value(),'新标题')
    self.assertEqual(await page.locator('[contenteditable]').inner_text(),'新描述')
    self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await browser.close()
 async def test_login_network_error_is_not_cookie_expiry(self):
  import uploader.tencent_uploader.main as tencent
  import uploader.xiaohongshu_uploader.main as xhs
  for module in (tencent,xhs):
   with tempfile.TemporaryDirectory() as directory:
    cookie=Path(directory)/'account.json';cookie.write_text('{}')
    runtime=MagicMock();browser=AsyncMock();context=AsyncMock();page=AsyncMock()
    runtime.chromium.launch=AsyncMock(return_value=browser);browser.new_context.return_value=context;context.new_page.return_value=page
    page.goto.side_effect=RuntimeError('connection interrupted')
    manager=MagicMock();manager.__aenter__=AsyncMock(return_value=runtime);manager.__aexit__=AsyncMock(return_value=False)
    with patch.object(module,'async_playwright',return_value=manager),patch.object(module,'set_init_script',new=AsyncMock(return_value=context)):
     with self.assertRaisesRegex(RuntimeError,'不代表cookie失效'):await module.cookie_auth(str(cookie))
    browser.close.assert_awaited_once()
 async def test_baijiahao_new_title_placeholder(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<input placeholder="请输入作品标题"><button onclick="document.body.dataset.published=1">发布</button>')
    app=object.__new__(BaiJiaHaoVideo);app.title='用于测试的较长作品标题'
    await app.add_title_tags(page)
    self.assertEqual(await page.locator('input').input_value(),app.title)
    self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await browser.close()
 async def test_baijiahao_real_editor_contenteditable(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<div role="textbox" contenteditable="true" class="FeEditorApp-d482ca4cbff50e1c-contentEditable"></div>')
    app=object.__new__(BaiJiaHaoVideo);app.title='短标题'
    await app.add_title_tags(page)
    self.assertEqual(await page.get_by_role('textbox').inner_text(),'短标题')
   finally:await browser.close()
 async def test_xhs_title_does_not_mean_upload_done(self):
  import asyncio
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<input placeholder="填写标题会有更多赞哦"><div id="progress">上传中 52%</div><button>编辑封面</button>')
    app=object.__new__(XiaoHongShuVideo);task=asyncio.create_task(app.wait_for_video_upload(page))
    await asyncio.sleep(.2);self.assertFalse(task.done())
    await page.locator('#progress').evaluate('(el)=>el.innerText="上传成功"')
    await asyncio.wait_for(task,6)
   finally:await browser.close()
 async def test_douyin_cover_close_before_returning(self):
  from uploader.douyin_uploader.main import DouYinVideo
  with tempfile.TemporaryDirectory() as folder:
   image=Path(folder)/'cover.png';image.write_bytes(b'fixture')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<button onclick="document.querySelector('#creator-content-modal').style.display='block'">选择封面</button><div id="creator-content-modal" style="display:none"><button>横封面4:3</button><div class="semi-upload upload"><input class="semi-upload-hidden-input" type="file" onchange="setTimeout(()=>document.querySelector('#done').className='',100)"></div><button id="done" class="semi-button-disabled" onclick="if(!this.className.includes('disabled'))this.parentNode.style.display='none'">完成</button></div><button onclick="document.body.dataset.published=1">发布</button>''')
     app=object.__new__(DouYinVideo);app.thumbnail_landscape_path=str(image);app.thumbnail_portrait_path=None
     await app.set_thumbnail(page)
     self.assertFalse(await page.locator('#creator-content-modal').is_visible())
     self.assertIsNone(await page.evaluate('document.body.dataset.published'))
    finally:await browser.close()
 async def test_tencent_cover_edit_button_in_current_card(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    with tempfile.TemporaryDirectory() as directory:
     image=Path(directory)/'cover.png';image.write_bytes(b'fixture')
     page=await browser.new_page()
     await page.set_content('''<div class="cover-preview"><button onclick="document.querySelector('[role=dialog]').style.display='block'">编辑</button><span>个人主页和分享卡片(3:4)</span></div><div role="dialog" class="weui-desktop-dialog" style="display:none"><input type="file" accept="image/png"><div class="weui-desktop-dialog__ft"><button class="weui-desktop-btn_primary" onclick="this.closest('[role=dialog]').style.display='none'">确认</button></div></div><button onclick="document.body.dataset.published=1">发表</button>''')
     app=object.__new__(TencentVideo);app.thumbnail_path=str(image)
     await app.set_thumbnail(page)
     self.assertFalse(await page.get_by_role('dialog').is_visible())
     self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await browser.close()
 async def test_baijiahao_upload_percentage_blocks_readiness(self):
  import asyncio
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<div class="cover-tabs-container"><span id="progress">0%</span></div>')
    app=object.__new__(BaiJiaHaoVideo);task=asyncio.create_task(app.uploading_video(page))
    await asyncio.sleep(.2);self.assertFalse(task.done())
    await page.locator('#progress').evaluate('(el)=>el.innerText="更换"')
    self.assertTrue(await asyncio.wait_for(task,6))
   finally:await browser.close()
 async def test_xhs_cover_input_removed_after_selection(self):
  with tempfile.TemporaryDirectory() as directory:
   image=Path(directory)/'cover.png';image.write_bytes(b'fixture')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<div class="cover-edit-entry" onclick="document.querySelector('.cover-modal').style.display='block'">编辑封面</div><div class="d-modal cover-modal" style="display:none"><input type="file" accept=".png,.jpg" onchange="document.body.dataset.selected=this.files[0].name;this.remove()"><button onclick="this.parentNode.style.display='none'">完成</button></div><button onclick="document.body.dataset.published=1">发布</button>''')
     app=object.__new__(XiaoHongShuVideo);await app.set_thumbnail(page,str(image))
     self.assertEqual(await page.evaluate('document.body.dataset.selected'),'cover.png')
     self.assertFalse(await page.locator('.cover-modal').is_visible())
     self.assertIsNone(await page.evaluate('document.body.dataset.published'))
    finally:await browser.close()
 async def test_baijiahao_wide_cover_does_not_fill_portrait(self):
  from utils.video_covers import apply_baijiahao_video_cover
  with tempfile.TemporaryDirectory() as directory:
   image=Path(directory)/'wide.png';image.write_bytes(b'fixture')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<div class="form-cover"><div class="FeEditorApp-cover-container"><img src="old.png"><input type="file" accept="image/png" onchange="this.parentNode.querySelector('img').src='wide.png'"></div><div class="FeEditorApp-cover-container"><img src="portrait.png"><input type="file" accept="image/png"></div></div><button onclick="document.body.dataset.published=1">发布</button>''')
     await apply_baijiahao_video_cover(page,str(image))
     self.assertEqual(await page.locator('input').nth(0).evaluate('(el)=>el.files.length'),1)
     self.assertEqual(await page.locator('input').nth(1).evaluate('(el)=>el.files.length'),0)
     self.assertIsNone(await page.evaluate('document.body.dataset.published'))
    finally:await browser.close()
 async def test_baijiahao_uses_local_upload_inside_modal(self):
  from utils.video_covers import apply_baijiahao_video_cover
  with tempfile.TemporaryDirectory() as directory:
   image=Path(directory)/'wide.png';image.write_bytes(b'fixture')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<div class="form-cover"><div class="cover-container" onclick="document.querySelector('.cheetah-modal').style.display='block'"><img src="old.png"><input id="background" type="file" accept="image/png"></div></div><div class="cheetah-modal" role="dialog" style="display:none"><span><input type="file" accept="image/png" onchange="let img=document.createElement('img');img.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22/%3E';this.parentNode.append(img);this.parentNode.querySelector('b').remove()"><b>本地上传</b></span><button onclick="document.querySelector('.form-cover img').src='saved.png';this.parentNode.style.display='none'">确定</button></div>''')
     await apply_baijiahao_video_cover(page,str(image))
     self.assertEqual(await page.locator('#background').evaluate('(el)=>el.files.length'),0)
     self.assertEqual(await page.locator('[role=dialog] input').evaluate('(el)=>el.files.length'),1)
     self.assertFalse(await page.get_by_role('dialog').is_visible())
    finally:await browser.close()
 async def test_douyin_collection_placeholder_before_plain_label(self):
  from utils.publish_collections import apply_video_collection
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page()
    await page.set_content('''<div>添加合集</div><div id="field"><span id="trigger" onclick="document.querySelector('.custom-dropdown').style.display='block'">请选择合集</span></div><div class="custom-dropdown" style="display:none"><div class="option-card" onclick="document.querySelector('#trigger').textContent='米格尔街';this.parentNode.style.display='none'"><span>米格尔街</span><small>17个作品</small></div></div><button onclick="document.body.dataset.published=1">发布</button>''')
    await apply_video_collection(page,3,'米格尔街')
    self.assertEqual(await page.locator('#trigger').inner_text(),'米格尔街')
    self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await browser.close()
if __name__=='__main__':unittest.main()
