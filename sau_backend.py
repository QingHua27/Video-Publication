import asyncio
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from myUtils.auth import check_cookie
from flask import Flask, request, jsonify, Response, render_template, send_from_directory, send_file
from conf import BASE_DIR
from utils.publish_collections import validate_collection, CollectionSelectionError
from utils.publish_jobs import create_job, update_job, read_job, claim_job, list_jobs, record_preflight
from utils import publish_history
from utils.collection_catalog import discover_collections, CollectionCatalogError
from utils.material_classification import classify_material
from utils.local_materials import database as material_database, register_files, create_section, list_sections, list_materials, move_folders, pick_files, delete_folder_records, link_directory, sync_directories, list_directories, exclude_directory_records
from utils.local_exit import request_local_exit
from urllib.parse import urlsplit
from myUtils.login import get_tencent_cookie, douyin_cookie_gen, get_ks_cookie, xiaohongshu_cookie_gen, baijiahao_cookie_gen, bilibili_cookie_gen, toutiao_cookie_gen, sohu_cookie_gen, zhihu_cookie_gen
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs, post_video_baijiahao, post_video_bilibili, post_video_toutiao, post_article_toutiao, post_article_baijiahao, post_article_sohu, post_article_zhihu
from uploader.douyin_uploader.content_stats import (
    DouyinStatsSyncError,
    ensure_content_stats_table,
    replace_account_stats,
    row_to_stat_item,
    sync_recent_items_sync as sync_douyin_content_stats,
)
from uploader.ks_uploader.content_stats import (
    KuaishouStatsSyncError,
    sync_recent_items_sync as sync_kuaishou_content_stats,
)
from uploader.xiaohongshu_uploader.content_stats import (
    XiaohongshuStatsSyncError,
    sync_recent_items_sync as sync_xiaohongshu_content_stats,
)
from uploader.bilibili_uploader.content_stats import (
    BilibiliStatsSyncError,
    sync_recent_items_sync as sync_bilibili_content_stats,
)

SUPPORTED_STATS_PLATFORMS = {
    "douyin": {"type": 3, "label": "抖音"},
    "kuaishou": {"type": 4, "label": "快手"},
    "xiaohongshu": {"type": 1, "label": "小红书"},
    "bilibili": {"type": 6, "label": "B站"},
}

import conf as app_conf
from myUtils.dingtalk import (
    DingTalkPushError,
    format_multi_account_stats_markdown,
    send_markdown,
)


def _dingtalk_webhook_url() -> str:
    return (getattr(app_conf, "DINGTALK_WEBHOOK_URL", None) or "").strip()


def _dingtalk_secret() -> str:
    return (getattr(app_conf, "DINGTALK_SECRET", None) or "").strip()


def _dingtalk_rehost_covers() -> bool:
    return bool(getattr(app_conf, "DINGTALK_REHOST_COVERS", True))


def _dingtalk_push_covers() -> bool:
    return bool(getattr(app_conf, "DINGTALK_PUSH_COVERS", True))


active_queues = {}
app = Flask(__name__)
_collection_cache = {}
_collection_cache_lock = threading.Lock()
_collection_workers = threading.BoundedSemaphore(2)


def _db_path():
    return Path(BASE_DIR / "db" / "database.db")


def _row_to_stat_item(row):
    return row_to_stat_item(row)


