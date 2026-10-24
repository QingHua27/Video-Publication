import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from utils.local_materials import register_files, create_section, move_folders, list_materials

class LocalMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'db').mkdir()
        with closing(sqlite3.connect(self.root/'db/database.db')) as db:
            db.execute('CREATE TABLE file_records(id INTEGER PRIMARY KEY,filename TEXT,filesize REAL,file_path TEXT)');db.commit()
        self.video=self.root/'第一集.mp4';self.video.write_bytes(b'original')
    def tearDown(self):self.temp.cleanup()
    def test_register_only_records_path_and_deduplicates(self):
        register_files(self.root,[str(self.video)],0);register_files(self.root,[str(self.video)],0)
        rows=list_materials(self.root)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['file_path'],str(self.video.resolve()))
        self.assertEqual(rows[0]['source_kind'],'reference');self.assertFalse((self.root/'videoFile').exists())
    def test_sections_isolate_same_episode_and_move_metadata_only(self):
        a=create_section(self.root,'剧A');b=create_section(self.root,'剧B')
        register_files(self.root,[str(self.video)],a)
        other=self.root/'another';other.mkdir();v=other/'第一集.mp4';v.write_bytes(b'other')
        register_files(self.root,[str(v)],b)
        with self.assertRaises(ValueError):move_folders(self.root,a,b,['第一集'])
        move_folders(self.root,a,b,['第一集'],True)
        self.assertTrue(self.video.exists());self.assertTrue(v.exists())
        self.assertEqual([row['section_id'] for row in list_materials(self.root)],[b,b])
    def test_later_cover_and_video_join_and_stale_move_is_atomic(self):
        cover=self.root/'第一集封面竖版.png';cover.write_bytes(b'cover')
        register_files(self.root,[str(cover)],0);register_files(self.root,[str(self.video)],0)
        self.assertEqual({r['folder_name'] for r in list_materials(self.root)},{'第一集'})
        target=create_section(self.root,'新剧')
        with self.assertRaises(ValueError):move_folders(self.root,0,target,['第一集','第二集'])
        self.assertEqual({r['section_id'] for r in list_materials(self.root)},{0})
        self.assertEqual(self.video.read_bytes(),b'original');self.assertEqual(cover.read_bytes(),b'cover')

    def test_missing_source_is_reported(self):
        register_files(self.root,[str(self.video)],0);self.video.unlink()
        self.assertFalse(list_materials(self.root)[0]['available'])

    def test_video_dimensions_read_and_cached_by_source_change(self):
        from unittest.mock import patch,MagicMock
        from utils.local_materials import video_dimensions
        import cv2
        capture=MagicMock();capture.isOpened.return_value=True
        capture.get.side_effect=lambda property:1920 if property==cv2.CAP_PROP_FRAME_WIDTH else 1080
        video_dimensions.cache_clear()
        with patch.object(cv2,'VideoCapture',return_value=capture) as open_video:
            register_files(self.root,[str(self.video)],0)
            for _ in range(2):
                row=list_materials(self.root)[0]
                self.assertEqual((row['video_width'],row['video_height']),(1920,1080))
            self.assertEqual(open_video.call_count,1)
            self.video.write_bytes(b'updated source with new size')
            list_materials(self.root)
            self.assertEqual(open_video.call_count,2)
        video_dimensions.cache_clear()

if __name__=='__main__':unittest.main()
