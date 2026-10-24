"""Collection selection must succeed before an uploader can publish."""
import re


class CollectionSelectionError(RuntimeError):
    pass


def validate_collection(platform, value):
    if value is None or value == '':
        return ''
    if not isinstance(value, str):
        raise CollectionSelectionError('合集必须是名称或 B站数字合集 ID')
    value = value.strip()
    if not value:
        return ''
    if int(platform) not in (1, 2, 3, 4, 5, 6):
        raise CollectionSelectionError('该平台尚未接入合集，请留空后发布')
    if len(value) > 120:
        raise CollectionSelectionError('合集名称过长')
    if int(platform) == 6 and (not value.isascii() or not value.isdecimal() or int(value) <= 0):
        raise CollectionSelectionError('B站请填写平台合集页面中的数字合集 ID')
    return value


def bilibili_collection_fields(value):
    value = validate_collection(6, value)
    return {'season_id': int(value)} if value else {}


async def _apply_video_collection(page, platform, value):
    name = validate_collection(platform, value)
    if not name:
        return
    # Only collection controls are eligible: never click a publishing button.
    trigger = None
    for label in ('选择要加入到的合集', '请选择合集', '选择合集', '添加到合集', '添加合集', '加入合集', '所属合集'):
        candidates = [page.get_by_placeholder(label, exact=False),
                      page.get_by_role('button', name=label, exact=True),
                      page.get_by_text(label, exact=True)]
        for candidate in candidates:
            if await candidate.count() and await candidate.first.is_visible():
                trigger = candidate.first
                break
        if trigger:
            break
    if trigger is None:
        # A plain label may be next to a select, rather than the trigger itself.
        label = page.get_by_text('合集', exact=True)
        for index in range(await label.count()):
            field = label.nth(index).locator('xpath=..').locator(
                '[role="combobox"], input, [class*="select-selector"], [class*="select-selection"]'
            )
            if await field.count() and await field.first.is_visible():
                trigger = field.first
                break
    if trigger is None:
        raise CollectionSelectionError('发布页没有可用的合集入口，可能未开通权限；已停止发布')
    select_surface = trigger.locator('xpath=ancestor::*[contains(concat(" ",normalize-space(@class)," ")," ant-select-selector ")][1]')
    if await select_surface.count():
        trigger = select_surface.first
    # Bind elements before clicking: selecting an option changes the trigger's
    # accessible name, so the original text-based locator no longer matches.
    trigger_element = await trigger.element_handle()
    field_element = await trigger.locator('xpath=..').element_handle()
    await trigger.scroll_into_view_if_needed()
    await trigger.click(timeout=5000)
    # Search only if the opened collection control exposes a searchable field.
    search = page.locator('[role="listbox"] input, [class*="select-dropdown"] input, input[placeholder*="搜索合集"]')
    if await search.count() and await search.first.is_visible():
        await search.first.fill(name)
    option = page.get_by_role('option', name=name, exact=True)
    if not await option.count():
        option = page.locator(
            '[role="listbox"], [class*="select-dropdown"], [class*="option-list"], '
            '[class*="dropdown-menu"], [class*="popover"], [role="dialog"], '
            '[role="option"], [class*="option"], [class*="dropdown"], [class*="select-menu"], [class*="mix-list"]'
        ).get_by_text(name, exact=True)
    try:
        await option.first.wait_for(state='visible', timeout=7000)
    except Exception as error:
        from utils.publish_diagnostics import capture_editor_failure
        await capture_editor_failure(page,str(platform),'collection')
        raise CollectionSelectionError(f'未找到合集“{name}”，请核对名称及账号权限；已停止发布') from error
    if await option.count() != 1:
        raise CollectionSelectionError(f'合集“{name}”存在多个匹配项；已停止发布')
    option_element = await option.element_handle()
    await option.click(timeout=5000)
    await page.keyboard.press('Escape')
    # Require selected text/checked state in the same control before proceeding.
    selected = False
    actual = await trigger_element.evaluate('(el) => ({text:el.innerText || "", value:el.value || ""})')
    selected = name in actual['text'] or actual['value'] == name
    if not selected:
        selected = name in await field_element.inner_text()
    if not selected:
        selected_text = await field_element.evaluate('''el => Array.from(el.querySelectorAll(
            '.semi-select-selection-text, .ant-select-selection-item, .el-select__selected-item, [data-selected="true"]'
        )).map(item => item.innerText).join('\\n')''')
        selected = name in selected_text
    if not selected:
        selected = await option_element.get_attribute('aria-selected') == 'true'
    if not selected:
        raise CollectionSelectionError(f'未能确认合集“{name}”已选中；已停止发布')
    await page.keyboard.press('Escape')


async def apply_video_collection(page,platform,value):
    from utils.publish_jobs import phase_scope,report_phase
    with phase_scope('collection'):
        if not value:
            report_phase('collection','skipped','未选择合集')
            return
        report_phase('collection','running','选择并核对合集')
        try:await _apply_video_collection(page,platform,value)
        except Exception as error:
            report_phase('collection','failed',str(error));raise
        report_phase('collection','completed','已确认合集选择')
