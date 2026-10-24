"""Confirm a cover editor with bounded retries; never click a publish action."""
import asyncio
async def finish_cover_dialog(page,modal,platform,labels,timeout=90,interval=3):
    import re
    from utils.publish_diagnostics import capture_editor_failure
    deadline=asyncio.get_running_loop().time()+timeout
    pattern=re.compile('^(?:'+'|'.join(re.escape(x) for x in labels)+')$')
    while asyncio.get_running_loop().time()<deadline:
        if not await modal.is_visible():return
        busy=modal.locator('[aria-busy=true]:visible,.semi-upload-file-status-uploading:visible,.semi-spin-spinning:visible')
        if not await busy.count():
            buttons=modal.get_by_role('button',name=pattern)
            visible=[buttons.nth(i) for i in range(await buttons.count()) if await buttons.nth(i).is_visible()]
            if len(visible)==1:
                button=visible[0]
                classes=await button.get_attribute('class') or ''
                if await button.is_enabled() and 'disabled' not in classes.lower():
                    try:await button.click(timeout=3000)
                    except Exception:
                        if not await modal.is_visible():return
        try:
            await modal.wait_for(state='hidden',timeout=int(interval*1000))
            return
        except Exception:pass
    await capture_editor_failure(page,platform,'cover-confirm-timeout')
    raise RuntimeError(f'{platform}封面仍未确认完成，已保存页面截图；未执行发布')
