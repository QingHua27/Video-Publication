"""One UI writer for covers while a read-only video completion observer runs."""
import asyncio
from utils.publish_jobs import report_stage, report_phase, phase_scope

class CoverNotReady(RuntimeError):
    """Platform explicitly refuses cover editing until video transfer completes."""


async def cover_entry_available(page, selectors=(), labels=()):
    candidates=[page.locator(selector) for selector in selectors]
    candidates.extend(page.get_by_text(label,exact=True) for label in labels)
    for candidate in candidates:
        for index in range(await candidate.count()):
            entry=candidate.nth(index)
            if await entry.is_visible() and await entry.is_enabled():
                blocked=await entry.evaluate("el=>!!el.closest('[aria-disabled=true],button:disabled,.semi-button-disabled,.is-disabled,.ant-btn-disabled')")
                if not blocked:return True
    return False

async def prepare_video_and_cover(wait_video, cover_ready, set_cover, *, required=True, timeout=1200, poll_interval=.5):
    """Return only once video and optional cover are ready. Never submit here."""
    async def observe_video():
        with phase_scope('upload'):
            report_phase('upload','running','等待视频上传完成')
            try:
                result=await wait_video()
                if result is False:raise RuntimeError('视频上传失败，未执行发布')
                report_phase('upload','completed','视频上传已完成',100)
                return result
            except asyncio.CancelledError:
                report_phase('upload','cancelled','上传观察已停止，结果尚未确认');raise
            except Exception as error:
                report_phase('upload','failed',str(error));raise
    async def prepare_cover():
        with phase_scope('cover'):
            report_phase('cover','running','设置封面')
            try:
                await set_cover()
            except CoverNotReady:
                report_phase('cover','waiting','平台暂不允许编辑封面，等待视频上传完成');raise
            except Exception as error:
                report_phase('cover','failed',str(error));raise
            else:report_phase('cover','completed','封面已确认完成')
    report_phase('cover','waiting' if required else 'skipped','等待封面入口' if required else '未指定封面，使用平台默认封面')
    video=asyncio.create_task(observe_video())
    covered=not required
    defer_cover=False
    try:
        async with asyncio.timeout(timeout):
            while not video.done():
                if not covered and not defer_cover and await cover_ready():
                    try:
                        await prepare_cover()
                    except CoverNotReady:
                        defer_cover=True
                    else:
                        covered=True
                if not video.done():await asyncio.wait({video},timeout=poll_interval)
            result=await video
            if result is False:raise RuntimeError('视频上传失败，未执行发布')
            if not covered:
                await prepare_cover()
            report_phase('preparation','completed','视频和封面均已就绪',overall_progress=70)
    finally:
        if not video.done():video.cancel()
        await asyncio.gather(video,return_exceptions=True)
