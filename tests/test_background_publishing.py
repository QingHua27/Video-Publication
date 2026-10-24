import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock,MagicMock
from myUtils import postVideo as publishing


class BackgroundPublishingTests(unittest.TestCase):
    def test_video_dispatch_hides_publishing_but_keeps_preview_visible(self):
        cases=[('TencentVideo',publishing.post_video_tencent),('DouYinVideo',publishing.post_video_DouYin),
               ('KSVideo',publishing.post_video_ks),('XiaoHongShuVideo',publishing.post_video_xhs)]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for dry_run in (False,True):
                for class_name,dispatch in cases:
                    with self.subTest(platform=class_name,dry_run=dry_run):
                        app=MagicMock();app.main=AsyncMock();app.douyin_upload_video=AsyncMock()
                        with patch.object(publishing,'BASE_DIR',root),patch.object(publishing,class_name,return_value=app) as constructor:
                            dispatch('标题',['episode.mp4'],[],['account.json'],dry_run=dry_run)
                        self.assertEqual(constructor.call_args.kwargs['headless'],not dry_run)

    def test_positional_video_dispatch_also_hides_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'videoFile').mkdir();(root/'cookiesFile').mkdir()
            (root/'videoFile/episode.mp4').write_bytes(b'fixture');(root/'cookiesFile/account.json').write_text('{}')
            for dry_run in (False,True):
                for class_name,dispatch in [('BaiJiaHaoVideo',publishing.post_video_baijiahao),('TouTiaoVideo',publishing.post_video_toutiao)]:
                    app=MagicMock();app.main=AsyncMock()
                    with patch.object(publishing,'BASE_DIR',root),patch.object(publishing,class_name,return_value=app):
                        dispatch('标题',['episode.mp4'],[],['account.json'],dry_run=dry_run)
                    self.assertEqual(app.headless,not dry_run)
