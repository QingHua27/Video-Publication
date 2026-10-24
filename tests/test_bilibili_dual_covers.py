import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from myUtils.postVideo import post_video_bilibili
from utils.local_materials import image_cover_role
from utils.material_classification import classify_material
from uploader.bilibili_uploader.covers import upload_recommendation_cover


class DualCoverTests(unittest.TestCase):
    def test_plain_upload_uses_web_without_collection_or_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('videoFile','cookiesFile'):(root/name).mkdir()
            (root/'videoFile/demo.mp4').touch()
            (root/'cookiesFile/6.json').write_text('{}')
            with patch('myUtils.postVideo.BASE_DIR',root), patch('myUtils.postVideo.run_biliup_command',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')) as command:
                post_video_bilibili('title',['demo.mp4'],[],['6.json'])
                args=command.call_args.args[0]
                self.assertIn('--submit',args)
                self.assertEqual(args[args.index('--submit')+1],'web')
            with patch('myUtils.postVideo.BASE_DIR',root), patch('myUtils.postVideo.run_biliup_command',return_value=SimpleNamespace(returncode=1,stdout='',stderr='ResponseData { code: 21566, message: "投稿过于频繁，建议将APP升级至最新版本后再试" }')) as command:
                with self.assertRaisesRegex(RuntimeError,'21566.*核对'):
                    post_video_bilibili('title',['demo.mp4'],[],['6.json'])
                self.assertEqual(command.call_count,1)

    def test_image_dimensions_override_ambiguous_landscape_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '第一集封面横版.png'
            for size, role in [((800,600),'recommendation_cover'),((960,540),'landscape_cover')]:
                Image.new('RGB',size).save(path)
                stat = path.stat()
                self.assertEqual(image_cover_role(str(path),stat.st_mtime_ns,stat.st_size),role)
        self.assertEqual(classify_material('第一集封面4x3.png')['material_role'],'recommendation_cover')
        self.assertEqual(classify_material('第一集封面16x9.png')['material_role'],'landscape_cover')

    def test_cover43_is_sent_only_as_web_extra_field_with_independent_space_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('videoFile','cookiesFile'):(root/name).mkdir()
            for name in ('demo.mp4','wide.png','recommended.png'):(root/'videoFile'/name).touch()
            (root/'cookiesFile/6.json').write_text('{}')
            with patch('myUtils.postVideo.BASE_DIR',root), patch('uploader.bilibili_uploader.covers.upload_recommendation_cover',return_value='https://i0.hdslb.com/43.jpg') as upload, patch('myUtils.postVideo.run_biliup_command',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')) as command:
                post_video_bilibili('title',['demo.mp4'],[],['6.json'],thumbnail_path='wide.png',recommendation_cover='recommended.png',creation_statement=1,collection_name='123')
                args=command.call_args.args[0]
                self.assertEqual(args[args.index('--cover')+1],str((root/'videoFile/wide.png').resolve()))
                fields=json.loads(args[args.index('--extra-fields')+1])
                self.assertEqual(fields['cover43'],'https://i0.hdslb.com/43.jpg')
                self.assertEqual(fields['season_id'],123)
                self.assertEqual(fields['creation_statement'],{'id':1})
                self.assertEqual(args[args.index('--submit')+1],'web')
                upload.assert_called_once()
                upload.reset_mock();command.reset_mock()
                post_video_bilibili('title',['demo.mp4'],[],['6.json'],recommendation_cover='recommended.png',dry_run=True)
                upload.assert_not_called();command.assert_not_called()

    def test_upload_failure_stops_instead_of_dropping_selected_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);image=root/'image.png';image.write_bytes(b'image')
            cookie=root/'cookie.json';cookie.write_text(json.dumps({'cookie_info':{'cookies':[{'name':'SESSDATA','value':'fixture'},{'name':'bili_jct','value':'csrf'}]}}))
            with patch('uploader.bilibili_uploader.covers.requests.Session') as session:
                session.return_value.__enter__.return_value.post.return_value.json.return_value={'code':-101}
                with self.assertRaisesRegex(RuntimeError,'上传失败'):
                    upload_recommendation_cover(image,cookie)


if __name__=='__main__':unittest.main()
