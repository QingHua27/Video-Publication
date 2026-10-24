import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sau_backend

class UploadStorageTests(unittest.TestCase):
    def test_413_is_reported_as_json_for_active_upload_path(self):
        with patch.dict(sau_backend.app.config,MAX_CONTENT_LENGTH=10):
            response=sau_backend.app.test_client().post('/upload',data={'file':(io.BytesIO(b'x'*20),'video.mp4')})
            self.assertEqual(response.status_code,413)
            self.assertEqual(response.json['code'],413)
            self.assertTrue(response.json['msg'])
    def test_local_video_upload_has_no_arbitrary_160mb_cap(self):
        self.assertIsNone(sau_backend.app.config['MAX_CONTENT_LENGTH'])

    def test_retired_library_copy_endpoint_rejects_without_writing_files(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(sau_backend,'BASE_DIR',Path(folder)):
            response=sau_backend.app.test_client().post('/uploadSave',data={'file':(io.BytesIO(b'video fixture'),'第十二集封面竖版.png')})
            self.assertEqual(response.status_code,410,response.json)
            self.assertEqual(response.json['code'],410)
            self.assertIn('本地路径',response.json['msg'])
            self.assertEqual(list(Path(folder).iterdir()),[])
    def test_upload_recreates_missing_material_directory(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(sau_backend,'BASE_DIR',Path(folder)):
            response=sau_backend.app.test_client().post('/upload',data={'file':(io.BytesIO(b'image fixture'),'封面.png')})
            self.assertEqual(response.status_code,200,response.json)
            saved=Path(folder)/'videoFile'/response.json['data']
            self.assertEqual(saved.read_bytes(),b'image fixture')

if __name__=='__main__':unittest.main()
