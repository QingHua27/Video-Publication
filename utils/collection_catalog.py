"""Read collection metadata from signed-in creator pages, without uploading."""
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit


class CollectionCatalogError(RuntimeError):
    def __init__(self, message, status='unavailable'):
        super().__init__(message)
        self.status = status


def normalize_catalog(platform, payload, path):
    if not isinstance(payload, dict):
        return None
    relevant = any(word in path.lower() for word in ('collection','season','album','mix/','mix_','series'))
    if not relevant:
        return None
    if platform == 6 and payload.get('code',0) != 0:
        raise CollectionCatalogError('B站登录已失效或无合集访问权限，请在账号管理重新登录','login_required' if payload.get('code')==-101 else 'unavailable')
    if platform == 2 and payload.get('errCode',0) != 0:
        raise CollectionCatalogError('视频号合集读取失败，请检查登录和账号权限')
    if platform == 3 and payload.get('status_code',0) != 0:
        raise CollectionCatalogError('抖音合集读取失败，请检查登录和账号权限')
    if platform == 4 and payload.get('result',1) != 1:
        raise CollectionCatalogError('快手合集读取失败，请检查登录和账号权限')
    data = payload.get('data',payload)
    if platform == 4 and path.endswith('/collection/visible'):
        if data is False:
            raise CollectionCatalogError('该快手账号当前未开放合集功能','unsupported')
        return None
    list_keys = ('seasons','collectionInfoList','collectionList','collection_list','collections','mix_infos','mix_list','album_list','albums','series_list')
    # Generic list/items are accepted only on a collection-list endpoint, not feed/detail APIs.
    if any(word in path.lower() for word in ('list','seasons')):
        list_keys += ('list','items')
    raw = None
    list_node = {}
    def find(node):
        nonlocal raw, list_node
        if not isinstance(node,dict):
            return
        for key in list_keys:
            if key in node and (isinstance(node[key],list) or (node[key] is None and node.get('total')==0)):
                raw = node[key] or []
                list_node = node
                return
        for key in ('data','result','resultData'):
            if raw is None:
                find(node.get(key))
    find(data)
    if raw is None:
        return None
    items=[];seen=set()
    for entry in raw:
        if not isinstance(entry,dict):
            continue
        entry=entry.get('mix_info') or entry.get('collection') or entry
        if any(key in entry for key in ('aweme_id','bvid','photoId')):
            continue
        key=next((entry[k] for k in ('season_id','mix_id','collectionId','collection_id','album_id','id') if entry.get(k) is not None),None)
        name=next((entry[k] for k in ('mix_name','collectionName','collection_name','album_name','title','name') if entry.get(k)),None)
        if key is None or not isinstance(name,str) or not name.strip():
            continue
        key=str(key);name=name.strip()
        if platform==6 and (not key.isascii() or not key.isdecimal() or int(key)<=0):
            continue
        if key in seen:
            continue
        seen.add(key)
        item={'id':key,'name':name,'value':key if platform==6 else name}
        if platform==4 and 'status' in entry and entry['status']!=1:
            reason=str(entry.get('offlineReason') or '平台尚未开放此合集用于投稿')
            if entry['status']==4 and '有效剧集数不足' in reason:
                item.update(deferred=True,unavailableReason=reason,displayName=f'{name}（发布后加入）')
            else:
                item.update(disabled=True,unavailableReason=reason,displayName=f'{name}（暂不可投稿）')
        items.append(item)
    if raw and not items:
        return None  # Unknown schema must never look like an empty account.
    total = next((list_node.get(key) for key in ('total','collectionListCount','total_count') if isinstance(list_node.get(key),int)),len(raw))
    partial = total > len(raw) or any(list_node.get(key) in (True,1) for key in ('has_more','hasMore'))
    message = f'已读取 {len(items)} 个合集' if items else '该账号暂无合集，请先到平台创建后刷新'
    unavailable=sum(bool(item.get('disabled')) for item in items)
    if unavailable:message+=f'；其中{unavailable}个合集暂不可用于投稿，请到平台合集管理处理'
    if partial: message += '（仅获取部分列表；未显示的合集请到平台后台操作）'
    return {'status':'ready' if items else 'empty','items':items,'partial':partial,'message':message}


