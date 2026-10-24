"""Report observed platform upload progress without inventing transfer percentages."""
import re
from utils import publish_jobs

async def report_upload_wait(page, scope=None):
    percent=None
    try:
        samples=await (scope if scope is not None else page).locator('[role="progressbar"],[class*="progress"],[class*="Progress"]').evaluate_all("nodes=>nodes.filter(el=>el.getClientRects().length).slice(0,30).map(el=>({value:el.getAttribute('aria-valuenow'),text:el.innerText || ''}))")
        for sample in samples:
            text=sample.get('value')
            match=re.search(r'(?<![0-9])(100|[0-9]{1,2})(?:\.[0-9]+)?\s*%',sample.get('text',''))
            if text is None and match:text=match.group(0).rstrip('%').strip()
            if text is not None:
                value=float(text)
                if 0<=value<=100:percent=value;break
    except Exception:pass
    publish_jobs.report_upload_progress(percent)
