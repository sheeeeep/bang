"""pi 迁移验收：临时 HOME、替身 pi 进程，不触碰本机配置或联网。"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bang


class PiTests(unittest.TestCase):
    def setUp(self):
        """准备隔离设备、备份和可记录参数的 pi 替身。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.root = self.home / ".pi/agent"
        self.root.mkdir(parents=True)
        self.bundle = self.home / "bundle"
        self.bundle.mkdir()
        self.snapshot = {
            "settings.json": {"packages": ["npm:pi-web-access"], "theme": "light/dark"},
            "extensions/pi-session-auto-rename.json": {
                "provider": "openai-codex",
                "id": "model-1",
            },
        }
        self.save(self.bundle / "config.json", self.snapshot)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        executable = self.bin / "pi"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "root = Path(os.environ['PI_CODING_AGENT_DIR'])\n"
            "Path(os.environ['HOME'], 'invocation.json').write_text(json.dumps({"
            "'args': sys.argv[1:], 'cwd': os.getcwd(), "
            "'settings': json.loads((root/'settings.json').read_text())}))\n"
            "sys.exit(int(os.environ.get('PI_TEST_EXIT', '0')))\n"
        )
        executable.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PI_CODING_AGENT_DIR": str(self.root),
            "PATH": str(self.bin),
        }

    def save(self, path, data):
        """写入临时 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def launch(self, args=None):
        """运行使用临时资源和临时设备的真实同步逻辑。"""
        with (
            patch.dict(os.environ, self.env, clear=True),
            patch("bang.importlib.resources.files", return_value=self.bundle),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return bang.main(["pi", "launch", *(args or [])])

    def test_backup_overwrites_and_excludes_credentials(self):
        """备份只保留白名单，并在再次执行时删除过时的备份字段。"""
        source = {
            **self.snapshot["settings.json"],
            "apiKey": "secret-sentinel",
            "httpProxy": "https://user:secret@host",
            "shellCommandPrefix": "secret",
        }
        self.save(self.root / "settings.json", source)
        self.save(self.root / "auth.json", {"token": "secret-sentinel"})
        self.save(
            self.root / "extensions/pi-session-auto-rename.json",
            {"provider": "openai", "id": "model-1", "token": "secret-sentinel"},
        )
        with (
            patch.dict(os.environ, self.env, clear=True),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            bang.backup_pi(self.bundle / "config.json")
            saved = (self.bundle / "config.json").read_text()
            self.assertNotIn("secret", saved)
            self.assertEqual(
                json.loads(saved)["settings.json"], self.snapshot["settings.json"]
            )
            self.save(self.root / "settings.json", {"packages": []})
            (self.root / "extensions/pi-session-auto-rename.json").unlink()
            bang.backup_pi(self.bundle / "config.json")
        self.assertEqual(
            json.loads((self.bundle / "config.json").read_text()),
            {"settings.json": {"packages": []}},
        )

    def test_launch_preserves_credentials_and_cwd_and_arguments(self):
        """覆盖受管设置但保留目标凭据、未知字段和启动上下文。"""
        self.save(
            self.root / "settings.json",
            {
                "packages": ["npm:old"],
                "defaultModel": "old",
                "apiKey": "device-secret",
                "httpProxy": "device-proxy",
            },
        )
        self.save(
            self.root / "extensions/pi-session-auto-rename.json",
            {"provider": "old", "token": "device-secret"},
        )
        auth = self.root / "auth.json"
        auth.write_bytes(b'{"token":"device-secret"}\n')
        self.assertEqual(self.launch(["--", "--mode", "rpc", "hello world"]), 0)
        actual = json.loads((self.home / "invocation.json").read_text())
        self.assertEqual(actual["args"], ["--mode", "rpc", "hello world"])
        self.assertEqual(actual["cwd"], str(Path.cwd()))
        self.assertEqual(
            actual["settings"],
            {
                **self.snapshot["settings.json"],
                "apiKey": "device-secret",
                "httpProxy": "device-proxy",
            },
        )
        self.assertEqual(auth.read_bytes(), b'{"token":"device-secret"}\n')
        rename = json.loads(
            (self.root / "extensions/pi-session-auto-rename.json").read_text()
        )
        self.assertEqual(rename["token"], "device-secret")
        self.assertEqual(rename["id"], "model-1")
        before = (self.root / "settings.json").stat().st_mtime_ns
        self.assertEqual(self.launch(["--help"]), 0)
        self.assertEqual((self.root / "settings.json").stat().st_mtime_ns, before)
        self.assertEqual(
            json.loads((self.home / "invocation.json").read_text())["args"], ["--help"]
        )

    def test_missing_optional_configuration_clears_only_managed_fields(self):
        """备份移除独立配置后，清除旧模型但保留设备私有字段。"""
        self.save(self.bundle / "config.json", {"settings.json": {"packages": []}})
        self.save(
            self.root / "extensions/pi-session-auto-rename.json",
            {"id": "old", "provider": "old", "token": "keep"},
        )
        self.assertEqual(self.launch(), 0)
        self.assertEqual(
            json.loads(
                (self.root / "extensions/pi-session-auto-rename.json").read_text()
            ),
            {"token": "keep"},
        )

    def test_failures_do_not_start_pi_or_overwrite_backup(self):
        """无效类型、未知文件、凭据来源和非法字段必须明确失败。"""
        for source in [
            "https://user:secret@host/repo",
            "npm:pkg?token=secret",
            "../local",
            {"source": "npm:pkg"},
        ]:
            with self.subTest(source=source):
                self.save(self.root / "settings.json", {"packages": [source]})
                original = (self.bundle / "config.json").read_bytes()
                with (
                    patch.dict(os.environ, self.env, clear=True),
                    self.assertRaises(ValueError),
                ):
                    bang.backup_pi(self.bundle / "config.json")
                self.assertEqual((self.bundle / "config.json").read_bytes(), original)
        for invalid in [
            [],
            {},
            {"settings.json": {"packages": [], "apiKey": "secret"}},
            {"../auth.json": {}},
            {"settings.json": {"packages": [], "theme": "https://secret"}},
        ]:
            with self.subTest(invalid=invalid):
                self.save(self.bundle / "config.json", invalid)
                self.assertEqual(self.launch(), 1)
        self.assertFalse((self.home / "invocation.json").exists())

    def test_preflight_rejects_bad_json_and_symlinks_before_writes(self):
        """后续配置损坏或链接跳转时，不提前覆盖主配置。"""
        main = self.root / "settings.json"
        main.write_text('{"packages": []}')
        original = main.read_bytes()
        rename = self.root / "extensions/pi-session-auto-rename.json"
        rename.parent.mkdir()
        rename.write_text("invalid secret-sentinel")
        self.assertEqual(self.launch(), 1)
        self.assertEqual(main.read_bytes(), original)
        rename.unlink()
        rename.symlink_to(self.home / "outside.json")
        self.assertEqual(self.launch(), 1)
        self.assertEqual(main.read_bytes(), original)
        rename.unlink()
        rename.parent.rmdir()
        outside = self.home / "outside"
        outside.mkdir()
        rename.parent.symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.launch(), 1)
        self.assertEqual(main.read_bytes(), original)
        self.assertFalse((self.home / "invocation.json").exists())

    def test_missing_executable_and_process_failure(self):
        """缺少 pi 不写配置，pi 失败则返回其退出码。"""
        (self.bin / "pi").unlink()
        self.assertEqual(self.launch(), 1)
        self.assertFalse((self.root / "settings.json").exists())
        with (
            patch("bang.shutil.which", return_value="pi"),
            patch(
                "bang.subprocess.run", return_value=subprocess.CompletedProcess([], 23)
            ),
        ):
            self.assertEqual(self.launch(), 23)

    def test_environment_root_and_backup_symlink(self):
        """遵循自定义根目录，拒绝相对路径和软链接备份目标。"""
        with patch.dict(os.environ, {"HOME": str(self.home)}, clear=True):
            self.assertEqual(bang.pi_agent_dir(), self.root)
        with (
            patch.dict(os.environ, {"PI_CODING_AGENT_DIR": "relative"}, clear=True),
            self.assertRaises(ValueError),
        ):
            bang.pi_agent_dir()
        self.save(self.root / "settings.json", {"packages": []})
        target = self.home / "link.json"
        target.symlink_to(self.bundle / "config.json")
        with (
            patch.dict(os.environ, self.env, clear=True),
            self.assertRaises(ValueError),
        ):
            bang.backup_pi(target)

    def test_script_runs_outside_repository_and_reports_errors(self):
        """工程脚本固定写回自身仓库，缺少来源时明确失败且保留旧备份。"""
        repository = self.home / "repository"
        (repository / "scripts").mkdir(parents=True)
        shutil.copy(Path(bang.__file__).resolve(), repository / "bang.py")
        shutil.copy(
            Path(bang.__file__).resolve().parent / "scripts/backup_pi.py",
            repository / "scripts/backup_pi.py",
        )
        self.save(
            self.root / "settings.json", {"theme": "dark", "apiKey": "secret-sentinel"}
        )
        command = [sys.executable, "-B", str(repository / "scripts/backup_pi.py")]
        result = subprocess.run(
            command,
            cwd=self.home,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = repository / "bang_pi/config.json"
        self.assertEqual(
            json.loads(saved.read_text()),
            {"settings.json": {"theme": "dark", "packages": []}},
        )
        before = saved.read_bytes()
        (self.root / "settings.json").unlink()
        result = subprocess.run(
            command,
            cwd=self.home,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("备份失败", result.stderr)
        self.assertEqual(saved.read_bytes(), before)

    def test_atomic_write_failure_keeps_original_and_cleans_temporary(self):
        """替换失败不破坏旧备份，也不遗留含设备配置的临时文件。"""
        target = self.bundle / "config.json"
        before = target.read_bytes()
        with (
            patch("bang.os.replace", side_effect=OSError("write failed")),
            self.assertRaises(OSError),
        ):
            bang.pi_write_json(target, {"settings.json": {"packages": []}})
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(self.bundle.iterdir()), [target])

    def test_custom_root_keeps_rename_plugins_actual_home_path(self):
        """自定义 pi 根目录时，命名插件仍读取其固定 HOME 配置路径。"""
        self.env["PI_CODING_AGENT_DIR"] = str(self.home / "custom-agent")
        custom = Path(self.env["PI_CODING_AGENT_DIR"])
        self.save(custom / "settings.json", {"packages": []})
        self.save(
            self.root / "extensions/pi-session-auto-rename.json",
            {"provider": "openai", "id": "model-2"},
        )
        with (
            patch.dict(os.environ, self.env, clear=True),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            bang.backup_pi(self.bundle / "config.json")
        self.assertEqual(
            json.loads((self.bundle / "config.json").read_text())[
                "extensions/pi-session-auto-rename.json"
            ]["id"],
            "model-2",
        )
        self.save(self.bundle / "config.json", self.snapshot)
        self.assertEqual(self.launch(), 0)
        self.assertEqual(
            json.loads((custom / "settings.json").read_text()),
            self.snapshot["settings.json"],
        )
        self.assertEqual(
            json.loads(
                (self.root / "extensions/pi-session-auto-rename.json").read_text()
            )["id"],
            "model-1",
        )
        self.assertFalse((custom / "extensions").exists())

    def test_cli_uses_bundled_snapshot_without_skill_configuration(self):
        """从非仓库目录调用 CLI，无需先运行 bang init。"""
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(bang.__file__).resolve()),
                "pi",
                "launch",
                "--version",
            ],
            cwd=self.home,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            json.loads((self.home / "invocation.json").read_text())["args"],
            ["--version"],
        )


if __name__ == "__main__":
    unittest.main()
