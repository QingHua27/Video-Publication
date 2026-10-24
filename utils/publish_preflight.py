"""Local, non-reserving publication preflight. Never logs into external platforms."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from PIL import Image
from utils.material_classification import classify_material
from utils import publish_history

VIDEO_EXTENSIONS={'.mp4','.mov','.avi','.mkv','.webm','.m4v','.flv','.wmv'}
IMAGE_EXTENSIONS={'.png','.jpg','.jpeg','.webp','.bmp','.gif','.avif'}

def preflight_publish(root,payload,*,manual=False,job_reader=None):
    root=Path(root);checks=[];warnings=[];errors=[];repeat=False;active_task=False
    def check(label,status,message):
        checks.append({'label':label,'status':status,'message':message})
        if status=='error':errors.append(message)
        elif status=='warning':warnings.append(message)
    def result():return {'ok':not errors,'checks':checks,'errors':errors,'warnings':warnings,'confirmRepeatRequired':repeat,'activeTask':active_task}
    if not isinstance(payload,dict):
        check('发布参数','error','发布参数必须是对象');return result()
    try:platform=int(payload.get('type'))
    except (TypeError,ValueError):platform=0
    if platform not in range(1,10):
        check('发布平台','error','请选择支持的发布平台');return result()
    if platform==2:
        from utils.channels_session import session_owner
        owner=session_owner()
        if owner:
            active_task=True
            check('视频号会话','error','视频号正在'+owner.get('purpose','使用')+'，请先关闭后台页面或等待操作结束后再提交')
    manual=manual is True and platform==1
    article=platform in (8,9) or (platform in (5,7) and payload.get('contentType')=='article')
    accounts=payload.get('accountList')
    if not isinstance(accounts,list) or not accounts or len(accounts)>50 or any(not isinstance(item,str) or not item for item in accounts):
        check('发布账号','error','请选择1至50个有效发布账号');accounts=[]
    files=payload.get('fileList',[])
    if not isinstance(files,list) or len(files)>50 or any(not isinstance(item,str) or not item for item in files):
        check('视频素材','error','请选择有效的视频素材路径，最多50个');files=[]
    if not article and not files:check('视频素材','error','请先选择视频素材')
    if len(set(files))!=len(files):check('视频素材','error','同一视频被重复选择，请移除重复素材')
    names={};tables=set();allowed=set()
    database=root/'db/database.db'
    if not database.is_file():check('本地资料库','error','本地账号资料库不存在')
    else:
        with closing(sqlite3.connect(database,timeout=15)) as db:
            db.execute('PRAGMA query_only=ON')
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'user_info' in tables:allowed={row[0] for row in db.execute('SELECT filePath FROM user_info WHERE type=?',(platform,))}
            if 'file_records' in tables:
                names={str(row[0]).casefold():row[1] for row in db.execute('SELECT file_path,filename FROM file_records')}
    for account in accounts:
        if account not in allowed:
            check('发布账号','error',f'账号与发布平台不匹配：{account}');continue
        if manual:
            check('发布账号','pass','半自动账号已选择，请在官方页面核对实际登录账号');continue
        path=(root/'cookiesFile'/account).resolve()
        if not path.is_relative_to((root/'cookiesFile').resolve()):
            check('登录文件','error','登录文件路径无效');continue
        try:
            value=json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(value,(dict,list)):raise ValueError('invalid storage state')
            check('登录文件','pass',f'{account}：登录文件可读取；未联网验证平台登录状态')
        except (OSError,ValueError,UnicodeError):check('登录文件','error',f'{account}：登录文件不存在、无法读取或格式损坏，请重新登录')
    def resolve_file(raw,label,extensions):
        if not isinstance(raw,str) or not raw:
            check(label,'error',f'{label}路径无效');return None
        path=Path(raw)
        if not path.is_absolute():
            path=(root/'videoFile'/path).resolve()
            if not path.is_relative_to((root/'videoFile').resolve()):
                check(label,'error',f'{label}路径越界');return None
        try:
            if path.suffix.lower() not in extensions:raise ValueError('unsupported extension')
            if not path.is_file() or path.stat().st_size==0:raise OSError('missing or empty file')
            with path.open('rb') as stream:stream.read(1)
        except (OSError,ValueError):
            check(label,'error',f'{label}不可用：{path.name}（文件不存在、为空、不可读或格式不支持）');return None
        check(label,'pass',f'{path.name}：文件存在且可读取')
        return path
    episodes=set()
    for raw in files:
        path=resolve_file(raw,'视频素材',VIDEO_EXTENSIONS)
        info=classify_material(names.get(raw.casefold(),path.name if path else Path(raw).name))
        if info['episode_number'] is not None:episodes.add((info['episode_number'],info['episode_unit']))
    covers=[]
    thumbnail=payload.get('thumbnail') or payload.get('coverImage')
    if thumbnail:covers.append(('发布封面',thumbnail,None if article else 'portrait' if platform in (1,2,4) else 'landscape'))
    elif not article:check('发布封面','warning','未指定发布封面，将使用平台默认封面；请确认是否符合预期')
    if payload.get('portraitCover'):covers.append(('抖音竖版封面',payload['portraitCover'],'portrait'))
    if payload.get('bilibiliCover43'):covers.append(('B站推荐页封面',payload['bilibiliCover43'],'recommendation'))
    images=payload.get('coverImages') or []
    if isinstance(images,list):
        covers.extend((f'图文封面{index+1}',raw,None) for index,raw in enumerate(images) if raw!=thumbnail)
    else:check('图文封面','error','图文封面列表格式无效')
    for label,raw,direction in covers:
        path=resolve_file(raw,label,IMAGE_EXTENSIONS)
        if not path:continue
        try:
            with Image.open(path) as image:
                from PIL import ImageOps
                oriented=ImageOps.exif_transpose(image);width,height=oriented.size
            with Image.open(path) as image:image.verify()
        except (OSError,ValueError,Image.DecompressionBombError):
            check(label,'error',f'{path.name}：封面图片损坏或无法读取');continue
        if direction=='portrait' and width>height:check(label,'error',f'{path.name}：该平台使用竖版封面，当前图片为横版，请重新选择')
        elif direction=='landscape' and height>width:check(label,'error',f'{path.name}：该位置使用横版封面，当前图片为竖版，请重新选择')
        else:
            ratio={'portrait':3/4,'landscape':16/9,'recommendation':4/3}.get(direction)
            if ratio and abs(width/height-ratio)>.04:check(label,'warning',f'{path.name}：封面比例为{width}×{height}，与该封面位置的建议比例不同，请核对裁剪效果')
        info=classify_material(names.get(raw.casefold(),path.name))
        if episodes and info['episode_number'] is not None and any(episode!=(info['episode_number'],info['episode_unit']) for episode in episodes):
            check('封面集数','error',f'{path.name}：封面集数与所选视频集数不一致，请检查是否沿用了上一集封面')
    if 'publish_history' in tables and files and accounts and not article:
        with closing(sqlite3.connect(database,timeout=15)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            for account in accounts:
                for source in files:
                    item=publish_history.describe(db,source,payload.get('title',''))
                    old=db.execute('SELECT * FROM publish_history WHERE platform=? AND account=? AND (identity=? OR source_path=? COLLATE NOCASE) ORDER BY updated_at DESC LIMIT 1',(platform,account,item['identity'],source)).fetchone()
                    if not old or old['status'] in ('failed','cleared'):continue
                    active=job_reader(old['job_id']) if job_reader and old['job_id'] else None
                    if active and active['status'] in ('queued','running'):
                        active_task=True
                        check('重复提交','error',f'{account} · {item["filename"]}：已有任务正在执行，请等待结束')
                    else:
                        repeat=True;check('重复发布','warning',f'{account} · {item["filename"]}：已有发布或待核对记录，请先到平台核对；继续提交仍需逐账号确认')
    if article:
        if not str(payload.get('title') or '').strip():check('图文标题','error','文章标题不能为空')
        if not str(payload.get('articleBody') or '').strip():check('图文正文','error','文章正文不能为空')
    return result()
