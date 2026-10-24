import asyncio
import base64
import subprocess
import sqlite3
import tempfile
import unittest
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from utils.bilibili_web_login import collect_login_qrcode


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==')


class BilibiliWebLoginTests(unittest.TestCase):
    def run_case(self, mode):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            account = root / 'account.json'
            queue = Queue()
            captured = {}

            class Process:
                returncode = None
                terminated = False

                def __init__(self, command, **kwargs):
                    captured.update(kwargs)
                    captured['command'] = command
                    self.work = Path(kwargs['cwd'])
                    self.calls = 0
                    if mode != 'timeout':
                        (self.work / 'qrcode.png').write_bytes(PNG)

                def poll(self):
                    self.calls += 1
                    if self.terminated:
                        return -15
                    if mode == 'success' and self.calls > 1:
                        account.write_text('{}')
                        self.returncode = 0
                    elif mode == 'failure':
                        self.returncode = 1
                    return self.returncode

                def terminate(self):
                    self.terminated = True

                def wait(self, timeout=None):
                    return self.poll()

                def kill(self):
                    self.terminated = True

            with patch('utils.bilibili_web_login._spawn_login', side_effect=Process):
                result = asyncio.run(collect_login_qrcode(
                    Path('biliup.exe'), account, queue, root / 'sessions',
                    timeout=0.03, poll_interval=0.001,
                ))
            messages = list(queue.queue)
            self.assertFalse(Path(captured['cwd']).exists())
            self.assertFalse(captured.get('creationflags', 0) & getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
            return result, messages

    def test_image_is_streamed_and_success_requires_cookie_and_exit(self):
        success, messages = self.run_case('success')
        self.assertTrue(success)
        self.assertEqual(messages, ['data:image/png;base64,' + base64.b64encode(PNG).decode('ascii')])

    def test_failed_process_does_not_report_success(self):
        success, messages = self.run_case('failure')
        self.assertFalse(success)
        self.assertNotIn('200', messages)

    def test_timeout_terminates_process_and_cleans_session(self):
        success, messages = self.run_case('timeout')
        self.assertFalse(success)
        self.assertEqual(messages, [])

    def test_web_login_registers_verified_cookie_and_updates_existing_account(self):
        from myUtils import login
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'db').mkdir()
            with sqlite3.connect(root / 'db/database.db') as conn:
                conn.execute('CREATE TABLE user_info (id INTEGER PRIMARY KEY, type INTEGER, filePath TEXT, userName TEXT, status INTEGER)')
            conn.close()

            async def verified_login(binary, account_file, queue, session_root):
                account_file.write_text('{}')
                queue.put('data:image/png;base64,test')
                return True

            for _ in range(2):
                queue = Queue()
                with patch.object(login, 'BASE_DIR', root), \
                     patch('uploader.bilibili_uploader.runtime.ensure_biliup_binary', return_value=Path('biliup.exe')), \
                     patch('utils.bilibili_web_login.collect_login_qrcode', side_effect=verified_login), \
                     patch.object(login, 'run_biliup_command', return_value=SimpleNamespace(returncode=0)):
                    asyncio.run(login.bilibili_cookie_gen('test-account', queue))
                self.assertEqual(list(queue.queue), ['data:image/png;base64,test', '200'])
            with sqlite3.connect(root / 'db/database.db') as conn:
                rows = conn.execute('SELECT type, filePath, userName, status FROM user_info').fetchall()
            conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0][0], rows[0][2], rows[0][3]), (6, 'test-account', 1))
            self.assertTrue((root / 'cookiesFile' / rows[0][1]).is_file())

    def test_web_login_timeout_emits_failure_without_success(self):
        from myUtils import login
        with tempfile.TemporaryDirectory() as directory:
            queue = Queue()
            with patch.object(login, 'BASE_DIR', Path(directory)), \
                 patch('uploader.bilibili_uploader.runtime.ensure_biliup_binary', return_value=Path('biliup.exe')), \
                 patch('utils.bilibili_web_login.collect_login_qrcode', new=AsyncMock(return_value=False)):
                asyncio.run(login.bilibili_cookie_gen('test-account', queue))
            self.assertEqual(list(queue.queue), ['500'])


if __name__ == '__main__':
    unittest.main()
