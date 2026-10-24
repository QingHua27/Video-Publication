import unittest,tempfile
from pathlib import Path
import conf
from patchright.async_api import async_playwright
from utils.ks_covers import select_cover_file
class KuaishouCoverInputs(unittest.IsolatedAsyncioTestCase):
 async def test_image_input_outside_modal_selected_by_real_upload_action(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page()
    await page.set_content('<input id="unrelated" type="file" accept="image/png"><div role="document" class="ant-modal"><button onclick="document.querySelector(\'#portal-input\').click()">上传图片</button><button onclick="document.body.dataset.published=1">确认</button></div><div><input id="portal-input" type="file" accept="image/png" style="display:none"></div>')
    with tempfile.TemporaryDirectory() as tmp:
     image=Path(tmp)/'cover.png';image.write_bytes(b'image')
     await select_cover_file(page,page.locator('.ant-modal'),str(image))
     self.assertEqual(await page.locator('#portal-input').evaluate('el=>el.files[0].name'),'cover.png')
     self.assertEqual(await page.locator('#unrelated').evaluate('el=>el.files.length'),0)
     self.assertIsNone(await page.locator('body').get_attribute('data-published'))
   finally:await b.close()
 async def test_legacy_modal_input_still_supported(self):
  async with async_playwright() as p:
   b=await p.chromium.launch(headless=True)
   try:
    page=await b.new_page();await page.set_content('<div class="ant-modal"><input type="file" accept="image/png"></div>')
    with tempfile.TemporaryDirectory() as tmp:
     image=Path(tmp)/'cover.png';image.write_bytes(b'image');await select_cover_file(page,page.locator('.ant-modal'),str(image))
     self.assertEqual(await page.locator('input').evaluate('el=>el.files[0].name'),'cover.png')
   finally:await b.close()