URLS={
    1:'https://creator.xiaohongshu.com/publish/publish?source=official',
    2:'https://channels.weixin.qq.com/platform/post/create',
    3:'https://creator.douyin.com/creator-micro/content/upload',
    4:'https://cp.kuaishou.com/article/publish/video',
    5:'https://baijiahao.baidu.com/builder/rc/home',
    6:'https://member.bilibili.com/platform/upload/video/frame',
}


async def read_xhs_publish_collections(page):
    """Use the authenticated official page's list client; never upload media.

    The list API requires the creator client's request handling. Resolve its
    loaded list method by purpose rather than a changing webpack module ID.
    This runs in the main page world (Playwright), not an isolated script world.
    """
    await page.wait_for_function('Array.isArray(window.webpackChunkugc)',timeout=15000)
    pages=await page.evaluate('''async()=>{
        let require;
        window.webpackChunkugc.push([['omnipost-read-collections-'+Date.now()],{},r=>require=r]);
        let list;
        for(const id of Object.keys(require.m)){
            const source=String(require.m[id]);
            if(!source.includes('.GET_COLLECTION_LIST') || !source.includes('.post('))continue;
            const exports=require(id);
            list=Object.values(exports).find(value=>typeof value==='function' && String(value).includes('.GET_COLLECTION_LIST'));
            if(list)break;
        }
        if(!list)throw new Error('Official collection list client is unavailable');
        const pages=[];const cursors=new Set();let cursor='';
        for(let n=0;n<30;n++){
            const data=await list({cursor,needTypeList:[0],targetUid:''});
            if(!Array.isArray(data?.collectionInfoList))throw new Error('Unknown collection list response');
            pages.push(data);
            if(!data.hasMore || !data.nextCursor || cursors.has(data.nextCursor))break;
            cursor=data.nextCursor;cursors.add(cursor);
        }
        return pages;
    }''')
    items={}
    for payload in pages:
        normalized=normalize_catalog(1,{'data':payload},'/api/sns/v1/note/collection/pc/list_v2')
        if normalized is None:raise CollectionCatalogError('小红书合集列表格式已变更，请稍后刷新')
        items.update({item['id']:item for item in normalized['items']})
    partial=bool(pages and pages[-1].get('hasMore'))
    return {'status':'ready' if items else 'empty','items':list(items.values()),'partial':partial,
            'message':f'已读取 {len(items)} 个合集'+('（仅获取部分列表）' if partial else '') if items else '该账号暂无可用于视频/图文笔记的创作合集'}


def browser_storage_state(platform, account_file):
    try:
        state=json.loads(Path(account_file).read_text(encoding='utf-8'))
    except (OSError,ValueError) as error:
        raise CollectionCatalogError('登录文件不可用，请在账号管理重新登录','login_required') from error
    if platform!=6:
        return state
    raw=state.get('cookie_info',{}).get('cookies') or state.get('cookies') or []
    cookies=[{'name':row['name'],'value':row['value'],'domain':'.bilibili.com','path':'/'}
             for row in raw if isinstance(row,dict) and row.get('name') and isinstance(row.get('value'),str)]
    if not any(row['name']=='SESSDATA' for row in cookies):
        raise CollectionCatalogError('B站登录文件缺少登录状态，请重新登录','login_required')
    return {'cookies':cookies,'origins':[]}


async def discover_collections(platform, account_file):
    from utils.channels_session import channels_session,SessionBusy
    if platform!=2:return await _discover_collections(platform,account_file)
    try:
        with channels_session(account_file,'读取合集'):
            return await _discover_collections(platform,account_file)
    except SessionBusy as error:raise CollectionCatalogError(str(error)) from error


