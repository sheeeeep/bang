"""CLI acceptance tests: isolated HOME, real files and real Git repositories."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bang

CLI = Path(__file__).with_name("bang.py")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.library = self.home / "my-skills"
        self.source = self.home / ".agents/skills"
        self.project = self.home / "project"
        self.project.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "GIT_CONFIG_NOSYSTEM": "1"}
        for key in list(self.env):
            if key.startswith("GIT_") and key != "GIT_CONFIG_NOSYSTEM":
                self.env.pop(key)
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.project), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        ).stdout

    def skill(self, base, name, content="new"):
        path = base / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(content)
        return path

    def cli(self, command, answers, cwd=None):
        return subprocess.run(
            [sys.executable, str(CLI), "skill", command],
            cwd=cwd or self.project,
            env=self.env,
            input=answers,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_main(self, command, answer):
        output = io.StringIO()
        with (
            patch.dict(os.environ, self.env, clear=True),
            patch(
                "pathlib.Path.cwd",
                return_value=self.project,
            ),
            patch("builtins.input", side_effect=answer),
            contextlib.redirect_stdout(output),
        ):
            code = bang.main(["skill", command])
        return code, output.getvalue()

    def init_cli(self, answers, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "init", *args],
            cwd=self.project,
            env=self.env,
            input=answers,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_defaults_cancel_and_eof_do_not_touch_skills(self):
        config = self.home / ".config/bang/config.json"
        for answers, expected in (("\n\nn\n", 0), ("", 130)):
            result = self.init_cli(answers)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertFalse(config.parent.exists())
        result = self.init_cli("\n\ny\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = config.read_bytes()
        self.assertEqual(
            json.loads(before),
            {
                "library": "~/my-skills",
                "source": "~/.agents/skills",
            },
        )
        self.assertFalse(self.library.exists())
        self.assertFalse(self.source.exists())
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.init_cli("\n\ny\n").returncode, 0)
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(self.init_cli("~/changed\n\nn\n").returncode, 0)
        self.assertEqual(config.read_bytes(), before)

    def test_configured_paths_drive_both_skill_commands(self):
        library = self.home / "custom library"
        source = self.home / "incoming"
        self.skill(source, "alpha")
        result = self.init_cli(
            "y\n", "--library", "~/custom library", "--source", str(source)
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli("collect", "y\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((library / "alpha/SKILL.md").is_file())
        self.assertFalse((source / "alpha").exists())
        result = self.cli("select", "1\n\ny\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            (self.project / ".agents/skills/alpha").resolve(), library / "alpha"
        )
        self.assertFalse(self.library.exists())

    def test_invalid_config_and_overlapping_roots_fail_without_writes(self):
        config = self.home / ".config/bang/config.json"
        config.parent.mkdir(parents=True)
        for content in (
            "{broken",
            "[]",
            '{"library": 42, "source": "~/in"}',
            '{"library": "relative", "source": "~/in"}',
            '{"library": "~/same", "source": "~/same"}',
            '{"library": "~/a", "source": "~/a/child"}',
            '{"library": "~/a/child", "source": "~/a"}',
            '{"library": "~/a", "source": "~/b", "typo": true}',
            json.dumps({"library": "~/a", "source": "~/b\u0000"}),
        ):
            with self.subTest(content=content):
                config.write_text(content)
                result = self.cli("collect", "y\n")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(config.read_text(), content)
                self.assertFalse(self.library.exists())
        config.unlink()
        outside = self.home / "outside.json"
        outside.write_text("{}")
        config.symlink_to(outside)
        result = self.init_cli("\n\ny\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(outside.read_text(), "{}")

    def test_init_rejects_redirected_paths_and_preserves_existing_config_on_failure(
        self,
    ):
        self.assertEqual(self.init_cli("\n\ny\n").returncode, 0)
        config = self.home / ".config/bang/config.json"
        before = config.read_bytes()
        self.library.mkdir()
        redirected = self.home / "redirected"
        redirected.symlink_to(self.library)
        result = self.init_cli("y\n", "--library", str(redirected), "--source", "~/in")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(config.read_bytes(), before)
        with (
            patch.dict(os.environ, self.env, clear=True),
            patch("builtins.input", return_value="y"),
            patch("os.replace", side_effect=OSError("disk failure")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = bang.main(["init", "--library", "~/new", "--source", "~/in"])
        self.assertEqual(code, 1)
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(list(config.parent.iterdir()), [config])

    def test_command_hierarchy_requires_skill_group(self):
        for args in (
            ["--help"],
            ["skill", "--help"],
            ["init", "--help"],
            ["select"],
            ["skill"],
        ):
            result = subprocess.run(
                [sys.executable, str(CLI), *args],
                env=self.env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0 if "--help" in args else 2)
            self.assertIn("bang", result.stdout + result.stderr)

    def test_project_selection_syncs_links_and_local_git_exclusions(self):
        a = self.skill(self.library, "alpha")
        b = self.skill(self.library, "beta")
        ignore = self.project / ".gitignore"
        ignore.write_text("keep-me\n")
        nested = self.project / "src"
        nested.mkdir()
        result = self.cli("select", "1 2\n\ny\n", cwd=nested)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        links = self.project / ".agents/skills"
        self.assertEqual((links / "alpha").resolve(), a)
        self.assertEqual((links / "beta").resolve(), b)
        self.assertEqual(
            self.git(
                "check-ignore", ".agents/skills/alpha", ".agents/skills/beta"
            ).splitlines(),
            [".agents/skills/alpha", ".agents/skills/beta"],
        )
        exclude = self.project / ".git/info/exclude"
        before = exclude.read_bytes()
        again = self.cli("select", "\ny\n")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("[x] alpha", again.stdout)
        self.assertEqual(exclude.read_bytes(), before)
        removed = self.cli("select", "1\n\ny\n")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertFalse((links / "alpha").is_symlink())
        self.assertTrue(a.is_dir())
        self.assertTrue((links / "beta").is_symlink())
        self.assertEqual(ignore.read_text(), "keep-me\n")

    def test_non_git_selection_continues_without_exclusions(self):
        project = self.home / "plain"
        project.mkdir()
        source = self.skill(self.library, "alpha")
        link = project / ".agents/skills/alpha"
        cancelled = self.cli("select", "1\n\nn\n", cwd=project)
        self.assertEqual(cancelled.returncode, 0, cancelled.stdout + cancelled.stderr)
        self.assertFalse((project / ".agents").exists())
        for answers, selected in (
            ("1\n\ny\n", True),
            ("\ny\n", True),
            ("1\n\ny\n", False),
        ):
            result = self.cli("select", answers, cwd=project)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("不是 Git 工程，跳过 Git exclude", result.stdout)
            self.assertNotIn("Git 本地排除:", result.stdout)
            self.assertEqual(link.is_symlink(), selected)
            if selected:
                self.assertEqual(link.resolve(), source)
            self.assertTrue(source.is_dir())
            self.assertFalse((project / ".git").exists())
        owned = self.skill(project / ".agents/skills", "alpha", "project-owned")
        conflict = self.cli("select", "1\n\ny\n", cwd=project)
        self.assertEqual(conflict.returncode, 1, conflict.stdout + conflict.stderr)
        self.assertIn("冲突", conflict.stdout)
        self.assertEqual((owned / "SKILL.md").read_text(), "project-owned")

    def test_invalid_git_metadata_still_fails(self):
        (self.project / ".git").rename(self.project / "git-backup")
        (self.project / ".git").write_text("invalid gitfile\n")
        self.skill(self.library, "alpha")
        result = self.cli("select", "1\n\ny\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("跳过 Git exclude", result.stdout)
        self.assertFalse((self.project / ".agents").exists())

    def test_cancel_and_conflicts_never_modify_unowned_or_tracked_paths(self):
        for name in ("directory", "external", "tracked", "valid"):
            self.skill(self.library, name)
        links = self.project / ".agents/skills"
        owned = self.skill(links, "directory", "project-owned")
        outside = self.skill(self.home, "outside")
        (links / "external").symlink_to(outside)
        (links / "tracked").symlink_to(self.library / "tracked")
        self.git("add", ".agents/skills/tracked")
        index = self.git("ls-files", "--stage")
        exclude = self.project / ".git/info/exclude"
        before = exclude.read_bytes()
        cancelled = self.cli("select", "1 2 4\n\nn\n")
        self.assertEqual(cancelled.returncode, 0, cancelled.stdout)
        self.assertEqual(exclude.read_bytes(), before)
        self.assertFalse((links / "valid").exists())
        applied = self.cli("select", "1 2 4\n\ny\n")
        self.assertEqual(applied.returncode, 1, applied.stdout)
        self.assertIn("冲突", applied.stdout)
        self.assertEqual((owned / "SKILL.md").read_text(), "project-owned")
        self.assertEqual((links / "external").resolve(), outside)
        self.assertEqual(self.git("ls-files", "--stage"), index)
        self.assertTrue((links / "valid").is_symlink())
        self.assertNotIn(b"/tracked\n", exclude.read_bytes())

    def test_global_collection_moves_new_skills_and_skips_symlinks(self):
        source = self.skill(self.source, "alpha")
        (source / "asset.txt").write_text("asset")
        external = self.skill(self.home, "external")
        (self.source / "linked").symlink_to(external)
        cancelled = self.cli("collect", "n\n")
        self.assertEqual(cancelled.returncode, 0, cancelled.stdout)
        self.assertFalse(self.library.exists())
        self.assertTrue(source.is_dir())
        result = self.cli("collect", "y\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(source.exists())
        self.assertFalse(source.is_symlink())
        self.assertEqual((self.library / "alpha/asset.txt").read_text(), "asset")
        self.assertTrue((self.source / "linked").is_symlink())
        self.assertEqual((external / "SKILL.md").read_text(), "new")
        self.assertIn("跳过来源软链接", result.stdout)
        self.assertIn("失效", result.stdout)

    def test_upgrade_defaults_to_backup_with_one_overall_confirmation(self):
        old = self.skill(self.library, "alpha", "old")
        (old / "obsolete.txt").write_text("remove on upgrade")
        source = self.skill(self.source, "alpha", "new")
        link = self.project / ".agents/skills/alpha"
        link.parent.mkdir(parents=True)
        link.symlink_to(old)
        cancelled = self.cli("collect", "n\n")
        self.assertEqual(cancelled.returncode, 0, cancelled.stdout)
        self.assertFalse((self.library / ".backups").exists())
        self.assertEqual((old / "SKILL.md").read_text(), "old")
        self.assertTrue(source.exists())
        result = self.cli("collect", "y\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("[y/N]"), 1)
        self.assertIn("备份并替换: alpha", result.stdout)
        self.assertEqual((link / "SKILL.md").read_text(), "new")
        self.assertFalse((old / "obsolete.txt").exists())
        self.assertFalse(source.exists())
        backups = list((self.library / ".backups").glob("*/old/SKILL.md"))
        self.assertEqual([p.read_text() for p in backups], ["old"])
        self.skill(self.source, "alpha", "newer")
        again = self.cli("collect", "y\n")
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertEqual((link / "SKILL.md").read_text(), "newer")
        self.assertEqual(
            sorted(
                p.read_text()
                for p in (self.library / ".backups").glob("*/old/SKILL.md")
            ),
            ["new", "old"],
        )
        selection = self.cli("select", "q\n")
        self.assertNotIn(".backups", selection.stdout)

    def test_selection_rejects_source_changed_after_preview(self):
        source = self.skill(self.library, "alpha")
        exclude = self.project / ".git/info/exclude"
        before = exclude.read_bytes()
        answers = iter(["1", "", "y"])

        def answer(prompt):
            if "执行" in prompt:
                source.rename(self.library / "moved")
                source.symlink_to(self.home / "unrelated")
            return next(answers)

        code, output = self.run_main("select", answer)
        self.assertEqual(code, 1, output)
        self.assertFalse((self.project / ".agents").exists())
        self.assertEqual(exclude.read_bytes(), before)

    def test_copy_failure_preserves_old_version_and_source_for_retry(self):
        old = self.skill(self.library, "alpha", "old")
        source = self.skill(self.source, "alpha", "new")
        with patch("shutil.copyfile", side_effect=OSError("disk full")):
            code, output = self.run_main("collect", ["y"])
        self.assertEqual(code, 1, output)
        self.assertIn("恢复目录", output)
        self.assertEqual((old / "SKILL.md").read_text(), "old")
        self.assertEqual((source / "SKILL.md").read_text(), "new")
        retried = self.cli("collect", "y\n")
        self.assertEqual(retried.returncode, 0, retried.stdout)
        self.assertEqual((old / "SKILL.md").read_text(), "new")

    def test_cleanup_failure_cannot_reimport_a_partial_source(self):
        self.skill(self.source, "alpha", "new")
        with patch("shutil.rmtree", side_effect=OSError("cleanup denied")):
            code, output = self.run_main("collect", ["y"])
        self.assertEqual(code, 1, output)
        self.assertIn("待清理", output)
        self.assertFalse((self.source / "alpha").exists())
        self.assertEqual((self.library / "alpha/SKILL.md").read_text(), "new")
        retried = self.cli("collect", "")
        self.assertEqual(retried.returncode, 0, retried.stdout)
        self.assertIn("没有待归集", retried.stdout)

    def test_late_collection_target_is_not_overwritten(self):
        source = self.skill(self.source, "alpha", "incoming")

        def answer(prompt):
            self.skill(self.library, "alpha", "late arrival")
            return "y"

        code, output = self.run_main("collect", answer)
        self.assertEqual(code, 1, output)
        self.assertEqual((source / "SKILL.md").read_text(), "incoming")
        self.assertEqual((self.library / "alpha/SKILL.md").read_text(), "late arrival")

    def test_non_git_eof_cancels_and_redirected_project_is_rejected(self):
        self.skill(self.library, "alpha")
        outside = self.home / "outside"
        outside.mkdir()
        non_git = self.cli("select", "", cwd=outside)
        self.assertEqual(non_git.returncode, 130, non_git.stdout)
        self.assertFalse((outside / ".agents").exists())
        (self.project / ".agents").symlink_to(outside)
        redirected = self.cli("select", "1\n\ny\n")
        self.assertEqual(redirected.returncode, 1, redirected.stdout)
        self.assertEqual(list(outside.iterdir()), [])

    def test_git_worktree_and_literal_skill_names(self):
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--allow-empty",
            "-qm",
            "init",
        )
        worktree = self.home / "worktree"
        self.git("worktree", "add", "-qb", "test-worktree", str(worktree))
        name = "a[1]*? space"
        self.skill(self.library, name)
        result = self.cli("select", "1\n\ny\n", cwd=worktree)
        self.assertEqual(result.returncode, 0, result.stdout)
        checked = subprocess.run(
            [
                "git",
                "-C",
                str(worktree),
                "check-ignore",
                "--",
                f".agents/skills/{name}",
            ],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertTrue((worktree / ".agents/skills" / name).is_symlink())
        self.assertTrue((worktree / ".git").is_file())

    def test_publish_failure_restores_old_version_without_losing_incoming(self):
        old = self.skill(self.library, "alpha", "old")
        source = self.skill(self.source, "alpha", "new")
        replace = os.replace

        def fail_publish(src, dst):
            if Path(src).name == "incoming":
                raise OSError("publish denied")
            return replace(src, dst)

        with patch("os.replace", side_effect=fail_publish):
            code, output = self.run_main("collect", ["y"])
        self.assertEqual(code, 1, output)
        self.assertIn("已恢复旧版", output)
        self.assertEqual((old / "SKILL.md").read_text(), "old")
        self.assertEqual((source / "SKILL.md").read_text(), "new")

    def test_failed_link_changes_leave_exclusions_matching_actual_links(self):
        self.skill(self.library, "alpha")
        exclude = self.project / ".git/info/exclude"
        before = exclude.read_bytes()
        with patch("os.symlink", side_effect=OSError("link denied")):
            code, output = self.run_main("select", ["1", "", "y"])
        self.assertEqual(code, 1, output)
        self.assertEqual(exclude.read_bytes(), before)
        created = self.cli("select", "1\n\ny\n")
        self.assertEqual(created.returncode, 0, created.stdout)
        before = exclude.read_bytes()
        with patch("pathlib.Path.unlink", side_effect=OSError("unlink denied")):
            code, output = self.run_main("select", ["1", "", "y"])
        self.assertEqual(code, 1, output)
        self.assertEqual(exclude.read_bytes(), before)
        self.assertTrue((self.project / ".agents/skills/alpha").is_symlink())

    def test_interrupt_during_collection_reports_recovery_locations(self):
        self.skill(self.source, "alpha")
        with patch("shutil.rmtree", side_effect=KeyboardInterrupt):
            code, output = self.run_main("collect", ["y"])
        self.assertEqual(code, 130, output)
        self.assertIn("alpha", output)
        self.assertIn(".skillctl-cleanup-", output)
        self.assertIn("恢复目录", output)
        self.assertEqual((self.library / "alpha/SKILL.md").read_text(), "new")

    def test_user_exclude_rules_are_preserved_without_overriding_managed_rules(self):
        self.skill(self.library, "alpha")
        self.assertEqual(self.cli("select", "1\n\ny\n").returncode, 0)
        exclude = self.project / ".git/info/exclude"
        with exclude.open("a") as stream:
            stream.write("# user rule\n!/.agents/skills/alpha\n")
        result = self.cli("select", "\ny\n")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(b"# user rule\n!/.agents/skills/alpha\n", exclude.read_bytes())
        self.assertEqual(
            self.git("check-ignore", ".agents/skills/alpha"), ".agents/skills/alpha\n"
        )

    def test_higher_priority_gitignore_is_reported_without_modifying_it(self):
        self.skill(self.library, "alpha")
        ignore = self.project / ".gitignore"
        ignore.write_text("!/.agents/skills/alpha\n")
        result = self.cli("select", "1\n\ny\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("未被 Git 排除", result.stdout)
        self.assertEqual(ignore.read_text(), "!/.agents/skills/alpha\n")

    def test_hidden_skill_names_work_but_recovery_directories_stay_hidden(self):
        self.skill(self.source, ".hidden")
        collected = self.cli("collect", "y\n")
        self.assertEqual(collected.returncode, 0, collected.stdout)
        self.assertTrue((self.library / ".hidden/SKILL.md").is_file())
        self.skill(self.library, ".backups/nested", "backup")
        selected = self.cli("select", "1\n\ny\n")
        self.assertEqual(selected.returncode, 0, selected.stdout)
        self.assertTrue((self.project / ".agents/skills/.hidden").is_symlink())
        self.assertNotIn("nested", selected.stdout)


if __name__ == "__main__":
    unittest.main()
