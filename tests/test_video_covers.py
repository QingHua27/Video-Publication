import tempfile
import unittest
from pathlib import Path
import conf
from patchright.async_api import async_playwright
from utils.video_covers import apply_custom_video_cover
from uploader.tencent_uploader.main import TencentVideo


class VideoCoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_scoped_cover_upload_and_missing_control_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            image=Path(folder)/'cover.png';image.write_bytes(b'fixture')
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True)
                try:
                    page=await browser.new_page()
                    await page.set_content('''<button onclick="document.querySelector('[role=dialog]').style.display='block'">选择封面</button>
                    <div role="dialog" style="display:none"><input type="file" accept="image/png"><button onclick="this.parentNode.style.display='none'">确定</button></div>
                    <button onclick="window.published=true">发布</button>''')
                    await apply_custom_video_cover(page,str(image))
                    self.assertEqual(await page.locator('input').evaluate('(input)=>input.files[0].name'),'cover.png')
                    self.assertIsNone(await page.evaluate('window.published'))
                    await page.set_content('<button onclick="window.published=true">发布</button>')
                    with self.assertRaisesRegex(RuntimeError,'停止发布'):
                        await apply_custom_video_cover(page,str(image))
                    app=object.__new__(TencentVideo);app.thumbnail_path=str(image)
                    with self.assertRaisesRegex(RuntimeError,'停止发布'):
                        await app.set_thumbnail(page)
                    self.assertIsNone(await page.evaluate('window.published'))
                finally:
                    await browser.close()

if __name__=='__main__':unittest.main()
