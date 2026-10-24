import asyncio,unittest
import conf
from patchright.async_api import async_playwright
from uploader.douyin_uploader.main import DouYinVideo

class EarlyDouyinCovers(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.runtime=await async_playwright().start();self.browser=await self.runtime.chromium.launch(headless=True)
  self.page=await self.browser.new_page()
  self.app=object.__new__(DouYinVideo);self.app.thumbnail_landscape_path='wide.png';self.app.thumbnail_portrait_path='tall.png'
 async def asyncTearDown(self):await self.browser.close();await self.runtime.stop()
 async def test_cover_starts_while_video_uploading_and_waits_for_both(self):
  await self.page.set_content('<button>选择封面</button><div class="long-card-test"></div>')
  events=[]
  async def cover(page):
   events.append('cover-start');self.assertEqual(await page.locator('text=重新上传').count(),0)
   await page.wait_for_timeout(150)
   events.append('cover-done')
  self.app.set_thumbnail=cover
  async def finish_video():
   await self.page.wait_for_timeout(300);await self.page.locator('.long-card-test').evaluate('el=>el.innerHTML="<div>重新上传</div>"');events.append('video-done')
  video=asyncio.create_task(finish_video())
  await self.app.prepare_video_and_covers(self.page,timeout=3,poll_interval=.03)
  events.append('ready');await video
  self.assertEqual(events,['cover-start','cover-done','video-done','ready'])
 async def test_video_finishing_first_still_waits_for_cover(self):
  await self.page.set_content('<button>选择封面</button><div class="long-card-test"><div>重新上传</div></div>')
  done=[]
  async def cover(page):await page.wait_for_timeout(120);done.append('cover-done')
  self.app.set_thumbnail=cover
  await self.app.prepare_video_and_covers(self.page,timeout=3,poll_interval=.03)
  self.assertEqual(done,['cover-done'])
 async def test_disabled_cover_entry_waits_until_video_ready(self):
  await self.page.set_content('<button disabled>选择封面</button><div class="long-card-test"></div>')
  calls=[]
  async def cover(page):calls.append(1)
  self.app.set_thumbnail=cover
  async def finish():
   await self.page.wait_for_timeout(120);self.assertFalse(calls)
   await self.page.locator('button').evaluate('el=>el.disabled=false')
   await self.page.locator('.long-card-test').evaluate('el=>el.innerHTML="<div>重新上传</div>"')
  video=asyncio.create_task(finish())
  await self.app.prepare_video_and_covers(self.page,timeout=3,poll_interval=.03);await video
  self.assertEqual(calls,[1])
 async def test_cover_failure_is_not_swallowed_as_video_poll_retry(self):
  await self.page.set_content('<button>选择封面</button><div class="long-card-test"><div>重新上传</div></div>')
  async def cover(page):raise RuntimeError('cover failed')
  self.app.set_thumbnail=cover
  with self.assertRaisesRegex(RuntimeError,'cover failed'):await self.app.prepare_video_and_covers(self.page,timeout=3,poll_interval=.03)
 async def test_video_never_completes_cannot_return_ready(self):
  await self.page.set_content('<div class="long-card-test"></div>')
  self.app.thumbnail_landscape_path='';self.app.thumbnail_portrait_path=''
  with self.assertRaisesRegex(RuntimeError,'视频上传超时'):await self.app.prepare_video_and_covers(self.page,timeout=.15,poll_interval=.03)
