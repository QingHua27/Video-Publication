import asyncio,unittest
from unittest.mock import AsyncMock,patch
import conf
from patchright.async_api import async_playwright
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
class SubmitOnceTests(unittest.IsolatedAsyncioTestCase):
 async def test_delayed_success_only_clicks_once(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page()
    await page.route('**/*',lambda route:route.fulfill(content_type='text/html; charset=utf-8',body="<button onclick=\"localStorage.setItem('clicks',Number(localStorage.getItem('clicks')||0)+1);setTimeout(()=>location.href='/publish/success?ok=1',4000)\">发布</button>"))
    await page.goto('https://creator.xiaohongshu.com/publish/publish')
    app=object.__new__(XiaoHongShuVideo)
    await app.publish_once_and_confirm(page,timeout=6,poll_interval=.05)
    self.assertEqual(await page.evaluate("localStorage.getItem('clicks')"),'1')
   finally:await browser.close()
 async def test_uncertain_result_does_not_retry_and_reports_manual_check(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<button onclick="document.body.dataset.clicks=Number(document.body.dataset.clicks||0)+1">发布</button>')
    app=object.__new__(XiaoHongShuVideo)
    with patch('utils.publish_diagnostics.capture_editor_failure',new=AsyncMock(return_value='evidence.png')):
     with self.assertRaisesRegex(RuntimeError,'仅点击一次.*核对'):
      await app.publish_once_and_confirm(page,timeout=.15,poll_interval=.02)
    self.assertEqual(await page.evaluate('document.body.dataset.clicks'),'1')
   finally:await browser.close()
 async def test_risk_message_stops_before_submission(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<div role="alert">操作过于频繁</div><button onclick="document.body.dataset.clicked=1">发布</button>')
    app=object.__new__(XiaoHongShuVideo)
    with self.assertRaisesRegex(RuntimeError,'频繁'):
     await app.publish_once_and_confirm(page,timeout=.1,poll_interval=.02)
    self.assertIsNone(await page.evaluate('document.body.dataset.clicked'))
   finally:await browser.close()
