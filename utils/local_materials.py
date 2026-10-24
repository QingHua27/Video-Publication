"""Local references and logical sections; never copy or move source files."""
import json
import os
import sqlite3
import subprocess
import threading
from functools import lru_cache
from contextlib import closing, contextmanager
from pathlib import Path
from utils.material_classification import classify_material

@lru_cache(maxsize=4096)
def image_content_hash(path, modified, size):
    """Exact decoded pixels, dimensions and EXIF orientation; no fuzzy matching."""
    from PIL import Image, ImageOps
    import hashlib
    try:
        with Image.open(path) as image:
            if getattr(image,'n_frames',1)!=1:return ''
            pixels=ImageOps.exif_transpose(image).convert('RGBA')
            digest=hashlib.sha256(f'{pixels.width}x{pixels.height}:RGBA:'.encode())
            digest.update(pixels.tobytes())
        stat=Path(path).stat()
        return digest.hexdigest() if stat.st_mtime_ns==modified and stat.st_size==size else ''
    except (OSError, ValueError, Image.DecompressionBombError):
        return ''

@lru_cache(maxsize=4096)
def image_cover_role(path, modified, size):
    from PIL import Image
    try:
        with Image.open(path) as image:
            width, height = image.size
        ratio = width / height
        if abs(ratio - 4/3) < 0.025:
            return 'recommendation_cover'
        if abs(ratio - 3/4) < 0.025:
            return 'portrait_cover'
        if abs(ratio - 16/9) < 0.025:
            return 'landscape_cover'
    except (OSError, ValueError, ZeroDivisionError):
        pass
    return None

@lru_cache(maxsize=4096)
def video_dimensions(path,modified,size):
    capture=None
    try:
        import cv2
        capture=cv2.VideoCapture(path,cv2.CAP_FFMPEG,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,3000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,3000])
        if capture.isOpened():
            width,height=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if width>0 and height>0:return width,height
    except Exception:
        # Unreadable metadata must not make the rest of the library unavailable.
        pass
    finally:
        if capture is not None:capture.release()
    return 0,0

@contextmanager
def database(root):
    with closing(sqlite3.connect(Path(root)/'db/database.db',timeout=15)) as db:
        db.row_factory=sqlite3.Row
        columns={row[1] for row in db.execute('PRAGMA table_info(file_records)')}
        for name,definition in [('section_id','INTEGER NOT NULL DEFAULT 0'),('source_kind',"TEXT NOT NULL DEFAULT 'copied'"),('source_mtime_ns','INTEGER NOT NULL DEFAULT 0')]:
            if name not in columns:
                try:db.execute(f'ALTER TABLE file_records ADD COLUMN {name} {definition}')
                except sqlite3.OperationalError as error:
                    if 'duplicate column' not in str(error).lower():raise
        db.execute('CREATE TABLE IF NOT EXISTS material_sections(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE)')
        db.execute("CREATE TABLE IF NOT EXISTS material_directories(id INTEGER PRIMARY KEY,path TEXT NOT NULL COLLATE NOCASE,section_id INTEGER NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'ready',message TEXT NOT NULL DEFAULT '',UNIQUE(path,section_id))")
        db.execute('CREATE TABLE IF NOT EXISTS material_directory_files(directory_id INTEGER NOT NULL,file_id INTEGER NOT NULL,path TEXT NOT NULL COLLATE NOCASE,PRIMARY KEY(directory_id,path))')
        db.execute('CREATE TABLE IF NOT EXISTS material_directory_episode_sections(directory_id INTEGER NOT NULL,folder_name TEXT NOT NULL,section_id INTEGER NOT NULL,PRIMARY KEY(directory_id,folder_name))')
        db.execute('CREATE TABLE IF NOT EXISTS material_directory_exclusions(directory_id INTEGER NOT NULL,path TEXT NOT NULL COLLATE NOCASE,PRIMARY KEY(directory_id,path))')
        db.commit()
        yield db

