import unittest
from unittest.mock import AsyncMock,patch
import conf
from patchright.async_api import async_playwright
from utils.cover_confirmation import finish_cover_dialog
class CoverConfirmTests(unittest.IsolatedAsyncioTestCase):
 async def test_retries_only_cover_confirmation_until_modal_closes(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div id="modal"><button onclick="this.dataset.count=Number(this.dataset.count||0)+1;if(Number(this.dataset.count)===2)this.parentElement.style.display=\'none\'">确认</button></div><button onclick="window.published=true">发布</button>')
    await finish_cover_dialog(page,page.locator('#modal'),'fixture',('确认',),timeout=2,interval=.1)
    self.assertEqual(int(await page.locator('#modal button').get_attribute('data-count')),2);self.assertIsNone(await page.evaluate('window.published'))
   finally:await b.close()
 async def test_permanent_refusal_saves_evidence_and_fails(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div id="modal"><button>完成</button></div>')
    with patch('utils.publish_diagnostics.capture_editor_failure',new=AsyncMock()) as capture:
     with self.assertRaisesRegex(RuntimeError,'未执行发布'):await finish_cover_dialog(page,page.locator('#modal'),'fixture',('完成',),timeout=.3,interval=.1)
     capture.assert_awaited_once()
   finally:await b.close()
