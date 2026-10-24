import asyncio,unittest
import conf
from patchright.async_api import async_playwright
from utils.early_video_cover import prepare_video_and_cover,cover_entry_available
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.ks_uploader.main import KSVideo
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from uploader.toutiao_uploader.main import TouTiaoVideo
class PlatformGateTests(unittest.IsolatedAsyncioTestCase):
 async def test_all_platform_observers_wait_for_video_after_early_cover(self):
  cases=[(XiaoHongShuVideo,'wait_for_video_upload'),(TencentVideo,'wait_for_upload_complete'),(KSVideo,'wait_for_video_upload'),(BaiJiaHaoVideo,'uploading_video'),(TouTiaoVideo,'wait_for_upload')]
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    for cls,method in cases:
     with self.subTest(platform=cls.__name__):
      page=await browser.new_page()
      await page.set_content('<input placeholder="填写标题，30字符"><div class="cover-tabs-container"><div id="progress">上传中 45%</div></div><button id="cover">上传封面</button><button id="publish" disabled>发布</button>')
      app=object.__new__(cls);events=[]
      async def cover():
       self.assertIn('45%',await page.locator('#progress').inner_text());events.append('cover')
       await page.wait_for_timeout(120)
       await page.locator('#progress').evaluate('el=>el.textContent="上传成功"')
       await page.locator('#publish').evaluate('el=>el.disabled=false')
       if cls is KSVideo:await page.locator('#progress').evaluate('el=>el.innerHTML="<video></video><div>重新上传</div>"')
       events.append('video')
      await prepare_video_and_cover(lambda:getattr(app,method)(page),lambda:cover_entry_available(page,labels=('上传封面',)),cover,timeout=12,poll_interval=.02)
      self.assertEqual(events,['cover','video']);await page.close()
   finally:await browser.close()
 async def test_disabled_cover_entry_is_not_available(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<button disabled>上传封面</button>')
    self.assertFalse(await cover_entry_available(page,labels=('上传封面',)))
    await page.locator('button').evaluate('el=>el.disabled=false')
    self.assertTrue(await cover_entry_available(page,labels=('上传封面',)))
   finally:await b.close()

 async def test_tencent_visible_edit_during_upload_is_not_available(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div class="cover-preview"><button>编辑</button>个人主页分享卡片(3:4)</div><div id="state">取消上传</div>')
    app=object.__new__(TencentVideo)
    self.assertFalse(await app.cover_entry_ready(page))
    await page.locator('#state').evaluate('el=>el.textContent="视频上传完成"')
    self.assertTrue(await app.cover_entry_ready(page))
    await page.evaluate('''()=>{const host=document.createElement('wujie-app');const root=host.attachShadow({mode:'open'});const body=document.createElement('body');body.textContent='取消上传';root.append(body);document.body.append(host)}''')
    self.assertFalse(await app.cover_entry_ready(page))
   finally:await b.close()