def validate_section(db,value):
    if isinstance(value,bool):raise ValueError('分区参数无效')
    try:section=int(value)
    except (TypeError,ValueError):raise ValueError('请先选择分区')
    if section<0 or (section and not db.execute('SELECT id FROM material_sections WHERE id=?',(section,)).fetchone()):
        raise ValueError('分区不存在，请刷新后重新选择')
    return section

def create_section(root,name):
    if not isinstance(name,str) or not name.strip() or len(name.strip())>60 or name.strip()=='未分区':raise ValueError('分区名称需为1至60字，且不能使用保留名称“未分区”')
    with database(root) as db:
        try:
            result=db.execute('INSERT INTO material_sections(name) VALUES(?)',(name.strip(),));db.commit();return result.lastrowid
        except sqlite3.IntegrityError:raise ValueError('已有同名分区')

def delete_section(root,section):
    """Remove a classification, retaining material IDs, files and history."""
    with _sync_lock:
        with database(root) as db:
            with db:
                db.execute('BEGIN IMMEDIATE')
                section=validate_section(db,section)
                if section==0:raise ValueError('未分区是系统保留分类，不能删除')
                count=db.execute('SELECT COUNT(*) FROM file_records WHERE section_id=?',(section,)).fetchone()[0]
                db.execute('UPDATE file_records SET section_id=0 WHERE section_id=?',(section,))
                db.execute('UPDATE material_directory_episode_sections SET section_id=0 WHERE section_id=?',(section,))
                for source in db.execute('SELECT id,path,kind FROM material_directories WHERE section_id=?',(section,)).fetchall():
                    target=db.execute('SELECT id,kind FROM material_directories WHERE path=? COLLATE NOCASE AND section_id=0',(source['path'],)).fetchone()
                    if not target:
                        db.execute('UPDATE material_directories SET section_id=0 WHERE id=?',(source['id'],));continue
                    # Same folder may already be associated with Unassigned. Merge
                    # ownership metadata without deleting any existing material IDs.
                    db.execute('INSERT OR IGNORE INTO material_directory_files(directory_id,file_id,path) SELECT ?,file_id,path FROM material_directory_files WHERE directory_id=?',(target['id'],source['id']))
                    db.execute('INSERT OR IGNORE INTO material_directory_exclusions(directory_id,path) SELECT ?,path FROM material_directory_exclusions WHERE directory_id=?',(target['id'],source['id']))
                    db.execute('INSERT OR IGNORE INTO material_directory_episode_sections(directory_id,folder_name,section_id) SELECT ?,folder_name,section_id FROM material_directory_episode_sections WHERE directory_id=?',(target['id'],source['id']))
                    if target['kind']!=source['kind']:db.execute("UPDATE material_directories SET kind='all' WHERE id=?",(target['id'],))
                    for table in ('material_directory_files','material_directory_exclusions','material_directory_episode_sections'):
                        db.execute(f'DELETE FROM {table} WHERE directory_id=?',(source['id'],))
                    db.execute('DELETE FROM material_directories WHERE id=?',(source['id'],))
                db.execute('DELETE FROM material_sections WHERE id=?',(section,))
                return count


def list_sections(root):
    with database(root) as db:
        return [dict(row) for row in db.execute('SELECT s.id,s.name,COUNT(f.file_path) AS count FROM material_sections s LEFT JOIN file_records f ON f.section_id=s.id GROUP BY s.id ORDER BY s.id')]

def list_materials(root):
    with database(root) as db:
        rows=[dict(row) for row in db.execute("SELECT f.*,COALESCE(s.name,'未分区') AS section_name FROM file_records f LEFT JOIN material_sections s ON s.id=f.section_id")]
    for row in rows:
        path=Path(row['file_path']) if row['source_kind']=='reference' else Path(root)/'videoFile'/row['file_path']
        row.update(classify_material(row['filename']))
        row['available']=path.is_file()
        if row['available'] and row['material_role'] in ('image','landscape_cover','portrait_cover','recommendation_cover'):
            try:
                stat = path.stat()
                detected = image_cover_role(str(path), stat.st_mtime_ns, stat.st_size)
                row['image_content_hash'] = image_content_hash(str(path),stat.st_mtime_ns,stat.st_size)
                if detected:
                    row['material_role'] = detected
            except OSError:
                pass
        if row['available'] and row['material_role']=='video':
            try:
                stat=path.stat()
                row['video_width'],row['video_height']=video_dimensions(str(path),stat.st_mtime_ns,stat.st_size)
            except OSError:
                row['video_width']=row['video_height']=0
        row['uuid']=str(row.get('id','')) if row['source_kind']=='reference' else row['file_path'].split('_',1)[0]
    return rows

