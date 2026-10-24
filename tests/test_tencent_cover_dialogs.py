import unittest
from unittest.mock import AsyncMock,patch
import conf
from patchright.async_api import async_playwright
from uploader.tencent_uploader.main import TencentVideo
class TencentCoverDialogs(unittest.IsolatedAsyncioTestCase):
 async def test_visible_crop_button_and_original_main_close_ignore_other_dialog(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div id="main" class="weui-desktop-dialog"><input type="file"><button hidden>确定</button><button onclick="this.parentElement.hidden=true">保存</button></div><div id="crop" class="weui-desktop-dialog"><h3>裁剪封面图</h3><button hidden>确定</button><button onclick="this.parentElement.hidden=true">确定</button></div><div id="other" class="weui-desktop-dialog">其他提示</div><button onclick="document.body.dataset.published=1">发布</button>')
    main=await page.locator('#main').element_handle();app=object.__new__(TencentVideo)
    await app.confirm_thumbnail_dialog(page,main,timeout=1500)
    self.assertFalse(await page.locator('#main').is_visible());self.assertFalse(await page.locator('#crop').is_visible())
    self.assertTrue(await page.locator('#other').is_visible());self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await b.close()
 async def test_unclosed_cover_returns_specific_failure_without_publish(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div id="main" class="weui-desktop-dialog"><button>保存</button></div>')
    app=object.__new__(TencentVideo)
    with patch('utils.publish_diagnostics.capture_editor_failure',new=AsyncMock(return_value='evidence.png')):
     with self.assertRaisesRegex(RuntimeError,'视频号封面.*未执行发布'):
      await app.confirm_thumbnail_dialog(page,await page.locator('#main').element_handle(),timeout=100)
   finally:await b.close()
