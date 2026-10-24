import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sau_backend

class ExitTests(unittest.TestCase):
    def test_foreign_webpage_cannot_stop_local_services(self):
        with patch('sau_backend.request_local_exit') as stop:
            result=sau_backend.app.test_client().post('/local/exit',json={},headers={'Origin':'https://example.com','X-OmniPost-Exit':'1'})
            self.assertEqual(result.status_code,403)
            stop.assert_not_called()

    def test_exit_requires_explicit_header_and_post(self):
        client=sau_backend.app.test_client()
        self.assertEqual(client.get('/local/exit').status_code,405)
        self.assertEqual(client.post('/local/exit',json={}).status_code,403)

    def test_ui_receives_ack_before_background_stop(self):
        with patch('sau_backend.request_local_exit') as stop:
            result=sau_backend.app.test_client().post('/local/exit',json={},headers={'Origin':'http://127.0.0.1:5173','X-OmniPost-Exit':'1'})
            self.assertEqual(result.status_code,200,result.json)
            stop.assert_called_once()

    def test_helper_only_stops_recorded_instance_and_runs_hidden(self):
        from utils.local_exit import request_local_exit
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'logs').mkdir();(root/'stop-local.ps1').write_text('param($DelaySeconds)')
            (root/'logs/local-processes.json').write_text(json.dumps([{'Id':os.getpid(),'StartTime':'2026-10-23'}]))
            with patch('utils.local_exit.subprocess.Popen') as launch:
                request_local_exit(root)
                args=launch.call_args.args[0]
                self.assertIn('-WindowStyle',args);self.assertIn('Hidden',args)
                self.assertIn(str((root/'stop-local.ps1').resolve()),args)
                self.assertIn('-DelaySeconds',args)
            (root/'logs/local-processes.json').write_text('[{"Id":999999}]')
            with patch('utils.local_exit.subprocess.Popen') as launch:
                with self.assertRaises(RuntimeError):request_local_exit(root)
                launch.assert_not_called()

    def test_windows_venv_launcher_parent_is_a_managed_instance(self):
        from utils.local_exit import request_local_exit
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'logs').mkdir();(root/'stop-local.ps1').write_text('param($DelaySeconds)')
            (root/'logs/local-processes.json').write_text('[{"Id":12345,"StartTime":"2026-10-23"}]')
            with patch('utils.local_exit.os.getppid',return_value=12345),patch('utils.local_exit.subprocess.Popen') as launch:
                request_local_exit(root)
                launch.assert_called_once()

if __name__=='__main__':unittest.main()
