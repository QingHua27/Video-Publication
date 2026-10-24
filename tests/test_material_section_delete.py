import sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from utils.local_materials import create_section,link_directory,list_sections,list_materials,sync_directories,delete_section

class DeleteSectionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'db').mkdir()
  with closing(sqlite3.connect(self.root/'db/database.db')) as db:db.execute('CREATE TABLE file_records(id INTEGER PRIMARY KEY,filename TEXT,filesize REAL,file_path TEXT)')
  self.source=self.root/'media';self.source.mkdir();self.file=self.source/'第一集.mp4';self.file.write_bytes(b'original')
 def tearDown(self):self.temp.cleanup()
 def test_deleting_section_keeps_ids_files_and_syncs_new_files_to_unassigned(self):
  section=create_section(self.root,'测试分区');link_directory(self.root,str(self.source),section)
  original=list_materials(self.root)[0]
  self.assertEqual(delete_section(self.root,section),1)
  self.assertEqual(list_sections(self.root),[])
  self.assertEqual([(r['id'],r['section_id']) for r in list_materials(self.root)],[(original['id'],0)])
  (self.source/'第二集.mp4').write_bytes(b'next');sync_directories(self.root)
  self.assertEqual({r['section_id'] for r in list_materials(self.root)},{0});self.assertEqual(len(list_materials(self.root)),2)
  self.assertEqual(self.file.read_bytes(),b'original')
 def test_reserved_or_missing_section_cannot_be_deleted(self):
  for value in (0,False,-1,999,'oops'):
   with self.subTest(value=value),self.assertRaises(ValueError):delete_section(self.root,value)
 def test_existing_unassigned_directory_merges_and_other_sections_stay(self):
  section=create_section(self.root,'删除');other=create_section(self.root,'保留')
  link_directory(self.root,str(self.source),section);link_directory(self.root,str(self.source),0)
  before={r['id'] for r in list_materials(self.root)}
  delete_section(self.root,section);sync_directories(self.root)
  self.assertEqual({r['id'] for r in list_materials(self.root)},before)
  self.assertEqual([r['id'] for r in list_sections(self.root)],[other])
  with closing(sqlite3.connect(self.root/'db/database.db')) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM material_directories').fetchone()[0],1)
 def test_local_api_and_reserved_section_rejection(self):
  from unittest.mock import patch
  import sau_backend
  section=create_section(self.root,'删除')
  with patch.object(sau_backend,'BASE_DIR',self.root):
   client=sau_backend.app.test_client();headers={'X-OmniPost-Local':'1','Origin':'http://127.0.0.1:5173'}
   self.assertEqual(client.post('/materialSections/delete',json={'sectionId':section}).status_code,403)
   self.assertEqual(client.post('/materialSections/delete',json={'sectionId':0},headers=headers).status_code,400)
   self.assertEqual(client.post('/materialSections/delete',json={'sectionId':section},headers=headers).status_code,200)
