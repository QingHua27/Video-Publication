import asyncio
import unittest
import conf
from patchright.async_api import async_playwright
from utils.publish_collections import apply_video_collection, CollectionSelectionError


HTML = '''<button id="collection" onclick="document.querySelector('[role=listbox]').hidden=false">选择合集</button>
<div role="listbox" hidden><div role="option" onclick="document.querySelector('#collection').innerText=this.innerText;this.parentElement.hidden=true">我的合集</div></div>
<button id="publish" onclick="this.dataset.clicked='yes'">发布</button>'''


class BrowserCollectionTests(unittest.TestCase):
    def test_exact_collection_selection_for_each_browser_platform(self):
        async def check():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                for platform in (1,2,3,4,5):
                    await page.set_content(HTML)
                    await apply_video_collection(page,platform,'我的合集')
                    self.assertEqual(await page.locator('#collection').inner_text(),'我的合集')
                    self.assertIsNone(await page.locator('#publish').get_attribute('data-clicked'))
                await page.set_content('<button id="publish">发布</button>')
                with self.assertRaises(CollectionSelectionError):
                    await apply_video_collection(page,3,'不存在的合集')
                await browser.close()
        asyncio.run(check())

if __name__=='__main__':
    unittest.main()
