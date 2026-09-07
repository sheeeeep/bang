#!/usr/bin/env python3
"""Personal skill selection and collection, using only the standard library."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

BEGIN = b"# BEGIN skillctl managed links\n"
END = b"# END skillctl managed links\n"


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "需要非 bare Git 项目")
    return result.stdout.rstrip("\n")


def signature(path: Path) -> tuple[int, int, int, int, int] | None:
    try:
        stat = path.lstat()
        return (
            stat.st_dev,
            stat.st_ino,
            stat.st_mode,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
        )
    except FileNotFoundError:
        return None


def real_directory(path: Path) -> None:
    """Reject redirected ancestors before writing anywhere beneath a managed root."""
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and not part.is_dir()):
            raise ValueError(f"不是安全的真实目录: {part}")


def skills(base: Path) -> dict[str, Path]:
    real_directory(base)
    found = {}
    if base.exists():
        for path in sorted(base.iterdir()):
            if path.name == ".backups" or path.name.startswith(".skillctl-cleanup-"):
                continue
            if path.is_symlink():
                print(f"跳过来源软链接: {path}")
            elif path.is_dir() and (path / "SKILL.md").is_file():
                if any(ord(c) < 32 or ord(c) == 127 for c in path.name):
                    print(f"跳过不可显示的名称: {path.name!r}")
                else:
                    found[path.name] = path
    return found


def confirm(message: str) -> bool:
    return input(f"{message} [y/N] ").strip().lower() == "y"


def choose(names: list[str], selected: set[str]) -> set[str]:
    selected = set(selected)
    while True:
        for index, name in enumerate(names, 1):
            print(f"{index:>3}. [{'x' if name in selected else ' '}] {name}")
        answer = input("输入编号切换（空格分隔），回车预览，q 取消: ").strip()
        if answer.lower() == "q":
            raise EOFError
        if not answer:
            return selected
        try:
            indices = {int(value) for value in answer.split()}
            if not indices or min(indices) < 1 or max(indices) > len(names):
                raise ValueError
        except ValueError:
            print("请输入列表中的有效编号。")
            continue
        selected.symmetric_difference_update(names[i - 1] for i in indices)


def managed_link(path: Path, library: Path) -> bool:
    if not path.is_symlink():
        return False
    target = Path(os.path.abspath(path.parent / os.readlink(path)))
    return target == library / path.name


def exclude_bytes(path: Path) -> bytes:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"不能修改 Git 排除文件: {path}")
    return path.read_bytes() if path.exists() else b""


def exclusion_update(content: bytes, add: set[str], remove: set[str]) -> bytes:
    prefix, suffix, owned = content, b"", set()
    if BEGIN in content or END in content:
        if content.count(BEGIN) != 1 or content.count(END) != 1:
            raise ValueError("Git exclude 中的 skillctl 区块损坏，请先修复")
        prefix, rest = content.split(BEGIN)
        block, suffix = rest.split(END)
        owned = set(block.decode("utf-8").splitlines())

    def pattern(name: str) -> str:
        escaped = "".join("\\" + c if c in "\\*?[] " else c for c in name)
        return f"/.agents/skills/{escaped}"

    owned.difference_update(pattern(name) for name in remove)
    # Reassert owned patterns after user rules, including negations.
    owned.update(pattern(name) for name in add)
    block = BEGIN + ("\n".join(sorted(owned)) + "\n").encode() + END if owned else b""
    unmanaged = prefix + suffix
    if block and unmanaged and not unmanaged.endswith(b"\n"):
        unmanaged += b"\n"
    return unmanaged + block


def write_exclude(path: Path, before: bytes, after: bytes) -> None:
    if before == after:
        return
    real_directory(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    # Git's lock-file convention avoids clobbering cooperating concurrent writers.
    with lock.open("xb") as stream:
        try:
            if exclude_bytes(path) != before:
                raise ValueError("Git exclude 在预览后发生变化，请重试")
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
            if path.exists():
                os.chmod(lock, path.stat().st_mode & 0o777)
            os.replace(lock, path)
        finally:
            lock.unlink(missing_ok=True)


def select_skills(library: Path) -> int:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    links = root / ".agents/skills"
    real_directory(links)
    available = skills(library)
    source_states = {name: signature(path) for name, path in available.items()}
    current = (
        {p.name for p in links.iterdir() if managed_link(p, library)}
        if links.exists()
        else set()
    )
    names = sorted(set(available) | current)
    if not names:
        print("个人库没有可选 skill。")
        return 0
    chosen = choose(names, current)
    exclude = Path(
        git(root, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude")
    )
    before = exclude_bytes(exclude)
    states = {name: signature(links / name) for name in names}
    actionable, removals = set(), set()
    conflicts = 0
    for name in names:
        path = links / name
        tracked = git(root, "ls-files", "-z", "--", f":(literal).agents/skills/{name}")
        if tracked or (signature(path) is not None and name not in current):
            print(f"冲突，跳过: {name}（已跟踪或非个人库链接）")
            conflicts += 1
        elif name in chosen:
            if name not in available:
                print(f"冲突，跳过: {name}（个人库源目录无效）")
                conflicts += 1
            else:
                actionable.add(name)
                print(f"{'保留' if name in current else '新增'}链接: {name}")
        elif name in current:
            removals.add(name)
            print(f"移除链接: {name}")
    after = exclusion_update(before, actionable, removals)
    print(f"Git 本地排除: {exclude}（{'更新' if before != after else '不变'}）")
    for line in sorted(actionable):
        print(f"  排除 .agents/skills/{line}")
    if not confirm("执行以上变更？"):
        print("已取消，无修改。")
        return 0
    real_directory(links)
    real_directory(library)
    for name in actionable:
        if (
            signature(library / name) != source_states[name]
            or not (library / name / "SKILL.md").is_file()
        ):
            raise ValueError(f"预览后来源发生变化: {library / name}，请重试")
    if exclude_bytes(exclude) != before:
        raise ValueError("Git exclude 在预览后发生变化，请重试")
    # Recheck the full plan before the first write; never overwrite a late arrival.
    for name in actionable | removals:
        if signature(links / name) != states[name] or git(
            root, "ls-files", "-z", "--", f":(literal).agents/skills/{name}"
        ):
            raise ValueError(f"预览后路径发生变化: {links / name}，请重试")
    if actionable:
        links.mkdir(parents=True, exist_ok=True)
    linked, removed = set(), set()
    for name in sorted(actionable | removals):
        path = links / name
        try:
            if signature(path) != states[name]:
                raise ValueError("路径发生变化，请重试")
            if name in removals:
                path.unlink()
                removed.add(name)
            else:
                if name not in current:
                    path.symlink_to(library / name, target_is_directory=True)
                linked.add(name)
            print(f"成功: {name}")
        except (OSError, ValueError) as error:
            print(f"失败: {name}: {error}")
            conflicts += 1
    write_exclude(exclude, before, exclusion_update(before, linked, removed))
    for name in sorted(linked):
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "check-ignore",
                "-q",
                "--",
                f".agents/skills/{name}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            print(
                f"失败: {name} 未被 Git 排除，请检查更高优先级规则（如 .gitignore）；未自动修改这些规则。"
            )
            conflicts += 1
    return 1 if conflicts else 0


def tree_state(path: Path) -> dict[str, tuple[int, int, int, int, int] | None]:
    """Snapshot metadata without following directory symlinks."""
    # ponytail: metadata checks detect ordinary edits, not adversarial writers;
    # use a shared locking protocol if concurrent editing becomes a requirement.
    state = {".": signature(path)}
    if path.is_dir() and not path.is_symlink():

        def fail(error: OSError) -> None:
            raise error

        for root, dirs, files in os.walk(path, onerror=fail, followlinks=False):
            for name in dirs + files:
                child = Path(root) / name
                state[str(child.relative_to(path))] = signature(child)
    return state


def publish_directory(source: Path, destination: Path) -> None:
    # Reserve exclusively, then replace only our own empty directory atomically.
    destination.mkdir()
    reserved = signature(destination)
    try:
        if signature(destination) != reserved:
            raise ValueError(f"目标发生变化: {destination}")
        os.replace(source, destination)
    except BaseException:
        if signature(destination) == reserved:
            destination.rmdir()
        raise


def restore_old(work: Path | None, destination: Path) -> None:
    if (
        work is None
        or not (work / "old").exists()
        or signature(destination) is not None
    ):
        return
    try:
        real_directory(destination.parent)
        publish_directory(work / "old", destination)
        print(f"已恢复旧版: {destination}")
    except (OSError, ValueError) as error:
        print(f"恢复失败，旧版仍在 {work / 'old'}: {error}")


def collect_one(
    path: Path,
    destination: Path,
    source_state: dict[str, tuple[int, int, int, int, int] | None],
    target_state: dict[str, tuple[int, int, int, int, int] | None],
) -> int:
    backup_root = destination.parent / ".backups"
    work = None
    cleanup = None
    try:
        real_directory(path.parent)
        real_directory(backup_root)
        if tree_state(path) != source_state or tree_state(destination) != target_state:
            raise ValueError("来源或目标在预览后发生变化，请重试")
        backup_root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="skill-", dir=backup_root))
        shutil.copytree(path, work / "incoming", symlinks=True)
        real_directory(path.parent)
        real_directory(backup_root)
        if tree_state(path) != source_state or tree_state(destination) != target_state:
            raise ValueError("复制期间来源或目标发生变化，未替换")
        if target_state["."] is not None:
            publish_directory(destination, work / "old")
            print(f"备份: {work / 'old'}")
        publish_directory(work / "incoming", destination)
        real_directory(path.parent)
        if tree_state(path) != source_state:
            raise ValueError("来源发生变化，已保留来源和新目标，请检查后重试")
        # Hide the consumed source before cleanup: a failed rmtree must never
        # leave a partial skill eligible for another upgrade.
        cleanup = Path(tempfile.mkdtemp(prefix=".skillctl-cleanup-", dir=path.parent))
        publish_directory(path, cleanup / "consumed")
        shutil.rmtree(cleanup)
        if not (work / "old").exists():
            work.rmdir()
        print(f"成功: {path.name} → {destination}")
        return 0
    except (OSError, ValueError, KeyboardInterrupt) as error:
        restore_old(work, destination)
        print(
            f"失败／中断: {path.name}: {error}; 来源: {path}; 目标: {destination}; 恢复目录: {work}; 待清理: {cleanup}"
        )
        return 130 if isinstance(error, KeyboardInterrupt) else 1


def collect_skills(source: Path, library: Path) -> int:
    incoming = skills(source)
    real_directory(library / ".backups")
    if not incoming:
        print("全局入口没有待归集的 skill。")
        return 0
    sources = {name: tree_state(path) for name, path in incoming.items()}
    targets = {name: tree_state(library / name) for name in incoming}
    approved = []
    errors = 0
    for name in incoming:
        destination = library / name
        if targets[name]["."] is None:
            print(f"搬入: {name}")
            approved.append(name)
        elif (
            destination.is_symlink()
            or not destination.is_dir()
            or not (destination / "SKILL.md").is_file()
        ):
            print(f"冲突，跳过非真实 skill 目标: {destination}")
            errors += 1
        elif confirm(f"同名: {name}，备份旧版后整份替换？"):
            approved.append(name)
            print(f"备份并替换: {name}")
        else:
            print(f"跳过: {name}（未确认升级）")
    print(f"备份／恢复目录: {library / '.backups'}（每项独立目录，不覆盖旧备份）")
    print("警告：搬走后不保留全局软链接；其他 agent 对旧位置的引用可能失效。")
    if not confirm("执行以上归集？"):
        print("已取消，无修改。")
        return 0
    for name in approved:
        code = collect_one(incoming[name], library / name, sources[name], targets[name])
        if code == 130:
            print("已中断，后续项未执行。")
            return code
        errors += code
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="选择项目 skill 或归集全局 skill")
    parser.add_argument("command", choices=["select", "collect"])
    args = parser.parse_args(argv)
    home = Path.home().resolve()
    try:
        if args.command == "select":
            return select_skills(home / "my-skills")
        return collect_skills(home / ".agents/skills", home / "my-skills")
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        return 130
    except (OSError, ValueError) as error:
        print(f"错误: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