def _load_stats_payload(conn, platform: str, account_id: int):
    ensure_content_stats_table(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM content_stats
        WHERE platform = ? AND account_id = ?
        ORDER BY published_at DESC, id DESC
        """,
        (platform, account_id),
    )
    rows = cur.fetchall()
    last = rows[0]["synced_at"] if rows else None
    return {"items": [_row_to_stat_item(r) for r in rows], "lastSyncedAt": last}

#允许所有来源跨域访问
TRUSTED_LOCAL_ORIGINS = [f'http://{host}:{port}' for host in ('localhost','127.0.0.1','[::1]') for port in (5173,5409)]
CORS(app, origins=TRUSTED_LOCAL_ORIGINS)

@app.route('/local/status', methods=['GET'])
def local_status():
    return jsonify({'code':200,'data':{'running':True}})


@app.route('/local/exit', methods=['POST'])
def local_exit():
    origin=request.headers.get('Origin')
    allowed_origin=True
    if origin:
        try:
            parsed=urlsplit(origin)
            allowed_origin=parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1','::1') and parsed.port in (5173,5409)
        except ValueError:
            allowed_origin=False
    if request.remote_addr not in ('127.0.0.1','::1') or request.headers.get('X-OmniPost-Exit')!='1' or not request.is_json or not allowed_origin:
        return jsonify({'code':403,'msg':'只能从本机管理台执行退出'}),403
    try:
        request_local_exit(BASE_DIR)
    except (RuntimeError,OSError) as error:
        return jsonify({'code':409,'msg':str(error)}),409
    return jsonify({'code':200,'data':{'stopping':True},'msg':'正在停止本机服务'})

# Local video uploads are spooled to disk by Werkzeug and saved as streams.
# A global 160MB request cap incorrectly rejected normal video materials.
app.config['MAX_CONTENT_LENGTH'] = None


@app.errorhandler(413)
def upload_too_large(error):
    return jsonify({'code':413,'data':None,'msg':'上传请求超过当前服务限制，请检查上传配置或减少表单大小'}),413

# 获取当前目录（假设 index.html 和 assets 在这里）
current_dir = os.path.dirname(os.path.abspath(__file__))

# 处理所有静态资源请求（未来打包用）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（未来打包用）
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

@app.route('/vite.svg')
def vite_svg():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

# （未来打包用）
@app.route('/')
def index():  # put application's code here
    return send_from_directory(current_dir, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        # 保存文件到指定位置
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        (BASE_DIR / "videoFile").mkdir(parents=True, exist_ok=True)
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{file.filename}")
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": f"{uuid_v1}_{file.filename}"}), 200
    except Exception as e:
        return jsonify({"code":500,"msg": str(e),"data":None}), 500

def local_material_read_allowed():
    if request.remote_addr not in ('127.0.0.1','::1'):return False
    origin=request.headers.get('Origin')
    if origin:return origin in TRUSTED_LOCAL_ORIGINS
    referer=request.headers.get('Referer')
    if referer:
        try:
            url=urlsplit(referer)
            return f'{url.scheme}://{url.netloc}' in TRUSTED_LOCAL_ORIGINS
        except ValueError:return False
    return request.headers.get('Sec-Fetch-Site') not in ('cross-site','same-site')

@app.before_request
def protect_local_material_reads():
    if request.path in ('/getFiles','/getFile','/materialSections','/deleteFile') and request.method=='GET' and not local_material_read_allowed():
        return jsonify({'code':403,'msg':'请从本机管理台访问素材'}),403

@app.after_request
def sandbox_material_response(response):
    if request.path=='/getFile':
        response.headers['Content-Security-Policy']="sandbox; default-src 'none'"
        response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.route('/getFile', methods=['GET'])
def get_file():
    # 获取 filename 参数
    filename = request.args.get('filename')

    if not filename:
        return jsonify({"code": 400, "msg": "filename is required", "data": None}), 400

    if Path(filename).is_absolute():
        filename=str(Path(filename).resolve())
        with material_database(BASE_DIR) as db:
            registered=db.execute("SELECT filename FROM file_records WHERE file_path=? COLLATE NOCASE AND source_kind='reference'",(filename,)).fetchone()
        if not registered:return jsonify({'code':403,'msg':'此路径未登记为素材'}),403
        if not Path(filename).is_file():return jsonify({'code':404,'msg':'原文件已移动或删除，路径失效'}),404
        return send_file(filename,conditional=True,as_attachment=request.args.get('download')=='1' or Path(filename).suffix.lower() not in ('.mp4','.webm','.mov','.jpg','.jpeg','.png','.gif','.webp','.avif'),download_name=registered['filename'])

    # 防止路径穿越攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({"code": 400, "msg": "Invalid filename", "data": None}), 400

    # 拼接完整路径
    file_path = str(Path(BASE_DIR / "videoFile"))

    # 返回文件
    return send_from_directory(file_path,filename)


@app.route('/uploadSave', methods=['POST'])
def upload_save():
    return jsonify({'code':410,'msg':'素材库现仅登记本地路径，请使用“添加本地素材”'}),410

@app.route('/getFiles', methods=['GET'])
def get_all_files():
    try:
        directories=sync_directories(BASE_DIR)
        return jsonify({'code':200,'data':list_materials(BASE_DIR),'directories':directories})
    except Exception:
        return jsonify({'code':500,'msg':'读取素材失败，请检查数据库和文件路径'}),500


def local_material_action_allowed():
    origin=request.headers.get('Origin')
    if request.remote_addr not in ('127.0.0.1','::1') or request.headers.get('X-OmniPost-Local')!='1' or not request.is_json:return False
    if not origin:return True
    try:
        url=urlsplit(origin)
        return url.scheme=='http' and url.hostname in ('localhost','127.0.0.1','::1') and url.port in (5173,5409)
    except ValueError:return False


@app.route('/materialSections', methods=['GET','POST'])
def material_sections():
    if request.method=='GET':return jsonify({'code':200,'data':list_sections(BASE_DIR)})
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    try:
        section=create_section(BASE_DIR,(request.get_json() or {}).get('name'))
        return jsonify({'code':200,'data':{'id':section}})
    except ValueError as error:return jsonify({'code':400,'msg':str(error)}),400


@app.route('/materialSections/delete',methods=['POST'])
def delete_material_section():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    from utils.local_materials import delete_section
    try:
        data=request.get_json(silent=True) or {}
        if not isinstance(data,dict) or type(data.get('sectionId')) is not int:raise ValueError('请选择有效分区')
        count=delete_section(BASE_DIR,data['sectionId'])
        return jsonify({'code':200,'data':{'moved':count},'msg':'分区已删除，素材已移至未分区'})
    except ValueError as error:return jsonify({'code':400,'msg':str(error)}),400


@app.route('/materialSections/move', methods=['POST'])
def move_material_folders():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    data=request.get_json() or {}
    try:
        count=move_folders(BASE_DIR,data.get('sourceSectionId'),data.get('targetSectionId'),data.get('folders'),data.get('allowMerge') is True)
        return jsonify({'code':200,'data':{'moved':count}})
    except ValueError as error:return jsonify({'code':409,'msg':str(error)}),409


@app.route('/local/materials/delete-folders', methods=['POST'])
def delete_material_folder_records():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    data=request.get_json() or {}
    try:
        count=delete_folder_records(BASE_DIR,data.get('sectionId'),data.get('folders'),data.get('ids'))
        return jsonify({'code':200,'data':{'deleted':count}})
    except ValueError as error:return jsonify({'code':409,'msg':str(error)}),409


@app.route('/local/materials/reveal', methods=['POST'])
def reveal_local_material():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    try:
        raw=(request.get_json() or {}).get('path')
        if not isinstance(raw,str) or not raw:raise ValueError('请选择素材文件')
        path=Path(raw)
        if path.is_absolute():
            path=path.resolve()
            with material_database(BASE_DIR) as db:
                registered=db.execute("SELECT id FROM file_records WHERE file_path=? COLLATE NOCASE AND source_kind='reference'",(str(path),)).fetchone()
            if not registered:raise ValueError('此路径未登记为素材')
        else:
            storage=(Path(BASE_DIR)/'videoFile').resolve()
            path=(storage/path).resolve()
            if not path.is_relative_to(storage):raise ValueError('非法素材路径')
        if path.suffix.lower() not in ('.mp4','.mov','.avi','.mkv','.webm','.m4v','.flv','.wmv','.png','.jpg','.jpeg','.webp','.gif','.avif'):raise ValueError('仅支持打开视频和封面所在文件夹')
        if not path.is_file():raise ValueError('素材文件已移动或删除')
        import subprocess
        subprocess.Popen(['explorer.exe','/select,',str(path)])
        return jsonify({'code':200,'msg':'已打开素材所在文件夹'})
    except ValueError as error:return jsonify({'code':400,'msg':str(error)}),400
    except OSError:return jsonify({'code':500,'msg':'打开文件夹失败，请复制路径手动打开'}),500


@app.route('/local/materials/pick', methods=['POST'])
def pick_local_materials():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台选择文件'}),403
    try:return jsonify({'code':200,'data':pick_files(BASE_DIR,(request.get_json() or {}).get('kind','all'))})
    except (ValueError,RuntimeError) as error:return jsonify({'code':400,'msg':str(error)}),400
    except Exception:return jsonify({'code':500,'msg':'本机文件窗口未能返回，请重试'}),500


@app.route('/local/materials/directories', methods=['GET','POST'])
def material_directory_links():
    if request.method=='GET':
        if not local_material_read_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
        return jsonify({'code':200,'data':list_directories(BASE_DIR)})
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    data=request.get_json() or {}
    try:
        directories=link_directory(BASE_DIR,data.get('path'),data.get('sectionId'),data.get('kind','all'))
        directory=next((item for item in directories if item['path'].casefold()==str(Path(data['path']).resolve()).casefold() and item['section_id']==int(data['sectionId'])),None)
        return jsonify({'code':200,'data':{'directory':directory,'directories':directories,'files':list_materials(BASE_DIR)}})
    except (ValueError,OSError) as error:return jsonify({'code':400,'msg':str(error)}),400


@app.route('/local/materials/register', methods=['POST'])
def register_local_materials():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台添加素材'}),403
    data=request.get_json() or {}
    try:
        ids=register_files(BASE_DIR,data.get('paths'),data.get('sectionId'))
        return jsonify({'code':200,'data':{'ids':ids,'files':[file for file in list_materials(BASE_DIR) if file['id'] in ids]}})
    except (ValueError,OSError) as error:return jsonify({'code':400,'msg':str(error)}),400


@app.route("/getAccounts", methods=['GET'])
def getAccounts():
    """快速获取所有账号信息，不进行cookie验证"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM user_info''')
            rows = cursor.fetchall()
            rows_list = [list(row) for row in rows]

            print("\n📋 当前数据表内容（快速获取）：")
            for row in rows:
                print(row)

            return jsonify(
                {
                    "code": 200,
                    "msg": None,
                    "data": rows_list
                }), 200
    except Exception as e:
        print(f"获取账号列表时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"获取账号列表失败: {str(e)}",
            "data": None
        }), 500


