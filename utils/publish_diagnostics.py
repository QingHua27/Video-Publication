"""Save local evidence for failing editor controls without publishing anything."""
from pathlib import Path
from conf import BASE_DIR

async def capture_editor_failure(page, platform, stage):
    root=Path(BASE_DIR)/'logs'/'publish-diagnostics'
    root.mkdir(parents=True,exist_ok=True)
    target=root/f'{platform}-{stage}.png'
    try:await page.screenshot(path=str(target),full_page=True,timeout=5000)
    except Exception:pass
    try:
        controls=await page.locator('input,textarea,[contenteditable="true"],button,[role="dialog"]').evaluate_all("nodes=>nodes.map(n=>({tag:n.tagName,type:n.type,placeholder:n.getAttribute('placeholder'),accept:n.getAttribute('accept'),role:n.getAttribute('role'),contenteditable:n.getAttribute('contenteditable'),dataPlaceholder:n.getAttribute('data-placeholder'),class:n.className,text:n.tagName==='BUTTON' ? n.innerText : undefined}))")
        import json
        target.with_suffix('.json').write_text(json.dumps(controls,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:pass
    return str(target)