def register_files(root,paths,section):
    if not isinstance(paths,list) or not paths or len(paths)>1000:raise ValueError('请选择1至1000个本地文件')
    resolved=[]
    for raw in paths:
        if not isinstance(raw,str) or not Path(raw).is_absolute():raise ValueError('需要完整的本地文件路径，请使用本机选择窗口')
        path=Path(raw).resolve()
        if not path.is_file():raise ValueError(f'文件不存在：{path.name}')
        if os.path.normcase(str(path)) not in {os.path.normcase(str(p)) for p in resolved}:resolved.append(path)
    ids=[]
    with database(root) as db:
        section=validate_section(db,section)
        with db:
            for path in resolved:
                existing=db.execute('SELECT id FROM file_records WHERE file_path=? COLLATE NOCASE AND section_id=?',(str(path),section)).fetchone()
                if existing:ids.append(existing['id']);continue
                record=db.execute("INSERT INTO file_records(filename,filesize,file_path,section_id,source_kind) VALUES(?,?,?,?,'reference')",(path.name,round(path.stat().st_size/1048576,2),str(path),section))
                ids.append(record.lastrowid)
    return ids

def move_folders(root,source,target,folders,merge=False):
    if not isinstance(folders,list) or not folders or len(folders)>1000 or any(not isinstance(name,str) for name in folders):raise ValueError('请选择需要移动的文件夹')
    with database(root) as db:
        source=validate_section(db,source);target=validate_section(db,target)
        if source==target:raise ValueError('目标分区与当前分区相同')
        with db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute('SELECT id,filename,section_id FROM file_records WHERE section_id IN (?,?)',(source,target)).fetchall()
            sources=[row for row in rows if row['section_id']==source and classify_material(row['filename'])['folder_name'] in folders]
            found={classify_material(row['filename'])['folder_name'] for row in sources}
            if found!=set(folders):raise ValueError('部分文件夹已变化，请刷新后重试')
            conflicts=found & {classify_material(row['filename'])['folder_name'] for row in rows if row['section_id']==target}
            if conflicts and not merge:raise ValueError('目标存在同名文件夹：'+ '、'.join(sorted(conflicts))+'；如确认合并，请再次确认')
            for row in sources:
                for link in db.execute('SELECT directory_id FROM material_directory_files WHERE file_id=?',(row['id'],)).fetchall():
                    db.execute('INSERT INTO material_directory_episode_sections(directory_id,folder_name,section_id) VALUES(?,?,?) ON CONFLICT(directory_id,folder_name) DO UPDATE SET section_id=excluded.section_id',(link['directory_id'],classify_material(row['filename'])['folder_name'],target))
            db.executemany('UPDATE file_records SET section_id=? WHERE id=?',[(target,row['id']) for row in sources])
            return len(sources)

def delete_folder_records(root,section,folders,ids):
    """Delete an exact confirmed snapshot of records; never touch the filesystem."""
    if not isinstance(folders,list) or not folders or len(folders)>1000 or any(not isinstance(name,str) for name in folders):raise ValueError('请选择需要删除记录的文件夹')
    if not isinstance(ids,list) or not ids or any(type(value) is not int for value in ids):raise ValueError('素材记录参数无效，请刷新重试')
    with database(root) as db:
        section=validate_section(db,section)
        with db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute('SELECT id,filename FROM file_records WHERE section_id=?',(section,)).fetchall()
            selected=[row for row in rows if classify_material(row['filename'])['folder_name'] in folders]
            if {row['id'] for row in selected}!=set(ids) or {classify_material(row['filename'])['folder_name'] for row in selected}!=set(folders):
                raise ValueError('所选文件夹内容已变化，请刷新后重新确认删除')
            exclude_directory_records(db,[row['id'] for row in selected])
            db.executemany('DELETE FROM file_records WHERE id=?',[(row['id'],) for row in selected])
            return len(selected)


