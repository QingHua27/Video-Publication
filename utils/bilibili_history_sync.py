"""Read published Bilibili archives and reconcile only unambiguous local episodes."""
import csv
import re
import threading
import time
import unicodedata
from pathlib import Path

from utils import publish_history
from utils.local_materials import list_materials
from utils.material_classification import classify_material
from uploader.bilibili_uploader.content_stats import (
    load_bilibili_cookies, fetch_archives_payload, _extract_list, _archive_block,
)

_lock = threading.Lock()
_cache = {}


def normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKC',str(value or '')).casefold() if char.isalnum())


def episode_numbers(text):
    return {classify_material(match.group())['episode_number'] for match in re.finditer(
        r'第\s*[0-9零〇一二两三四五六七八九十百千万]+\s*[集话期]|\bEP?\s*0*[0-9]+\b',str(text),re.I)} - {None}


def match_archives(archives, groups, previous_titles):
    result={}
    keys={group['key'] for group in groups}
    for archive in archives:
        if archive.get('state') not in (0,'0') or not (archive.get('aid') or archive.get('bvid')):
            continue
        title=normalized(archive.get('title'))
        text=f"{archive.get('title','')} {archive.get('desc','')}"
        whole=normalized(text)
        numbers=episode_numbers(text)
        candidates=set(previous_titles.get(title,set())) & keys if title else set()
        if len(candidates)>1:
            continue
        if not candidates:
            for group in groups:
                series=normalized(group['series'])
                if not series or series not in whole:
                    continue
                remainder=title.replace(series,'',1)
                if (numbers == {group['episode']} or
                    (not numbers and remainder and remainder in {normalized(alias) for alias in group['aliases']})):
                    candidates.add(group['key'])
        # Titles/descriptions containing conflicting episode references must not be guessed.
        if len(candidates)==1 and len(numbers)<=1:
            key=next(iter(candidates))
            group=next(group for group in groups if group['key']==key)
            if not numbers or numbers=={group['episode']}:
                result[key]=archive
    return result


def fetch_published(account_file):
    cookies=load_bilibili_cookies(account_file)
    archives=[];seen=set()
    for page in range(1,101):
        payload=fetch_archives_payload(cookies,page_size=50,page=page,status='pubed')
        raw=_extract_list(payload)
        for item in raw:
            archive=_archive_block(item)
            key=archive.get('aid') or archive.get('bvid')
            if key and key in seen:
                raise ValueError('B站稿件分页重复，本次未写入同步结果')
            if key:seen.add(key)
            archives.append(archive)
        count=(payload.get('data') or {}).get('page',{}).get('count')
        if (count is not None and page*50>=int(count)) or len(raw)<50:
            return archives
    raise ValueError('B站投稿超过5000条，本次未写入同步结果')


def local_groups(root):
    materials=[item for item in list_materials(root) if item['material_role']=='video' and item.get('episode_number')]
    groups={}
    with publish_history.database(root) as db:
        for material in materials:
            item=publish_history.describe(db,material['file_path'])
            if item['identity'] not in groups:
                parent=Path(material['file_path']).parent
                series=item['series']
                if not material.get('section_id') and parent.name in ('成片','videos','videoFile'):
                    series=parent.parent.name
                groups[item['identity']]=dict(key=item['identity'],series=series,episode=item['episode'],source=material['file_path'],aliases=set())
        # Chapter titles are optional data, read only beside registered local videos.
        for parent in {Path(material['file_path']).parent for material in materials}:
            manifest=parent/'剧集清单.csv'
            try:
                if not manifest.is_file() or manifest.stat().st_size>2*1024*1024:continue
                with manifest.open(encoding='utf-8-sig',newline='') as handle:
                    for row in csv.DictReader(handle):
                        source=Path(row.get('成片',''))
                        if source.parent!=parent:continue
                        number=int(row.get('集数','0'))
                        for group in groups.values():
                            if Path(group['source']).parent==parent and group['episode']==number and row.get('章节'):
                                group['aliases'].add(row['章节'])
            except (OSError,UnicodeError,ValueError,csv.Error):
                continue
    return list(groups.values())


def sync_account(root, account_file, job_reader):
    archives=fetch_published(Path(root)/'cookiesFile'/account_file)
    groups=local_groups(root)
    with publish_history.database(root) as db:
        prior={}
        for row in db.execute('SELECT title,identity FROM publish_history WHERE platform=6 AND account=?',(account_file,)):
            prior.setdefault(normalized(row['title']),set()).add(row['identity'])
        matches=match_archives(archives,groups,prior)
        changed=0
        db.execute('BEGIN IMMEDIATE')
        for group in groups:
            archive=matches.get(group['key'])
            if not archive:continue
            old=db.execute('SELECT id,status,job_id FROM publish_history WHERE platform=6 AND account=? AND identity=?',(account_file,group['key'])).fetchone()
            active=job_reader(old['job_id']) if old and old['job_id'] else None
            if active and active['status'] in ('queued','running'):continue
            if old and old['status']=='published':continue
            item=publish_history.describe(db,group['source'],archive.get('title',''))
            message=f"B站自动核对已发布：{archive.get('bvid') or archive.get('aid')}"
            if old:
                db.execute('UPDATE publish_history SET status=?,message=?,title=?,updated_at=? WHERE id=?',('published',message,item['title'],time.time(),old['id']))
            else:
                db.execute('''INSERT INTO publish_history(platform,account,identity,series,episode,filename,source_path,title,status,message,updated_at)
                    VALUES(6,?,?,?,?,?,?,?,'published',?,?)''',(account_file,item['identity'],item['series'],item['episode'],item['filename'],item['source_path'],item['title'],message,time.time()))
            changed+=1
        db.commit()
    return {'published':sum(item.get('state') in (0,'0') for item in archives),'matched':len(matches),'updated':changed}


def sync_accounts(root, accounts, job_reader, force=False):
    if not _lock.acquire(blocking=False):
        return {'busy':True,'accounts':[],'errors':[]}
    try:
        results=[];errors=[]
        for account_id, account_file in accounts:
            key=(str(root),account_id,account_file)
            cached=_cache.get(key)
            if not force and cached and time.monotonic()-cached[0]<300:
                results.append({'accountId':account_id,**cached[1],'cached':True});continue
            try:
                result=sync_account(root,account_file,job_reader)
                _cache[key]=(time.monotonic(),result)
                results.append({'accountId':account_id,**result})
            except Exception as error:
                # No credentials or remote request details are returned to the browser.
                errors.append({'accountId':account_id,'message':'B站同步失败，请检查账号登录状态或网络后重试'})
        return {'accounts':results,'errors':errors,'busy':False}
    finally:
        _lock.release()
