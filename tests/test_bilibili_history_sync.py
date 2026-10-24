import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from utils.bilibili_history_sync import match_archives, sync_account, fetch_published
from utils import publish_history


class MatchTests(unittest.TestCase):
    def groups(self):
        return [dict(key='a1',series='剧甲',episode=1,source='a1.mp4',aliases={'开端'}),
                dict(key='a2',series='剧甲',episode=2,source='a2.mp4',aliases=set()),
                dict(key='b1',series='剧乙',episode=1,source='b1.mp4',aliases={'开端'})]

    def test_series_and_episode_or_chapter_are_unique_and_published_only(self):
        records=[{'aid':1,'state':0,'title':'《剧甲》第一集'},
                 {'aid':2,'state':0,'title':'剧乙-开端'},
                 {'aid':3,'state':-30,'title':'剧甲第二集'},
                 {'aid':4,'state':0,'title':'第一集'},
                 {'aid':5,'title':'剧甲第二集'}]
        matched=match_archives(records,self.groups(),{})
        self.assertEqual({key:item['aid'] for key,item in matched.items()},{'a1':1,'b1':2})

    def test_description_can_identify_episode_but_conflicts_are_rejected(self):
        rows=[{'aid':1,'state':0,'title':'第一集','desc':'小说《剧甲》解读'},
              {'aid':2,'state':0,'title':'剧甲第二集','desc':'剧乙第一集'}]
        self.assertEqual(set(match_archives(rows,self.groups(),{})),{'a1'})

    def test_unique_previous_account_title_maps_manual_upload_without_number(self):
        row={'aid':1,'state':0,'title':'剧甲-改名章节'}
        self.assertEqual(set(match_archives([row],self.groups(),{'剧甲改名章节':{'a2'}})),{'a2'})
        self.assertFalse(match_archives([row],self.groups(),{'剧甲改名章节':{'a1','a2'}}))

    def test_sync_persists_per_account_and_is_idempotent_without_overwriting_active_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'db').mkdir()
            source=str(root/'第一集.mp4')
            with sqlite3.connect(root/'db/database.db') as db:
                db.execute('CREATE TABLE file_records(id INTEGER,filename TEXT,file_path TEXT,section_id INTEGER,source_kind TEXT)')
                db.execute('INSERT INTO file_records VALUES(1,?,?,1,?)',('第一集.mp4',source,'reference'))
                db.execute('CREATE TABLE material_sections(id INTEGER,name TEXT)')
                db.execute('INSERT INTO material_sections VALUES(1,?)',('剧甲',))
            db.close()
            with patch('utils.bilibili_history_sync.fetch_published',return_value=[{'aid':1,'state':0,'title':'剧甲第一集'}]):
                active=publish_history.reserve(root,6,['active.json'],[source],'剧甲第一集','running')
                self.assertEqual(sync_account(root,'active.json',lambda key:{'status':'running'})['updated'],0)
                self.assertEqual(sync_account(root,'confirmed.json',lambda key:None)['updated'],1)
                self.assertEqual(sync_account(root,'confirmed.json',lambda key:None)['updated'],0)
                rows=publish_history.list_records(root)
                self.assertEqual({row['account']:row['status'] for row in rows},{'active.json':'pending','confirmed.json':'published'})

    def test_fetch_paginates_and_asks_only_for_published_archives(self):
        first=[{'Archive':{'aid':n,'state':0}} for n in range(1,51)]
        payloads=[{'data':{'arc_audits':first,'page':{'count':51}}},
                  {'data':{'arc_audits':[{'Archive':{'aid':51,'state':0}}],'page':{'count':51}}}]
        with patch('utils.bilibili_history_sync.load_bilibili_cookies',return_value={}),patch('utils.bilibili_history_sync.fetch_archives_payload',side_effect=payloads) as fetch:
            self.assertEqual(len(fetch_published('fixture.json')),51)
            self.assertEqual([call.kwargs['page'] for call in fetch.call_args_list],[1,2])
            self.assertTrue(all(call.kwargs['status']=='pubed' for call in fetch.call_args_list))


if __name__=='__main__':unittest.main()
