import tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
import conf
from patchright.async_api import async_playwright
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo

class XhsCoverReadiness(unittest.IsolatedAsyncioTestCase):
 async def test_slow_editor_mounts_image_input_after_old_ten_second_limit(self):
  with tempfile.TemporaryDirectory() as directory:
   image=Path(directory)/'cover.png';image.write_bytes(b'fixture')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content("""<button class="cover-edit-entry" onclick="document.querySelector('.main-cover-editor-modal').hidden=false;setTimeout(()=>document.querySelector('#slot').innerHTML='<input type=file accept=image/png>',11000)">编辑封面</button><div class="main-cover-editor-modal" hidden><div id="slot"></div><button class="mojito-button bg-red" onclick="this.parentElement.hidden=true">完成</button></div><button onclick="document.body.dataset.published='yes'">发布</button>""")
     app=object.__new__(XiaoHongShuVideo)
     await app.set_thumbnail(page,str(image))
     self.assertEqual(await page.locator('input[type=file]').evaluate('el=>el.files[0].name'),'cover.png')
     self.assertIsNone(await page.evaluate('document.body.dataset.published'))
    finally:await browser.close()
 async def test_missing_cover_input_has_specific_error_and_diagnostic(self):
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True)
   try:
    page=await browser.new_page();await page.set_content('<div class="main-cover-editor-modal">加载中</div>')
    app=object.__new__(XiaoHongShuVideo)
    with patch('utils.publish_diagnostics.capture_editor_failure',new=AsyncMock(return_value='evidence.png')) as capture:
     with self.assertRaisesRegex(RuntimeError,'封面.*上传控件.*未发布'):
      await app.upload_cover_image(page,page.locator('.main-cover-editor-modal'),'unused.png',timeout=100)
     capture.assert_awaited_once()
   finally:await browser.close()
