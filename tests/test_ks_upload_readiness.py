import asyncio,unittest
import conf
from patchright.async_api import async_playwright
from uploader.ks_uploader.main import KSVideo

class KuaishouUploadReadiness(unittest.IsolatedAsyncioTestCase):
 async def test_assistant_99_percent_is_not_video_upload(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<section><video></video><div>重新上传</div></section><aside><div class="loading-progress">创作助手 检测中99%</div></aside>')
    app=object.__new__(KSVideo)
    await asyncio.wait_for(app.wait_for_video_upload(page),4)
   finally:await b.close()
 async def test_real_upload_blocks_even_with_preview_and_assistant(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<video></video><div>重新上传</div><div id="progress">上传中 67%</div><aside>检测中99%</aside>')
    app=object.__new__(KSVideo);task=asyncio.create_task(app.wait_for_video_upload(page))
    await page.wait_for_timeout(250);self.assertFalse(task.done())
    await page.locator('#progress').evaluate('el=>el.remove()')
    await asyncio.wait_for(task,4)
   finally:await b.close()
 async def test_no_positive_completion_does_not_look_uploaded(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div>正在准备上传</div>')
    app=object.__new__(KSVideo);task=asyncio.create_task(app.wait_for_video_upload(page))
    await page.wait_for_timeout(200);self.assertFalse(task.done());task.cancel();await asyncio.gather(task,return_exceptions=True)
   finally:await b.close()