@app.route('/account/openBackend',methods=['POST'])
def account_open_backend():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台打开后台'}),403
    from utils.account_backend import open_backend
    from utils.channels_session import SessionBusy
    try:
        data=request.get_json(silent=True) or {}
        account_id=data.get('accountId')
        if type(account_id) is not int:raise ValueError('账号参数无效')
        with closing(sqlite3.connect(_db_path())) as db:
            row=db.execute('SELECT type,filePath FROM user_info WHERE id=?',(account_id,)).fetchone()
        if not row:return jsonify({'code':404,'msg':'账号不存在'}),404
        return jsonify({'code':200,'data':open_backend(BASE_DIR,account_id,*row)})
    except SessionBusy as error:return jsonify({'code':409,'msg':str(error)}),409
    except ValueError as error:return jsonify({'code':400,'msg':str(error)}),400
    except Exception as error:return jsonify({'code':503,'msg':str(error)}),503


@app.route("/getValidAccounts",methods=['GET'])
async def getValidAccounts():
    platform_type = request.args.get('type')
    if platform_type is not None:
        try:
            platform_type = int(platform_type)
        except ValueError:
            return jsonify({
                "code": 400,
                "msg": "Invalid platform type",
                "data": None
            }), 400

    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        if platform_type is not None:
            cursor.execute('SELECT * FROM user_info WHERE type = ?', (platform_type,))
        else:
            cursor.execute('SELECT * FROM user_info')
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        scope = f"type={platform_type}" if platform_type is not None else "all"
        print(f"\n📋 校验账号 ({scope})，共 {len(rows_list)} 条：")
        for row in rows:
            print(row)
        for row in rows_list:
            from utils.channels_session import SessionBusy
            try:flag = await check_cookie(row[1],row[2])
            except SessionBusy:
                continue  # Busy is not an invalid login; preserve the previous status.
            new_status = 1 if flag else 0
            row[4] = new_status
            cursor.execute('''
            UPDATE user_info 
            SET status = ? 
            WHERE id = ?
            ''', (new_status, row[0]))
            conn.commit()
            print(f"✅ 用户状态已更新 id={row[0]} status={new_status}")
        return jsonify(
                        {
                            "code": 200,
                            "msg": None,
                            "data": rows_list
                        }),200

@app.route('/deleteFile', methods=['GET'])
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        with material_database(BASE_DIR):pass
        # 获取数据库连接
        with closing(sqlite3.connect(Path(BASE_DIR / "db" / "database.db"))) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # Referenced originals are never deleted. Only old app-owned copies may be removed.
            if record.get('source_kind','copied') != 'reference':
                storage=(BASE_DIR / 'videoFile').resolve()
                file_path=(storage / record['file_path']).resolve()
                if file_path.is_relative_to(storage) and file_path.is_file():
                    file_path.unlink()

            # 删除数据库记录
            exclude_directory_records(conn,[int(file_id)])
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/deleteAccount', methods=['GET'])
def delete_account():
    account_id = request.args.get('id')

    if not account_id or not account_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing account ID",
            "data": None
        }), 400

    account_id = int(account_id)

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除关联的cookie文件
            if record.get('filePath'):
                cookie_file_path = Path(BASE_DIR / "cookiesFile" / record['filePath'])
                if cookie_file_path.exists():
                    try:
                        cookie_file_path.unlink()
                        print(f"✅ Cookie文件已删除: {cookie_file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除Cookie文件失败: {e}")

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"delete failed: {str(e)}",
            "data": None
        }), 500


# SSE 登录接口
@app.route('/login')
def login():
    # 1 小红书 2 视频号 3 抖音 4 快手 5 百家号 6 B站 7 今日头条
    type = request.args.get('type')
    # 账号名
    id = request.args.get('id')
    print(f"登录请求: type={type}, id={id}")

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    active_queues[id] = status_queue

    def on_close():
        print(f"清理队列: {id}")
        del active_queues[id]
    # 启动异步任务线程
    thread = threading.Thread(target=run_async_function, args=(type,id,status_queue), daemon=True)
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 关键：禁用 Nginx 缓冲
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

publish_browser_slot = threading.BoundedSemaphore(2)

@app.route('/publishHistory', methods=['GET','POST'])
def publication_history():
    allowed=local_material_read_allowed() if request.method=='GET' else local_material_action_allowed()
    if not allowed:return jsonify({'code':403,'msg':'请从本机管理台操作'}),403
    try:
        if request.method=='GET':
            return jsonify({'code':200,'data':publish_history.list_records(BASE_DIR)})
        data=request.get_json() or {}
        if data.get('action')=='sync_bilibili':
            from utils.bilibili_history_sync import sync_accounts
            with closing(sqlite3.connect(_db_path())) as db:
                accounts=db.execute('SELECT id,filePath FROM user_info WHERE type=6').fetchall()
            result=sync_accounts(BASE_DIR,accounts,read_job,force=data.get('force') is True)
            return jsonify({'code':200,'data':result})
        if data.get('action')=='manual':
            with closing(sqlite3.connect(_db_path())) as db:
                account=db.execute('SELECT type,filePath FROM user_info WHERE id=?',(int(data.get('accountId')),)).fetchone()
            if not account:raise ValueError('账号不存在')
            files=data.get('fileList')
            if not isinstance(files,list) or not files or len(files)>50 or any(not isinstance(x,str) or not x for x in files):
                raise ValueError('请选择当前任务的视频素材后补记')
            publish_history.reserve(BASE_DIR,account[0],[account[1]],files,data.get('title',''),'',manual=True)
        else:
            publish_history.reconcile(BASE_DIR,int(data.get('id')),data.get('status'),read_job)
        return jsonify({'code':200,'msg':'发布记录已更新'})
    except (ValueError,TypeError) as error:
        return jsonify({'code':409,'msg':str(error)}),409

@app.route('/publishPreflight',methods=['POST'])
def publish_preflight_check():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'请从本机管理台检查发布素材'}),403
    from utils.publish_preflight import preflight_publish
    data=request.get_json(silent=True)
    report=preflight_publish(BASE_DIR,data,manual=isinstance(data,dict) and data.get('manual') is True,job_reader=read_job)
    return jsonify({'code':200,'data':report})


