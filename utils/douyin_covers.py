"""Select Douyin cover orientations by their visible labels, never DOM position."""
import re

async def find_cover_entry(page):
    """Use the same visible, enabled entry for readiness and clicking."""
    entries = page.get_by_text('选择封面', exact=True)
    for index in range(await entries.count()):
        entry = entries.nth(index)
        if await entry.is_visible() and await entry.is_enabled():
            blocked = await entry.evaluate(
                "el=>!!el.closest('[aria-disabled=true],button:disabled,.semi-button-disabled')"
            )
            if not blocked:
                return entry
    return None


async def upload_cover_for_orientation(page,modal,kind,path):
    patterns={
        'portrait':re.compile(r'竖(?:版)?封面|竖版|3\s*[:：/比]\s*4'),
        'landscape':re.compile(r'横(?:版)?封面|横版|(?:4\s*[:：/比]\s*3|16\s*[:：/比]\s*9)')
    }
    wanted=patterns[kind];opposite=patterns['landscape' if kind=='portrait' else 'portrait']
    selected=None
    for candidates in (modal.get_by_role('tab',name=wanted),modal.get_by_role('button',name=wanted),modal.get_by_text(wanted)):
        visible=[]
        for index in range(await candidates.count()):
            item=candidates.nth(index)
            if await item.is_visible():
                text=await item.inner_text()
                if wanted.search(text) and not opposite.search(text) and len(text.strip())<100:visible.append(item)
        if len(visible)==1:selected=visible[0];break
        if len(visible)>1:raise RuntimeError('抖音封面方向入口存在多个匹配项，已停止，避免上传错误封面')
    if selected is None:raise RuntimeError(f'无法确认抖音{"竖版3:4" if kind=="portrait" else "横版"}封面入口，未上传封面')
    await selected.scroll_into_view_if_needed();await selected.click(timeout=5000)
    await page.wait_for_timeout(250)
    # The editor keeps both upload/replace inputs, sometimes for both tabs.
    # Let the visible upload action choose its own input instead of guessing.
    upload_action=None
    for candidates in (modal.get_by_role('button',name='上传封面',exact=True),
                       modal.get_by_text('上传封面',exact=True)):
        visible=[]
        for index in range(await candidates.count()):
            candidate=candidates.nth(index)
            if await candidate.is_visible():visible.append(candidate)
        if len(visible)>1:raise RuntimeError('抖音当前方向存在多个可见上传入口，已停止，避免传错封面')
        if visible:upload_action=visible[0];break
    if upload_action is not None:
        # The text can sit underneath an absolute-positioned upload overlay.
        # Scope to its nearest upload region and distinguish primary vs replace
        # by exact class token; never use the other orientation's hidden input.
        region=upload_action.locator('xpath=ancestor-or-self::*[.//input[@type="file"]][1]')
        primary=region.locator('input[type="file"].semi-upload-hidden-input')
        if await primary.count()==1:
            await primary.set_input_files(str(path))
        else:
            scoped_inputs=region.locator('input[type="file"]')
            if await scoped_inputs.count()==1:
                await scoped_inputs.set_input_files(str(path))
            elif await scoped_inputs.count()>1:
                raise RuntimeError('抖音当前封面上传区域无法唯一定位主上传控件，已停止')
            else:
                async with page.expect_file_chooser(timeout=10000) as chooser:
                    await upload_action.click(timeout=5000)
                await (await chooser.value).set_files(str(path))
    else:
        inputs=modal.locator('div[class*="semi-upload"]:visible input[type="file"]')
        if await inputs.count()!=1:
            inputs=modal.locator('input[type="file"]')
            if await inputs.count()!=1:raise RuntimeError('抖音当前方向的封面上传控件不唯一，已停止')
        await inputs.set_input_files(str(path))
    # The new editor decodes/uploads asynchronously without consistently exposing
    # a busy indicator. Allow its image preview to settle before switching tabs.
    await page.wait_for_timeout(5000)
    busy=modal.locator('[aria-busy="true"]:visible,.semi-upload-file-status-uploading:visible,.semi-spin-spinning:visible')
    for index in range(await busy.count()):await busy.nth(index).wait_for(state='hidden',timeout=30000)