_picker_lock = threading.Lock()

def pick_files(root,kind):
    if kind not in ('all','video','image','folder'):raise ValueError('文件类型无效')
    if not _picker_lock.acquire(blocking=False):raise RuntimeError('已有文件选择窗口打开，请先完成或取消选择')
    startup = subprocess.STARTUPINFO() if os.name=='nt' else None
    if startup is not None:
        startup.lpDesktop='winsta0\\default'
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow=1
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(Path(root)/'utils/pick-materials.ps1'),'-Kind',kind],startupinfo=startup,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired:
        raise RuntimeError('文件选择已超时，请重新打开选择窗口')
    finally:
        _picker_lock.release()
    if result.returncode:raise RuntimeError('无法打开本机文件选择窗口，请确认客户端在当前桌面运行')
    paths=json.loads(result.stdout.decode('utf-8-sig').strip() or '[]')
    if not isinstance(paths,list):raise RuntimeError('文件选择结果无效')
    if kind=='folder':return [{'path':str(Path(path).resolve()),'name':Path(path).name,'size':0,'directory':True} for path in paths if Path(path).is_dir()]
    return [{'path':str(Path(path).resolve()),'name':Path(path).name,'size':Path(path).stat().st_size} for path in paths if Path(path).is_file()]


_sync_lock=threading.Lock()


def exclude_directory_records(db,ids):
    for key in ids:
        db.execute('INSERT OR IGNORE INTO material_directory_exclusions(directory_id,path) SELECT directory_id,path FROM material_directory_files WHERE file_id=?',(key,))


def scan_directory(path,kind):
    media=[]
    def error(problem):raise problem
    for parent,dirs,names in os.walk(path,followlinks=False,onerror=error):
        dirs[:]=[name for name in dirs if not (Path(parent)/name).is_symlink() and not (getattr(Path(parent)/name,'is_junction',lambda:False)())]
        for name in names:
            file=Path(parent)/name
            if file.is_symlink() or not file.is_file():continue
            role=classify_material(name)['material_role']
            if role=='other' or (kind=='video' and role!='video') or (kind=='image' and role=='video'):continue
            stat=file.stat();media.append((str(file.resolve()),file.name,round(stat.st_size/1048576,2),stat.st_mtime_ns))
            if len(media)>50000:raise ValueError('单个文件夹超过5万个素材，请选择更小的子文件夹')
    return media


def link_directory(root,path,section,kind='all'):
    if kind not in ('all','video','image'):raise ValueError('素材类型无效')
    if not isinstance(path,str) or not Path(path).is_absolute():raise ValueError('请选择完整的本地文件夹路径')
    folder=Path(path).resolve()
    if not folder.is_dir():raise ValueError('文件夹不存在或暂时无法访问')
    # Validate and enumerate before saving a new association.
    files=scan_directory(folder,kind)
    selected={os.path.normcase(path) for path,_,_,_ in files}
    with _sync_lock:
        with database(root) as db:
            section=validate_section(db,section)
            with db:
                db.execute('BEGIN IMMEDIATE')
                parents=[row for row in db.execute('SELECT * FROM material_directories WHERE section_id=?',(section,))
                         if Path(row['path']).resolve()!=folder and folder.is_relative_to(Path(row['path']).resolve())]
                db.execute("INSERT INTO material_directories(path,section_id,kind) VALUES(?,?,?) ON CONFLICT(path,section_id) DO UPDATE SET kind=excluded.kind",(str(folder),section,kind))
                target=db.execute('SELECT id FROM material_directories WHERE path=? COLLATE NOCASE AND section_id=?',(str(folder),section)).fetchone()['id']
                for parent in parents:
                    # Preserve retained IDs, explicit removals and moved episode destinations.
                    mappings=db.execute('SELECT file_id,path FROM material_directory_files WHERE directory_id=?',(parent['id'],)).fetchall()
                    for mapping in mappings:
                        if os.path.normcase(mapping['path']) in selected:
                            db.execute('INSERT OR IGNORE INTO material_directory_files(directory_id,file_id,path) VALUES(?,?,?)',(target,mapping['file_id'],mapping['path']))
                    for exclusion in db.execute('SELECT path FROM material_directory_exclusions WHERE directory_id=?',(parent['id'],)).fetchall():
                        if os.path.normcase(exclusion['path']) in selected:
                            db.execute('INSERT OR IGNORE INTO material_directory_exclusions(directory_id,path) VALUES(?,?)',(target,exclusion['path']))
                    db.execute('INSERT OR IGNORE INTO material_directory_episode_sections(directory_id,folder_name,section_id) SELECT ?,folder_name,section_id FROM material_directory_episode_sections WHERE directory_id=?',(target,parent['id']))
                    for table in ('material_directory_files','material_directory_exclusions','material_directory_episode_sections'):
                        db.execute(f'DELETE FROM {table} WHERE directory_id=?',(parent['id'],))
                    db.execute('DELETE FROM material_directories WHERE id=?',(parent['id'],))
                    for mapping in mappings:
                        db.execute("DELETE FROM file_records WHERE id=? AND section_id=? AND source_kind='reference' AND NOT EXISTS(SELECT 1 FROM material_directory_files WHERE file_id=file_records.id)",(mapping['file_id'],section))
    return sync_directories(root)


