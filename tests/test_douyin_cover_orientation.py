import asyncio,tempfile,unittest
from pathlib import Path
import conf
from patchright.async_api import async_playwright
from uploader.douyin_uploader.main import DouYinVideo
class DouyinOrientationTests(unittest.IsolatedAsyncioTestCase):
 async def test_orientation_labels_override_initial_tab_and_dom_order(self):
  with tempfile.TemporaryDirectory() as directory:
   wide=Path(directory)/'wide.png';tall=Path(directory)/'tall.png';wide.write_bytes(b'wide');tall.write_bytes(b'tall')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<button onclick="document.querySelector('#creator-content-modal').style.display='block'">选择封面</button><div id="creator-content-modal" style="display:none"><div class="steps"><div><button onclick="document.body.dataset.kind='portrait'">竖封面3:4</button></div><div><button onclick="document.body.dataset.kind='landscape'">横封面4:3</button></div></div><div class="semi-upload upload"><input type="file" class="semi-upload-hidden-input" onchange="document.body.setAttribute('data-upload-'+(document.body.dataset.kind || 'portrait'),this.files[0].name)"></div><button onclick="document.querySelector('#creator-content-modal').style.display='none'">完成</button></div><button onclick="document.body.dataset.published='yes'">发布</button><script>document.body.dataset.kind='portrait';window.uploads=[];</script>''')
     app=object.__new__(DouYinVideo);app.thumbnail_landscape_path=str(wide);app.thumbnail_portrait_path=str(tall)
     await asyncio.wait_for(app.set_thumbnail(page),20)
     self.assertEqual(await page.locator('body').get_attribute('data-upload-landscape'),'wide.png')
     self.assertEqual(await page.locator('body').get_attribute('data-upload-portrait'),'tall.png')
     self.assertFalse(await page.locator('#creator-content-modal').is_visible());self.assertIsNone(await page.locator('body').get_attribute('data-published'))
    finally:await browser.close()

 async def test_active_cover_upload_button_ignores_replace_and_other_orientation_inputs(self):
  from utils.douyin_covers import upload_cover_for_orientation
  with tempfile.TemporaryDirectory() as directory:
   wide=Path(directory)/'wide.png';wide.write_bytes(b'wide')
   tall=Path(directory)/'tall.png';tall.write_bytes(b'tall')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<div id="modal"><button onclick="switchKind('portrait')">设置竖封面</button><button onclick="switchKind('landscape')">设置横封面</button><div id="portrait" class="semi-upload"><input class="semi-upload-hidden-input" type="file" style="display:none" onchange="document.body.dataset.portrait=this.files[0].name"><input type="file" class="semi-upload-hidden-input-replace" style="display:none"><button onclick="this.parentElement.querySelector('input').click()">上传封面</button></div><div id="landscape" class="semi-upload" style="display:none"><input class="semi-upload-hidden-input" type="file" style="display:none" onchange="document.body.dataset.landscape=this.files[0].name"><input type="file" class="semi-upload-hidden-input-replace" style="display:none"><button onclick="this.parentElement.querySelector('input').click()">上传封面</button></div></div><script>function switchKind(kind){for(const k of ['portrait','landscape'])document.getElementById(k).style.display=k===kind?'block':'none'}</script>''')
     modal=page.locator('#modal')
     await upload_cover_for_orientation(page,modal,'landscape',wide)
     await upload_cover_for_orientation(page,modal,'portrait',tall)
     self.assertEqual(await page.locator('body').get_attribute('data-landscape'),'wide.png')
     self.assertEqual(await page.locator('body').get_attribute('data-portrait'),'tall.png')
    finally:await browser.close()

 async def test_upload_label_covered_by_upload_overlay(self):
  from utils.douyin_covers import upload_cover_for_orientation
  with tempfile.TemporaryDirectory() as directory:
   cover=Path(directory)/'wide.png';cover.write_bytes(b'image')
   async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    try:
     page=await browser.new_page()
     await page.set_content('''<div id="modal"><button>设置横封面</button><div style="position:relative;width:100px;height:60px"><div>上传封面</div><div class="semi-upload" style="position:absolute;inset:0;background:#ccc"><svg style="width:100%;height:100%"><rect width="100%" height="100%"/></svg><input type="file" class="semi-upload-hidden-input" style="display:none" onchange="document.body.dataset.cover=this.files[0].name"><input type="file" class="semi-upload-hidden-input-replace" style="display:none"></div></div><div style="display:none"><input class="semi-upload-hidden-input" type="file"></div></div>''')
     await upload_cover_for_orientation(page,page.locator('#modal'),'landscape',cover)
     self.assertEqual(await page.locator('body').get_attribute('data-cover'),'wide.png')
    finally:await browser.close()
