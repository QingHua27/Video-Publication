import sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from utils.local_materials import link_directory,sync_directories,list_materials,create_section,delete_folder_records,move_folders
class DirectorySyncTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'db').mkdir()
  with closing(sqlite3.connect(self.root/'db/database.db')) as db:db.execute('CREATE TABLE file_records(id INTEGER PRIMARY KEY,filename TEXT,filesize REAL,file_path TEXT)')
  self.source=self.root/'source';self.source.mkdir();self.video=self.source/'第一集.mp4';self.video.write_bytes(b'original')
 def tearDown(self):self.temp.cleanup()
 def test_recursive_sync_deduplicates_updates_and_keeps_missing(self):
  sub=self.source/'covers';sub.mkdir();(sub/'第一集封面竖版.png').write_bytes(b'image');(sub/'ignore.txt').write_text('ignore')
  a=create_section(self.root,'A');link_directory(self.root,str(self.source),a,'all');sync_directories(self.root)
  rows=list_materials(self.root);self.assertEqual(len(rows),2);self.assertEqual({r['folder_name'] for r in rows},{'第一集'})
  oldid=next(r['id'] for r in rows if r['filename']==self.video.name)
  self.video.write_bytes(b'x'*1048576);(self.source/'第二集.mp4').write_bytes(b'next');sync_directories(self.root)
  rows=list_materials(self.root);self.assertEqual(len(rows),3);self.assertEqual(next(r['filesize'] for r in rows if r['id']==oldid),1)
  self.video.unlink();sync_directories(self.root);self.assertFalse(next(r['available'] for r in list_materials(self.root) if r['id']==oldid))
  self.assertFalse((self.root/'videoFile').exists())
 def test_deleted_record_stays_deleted_and_moves_stay_moved(self):
  a=create_section(self.root,'A');b=create_section(self.root,'B');link_directory(self.root,str(self.source),a,'all')
  row=list_materials(self.root)[0];move_folders(self.root,a,b,['第一集']);sync_directories(self.root)
  self.assertEqual([(r['id'],r['section_id']) for r in list_materials(self.root)],[(row['id'],b)])
  delete_folder_records(self.root,b,['第一集'],[row['id']]);sync_directories(self.root)
  self.assertEqual(list_materials(self.root),[]);self.assertEqual(self.video.read_bytes(),b'original')
 def test_repeat_link_and_missing_directory(self):
  link_directory(self.root,str(self.source),0,'video');link_directory(self.root,str(self.source),0,'video')
  self.assertEqual(len(list_materials(self.root)),1)
  renamed=self.root/'offline';self.source.rename(renamed);result=sync_directories(self.root)
  self.assertEqual(result[0]['status'],'unavailable');self.assertEqual(len(list_materials(self.root)),1)

 def test_later_video_follows_moved_episode_cover(self):
  self.video.unlink();(self.source/'第一集封面竖版.png').write_bytes(b'cover')
  a=create_section(self.root,'A');b=create_section(self.root,'B');link_directory(self.root,str(self.source),a)
  move_folders(self.root,a,b,['第一集']);self.video.write_bytes(b'later');sync_directories(self.root)
  self.assertEqual({r['section_id'] for r in list_materials(self.root)},{b})

 def test_narrow_link_replaces_parent_and_preserves_files_and_ids(self):
  final=self.source/'成片';final.mkdir();finished=final/'第二集.mp4';finished.write_bytes(b'final')
  section=create_section(self.root,'A');link_directory(self.root,str(self.source),section)
  before={r['file_path']:r['id'] for r in list_materials(self.root)}
  links=link_directory(self.root,str(final),section)
  self.assertEqual([d['path'] for d in links],[str(final.resolve())])
  self.assertEqual([(r['file_path'],r['id']) for r in list_materials(self.root)],[(str(finished.resolve()),before[str(finished.resolve())])])
  sync_directories(self.root);self.assertEqual(len(list_materials(self.root)),1)
  self.assertTrue(self.video.exists());self.assertTrue(finished.exists())
 def test_narrow_link_keeps_other_sections_and_unrelated_links(self):
  final=self.source/'成片';final.mkdir();(final/'第二集.mp4').write_bytes(b'final')
  a=create_section(self.root,'A');b=create_section(self.root,'B')
  link_directory(self.root,str(self.source),a);move_folders(self.root,a,b,['第一集'])
  other=self.root/'other';other.mkdir();(other/'第三集.mp4').write_bytes(b'other');link_directory(self.root,str(other),a)
  link_directory(self.root,str(final),a)
  self.assertEqual({r['filename'] for r in list_materials(self.root)},{'第一集.mp4','第二集.mp4','第三集.mp4'})
  self.assertEqual(next(r['section_id'] for r in list_materials(self.root) if r['filename']=='第一集.mp4'),b)