@app.route('/postVideo', methods=['POST'])
def postVideo():
    # 获取JSON数据
    data = request.get_json()

    if not isinstance(data,dict) or not data:
        return jsonify({"code": 400, "msg": "请求数据必须为非空对象", "data": None}), 400

    # 从JSON数据中提取fileList和accountList
    file_list = data.get('fileList', [])
    account_list = data.get('accountList', [])
    type = data.get('type')
    title = data.get('title')
    tags = data.get('tags')
    category = data.get('category')
    enableTimer = data.get('enableTimer')
    if category == 0:
        category = None
    productLink = data.get('productLink', '')
    productTitle = data.get('productTitle', '')
    thumbnail_path = data.get('thumbnail', '') or data.get('coverImage', '')
    cover_images = data.get('coverImages') or data.get('cover_images') or []
    if isinstance(cover_images, str):
        cover_images = [x.strip() for x in cover_images.split(',') if x.strip()]
    elif not isinstance(cover_images, list):
        cover_images = []
    else:
        cover_images = [str(x).strip() for x in cover_images if str(x).strip()]
    # 兼容：仅传单图时并入 coverImages
    if thumbnail_path and str(thumbnail_path).strip() and str(thumbnail_path).strip() not in cover_images:
        if not cover_images:
            cover_images = [str(thumbnail_path).strip()]
    is_draft = data.get('isDraft', False)  # 新增参数：是否保存为草稿
    ai_generated = data.get('aiGenerated', False)  # 抖音/快手/小红书/视频号 AI 内容声明
    dry_run = data.get('dryRun', False)  # 仅预览不发布：填完表后不点发布
    # B站创作声明 id：-1/1/2/3/4；None 表示不传
    bilibili_creation_statement = data.get('bilibiliCreationStatement', None)
    # 今日头条内容类型：video（默认）| article
    content_type = (data.get('contentType') or 'video').strip().lower()
    article_body = data.get('articleBody') or data.get('body') or ''
    # 今日头条图文作品声明（单选）
    work_statement = data.get('workStatement') or data.get('work_statement') or ''
    work_statements = data.get('workStatements') or data.get('work_statements') or []
    if work_statement and str(work_statement).strip():
        work_statements = [str(work_statement).strip()]
    elif isinstance(work_statements, str):
        work_statements = [work_statements] if work_statements.strip() else []
    elif not isinstance(work_statements, list):
        work_statements = []
    else:
        work_statements = [str(x).strip() for x in work_statements if str(x).strip()]
    # 单选：最多保留第一项
    work_statements = work_statements[:1]

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')

    if type is None or type == "":
        return jsonify({"code": 400, "msg": "平台类型不能为空", "data": None}), 400
    try:
        type = int(type)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "msg": f"不支持的平台类型: {type}", "data": None}), 400

    # 支持图文文章的平台：5=百家号，7=今日头条，8=搜狐号，9=知乎
    ARTICLE_CAPABLE_PLATFORMS = (5, 7, 8, 9)
    # 搜狐号/知乎第一期仅支持图文
    if type == 8:
        content_type = 'article'
    if type == 9:
        content_type = 'article'
    is_article = (type in ARTICLE_CAPABLE_PLATFORMS and content_type == 'article')
    is_toutiao_article = (type == 7 and content_type == 'article')
    is_baijiahao_article = (type == 5 and content_type == 'article')
    is_sohu_article = (type == 8)
    is_zhihu_article = (type == 9)

    try:
        collection_name = validate_collection(type, data.get('collectionName', ''))
    except CollectionSelectionError as error:
        return jsonify({'code':400,'msg':str(error),'data':None}), 400
    if collection_name and is_article:
        return jsonify({'code':400,'msg':'合集目前仅用于视频发布，请切换视频或清空合集','data':None}), 400
    # Match account cookies to this platform before any background task starts.
    with closing(sqlite3.connect(_db_path())) as conn:
        allowed_accounts = {row[0] for row in conn.execute('SELECT filePath FROM user_info WHERE type = ?', (type,))}
    if not isinstance(account_list, list) or any(not isinstance(item, str) or item not in allowed_accounts for item in account_list):
        return jsonify({'code':400,'msg':'发布账号与平台不匹配，请重新选择账号','data':None}), 400

    if type==4 and collection_name:
        with _collection_cache_lock:catalogs=list(_collection_cache.items())
        for cache_key,(expiry,catalog) in catalogs:
            if cache_key[1]!=4 or cache_key[2] not in account_list or expiry<=time.monotonic():continue
            for item in catalog.get('items',[]):
                if item.get('value')==collection_name and item.get('disabled') and item.get('unavailableReason'):
                    return jsonify({'code':400,'msg':f'快手合集“{collection_name}”暂不可投稿：{item["unavailableReason"]}。请先在快手合集管理处理，或确认不加入合集后重新提交；本次未开始上传','data':None}),400

    # 参数校验
    if not is_article and not file_list:
        return jsonify({"code": 400, "msg": "文件列表不能为空", "data": None}), 400
    if not account_list:
        return jsonify({"code": 400, "msg": "账号列表不能为空", "data": None}), 400
    if is_article:
        if not title or not str(title).strip():
            return jsonify({"code": 400, "msg": "文章标题不能为空", "data": None}), 400
        if is_sohu_article:
            title_len = len(str(title).strip())
            if title_len < 5 or title_len > 72:
                return jsonify({"code": 400, "msg": "搜狐号文章标题需 5-72 个字", "data": None}), 400
        if is_zhihu_article:
            title_len = len(str(title).strip())
            if title_len > 100:
                return jsonify({"code": 400, "msg": "知乎文章标题最多 100 个字", "data": None}), 400
        if not article_body or not str(article_body).strip():
            return jsonify({"code": 400, "msg": "文章正文不能为空", "data": None}), 400
        # 百家号图文标题下限 2 字
        if is_baijiahao_article and len(str(title).strip()) < 2:
            return jsonify({"code": 400, "msg": "百家号图文标题至少 2 个字", "data": None}), 400
        if is_baijiahao_article and not str(thumbnail_path or "").strip():
            return jsonify({"code": 400, "msg": "百家号图文展示封面不能为空", "data": None}), 400
    # 小红书（1）、视频号（2）、抖音（3）、快手（4）标题非必填，其它平台仍必填
    elif type not in (1, 2, 3, 4) and not title:
        return jsonify({"code": 400, "msg": "标题不能为空", "data": None}), 400
    if title is None:
        title = ""
    if is_sohu_article:
        title = str(title).strip()[:72]
    if is_zhihu_article:
        title = str(title).strip()[:100]
    if bilibili_creation_statement is not None and bilibili_creation_statement != "":
        try:
            bilibili_creation_statement = int(bilibili_creation_statement)
        except (TypeError, ValueError):
            return jsonify({"code": 400, "msg": f"非法的创作声明: {bilibili_creation_statement}", "data": None}), 400
    else:
        bilibili_creation_statement = None

    # 打印获取到的数据（仅作为示例）
    print("File List:", file_list)
    print("Account List:", account_list)
    print(
        f"enableTimer={enableTimer}, dryRun={dry_run}, aiGenerated={ai_generated}, "
        f"bilibiliCreationStatement={bilibili_creation_statement}, "
        f"contentType={content_type}, cover={thumbnail_path}, workStatements={work_statements}",
        flush=True,
    )

    # 参数校验通过后，在后台线程中执行发布任务，避免阻塞Flask主线程。
    # 前端拿到的 200 只表示“任务已提交”，不代表平台已经发布成功。
    import hashlib
    digest=hashlib.sha256(json.dumps({key:value for key,value in data.items() if key!='requestId'},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    metadata={'title':title,'fileList':file_list,'accounts':account_list,'materialLabel':str(data.get('materialLabel') or title or '、'.join(Path(path).name for path in file_list))[:1000],'accountLabel':str(data.get('accountLabel') or '、'.join(account_list))[:500]}
    try:job_id,created=claim_job(type,metadata,data.get('requestId'),digest)
    except ValueError as error:return jsonify({'code':409,'msg':str(error),'data':None}),409
    if not created:
        job=read_job(job_id)
        if job.get('requestRejected'):
            return jsonify({'code':409,'msg':job['message'],'data':{'confirmRepeatRequired':job.get('confirmRepeatRequired',False)}}),409
        return jsonify({'code':200,'msg':'已找到同一次提交的任务，未重复执行','data':{'jobId':job_id,'deduplicated':True}})

    from utils.publish_preflight import preflight_publish
    preflight=preflight_publish(BASE_DIR,data,job_reader=read_job)
    record_preflight(job_id,preflight)
    if not preflight['ok']:
        message='发布前检查未通过：'+'；'.join(preflight['errors'][:4])
        update_job(job_id,'failed',message,requestRejected=True)
        code=409 if preflight.get('activeTask') else 422
        return jsonify({'code':code,'msg':message,'data':{'preflight':preflight}}),code
    history_ids=[]
    if not is_article and not dry_run and not is_draft:
        try:
            history_ids=publish_history.reserve(BASE_DIR,type,account_list,file_list,title,job_id,
                allow_repeat=data.get('confirmRepeat') is True,job_reader=read_job)
        except publish_history.DuplicatePublication as error:
            update_job(job_id,'failed',str(error),requestRejected=True,confirmRepeatRequired=True)
            return jsonify({'code':409,'msg':str(error),'data':{'confirmRepeatRequired':True}}),409
        except ValueError as error:
            update_job(job_id,'failed',str(error),requestRejected=True)
            return jsonify({'code':409,'msg':str(error),'data':None}),409
    def execute_publish_task():
        update_job(job_id, 'running', '正在执行上传/发布流程')
        try:
            print(
                f"🧵 后台发布线程启动: type={type}, title={title}, dryRun={dry_run}, contentType={content_type}",
                flush=True,
            )
            match type:
                case 1:
                    post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                       start_days, dry_run, ai_generated, collection_name=collection_name, thumbnail_path=thumbnail_path)
                case 2:
                    post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                       start_days, is_draft, dry_run, ai_generated, collection_name=collection_name, thumbnail_path=thumbnail_path)
                case 3:
                    post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                              start_days, thumbnail_path, productLink, productTitle, ai_generated, dry_run, collection_name=collection_name, portrait_cover=data.get('portraitCover', ''))
                case 4:
                    post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                              start_days, dry_run, ai_generated, collection_name=collection_name, thumbnail_path=thumbnail_path)
                case 5:
                    if content_type == 'article':
                        post_article_baijiahao(
                            title,
                            article_body,
                            tags,
                            account_list,
                            enableTimer,
                            videos_per_day,
                            daily_times,
                            start_days,
                            dry_run,
                            thumbnail_path,
                        )
                    else:
                        post_video_baijiahao(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                  start_days, dry_run, collection_name=collection_name, thumbnail_path=thumbnail_path)
                case 6:
                    post_video_bilibili(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                              start_days, dry_run, bilibili_creation_statement, collection_name=collection_name, thumbnail_path=thumbnail_path, recommendation_cover=data.get('bilibiliCover43', ''))
                case 7:
                    if content_type == 'article':
                        post_article_toutiao(
                            title,
                            article_body,
                            tags,
                            account_list,
                            enableTimer,
                            videos_per_day,
                            daily_times,
                            start_days,
                            dry_run,
                            thumbnail_path,
                            work_statements,
                        )
                    else:
                        post_video_toutiao(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                  start_days, dry_run, thumbnail_path=thumbnail_path)
                case 8:
                    post_article_sohu(
                        title,
                        article_body,
                        tags,
                        account_list,
                        enableTimer,
                        videos_per_day,
                        daily_times,
                        start_days,
                        dry_run,
                        thumbnail_path,
                        work_statements[0] if work_statements else (work_statement or None),
                        cover_images,
                    )
                case 9:
                    post_article_zhihu(
                        title,
                        article_body,
                        tags,
                        account_list,
                        enableTimer,
                        videos_per_day,
                        daily_times,
                        start_days,
                        dry_run,
                        thumbnail_path,
                        work_statements[0] if work_statements else (work_statement or None),
                    )
            print(f"✅ 发布任务完成: type={type}, title={title}", flush=True)
            if history_ids:publish_history.finish(BASE_DIR,history_ids,'submitted','流程完成，平台发布/审核状态待核对')
            update_job(job_id, 'completed', '预览流程已完成（未发布）' if dry_run else '执行流程已完成，请到平台核对发布/审核状态')
        except Exception as e:
            if history_ids:
                safe_failure=len(file_list)==1 and isinstance(e,(CollectionSelectionError,FileNotFoundError))
                publish_history.finish(BASE_DIR,history_ids,'failed' if safe_failure else 'needs_review',str(e))
            update_job(job_id, 'failed', str(e) if isinstance(e, (CollectionSelectionError, RuntimeError, FileNotFoundError)) else f'执行失败（{e.__class__.__name__}），请查看本机后端日志', resultUncertain=getattr(e,'result_uncertain',False))
            print(f"❌ 发布视频时出错: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()

    def run_publish_task():
        update_job(job_id, 'queued', '已排队，等待空闲上传名额（最多同时 2 个账号）')
        with publish_browser_slot:
            from utils.publish_jobs import bind_job
            bind_job(job_id)
            try:execute_publish_task()
            finally:bind_job(None)

    thread = threading.Thread(target=run_publish_task, daemon=True)
    thread.start()

    if type == 6 and dry_run:
        submit_msg = "B站仅预览模式不会实际上传（无浏览器可预览）"
    elif type == 6:
        submit_msg = "B站上传任务已提交，后台通过 biliup 执行（不会打开浏览器）"
    elif is_toutiao_article and dry_run:
        submit_msg = "今日头条文章任务已提交：仅预览不发布"
    elif is_toutiao_article:
        submit_msg = "今日头条文章发布任务已提交，正在后台执行"
    elif is_sohu_article and dry_run:
        submit_msg = "搜狐号文章任务已提交：仅预览不发布"
    elif is_sohu_article:
        submit_msg = "搜狐号文章发布任务已提交，正在后台执行"
    elif is_zhihu_article and dry_run:
        submit_msg = "知乎文章任务已提交：仅预览不发布"
    elif is_zhihu_article:
        submit_msg = "知乎文章发布任务已提交，正在后台执行"
    elif type == 5 and content_type == 'article' and dry_run:
        submit_msg = "百家号图文文章任务已提交：仅预览不发布（可能出现自动保存草稿，不等于已发布）"
    elif type == 5 and content_type == 'article':
        submit_msg = "百家号图文文章发布任务已提交，浏览器将自动打开"
    elif type == 5:
        submit_msg = "百家号视频发布任务已提交，浏览器将自动打开上传"
    else:
        submit_msg = "发布任务已提交，正在后台执行"

    return jsonify(
        {
            "code": 200,
            "msg": submit_msg,
            "data": {"jobId": job_id}
        }), 200


@app.route('/accountCollections', methods=['GET'])
def account_collections():
    try:
        account_id = int(request.args.get('accountId', ''))
    except (ValueError, TypeError):
        return jsonify({'code':400,'msg':'账号参数无效','data':None}), 400
    with closing(sqlite3.connect(_db_path())) as conn:
        row = conn.execute('SELECT type, filePath FROM user_info WHERE id = ?', (account_id,)).fetchone()
    if not row:
        return jsonify({'code':404,'msg':'账号不存在','data':None}), 404
    platform, filename = row
    cookie_root = (BASE_DIR / 'cookiesFile').resolve()
    cookie = (cookie_root / filename).resolve()
    if cookie.parent != cookie_root:
        return jsonify({'code':400,'msg':'账号登录文件路径无效','data':None}), 400
    stamp = cookie.stat().st_mtime_ns if cookie.exists() else None
    key = (account_id, platform, filename, stamp)
    refresh = request.args.get('refresh') == '1'
    with _collection_cache_lock:
        cached = _collection_cache.get(key)
    if cached and not refresh and cached[0] > time.monotonic():
        return jsonify({'code':200,'msg':'ok','data':cached[1]})
    if not _collection_workers.acquire(timeout=60):
        return jsonify({'code':200,'msg':'ok','data':{'status':'unavailable','items':[],'message':'合集读取请求较多，请稍后刷新'}})
    try:
        try:
            result = asyncio.run(asyncio.wait_for(discover_collections(platform, cookie), timeout=40))
        except CollectionCatalogError as error:
            result = {'status':error.status,'items':[],'message':str(error)}
        except Exception:
            result = {'status':'unavailable','items':[],'message':'合集读取失败，请检查网络或重新登录后刷新'}
        result = dict(result, accountId=account_id, platform=platform)
        if platform != 6:
            names = [item['name'] for item in result['items']]
            result['items'] = [dict(item, disabled=bool(item.get('disabled')) or names.count(item['name'])>1) for item in result['items']]
        ttl = 300 if result['status'] in ('ready','empty') else 15
        with _collection_cache_lock:
            # Invalidate older login states for this account.
            for old in list(_collection_cache):
                if old[0] == account_id:
                    del _collection_cache[old]
            _collection_cache[key] = (time.monotonic()+ttl, result)
        return jsonify({'code':200,'msg':'ok','data':result})
    finally:
        _collection_workers.release()


@app.route('/publishWindow', methods=['POST'])
def publish_window():
    if not local_material_action_allowed():return jsonify({'code':403,'msg':'仅允许本机管理台操作'}),403
    data=request.get_json()
    if not isinstance(data.get('visible'),bool):return jsonify({'code':400,'msg':'无效的显示状态'}),400
    job=read_job(data.get('id',''))
    if not job or job['status']!='running':return jsonify({'code':409,'msg':'任务已结束或尚未启动'}),409
    try:
        from utils.publish_windows import set_visible
        set_visible(job['id'],data['visible'])
        return jsonify({'code':200,'data':read_job(job['id']),'msg':'ok'})
    except ValueError as error:return jsonify({'code':409,'msg':str(error)}),409


@app.route('/publishJobs', methods=['GET'])
def publish_jobs_history():
    if not local_material_read_allowed():return jsonify({'code':403,'msg':'请从本机管理台查看任务记录'}),403
    return jsonify({'code':200,'data':list_jobs(200)})


@app.route('/publishJob', methods=['GET'])
def publish_job_status():
    from utils import ks_collection_tasks
    job_id=request.args.get('id', '')
    job = read_job(job_id)
    collection=ks_collection_tasks.get(job_id=job_id) if job_id else None
    if collection and collection['status']!='prepared':
        job=job or {'id':job_id,'platform':4,'status':'completed','progress':100,'stage':'视频已提交','message':'视频已提交，合集关联单独处理'}
        job['collectionTask']=ks_collection_tasks.public(collection)
        job['videoSubmitted']=True
    if not job:
        return jsonify({'code':404,'msg':'未找到任务记录，旧版本的内存任务可能未保存','data':None}), 404
    return jsonify({'code':200,'msg':'ok','data':job})


@app.route('/retryKuaishouCollection', methods=['POST'])
def retry_kuaishou_collection():
    if not local_material_action_allowed():
        return jsonify({'code':403,'msg':'仅允许本机操作','data':None}),403
    from utils import ks_collection_tasks
    task=ks_collection_tasks.get(task_id=(request.get_json(silent=True) or {}).get('id',''))
    if not task or task['status']=='prepared':
        return jsonify({'code':404,'msg':'没有已提交视频的合集任务','data':None}),404
    ks_collection_tasks.start(task['id'])
    return jsonify({'code':200,'msg':'已安排重试加入合集，不会重新上传视频','data':ks_collection_tasks.public(ks_collection_tasks.get(task['id']))})


@app.route('/updateUserinfo', methods=['POST'])
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500

@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"code": 400, "msg": "Expected a JSON array", "data": None}), 400
    for data in data_list:
        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None
        productLink = data.get('productLink', '')
        productTitle = data.get('productTitle', '')
        is_draft = data.get('isDraft', False)
        ai_generated = data.get('aiGenerated', False)
        dry_run = data.get('dryRun', False)
        thumbnail_path = data.get('thumbnail', '') or data.get('coverImage', '')
        cover_images = data.get('coverImages') or data.get('cover_images') or []
        if isinstance(cover_images, str):
            cover_images = [x.strip() for x in cover_images.split(',') if x.strip()]
        elif not isinstance(cover_images, list):
            cover_images = []
        else:
            cover_images = [str(x).strip() for x in cover_images if str(x).strip()]
        if thumbnail_path and str(thumbnail_path).strip() and str(thumbnail_path).strip() not in cover_images:
            if not cover_images:
                cover_images = [str(thumbnail_path).strip()]
        content_type = (data.get('contentType') or 'video').strip().lower()
        article_body = data.get('articleBody') or data.get('body') or ''
        work_statement = data.get('workStatement') or data.get('work_statement') or ''
        work_statements = data.get('workStatements') or data.get('work_statements') or []
        if work_statement and str(work_statement).strip():
            work_statements = [str(work_statement).strip()]
        elif isinstance(work_statements, str):
            work_statements = [work_statements] if work_statements.strip() else []
        elif not isinstance(work_statements, list):
            work_statements = []
        else:
            work_statements = [str(x).strip() for x in work_statements if str(x).strip()]
        work_statements = work_statements[:1]
        bilibili_creation_statement = data.get('bilibiliCreationStatement', None)
        if bilibili_creation_statement is not None and bilibili_creation_statement != "":
            try:
                bilibili_creation_statement = int(bilibili_creation_statement)
            except (TypeError, ValueError):
                bilibili_creation_statement = None
        else:
            bilibili_creation_statement = None

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        # 搜狐号/知乎第一期仅支持图文
        if type == 8:
            content_type = 'article'
            title_text = str(title or "").strip()
            if len(title_text) < 5 or len(title_text) > 72:
                return jsonify({"code": 400, "msg": "搜狐号文章标题需 5-72 个字", "data": None}), 400
            title = title_text[:72]
        if type == 9:
            content_type = 'article'
            title_text = str(title or "").strip()
            if len(title_text) > 100:
                return jsonify({"code": 400, "msg": "知乎文章标题最多 100 个字", "data": None}), 400
            title = title_text[:100]
        is_baijiahao_article = (type == 5 and content_type == 'article')
        if is_baijiahao_article and not str(thumbnail_path or "").strip():
            return jsonify({"code": 400, "msg": "百家号图文展示封面不能为空", "data": None}), 400
        # 打印获取到的数据（仅作为示例）
        print("File List:", file_list)
        print("Account List:", account_list)
        match type:
            case 1:
                post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                               start_days, dry_run, ai_generated)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft, dry_run, ai_generated)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, thumbnail_path, productLink, productTitle, ai_generated, dry_run)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, dry_run)
            case 5:
                if content_type == 'article':
                    post_article_baijiahao(
                        title,
                        article_body,
                        tags,
                        account_list,
                        enableTimer,
                        videos_per_day,
                        daily_times,
                        start_days,
                        dry_run,
                        thumbnail_path,
                    )
                else:
                    post_video_baijiahao(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                              start_days, dry_run)
            case 6:
                post_video_bilibili(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, dry_run, bilibili_creation_statement)
            case 7:
                if content_type == 'article':
                    post_article_toutiao(
                        title,
                        article_body,
                        tags,
                        account_list,
                        enableTimer,
                        videos_per_day,
                        daily_times,
                        start_days,
                        dry_run,
                        thumbnail_path,
                        work_statements,
                    )
                else:
                    post_video_toutiao(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                              start_days, dry_run)
            case 8:
                post_article_sohu(
                    title,
                    article_body,
                    tags,
                    account_list,
                    enableTimer,
                    videos_per_day,
                    daily_times,
                    start_days,
                    dry_run,
                    thumbnail_path,
                    work_statements[0] if work_statements else (work_statement or None),
                    cover_images,
                )
            case 9:
                post_article_zhihu(
                    title,
                    article_body,
                    tags,
                    account_list,
                    enableTimer,
                    videos_per_day,
                    daily_times,
                    start_days,
                    dry_run,
                    thumbnail_path,
                    work_statements[0] if work_statements else (work_statement or None),
                )
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

