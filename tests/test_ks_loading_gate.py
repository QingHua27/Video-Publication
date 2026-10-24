import unittest
from unittest.mock import AsyncMock,patch
import conf
from patchright.async_api import async_playwright
from utils import ks_collection_tasks as ks
class KuaishouLoadingTests(unittest.IsolatedAsyncioTestCase):
 async def test_waits_for_overlay_then_clicks_menu_without_publishing(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div class="el-submenu__title" onclick="document.body.dataset.menu=1">内容管理</div><div class="el-loading-mask loading-h5 is-fullscreen" style="position:fixed;inset:0;background:white"></div><button onclick="document.body.dataset.published=1">发布</button><script>setTimeout(()=>document.querySelector(".el-loading-mask").remove(),250)</script>')
    await ks.open_content_management(page,timeout=1500)
    self.assertEqual(await page.evaluate('document.body.dataset.menu'),'1');self.assertIsNone(await page.evaluate('document.body.dataset.published'))
   finally:await b.close()
 async def test_stuck_loading_mask_returns_specific_failure(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div class="el-submenu__title">内容管理</div><div class="el-loading-mask is-fullscreen" style="position:fixed;inset:0"></div>')
    with patch('utils.publish_diagnostics.capture_editor_failure',new=AsyncMock(return_value='evidence.png')):
     with self.assertRaisesRegex(RuntimeError,'快手合集页面加载超时'):
      await ks.open_content_management(page,timeout=100)
   finally:await b.close()