def sync_directories(root):
    with _sync_lock:
        with database(root) as db:
            directories=[dict(row) for row in db.execute('SELECT * FROM material_directories ORDER BY id')]
        for directory in directories:
            try:
                if not Path(directory['path']).is_dir():raise OSError('文件夹不存在或无法访问')
                files=scan_directory(directory['path'],directory['kind'])
                with database(root) as db:
                    with db:
                        for path,name,size,modified in files:
                            if db.execute('SELECT 1 FROM material_directory_exclusions WHERE directory_id=? AND path=?',(directory['id'],path)).fetchone():continue
                            override=db.execute('SELECT section_id FROM material_directory_episode_sections WHERE directory_id=? AND folder_name=?',(directory['id'],classify_material(name)['folder_name'])).fetchone()
                            section=override['section_id'] if override else directory['section_id']
                            mapping=db.execute('SELECT file_id FROM material_directory_files WHERE directory_id=? AND path=?',(directory['id'],path)).fetchone()
                            record=db.execute('SELECT id FROM file_records WHERE id=? AND file_path=? COLLATE NOCASE',(mapping['file_id'],path)).fetchone() if mapping else db.execute("SELECT id FROM file_records WHERE file_path=? COLLATE NOCASE AND section_id=? AND source_kind='reference'",(path,section)).fetchone()
                            # A removed mapping is a user removal, not a request to re-add it.
                            if mapping and not record:continue
                            if record:
                                file_id=record['id']
                                db.execute('UPDATE file_records SET filename=?,filesize=?,source_mtime_ns=? WHERE id=?',(name,size,modified,file_id))
                            else:
                                cursor=db.execute("INSERT INTO file_records(filename,filesize,file_path,section_id,source_kind,source_mtime_ns) VALUES(?,?,?,?,'reference',?)",(name,size,path,section,modified));file_id=cursor.lastrowid
                            db.execute('INSERT OR IGNORE INTO material_directory_files(directory_id,file_id,path) VALUES(?,?,?)',(directory['id'],file_id,path))
                        directory.update(status='ready',message=f'已同步 {len(files)} 个视频或图片')
                        db.execute('UPDATE material_directories SET status=?,message=? WHERE id=?',(directory['status'],directory['message'],directory['id']))
            except (OSError,ValueError) as problem:
                directory.update(status='unavailable',message=str(problem))
                with database(root) as db:
                    db.execute('UPDATE material_directories SET status=?,message=? WHERE id=?',(directory['status'],directory['message'],directory['id']));db.commit()
        return directories


def list_directories(root):
    with database(root) as db:
        return [dict(row) for row in db.execute('SELECT * FROM material_directories ORDER BY id')]
