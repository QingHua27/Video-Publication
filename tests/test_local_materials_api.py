import tempfile
import sqlite3
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import sau_backend

class LocalMaterialApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'db').mkdir()
        with closing(sqlite3.connect(self.root/'db/database.db')) as db:
            db.execute('CREATE TABLE file_records(id INTEGER PRIMARY KEY,filename TEXT,filesize REAL,file_path TEXT)');db.commit()
        self.file=self.root/'第一集 # &.mp4';self.file.write_bytes(b'0123456789')
        self.patch=patch.object(sau_backend,'BASE_DIR',self.root);self.patch.start();self.client=sau_backend.app.test_client()
        self.headers={'X-OmniPost-Local':'1','Origin':'http://127.0.0.1:5173'}
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def test_reveal_only_local_registered_material_and_never_runs_file(self):
        self.client.post('/local/materials/register',json={'paths':[str(self.file)],'sectionId':0},headers=self.headers)
        with patch('subprocess.Popen') as launch:
            denied=self.client.post('/local/materials/reveal',json={'path':str(self.file)},headers={**self.headers,'Origin':'https://example.com'})
            self.assertEqual(denied.status_code,403)
            response=self.client.post('/local/materials/reveal',json={'path':str(self.file)},headers=self.headers)
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(launch.call_args.args[0],['explorer.exe','/select,',str(self.file.resolve())])
            launch.reset_mock()
            unregistered=self.root/'other.mp4';unregistered.write_bytes(b'video')
            self.assertEqual(self.client.post('/local/materials/reveal',json={'path':str(unregistered)},headers=self.headers).status_code,400)
            self.assertEqual(self.client.post('/local/materials/reveal',json={'path':'../private.mp4'},headers=self.headers).status_code,400)
            launch.assert_not_called()

    def test_reference_preview_range_and_delete_never_touch_original(self):
        result=self.client.post('/local/materials/register',json={'paths':[str(self.file)],'sectionId':0},headers=self.headers)
        self.assertEqual(result.status_code,200,result.json)
        data=self.client.get('/getFiles').json['data'];self.assertEqual(len(data),1)
        preview=self.client.get('/getFile',query_string={'filename':data[0]['file_path']},headers={'Range':'bytes=0-3'})
        self.assertEqual(preview.status_code,206);self.assertEqual(preview.data,b'0123');preview.close()
        result=self.client.get('/deleteFile',query_string={'id':data[0]['id']})
        self.assertEqual(result.status_code,200,result.json)
        self.assertTrue(self.file.is_file());self.assertFalse((self.root/'videoFile').exists())
        self.assertEqual(self.client.get('/getFile',query_string={'filename':str(self.file)}).status_code,403)
    def test_external_page_cannot_register_or_trigger_picker(self):
        headers={**self.headers,'Origin':'https://example.com'}
        for endpoint in ['/local/materials/register','/local/materials/pick','/materialSections']:
            self.assertEqual(self.client.post(endpoint,json={},headers=headers).status_code,403)
    def test_read_origin_and_active_document_protection(self):
        self.client.post('/local/materials/register',json={'paths':[str(self.file)],'sectionId':0},headers=self.headers)
        for endpoint in ['/getFiles','/materialSections','/getFile?filename='+str(self.file)]:
            self.assertEqual(self.client.get(endpoint,headers={'Origin':'https://example.com'}).status_code,403)
            self.assertEqual(self.client.get(endpoint,headers={'Sec-Fetch-Site':'cross-site'}).status_code,403)
        self.assertEqual(self.client.get('/getFiles',headers={'Referer':'http://localhost:5173/materials'}).status_code,200)
        html=self.root/'unsafe.html';html.write_text('<script>alert(1)</script>')
        self.client.post('/local/materials/register',json={'paths':[str(html)],'sectionId':0},headers=self.headers)
        response=self.client.get('/getFile',query_string={'filename':str(html)})
        self.assertTrue(response.headers['Content-Disposition'].startswith('attachment'))
        self.assertIn('sandbox',response.headers['Content-Security-Policy']);response.close()

    def test_picker_cancel_and_sections(self):
        with patch.object(sau_backend,'pick_files',return_value=[]):
            self.assertEqual(self.client.post('/local/materials/pick',json={'kind':'image'},headers=self.headers).json['data'],[])
        section=self.client.post('/materialSections',json={'name':'剧A'},headers=self.headers).json['data']['id']
        self.assertEqual(self.client.post('/local/materials/register',json={'paths':[str(self.file)],'sectionId':section},headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/getFiles').json['data'][0]['section_name'],'剧A')
    def test_folder_delete_only_records_and_section_isolation(self):
        from utils.local_materials import register_files,create_section,database,list_materials
        a=create_section(self.root,'A');b=create_section(self.root,'B')
        ids=register_files(self.root,[str(self.file)],a);register_files(self.root,[str(self.file)],b)
        storage=self.root/'videoFile';storage.mkdir();legacy=storage/'legacy.mp4';legacy.write_bytes(b'legacy')
        with database(self.root) as db:
            record=db.execute("INSERT INTO file_records(filename,file_path,section_id,source_kind) VALUES(?,?,?,'copied')",('第一集.mp4','legacy.mp4',a));ids.append(record.lastrowid);db.commit()
        payload={'sectionId':a,'folders':['第一集'],'ids':ids}
        self.assertEqual(self.client.post('/local/materials/delete-folders',json=payload,headers={**self.headers,'Origin':'https://example.com'}).status_code,403)
        stale={**payload,'ids':ids[:1]}
        self.assertEqual(self.client.post('/local/materials/delete-folders',json=stale,headers=self.headers).status_code,409)
        self.assertEqual(len(list_materials(self.root)),3)
        result=self.client.post('/local/materials/delete-folders',json=payload,headers=self.headers)
        self.assertEqual(result.status_code,200,result.json);self.assertEqual(result.json['data']['deleted'],2)
        self.assertEqual([row['section_id'] for row in list_materials(self.root)],[b])
        self.assertEqual(self.file.read_bytes(),b'0123456789');self.assertEqual(legacy.read_bytes(),b'legacy')

    def test_old_upload_path_does_not_copy_anymore(self):
        self.assertEqual(self.client.post('/uploadSave').status_code,410)
        self.assertFalse((self.root/'videoFile').exists())

    def test_folder_links_refresh_and_deleted_record_not_restored(self):
        directory=self.root/'media';directory.mkdir();source=directory/'第二集.mp4';source.write_bytes(b'video')
        payload={'path':str(directory),'sectionId':0,'kind':'all'}
        self.assertEqual(self.client.post('/local/materials/directories',json=payload,headers={'Origin':'https://example.com'}).status_code,403)
        self.assertEqual(self.client.post('/local/materials/directories',json=payload,headers=self.headers).status_code,200)
        (directory/'第三集.mp4').write_bytes(b'new')
        response=self.client.get('/getFiles').json
        self.assertEqual(len(response['data']),2);self.assertEqual(len(response['directories']),1)
        key=next(row['id'] for row in response['data'] if row['filename']=='第二集.mp4')
        self.assertEqual(self.client.get('/deleteFile',query_string={'id':key}).status_code,200)
        rows=self.client.get('/getFiles').json['data']
        self.assertEqual([row['filename'] for row in rows],['第三集.mp4']);self.assertTrue(source.exists())
        self.assertEqual(self.client.get('/local/materials/directories',headers={'Origin':'https://example.com'}).status_code,403)

if __name__=='__main__':unittest.main()
