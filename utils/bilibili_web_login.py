"""Forward biliup QR images to the Web login stream without opening a console."""
import asyncio
import base64
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


class _PtyLogin:
    """Keep biliup's interactive selector in a hidden pseudo console."""
    def __init__(self, command, cwd):
        from winpty import PtyProcess
        self.process = PtyProcess.spawn(command, cwd=str(cwd), dimensions=(40, 120))
        self.reader = threading.Thread(target=self._drain, daemon=True)
        self.reader.start()

    def _drain(self):
        text = ''
        selected = False
        try:
            while self.process.isalive():
                text = (text + self.process.read(4096))[-8192:]
                if not selected and '扫码登录' in text:
                    # biliup 1.1.29 defaults to SMS (index 1); QR login is index 2.
                    self.process.write('\x1b[B\r')
                    selected = True
        except (EOFError, OSError):
            pass

    def poll(self):
        if self.process.isalive():
            return None
        return self.process.exitstatus if self.process.exitstatus is not None else 1

    def terminate(self):
        self.process.terminate(force=True)

    def kill(self):
        self.process.terminate(force=True)

    def wait(self, timeout=None):
        return self.process.wait()


def _spawn_login(command, cwd):
    if sys.platform != 'win32':
        raise RuntimeError('This local Web login adapter requires Windows')
    return _PtyLogin(command, cwd)


async def collect_login_qrcode(binary, account_file, status_queue, session_root,
                               timeout=200, poll_interval=0.5):
    session_root = Path(session_root)
    session_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bilibili-', dir=session_root) as directory:
        process = _spawn_login(
            [str(binary), '-u', str(account_file), 'login'],
            cwd=directory,
        )
        last_image = None
        deadline = asyncio.get_running_loop().time() + timeout
        try:
            while asyncio.get_running_loop().time() < deadline:
                image_path = Path(directory) / 'qrcode.png'
                try:
                    image = image_path.read_bytes()
                except OSError:
                    image = b''
                # Do not send a partially written PNG or a duplicate image.
                if (image.startswith(b'\x89PNG\r\n\x1a\n')
                        and image.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82')
                        and image != last_image):
                    status_queue.put('data:image/png;base64,' + base64.b64encode(image).decode('ascii'))
                    last_image = image
                code = process.poll()
                if code is not None:
                    return code == 0 and Path(account_file).is_file()
                await asyncio.sleep(poll_interval)
            return False
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait, timeout=5)
