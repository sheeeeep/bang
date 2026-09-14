"""Terminal acceptance tests for `bang skill select`.

These tests exercise the agreed seam only: the real CLI attached to a real PTY,
with an isolated HOME and real files/Git repository.  They intentionally do not
mock curses or call chooser internals.
"""

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path

CLI = Path(__file__).with_name("bang.py")


class PtySession:
    def __init__(self, argv, *, cwd, env, rows=24, cols=80, deadline=5.0):
        self.deadline = deadline
        self.output = bytearray()
        self.master_fd, slave_fd = pty.openpty()
        fcntl.ioctl(
            slave_fd,
            termios.TIOCSWINSZ,
            struct.pack("HHHH", rows, cols, 0, 0),
        )
        self.initial_attrs = termios.tcgetattr(slave_fd)
        self.proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=1)
        finally:
            try:
                os.close(self.master_fd)
            except OSError:
                pass

    def read_available(self):
        while True:
            try:
                chunk = os.read(self.master_fd, 4096)
            except BlockingIOError:
                return
            except OSError as error:
                if error.errno == errno.EIO:
                    return
                raise
            if not chunk:
                return
            self.output.extend(chunk)

    def text(self):
        return self.output.decode("utf-8", errors="replace")

    def wait_for(self, *needles, timeout=None):
        """Synchronize on transcript hooks; final behavior is checked in previews/files."""
        end = time.monotonic() + (self.deadline if timeout is None else timeout)
        while time.monotonic() < end:
            self.read_available()
            text = self.text()
            if all(needle in text for needle in needles):
                return text
            if self.proc.poll() is not None:
                self.read_available()
                break
            remaining = max(0, end - time.monotonic())
            select.select([self.master_fd], [], [], min(0.05, remaining))
        self.read_available()
        raise AssertionError(
            f"timed out waiting for {needles!r}; rc={self.proc.poll()}; output:\n{self.text()}"
        )

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        os.write(self.master_fd, data)

    def send_and_wait_for_output(self, data, timeout=1.0):
        self.read_available()
        before = len(self.output)
        self.send(data)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.read_available()
            if len(self.output) > before or self.proc.poll() is not None:
                return self.text()
            remaining = max(0, end - time.monotonic())
            select.select([self.master_fd], [], [], min(0.05, remaining))
        raise AssertionError(
            f"timed out waiting for terminal response; output:\n{self.text()}"
        )

    def wait_exit(self, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.read_available()
            code = self.proc.poll()
            if code is not None:
                self.read_available()
                return code, self.text()
            remaining = max(0, end - time.monotonic())
            select.select([self.master_fd], [], [], min(0.05, remaining))
        raise AssertionError(f"child did not exit; output:\n{self.text()}")


class TerminalSelectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.library = self.home / "my-skills"
        self.project = self.home / "project"
        self.project.mkdir()
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "TERM": "xterm-256color",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
        }
        for key in list(self.env):
            if key.startswith("GIT_") and key != "GIT_CONFIG_NOSYSTEM":
                self.env.pop(key)
        subprocess.run(
            ["git", "-C", str(self.project), "init", "-q"],
            env=self.env,
            check=True,
        )
        self.sessions = []
        self.addCleanup(self.cleanup_sessions)

    def cleanup_sessions(self):
        for session in self.sessions:
            session.close()

    def skill(self, name, content="new"):
        path = self.library / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(content, encoding="utf-8")
        return path

    def open_select(self, *, rows=24, cols=80):
        session = PtySession(
            [sys.executable, str(CLI), "skill", "select"],
            cwd=self.project,
            env=self.env,
            rows=rows,
            cols=cols,
        )
        self.sessions.append(session)
        return session

    def wait_for_terminal_chooser(self, session, *names):
        return session.wait_for("搜索", "已选", *names)

    def assert_linked(self, name):
        self.assertEqual(
            (self.project / ".agents/skills" / name).resolve(),
            self.library / name,
        )

    def assert_not_linked(self, name):
        self.assertFalse((self.project / ".agents/skills" / name).exists())

    def test_arrow_keys_move_cursor_and_space_toggles_only_focused_skill(self):
        self.skill("alpha")
        self.skill("beta")
        self.skill("gamma")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha", "beta", "gamma")
        session.send_and_wait_for_output("\x1bOB")
        session.send_and_wait_for_output("\x1bOB")
        session.send_and_wait_for_output("\x1bOA")
        session.send(" ")
        session.wait_for("已选", "1")
        session.send("\r")
        session.wait_for("新增链接: beta", "执行以上变更？")
        self.assertNotIn("新增链接: alpha", session.text())
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_not_linked("alpha")
        self.assert_linked("beta")

    def test_common_csi_arrow_keys_do_not_cancel_the_chooser(self):
        self.skill("alpha")
        self.skill("beta")
        self.skill("gamma")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha", "beta", "gamma")
        session.send("\x1b[B\x1b[B\x1b[A \r")
        session.wait_for("新增链接: beta", "执行以上变更？")
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_linked("beta")
        self.assert_not_linked("alpha")
        self.assert_not_linked("gamma")

    def test_space_selects_current_skill_and_enter_only_previews_until_confirmed(self):
        self.skill("alpha")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha")
        session.send(" ")
        session.wait_for("已选", "1")
        session.send("\r")
        session.wait_for("新增链接: alpha", "执行以上变更？")
        self.assert_not_linked("alpha")
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_linked("alpha")

    def test_case_insensitive_live_search_and_hidden_selections_are_preserved(self):
        self.skill("TDD")
        self.skill("alpha")
        self.skill("research")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "TDD", "alpha", "research")
        session.send("research")
        session.wait_for("搜索", "research")
        session.send(" ")
        session.wait_for("已选", "1")
        session.send("\x1b")
        session.wait_for("TDD", "alpha", "research")
        session.send_and_wait_for_output("tDd")
        session.send(" ")
        session.wait_for("已选", "2")
        session.send("\r")
        session.wait_for("新增链接: TDD", "新增链接: research", "执行以上变更？")
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_linked("TDD")
        self.assert_linked("research")
        self.assert_not_linked("alpha")

    def test_escape_clears_search_then_cancels_when_search_is_empty(self):
        self.skill("alpha")
        self.skill("beta")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha", "beta")
        session.send("alp")
        session.wait_for("搜索", "alp", "alpha")
        session.send("\x1b")
        session.send("\x1bOB \r")
        session.wait_for("新增链接: beta", "执行以上变更？")
        session.send("n\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_not_linked("alpha")
        self.assert_not_linked("beta")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha", "beta")
        session.send("\x1b")
        code, output = session.wait_exit()
        self.assertEqual(code, 130, output)
        self.assert_not_linked("alpha")
        self.assert_not_linked("beta")

    def test_no_matches_is_safe_and_does_not_toggle_hidden_items(self):
        self.skill("alpha")
        self.skill("beta")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha", "beta")
        session.send("zzz")
        session.wait_for("搜索", "无匹配")
        session.send(" \r")
        session.wait_for("Git 本地排除", "执行以上变更？")
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_not_linked("alpha")
        self.assert_not_linked("beta")

    def test_small_terminal_scrolls_to_reachable_items(self):
        for index in range(10):
            self.skill(f"skill-{index:02d}")
        session = self.open_select(rows=8, cols=40)
        self.wait_for_terminal_chooser(session, "skill-00")
        for _ in range(9):
            session.send_and_wait_for_output("\x1bOB")
        session.send(" ")
        session.wait_for("已选", "1")
        session.send("\r")
        session.wait_for("新增链接: skill-09", "执行以上变更？")
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_linked("skill-09")
        self.assert_not_linked("skill-00")

    def test_unicode_search_backspace_and_preselection_survive_cancelled_preview(self):
        existing = self.skill("alpha")
        self.skill("中文-tdd")
        link = self.project / ".agents/skills/alpha"
        link.parent.mkdir(parents=True)
        link.symlink_to(existing)
        exclude = self.project / ".git/info/exclude"
        before = exclude.read_bytes()
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha", "中文-tdd")
        session.send("中文x")
        session.wait_for("无匹配")
        session.send("\x7f \r")
        session.wait_for("保留链接: alpha", "新增链接: 中文-tdd", "执行以上变更？")
        session.send("n\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_linked("alpha")
        self.assert_not_linked("中文-tdd")
        self.assertEqual(exclude.read_bytes(), before)

    def test_equivalent_unicode_encodings_match_the_same_name(self):
        self.skill("CAFE\u0301")
        session = self.open_select()
        self.wait_for_terminal_chooser(session)
        session.send("café \r")
        session.wait_for("新增链接:", "执行以上变更？")
        session.send("y\r")
        code, output = session.wait_exit()
        self.assertEqual(code, 0, output)
        self.assert_linked("CAFE\u0301")

    def test_unusable_terminal_fails_cleanly_without_writes(self):
        self.skill("alpha")
        session = self.open_select(rows=4, cols=40)
        code, output = session.wait_exit()
        self.assertEqual(code, 1, output)
        self.assertIn("终端太小", output)
        self.assertNotIn("Traceback", output)
        self.assert_not_linked("alpha")
        self.assertEqual(termios.tcgetattr(session.master_fd), session.initial_attrs)

    def test_ctrl_c_exits_without_traceback_and_restores_terminal_modes(self):
        self.skill("alpha")
        session = self.open_select()
        self.wait_for_terminal_chooser(session, "alpha")
        os.kill(session.proc.pid, signal.SIGINT)
        code, output = session.wait_exit()
        self.assertEqual(code, 130, output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(
            termios.tcgetattr(session.master_fd), session.initial_attrs, output
        )
        self.assert_not_linked("alpha")


if __name__ == "__main__":
    unittest.main()
