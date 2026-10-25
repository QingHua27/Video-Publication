"""Read the logged-in profile without confusing an optional remark with identity."""
import json

class LoginLabel(str):
    def __new__(cls, remark='', account_id=None):
        value=super().__new__(cls, str(remark or '').strip()[:100])
        value.account_id=account_id
        return value

# Profile controls only: never scan arbitrary page text (which may contain video authors).
PROFILE_SELECTORS = {
 1: ['.user-info .user-name', '.user-info .username', '.account-name'],
 2: ['.finder-nickname', '.finder-name', '.account-name', '.user-info .nickname'],
 3: ['[class*="header"] [class*="nickname"]', '[class*="header"] [class*="user-name"]', '[class*="account"] [class*="name"]'],
 4: ['.user-info .name', '.user-info .nickname', '.account-name'],
 5: ['.user-name', '.author-name', '.account-name'],
 7: ['.user-info .user-name', '.auth-header .name', '.account-name'],
 8: ['.user-info .name', '.user-name', '.account-name'],
 9: ['.AppHeader-profile [alt]', '.AppHeader-profile [title]'],
}
async def read_username(page, platform):
    try:
        names=await page.evaluate("""selectors => selectors.flatMap(s => Array.from(document.querySelectorAll(s)))
         .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden')
         .map(e => (e.getAttribute('title') || e.getAttribute('alt') || e.textContent || '').trim())""", PROFILE_SELECTORS.get(int(platform), []))
        unique={str(name).strip() for name in names if isinstance(name,str) and 0<len(name.strip())<=100 and '\n' not in name.strip()}
        unique -= {'头像','用户头像','登录','退出登录','创作者中心'}
        return next(iter(unique)) if len(unique)==1 else ''
    except Exception:
        return ''

def account_remarks(db):
    db.execute('CREATE TABLE IF NOT EXISTS account_remarks(account_id INTEGER PRIMARY KEY, remark TEXT NOT NULL DEFAULT \'\')')
    return dict(db.execute('SELECT account_id,remark FROM account_remarks'))

def save_account(db, platform, filename, username, label, status):
    account_remarks(db)
    account_id=getattr(label,'account_id',None)
    existing=db.execute('SELECT id,userName FROM user_info WHERE id=? AND type=?',(account_id,platform)).fetchone() if account_id else None
    if account_id and not existing:
        raise ValueError('重新登录的账号不存在或平台不匹配，请重新打开账号列表')
    name=username or (existing[1] if existing else '用户名待补全')
    if existing:
        account_id=existing[0]
        db.execute('UPDATE user_info SET filePath=?,userName=?,status=? WHERE id=?',(filename,name,status,account_id))
    else:
        account_id=db.execute('INSERT INTO user_info(type,filePath,userName,status) VALUES(?,?,?,?)',(platform,filename,name,status)).lastrowid
    db.execute('INSERT OR REPLACE INTO account_remarks(account_id,remark) VALUES(?,?)',(account_id,str(label or '')))
    return account_id

def bili_username(account_file):
    try:
        payload=json.loads(account_file.read_text(encoding='utf-8'))
        return str((payload.get('user_info') or {}).get('name') or (payload.get('user_info') or {}).get('uname') or '')[:100]
    except Exception:
        return ''

def is_channels_platform_url(url):
    from urllib.parse import urlsplit
    parsed=urlsplit(str(url))
    return parsed.scheme=='https' and parsed.hostname=='channels.weixin.qq.com' and (parsed.path=='/platform' or parsed.path.startswith('/platform/'))
