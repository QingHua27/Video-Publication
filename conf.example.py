from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.resolve()
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BASE_DIR / ".browsers"))
XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = ""  # optional, e.g. C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = False  # show official pages for interactive login
PUBLISH_BROWSER_HEADLESS = True  # publishing jobs can reveal their existing window
DEBUG_MODE = True  # default debug behavior
DINGTALK_WEBHOOK_URL = ""  # DingTalk group robot webhook; empty disables push
DINGTALK_SECRET = ""  # optional robot secret for signed webhooks
DINGTALK_PUSH_COVERS = True  # False = do not embed cover images in DingTalk messages
DINGTALK_REHOST_COVERS = True  # rehost covers to a temp public JPEG URL so DingTalk can display them