async def _discover_collections(platform, account_file):
    from patchright.async_api import async_playwright
    if platform==1:
        from playwright.async_api import async_playwright
    if platform not in URLS:
        return {'status':'unsupported','items':[],'message':'该平台暂不支持自动获取合集'}
    state=browser_storage_state(platform,account_file)
    found=[];problems=[];pending=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            context=await browser.new_context(storage_state=state)
            page=await context.new_page()
            if platform==1:
                await page.goto(URLS[platform],wait_until='domcontentloaded',timeout=30000)
                try:return await read_xhs_publish_collections(page)
                except Exception as error:
                    from utils.publish_diagnostics import capture_editor_failure
                    await capture_editor_failure(page,'xiaohongshu','collection-catalog')
                    raise CollectionCatalogError('未能读取小红书创作合集，请刷新账号登录后重试；收藏专辑及长文合集不能用于视频投稿') from error
            async def receive(response):
                path=urlsplit(response.url).path
                if not any(word in path.lower() for word in ('collection','season','album','mix/','mix_','series')):
                    return
                try:
                    result=normalize_catalog(platform,await response.json(),path)
                    if result is not None:found.append(result)
                except CollectionCatalogError as error:problems.append(error)
                except Exception:pass
            page.on('response',lambda response:pending.append(asyncio.create_task(receive(response))))
            await page.goto(URLS[platform],wait_until='domcontentloaded',timeout=30000)
            await page.wait_for_timeout(2200)
            # Navigation only. Never create a collection, upload media or click publish.
            if not found:
                if platform==4:
                    menu=page.locator('.el-submenu__title').filter(has_text='内容管理')
                    if await menu.count():
                        await menu.first.click(timeout=3000)
                        await page.wait_for_timeout(300)
                elif platform in (1,3,5):
                    label={1:'笔记管理',3:'内容管理',5:'作品管理'}[platform]
                    menu=page.get_by_text(label,exact=True)
                    for index in range(await menu.count()):
                        if await menu.nth(index).is_visible():
                            await menu.nth(index).click(timeout=3000)
                            await page.wait_for_timeout(1000)
                            break
                for label in ('合集管理','我的合集','专辑管理'):
                    menu=page.get_by_text(label,exact=True)
                    for index in range(await menu.count()):
                        if await menu.nth(index).is_visible():
                            await menu.nth(index).click(timeout=3000)
                            await page.wait_for_timeout(1200)
                            break
            # Some sites expose collection selectors inside the creator iframe.
            if not found:
                for frame in page.frames:
                    for label in ('选择要加入到的合集','选择合集','添加合集','所属合集'):
                        trigger=frame.get_by_text(label,exact=True)
                        if await trigger.count() and await trigger.first.is_visible():
                            surface=trigger.first.locator('xpath=ancestor::*[contains(concat(" ",normalize-space(@class)," ")," ant-select-selector ")][1]')
                            await (surface.first if await surface.count() else trigger.first).click(timeout=2500)
                            await page.wait_for_timeout(700)
                            options=frame.locator('[role="option"], [class*="select-dropdown"] [class*="option"], [class*="option-list"] [class*="option"]')
                            items=[]
                            for index in range(await options.count()):
                                node=options.nth(index)
                                name=(await node.inner_text()).strip()
                                if name and name not in ('不选择','暂无数据','暂无合集','无') and await node.is_visible() and len(name)<=120:
                                    items.append({'id':name,'name':name,'value':name})
                            if items and platform!=6:
                                found.append({'status':'ready','items':items,'message':f'已读取 {len(items)} 个合集'})
                            await frame.page.keyboard.press('Escape')
            # Creator portals (especially Channels) mount their editor iframe
            # asynchronously; wait for its authenticated metadata response.
            for _ in range(24):
                if found or problems:
                    break
                await page.wait_for_timeout(250)
            if pending:await asyncio.gather(*pending,return_exceptions=True)
            ready=[value for value in found if value['items']]
            if ready:
                items={row['id']:row for value in ready for row in value['items']}
                partial=any(value.get('partial') for value in ready)
                return {'status':'ready','items':list(items.values()),'partial':partial,'message':f'已读取 {len(items)} 个合集'+('（仅获取部分列表；未显示的合集请到平台后台操作）' if partial else '')}
            if found:return found[-1]
            if problems:raise problems[-1]
            if any(word in urlsplit(page.url).path.lower() for word in ('/login','/passport','/auth')):
                raise CollectionCatalogError('平台登录已过期，请在账号管理重新登录','login_required')
            raise CollectionCatalogError('未能读取该账号的合集入口，可能未开通权限或平台页面已变更，请稍后刷新')
        finally:
            try:
                if platform==2 and 'context' in locals():await context.storage_state(path=account_file)
            finally:await browser.close()
