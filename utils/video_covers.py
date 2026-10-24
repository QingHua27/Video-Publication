"""Strict cover upload for creator editors without a dedicated uploader method."""
from pathlib import Path


async def apply_custom_video_cover(page, path):
    if not path:
        return
    if not Path(path).is_file():
        raise FileNotFoundError('所选封面不存在，请重新上传')
    trigger = page.get_by_text('上传封面', exact=True).or_(page.get_by_text('选择封面', exact=True)).or_(page.get_by_text('更换封面', exact=True))
    visible = [trigger.nth(i) for i in range(await trigger.count()) if await trigger.nth(i).is_visible()]
    if len(visible) != 1:
        raise RuntimeError('无法唯一定位视频封面入口，已停止发布')
    await visible[0].click()
    dialog = page.locator('[role="dialog"]:visible, .cheetah-modal:visible, .ant-modal:visible').filter(has=page.locator('input[type="file"]'))
    await dialog.first.wait_for(state='visible', timeout=10000)
    inputs = dialog.first.locator('input[type="file"][accept*="image"]')
    if await inputs.count() != 1:
        raise RuntimeError('无法唯一定位封面图片上传控件，已停止发布')
    await inputs.set_input_files(str(path))
    confirm = dialog.first.get_by_role('button', name='确定', exact=True).or_(dialog.first.get_by_role('button', name='确认', exact=True)).or_(dialog.first.get_by_role('button', name='完成', exact=True))
    await confirm.click(timeout=15000)
    await dialog.first.wait_for(state='hidden', timeout=30000)

async def apply_baijiahao_video_cover(page,path):
    if not path:return
    if not Path(path).is_file():raise FileNotFoundError('所选封面不存在')
    from utils.publish_jobs import report_stage
    report_stage('设置横版封面（视频可继续上传）',35)
    section=page.locator('.form-cover').first
    landscape=section.locator('[class*="cover-container"]').first
    await landscape.wait_for(state='visible',timeout=10000)
    previous_image=landscape.locator('img').first
    previous_src=await previous_image.get_attribute('src') if await previous_image.count() else ''
    await landscape.click()
    await page.wait_for_timeout(500)
    from utils.publish_diagnostics import capture_editor_failure
    await capture_editor_failure(page,'baijiahao','cover-opened')
    import json
    inputs=await page.locator('input[type="file"][accept*="image"]').evaluate_all("nodes=>nodes.map(n=>({accept:n.accept,parents:(()=>{let x=n;const a=[];for(let i=0;i<5&&x;i++,x=x.parentElement)a.push({tag:x.tagName,class:x.className});return a})()}))")
    (Path(__import__('conf').BASE_DIR)/'logs/publish-diagnostics/baijiahao-cover-inputs.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2),encoding='utf-8')
    dialogs=page.locator('.cheetah-modal:visible, [role="dialog"]:visible').filter(has=page.get_by_text('本地上传',exact=True))
    dialog_element=await dialogs.first.element_handle() if await dialogs.count() else None
    if dialog_element:
        local_upload=dialogs.first.get_by_text('本地上传',exact=True).first
        file_input=local_upload.locator('xpath=ancestor::*[.//input[@type="file"]][1]').locator('input[type="file"][accept*="image"]').first
    else:
        file_input=landscape.locator('input[type="file"][accept*="image"]').first
        if not await file_input.count():raise RuntimeError('百家号横版封面编辑器未打开，已停止发布')
    before_images=await dialog_element.eval_on_selector_all('img','nodes=>nodes.map(n=>n.getAttribute("src"))') if dialog_element else []
    await file_input.set_input_files(str(path))
    if dialog_element:
        # Uploading the file is asynchronous; newly loaded video frames are not
        # evidence that the local image was selected. The upload tile disappears
        # only after the editor replaces it with the uploaded thumbnail.
        await local_upload.wait_for(state='hidden',timeout=45000)
        await page.wait_for_function("args=>Array.from(args.root.querySelectorAll('img')).some(img=>img.complete && img.naturalWidth>=300 && !args.before.includes(img.getAttribute('src')))",arg={'root':dialog_element,'before':before_images},timeout=45000)
        await page.wait_for_timeout(5000)
        await capture_editor_failure(page,'baijiahao','cover-ready')
    else:await page.wait_for_timeout(1500)
    if dialog_element:
        confirm=page.get_by_role('button',name='确定',exact=True).first
        await confirm.wait_for(state='visible',timeout=15000)
        await confirm.click()
        await dialog_element.wait_for_element_state('hidden',timeout=30000)
        await page.wait_for_timeout(5000)
    try:
        await page.wait_for_function("old=>{const image=document.querySelector('.form-cover [class*=cover-container] img');return image && image.getAttribute('src') && image.getAttribute('src')!==old}",arg=previous_src,timeout=45000)
    except Exception as error:raise RuntimeError('百家号未能确认横版封面已更新，已停止发布') from error
