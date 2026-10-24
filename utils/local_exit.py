"""Run the existing instance-checked stopper after the HTTP response is sent."""
import json
import os
import subprocess
from pathlib import Path

def request_local_exit(root):
    root=Path(root).resolve()
    script=root/'stop-local.ps1'
    try:
        entries=json.loads((root/'logs/local-processes.json').read_text(encoding='utf-8-sig'))
    except (OSError,ValueError) as error:
        raise RuntimeError('找不到本次启动记录，请使用 stop.cmd 停止服务') from error
    own_family={os.getpid(),os.getppid()}
    if not script.is_file() or not isinstance(entries,list) or not any(row.get('Id') in own_family for row in entries if isinstance(row,dict)):
        raise RuntimeError('当前服务不是由 start.cmd 启动，请使用启动它的终端停止服务')
    with (root/'logs/shutdown.log').open('ab') as log:
        subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass',
                          '-File',str(script),'-DelaySeconds','2'],cwd=str(root),
                         stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)
