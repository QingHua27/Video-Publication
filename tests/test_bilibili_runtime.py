import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from uploader.bilibili_uploader.runtime import (
    build_biliup_runtime_path,
    ensure_biliup_binary,
    run_biliup_command,
)


class BiliupRuntimeTests(unittest.TestCase):
    @patch('uploader.bilibili_uploader.runtime.subprocess.run')
    @patch('uploader.bilibili_uploader.runtime.ensure_biliup_binary')
    def test_upload_bypasses_only_video_cdn_proxy_and_removes_ansi(self, binary, run):
        binary.return_value=Path('biliup.exe')
        run.return_value=Mock(returncode=1,stdout='',stderr='\x1b[31mcertificate expired\x1b[0m')
        with patch.dict('os.environ',{'HTTPS_PROXY':'http://127.0.0.1:7890','NO_PROXY':'localhost'},clear=True):
            result=run_biliup_command(['upload','video.mp4'])
        env=run.call_args.kwargs['env']
        self.assertNotIn('HTTPS_PROXY',env)
        self.assertEqual(env['NO_PROXY'],'*')
        self.assertEqual(result.stderr,'certificate expired')
        self.assertNotIn('bilibili.com',env['NO_PROXY'])

    @patch('uploader.bilibili_uploader.runtime.subprocess.run')
    @patch('uploader.bilibili_uploader.runtime.ensure_biliup_binary')
    def test_login_keeps_existing_proxy_exclusions(self, binary, run):
        binary.return_value=Path('biliup.exe')
        run.return_value=Mock(returncode=0,stdout='',stderr='')
        with patch.dict('os.environ',{'NO_PROXY':'localhost'},clear=True):
            run_biliup_command(['login'])
        self.assertEqual(run.call_args.kwargs['env']['NO_PROXY'],'localhost')

    def test_build_biliup_runtime_path_returns_platform_path(self):
        path = build_biliup_runtime_path("Windows")
        self.assertTrue(str(path).endswith("biliup.exe"))

    @patch("uploader.bilibili_uploader.runtime.fetch_latest_release")
    def test_ensure_biliup_binary_downloads_when_missing(self, mock_release):
        mock_release.return_value = {
            "tag_name": "v1.0.0",
            "asset_url": "https://example.invalid/biliup.exe",
            "asset_name": "biliup.exe",
        }
        with patch("uploader.bilibili_uploader.runtime.read_local_biliup_version", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("uploader.bilibili_uploader.runtime.download_biliup_asset") as mock_download:
                    with patch("uploader.bilibili_uploader.runtime.write_local_biliup_version") as mock_write_version:
                        ensure_biliup_binary(force_check=True)
        mock_download.assert_called_once()
        mock_write_version.assert_called_once_with("v1.0.0")

    @patch("uploader.bilibili_uploader.runtime.fetch_latest_release")
    def test_ensure_biliup_binary_reuses_local_when_up_to_date(self, mock_release):
        mock_release.return_value = {
            "tag_name": "v1.0.0",
            "asset_url": "https://example.invalid/biliup.exe",
            "asset_name": "biliup.exe",
        }
        with patch("uploader.bilibili_uploader.runtime.read_local_biliup_version", return_value="v1.0.0"):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("uploader.bilibili_uploader.runtime.download_biliup_asset") as mock_download:
                    with patch("uploader.bilibili_uploader.runtime.write_local_biliup_version") as mock_write_version:
                        ensure_biliup_binary(force_check=True)
        mock_download.assert_not_called()
        mock_write_version.assert_not_called()

    @patch("uploader.bilibili_uploader.runtime.subprocess.run")
    @patch("uploader.bilibili_uploader.runtime.ensure_biliup_binary")
    def test_run_biliup_command_returns_completed_process(self, mock_ensure_binary, mock_run):
        mock_ensure_binary.return_value = build_biliup_runtime_path("Windows")
        mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
        result = run_biliup_command(["login"])
        self.assertEqual(result.returncode, 0)

    @patch("uploader.bilibili_uploader.runtime.subprocess.run")
    @patch("uploader.bilibili_uploader.runtime.ensure_biliup_binary")
    def test_run_biliup_command_login_uses_interactive_stdio(self, mock_ensure_binary, mock_run):
        mock_ensure_binary.return_value = Path("C:/mock/biliup.exe")
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        run_biliup_command(["login"], interactive=True)
        _, kwargs = mock_run.call_args
        self.assertNotIn("capture_output", kwargs)