# Cookie文件上传API
@app.route('/uploadCookie', methods=['POST'])
def upload_cookie():
    try:
        if 'file' not in request.files:
            return jsonify({
                "code": 400,
                "msg": "没有找到Cookie文件",
                "data": None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "code": 400,
                "msg": "Cookie文件名不能为空",
                "data": None
            }), 400

        if not file.filename.endswith('.json'):
            return jsonify({
                "code": 400,
                "msg": "Cookie文件必须是JSON格式",
                "data": None
            }), 400

        # 获取账号信息
        account_id = request.form.get('id')
        platform = request.form.get('platform')

        if not account_id or not platform:
            return jsonify({
                "code": 400,
                "msg": "缺少账号ID或平台信息",
                "data": None
            }), 400

        # 从数据库获取账号的文件路径
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT filePath FROM user_info WHERE id = ?', (account_id,))
            result = cursor.fetchone()

        if not result:
            return jsonify({
                "code": 500,
                "msg": "账号不存在",
                "data": None
            }), 404

        # 保存上传的Cookie文件到对应路径
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / result['filePath'])
        cookie_file_path.parent.mkdir(parents=True, exist_ok=True)

        file.save(str(cookie_file_path))

        # 更新数据库中的账号信息（可选，比如更新更新时间）
        # 这里可以根据需要添加额外的处理逻辑

        return jsonify({
            "code": 200,
            "msg": "Cookie文件上传成功",
            "data": None
        }), 200

    except Exception as e:
        print(f"上传Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"上传Cookie文件失败: {str(e)}",
            "data": None
        }), 500


