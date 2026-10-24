"""Upload an optional recommendation cover before creating the video submission."""
import base64
import mimetypes
from pathlib import Path

import requests

from uploader.bilibili_uploader.content_stats import load_bilibili_cookies


def upload_recommendation_cover(path, account_file):
    cookies = load_bilibili_cookies(account_file)
    if not cookies.get('bili_jct'):
        raise RuntimeError('B站登录状态缺少CSRF凭据，请重新登录后上传4:3封面')
    image = Path(path)
    mime = mimetypes.guess_type(image.name)[0] or 'image/jpeg'
    encoded = base64.b64encode(image.read_bytes()).decode('ascii')
    with requests.Session() as session:
        session.trust_env = False
        session.cookies.update(cookies)
        response = session.post(
            'https://member.bilibili.com/x/vu/web/cover/up',
            headers={'Referer': 'https://member.bilibili.com/', 'User-Agent': 'Mozilla/5.0'},
            data={'csrf': cookies['bili_jct'], 'cover': f'data:{mime};base64,{encoded}'},
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
    url = (body.get('data') or {}).get('url')
    if body.get('code') != 0 or not isinstance(url, str) or not url.startswith(('http://', 'https://', '//')):
        raise RuntimeError('B站4:3推荐页封面上传失败，请检查登录状态或图片规格')
    return url
