#!/usr/bin/env python3
"""为 bang 的真实终端选择流程保留可复查证据。
从当前检出加载既有 PTY 驱动，用临时 HOME 和 Git 项目隔离用户数据。
收到 prove 后发送真实按键，核对链接与排除规则；doctor 仅检查运行前提。
失败也保存终端记录，关闭本次子进程并删除临时数据，证据目录独立保留。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from test_terminal import PtySession


def doctor():
    """只读检查源码、依赖和命令入口，返回检出的准确身份。"""
    version = subprocess.check_output(['git', '--version'], text=True).strip()
    if tuple(map(int, version.split()[2].split('.')[:2])) < (2, 31):
        raise RuntimeError('需要 Git 2.31+')
    for relative in ('bang.py', 'test_terminal.py', 'bang_templates/AGENTS.common.md',
                     'bang_templates/AGENTS.js.md', 'bang_skills/install/SKILL.md'):
        assert (ROOT / relative).is_file(), relative
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'bang.py'), '--help'],
                            capture_output=True, text=True, timeout=10, check=True)
    assert '{init,skill}' in result.stdout
    return {'root': str(ROOT), 'python': sys.version, 'git': version,
            'revision': subprocess.check_output(
                ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
            'bang_sha256': hashlib.sha256((ROOT / 'bang.py').read_bytes()).hexdigest(),
            'help': result.stdout}


def prove(evidence):
    """驱动选择和取消选择，保存动作、输出及磁盘副作用并清理。"""
    evidence.mkdir(parents=True, exist_ok=False)
    report = {'feature': 'select-add-remove', 'entry': 'Git root / PTY',
              'doctor': doctor(), 'actions': [], 'passed': False}
    sessions = []
    scratch = None
    try:
        with tempfile.TemporaryDirectory(prefix='bang-verify-') as temporary:
            scratch = Path(temporary).resolve()
            home, project = scratch / 'home', scratch / 'project'
            home.mkdir()
            project.mkdir()
            env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
            env.update(HOME=str(home), GIT_CONFIG_NOSYSTEM='1', TERM='xterm-256color',
                       LC_ALL='C.UTF-8', LANG='C.UTF-8', PYTHONIOENCODING='utf-8')
            subprocess.run(['git', 'init', '-q', str(project)], env=env, check=True)
            skill = home / 'my-skills/alpha'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('# Alpha\n', encoding='utf-8')
            link = project / '.agents/skills/alpha'
            exclude = project / '.git/info/exclude'
            before = exclude.read_bytes()
            added = before
            try:
                for verb in ('新增', '移除'):
                    argv = [sys.executable, '-B', str(ROOT / 'bang.py'), 'skill', 'select']
                    session = PtySession(argv, cwd=project, env=env)
                    sessions.append(session)
                    report['actions'].append({'argv': argv, 'cwd': str(project),
                                              'HOME': str(home), 'operation': verb})
                    session.wait_for('搜索', '已选', 'alpha')
                    session.send(' \r')
                    report['actions'].append({'send': 'SPACE ENTER'})
                    session.wait_for(f'{verb}链接: alpha', '执行以上变更？')
                    assert link.is_symlink() == (verb == '移除'), '预览不应修改链接'
                    assert exclude.read_bytes() == (before if verb == '新增' else added)
                    session.send('y\r')
                    report['actions'].append({'send': 'y ENTER'})
                    code, output = session.wait_exit()
                    report['actions'].append({'exit_code': code})
                    assert code == 0, output
                    assert link.is_symlink() == (verb == '新增')
                    assert (skill / 'SKILL.md').read_text() == '# Alpha\n'
                    if verb == '新增':
                        assert link.resolve() == skill
                        added = exclude.read_bytes()
                        assert b'/.agents/skills/alpha' in added
                        subprocess.run(['git', '-C', str(project), 'check-ignore', '-q',
                                        '.agents/skills/alpha'], env=env, check=True)
                        report['linked_target'] = os.readlink(link)
                        report['exclude_after_add'] = added.decode()
                    else:
                        assert not link.exists() and not link.is_symlink()
                        assert exclude.read_bytes() == before
                    assert not (project / '.gitignore').exists()
                report['passed'] = True
                report['final_state'] = '链接已移除；个人库内容未变；exclude 恢复；未创建 .gitignore'
            finally:
                for index, session in enumerate(sessions):
                    session.close()
                    (evidence / f'terminal-{index}.txt').write_text(session.text(), encoding='utf-8')
    finally:
        report['scratch_removed'] = scratch is not None and not scratch.exists()
        report['children_stopped'] = all(s.proc.poll() is not None for s in sessions)
        (evidence / 'report.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(evidence, flush=True)
    assert report['scratch_removed'] and report['children_stopped']
    assert (evidence / 'terminal-0.txt').is_file()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['doctor', 'prove'])
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if args.action == 'doctor':
        print(json.dumps(doctor(), ensure_ascii=False, indent=2))
    else:
        if args.evidence is None:
            parser.error('prove 需要 --evidence，目录必须尚不存在')
        prove(args.evidence.resolve())