# Cookie文件下载API
@app.route('/downloadCookie', methods=['GET'])
def download_cookie():
    try:
        file_path = request.args.get('filePath')
        if not file_path:
            return jsonify({
                "code": 500,
                "msg": "缺少文件路径参数",
                "data": None
            }), 400

        # 验证文件路径的安全性，防止路径遍历攻击
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / file_path).resolve()
        base_path = Path(BASE_DIR / "cookiesFile").resolve()

        if not cookie_file_path.is_relative_to(base_path):
            return jsonify({
                "code": 500,
                "msg": "非法文件路径",
                "data": None
            }), 400

        if not cookie_file_path.exists():
            return jsonify({
                "code": 500,
                "msg": "Cookie文件不存在",
                "data": None
            }), 404

        # 返回文件
        return send_from_directory(
            directory=str(cookie_file_path.parent),
            path=cookie_file_path.name,
            as_attachment=True
        )

    except Exception as e:
        print(f"下载Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"下载Cookie文件失败: {str(e)}",
            "data": None
        }), 500


@app.route("/proxyImage", methods=["GET"])
def proxy_image():
    """代理外链封面图，规避 B 站等 CDN 防盗链。"""
    from urllib.parse import urlparse

    import requests as http_requests

    raw_url = (request.args.get("url") or "").strip()
    if not raw_url:
        return jsonify({"code": 400, "msg": "url 不能为空", "data": None}), 400
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return jsonify({"code": 400, "msg": "url 无效", "data": None}), 400
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({"code": 400, "msg": "仅支持 http/https 图片地址", "data": None}), 400
    host = parsed.hostname
    if not host:
        return jsonify({"code": 400, "msg": "url 无效", "data": None}), 400
    host = host.lower()
    allowed_suffixes = (".hdslb.com",)
    allowed_exact = {"hdslb.com"}
    if not (host in allowed_exact or any(host.endswith(suf) for suf in allowed_suffixes)):
        return jsonify({"code": 403, "msg": "该图片域名不允许代理", "data": None}), 403

    try:
        upstream = http_requests.get(
            raw_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.bilibili.com/",
            },
            timeout=20,
            stream=True,
        )
    except Exception as e:
        return jsonify({"code": 502, "msg": f"拉取图片失败: {e}", "data": None}), 502
    if upstream.status_code != 200:
        return jsonify({"code": 502, "msg": f"上游返回 {upstream.status_code}", "data": None}), 502

    content_type = (upstream.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
    if not content_type.startswith("image/"):
        return jsonify({"code": 502, "msg": "上游不是图片", "data": None}), 502

    # cap ~5MB
    chunks = []
    total = 0
    for chunk in upstream.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > 5 * 1024 * 1024:
            return jsonify({"code": 502, "msg": "图片过大", "data": None}), 502
        chunks.append(chunk)
    body = b"".join(chunks)
    return Response(body, status=200, mimetype=content_type, headers={
        "Cache-Control": "public, max-age=86400",
    })


@app.route("/getContentStats", methods=["GET"])
def get_content_stats():
    account_id = request.args.get("accountId", type=int)
    platform = (request.args.get("platform") or "douyin").strip().lower()
    if not account_id:
        return jsonify({"code": 400, "msg": "accountId 不能为空", "data": None}), 400
    if platform not in SUPPORTED_STATS_PLATFORMS:
        return jsonify({"code": 400, "msg": "仅支持 platform=douyin|kuaishou|xiaohongshu|bilibili", "data": None}), 400
    try:
        with sqlite3.connect(_db_path()) as conn:
            payload = _load_stats_payload(conn, platform, account_id)
        return jsonify({"code": 200, "msg": None, "data": payload}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": f"读取失败: {e}", "data": None}), 500


@app.route("/syncContentStats", methods=["POST"])
def sync_content_stats():
    body = request.get_json(silent=True) or {}
    account_id = body.get("accountId")
    platform = str(body.get("platform") or "douyin").strip().lower()
    try:
        limit = int(body.get("limit") or 5)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "msg": "limit 无效", "data": None}), 400
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "msg": "accountId 无效", "data": None}), 400
    meta = SUPPORTED_STATS_PLATFORMS.get(platform)
    if not meta:
        return jsonify({"code": 400, "msg": "仅支持 platform=douyin|kuaishou|xiaohongshu|bilibili", "data": None}), 400
    if limit < 1 or limit > 20:
        return jsonify({"code": 400, "msg": "limit 需在 1-20", "data": None}), 400

    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, type, filePath FROM user_info WHERE id = ?", (account_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"code": 404, "msg": "账号不存在", "data": None}), 404
            if int(row["type"]) != meta["type"]:
                return jsonify({"code": 400, "msg": f"该账号不是{meta['label']}账号", "data": None}), 400
            cookie_path = Path(BASE_DIR / "cookiesFile" / row["filePath"])
    except Exception as e:
        return jsonify({"code": 500, "msg": f"查询账号失败: {e}", "data": None}), 500

    try:
        if platform == "douyin":
            items = sync_douyin_content_stats(cookie_path, limit=limit)
        elif platform == "kuaishou":
            items = sync_kuaishou_content_stats(cookie_path, limit=limit)
        elif platform == "xiaohongshu":
            items = sync_xiaohongshu_content_stats(cookie_path, limit=limit)
        else:
            items = sync_bilibili_content_stats(cookie_path, limit=limit)
    except (
        DouyinStatsSyncError,
        KuaishouStatsSyncError,
        XiaohongshuStatsSyncError,
        BilibiliStatsSyncError,
    ) as e:
        return jsonify({"code": e.code, "msg": e.message, "data": None}), e.code
    except Exception as e:
        return jsonify({"code": 500, "msg": f"同步失败: {e}", "data": None}), 500

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(_db_path()) as conn:
            replace_account_stats(
                conn,
                platform=platform,
                account_id=account_id,
                items=items,
                synced_at=synced_at,
            )
            payload = _load_stats_payload(conn, platform, account_id)
        return jsonify({"code": 200, "msg": "同步成功", "data": payload}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": f"写入失败: {e}", "data": None}), 500


@app.route("/pushContentStatsToDingTalk", methods=["POST"])
def push_content_stats_to_dingtalk():
    body = request.get_json(silent=True) or {}
    webhook = _dingtalk_webhook_url()
    if not webhook:
        return jsonify({"code": 400, "msg": "未配置 DINGTALK_WEBHOOK_URL", "data": None}), 400

    raw_accounts = body.get("accounts")
    targets = []
    if isinstance(raw_accounts, list) and raw_accounts:
        for entry in raw_accounts:
            if not isinstance(entry, dict):
                return jsonify({"code": 400, "msg": "accounts 项无效", "data": None}), 400
            platform = str(entry.get("platform") or "").strip().lower()
            try:
                account_id = int(entry.get("accountId"))
            except (TypeError, ValueError):
                return jsonify({"code": 400, "msg": "accountId 无效", "data": None}), 400
            if platform not in SUPPORTED_STATS_PLATFORMS:
                return jsonify(
                    {
                        "code": 400,
                        "msg": "仅支持 platform=douyin|kuaishou|xiaohongshu|bilibili",
                        "data": None,
                    }
                ), 400
            targets.append({"accountId": account_id, "platform": platform})
    else:
        platform = str(body.get("platform") or "douyin").strip().lower()
        try:
            account_id = int(body.get("accountId"))
        except (TypeError, ValueError):
            return jsonify({"code": 400, "msg": "accountId 无效", "data": None}), 400
        if platform not in SUPPORTED_STATS_PLATFORMS:
            return jsonify(
                {
                    "code": 400,
                    "msg": "仅支持 platform=douyin|kuaishou|xiaohongshu|bilibili",
                    "data": None,
                }
            ), 400
        targets.append({"accountId": account_id, "platform": platform})

    # de-dupe while preserving order
    seen = set()
    unique_targets = []
    for t in targets:
        key = (t["platform"], t["accountId"])
        if key in seen:
            continue
        seen.add(key)
        unique_targets.append(t)
    targets = unique_targets

    if not targets:
        return jsonify({"code": 400, "msg": "请选择账号", "data": None}), 400
    if len(targets) > 20:
        return jsonify({"code": 400, "msg": "一次最多推送 20 个账号", "data": None}), 400

    sections = []
    skipped = []
    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            for t in targets:
                platform = t["platform"]
                account_id = t["accountId"]
                meta = SUPPORTED_STATS_PLATFORMS[platform]
                cur.execute(
                    "SELECT id, type, userName FROM user_info WHERE id = ?",
                    (account_id,),
                )
                row = cur.fetchone()
                if not row:
                    skipped.append({"accountId": account_id, "platform": platform, "reason": "账号不存在"})
                    continue
                if int(row["type"]) != meta["type"]:
                    skipped.append(
                        {
                            "accountId": account_id,
                            "platform": platform,
                            "reason": f"不是{meta['label']}账号",
                        }
                    )
                    continue
                payload = _load_stats_payload(conn, platform, account_id)
                items = payload.get("items") or []
                if not items:
                    skipped.append(
                        {
                            "accountId": account_id,
                            "platform": platform,
                            "accountName": row["userName"] or str(account_id),
                            "reason": "尚未同步",
                        }
                    )
                    continue
                sections.append(
                    {
                        "platform_label": meta["label"],
                        "account_name": row["userName"] or str(account_id),
                        "last_synced_at": payload.get("lastSyncedAt"),
                        "items": items,
                        "accountId": account_id,
                        "platform": platform,
                    }
                )
    except Exception as e:
        return jsonify({"code": 500, "msg": f"读取失败: {e}", "data": None}), 500

    if not sections:
        return jsonify(
            {
                "code": 400,
                "msg": "所选账号均无已同步数据，请先同步",
                "data": {"skipped": skipped},
            }
        ), 400

    try:
        title, text = format_multi_account_stats_markdown(
            sections=sections,
            rehost_covers=_dingtalk_rehost_covers(),
            include_covers=_dingtalk_push_covers(),
        )
        send_markdown(
            webhook_url=webhook,
            secret=_dingtalk_secret(),
            title=title,
            text=text,
        )
    except DingTalkPushError as e:
        return jsonify({"code": e.code, "msg": e.message, "data": None}), e.code
    except Exception as e:
        return jsonify({"code": 502, "msg": f"推送失败: {e}", "data": None}), 502

    item_count = sum(len(s["items"]) for s in sections)
    return jsonify(
        {
            "code": 200,
            "msg": "推送成功",
            "data": {
                "accountCount": len(sections),
                "itemCount": item_count,
                "skipped": skipped,
            },
        }
    ), 200


# 包装函数：在线程中运行异步函数
def run_async_function(type,id,status_queue):
    print(f"🧵 登录线程启动: type={type}, id={id}", flush=True)
    try:
        match str(type):
            case '1':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue))
                loop.close()
            case '2':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(get_tencent_cookie(id,status_queue))
                loop.close()
            case '3':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(douyin_cookie_gen(id,status_queue))
                loop.close()
            case '4':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(get_ks_cookie(id,status_queue))
                loop.close()
            case '5':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(baijiahao_cookie_gen(id, status_queue))
                loop.close()
            case '6':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bilibili_cookie_gen(id, status_queue))
                loop.close()
            case '7':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(toutiao_cookie_gen(id, status_queue))
                loop.close()
            case '8':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(sohu_cookie_gen(id, status_queue))
                loop.close()
            case '9':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(zhihu_cookie_gen(id, status_queue))
                loop.close()
            case _:
                print(f"❌ 不支持的登录平台类型: {type}", flush=True)
                status_queue.put("500")
    except Exception as e:
        print(f"❌ 登录线程异常 type={type}, id={id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        try:
            status_queue.put("500")
        except Exception:
            pass

# SSE 流生成器函数
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
        else:
            # 避免 CPU 占满
            time.sleep(0.1)

if __name__ == '__main__':
    from utils.ks_collection_tasks import resume
    resume()
    app.run(host='0.0.0.0' ,port=5409)
