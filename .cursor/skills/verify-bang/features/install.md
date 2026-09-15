# 输出 skill 安装指南

用户在 agent 会话调用命令，把指南交给模型选择并确认安装；bang 本身只输出本地指南和路径上下文，不下载、不安装、不修改配置。

## Sub-features

- `install-default`：默认 source/library 与内置指南。
- `install-configured`：已保存的自定义路径进入上下文。
- `install-readonly`：输出前后 HOME、项目及 Git refs 不变。
- `install-arguments`：不接受目录参数，返回 argparse 错误。

## How to get to it (user POV)

在 agent 会话或普通终端运行 `bang skill install`；普通终端需要手动把输出交给 agent。更换目录先运行 `bang init`，不能给 install 传路径。

## Driving it with CLI pipes

Preconditions: Launch 的全新隔离 bash，未配置，输出文件在 EVIDENCE 而非 HOME/项目。

- **默认指南和只读性。** 运行以下命令，退出 0、指南包含只输出声明及默认路径；磁盘清单和 Git refs 无变化。

```bash
python3 -B - <<'PY'
import hashlib, os, subprocess
from pathlib import Path
h, project = Path(os.environ['HOME']), Path.cwd()
# 前后快照包含目录、软链接和文件字节；不跟随目录软链接。
before = {str(p): ('link', os.readlink(p)) if p.is_symlink() else
          ('dir', '') if p.is_dir() else ('file', hashlib.sha256(p.read_bytes()).hexdigest())
          for base in (h, project) for p in base.rglob('*')}
refs = subprocess.check_output(['git', 'for-each-ref'])
command = ['python3', '-B', os.environ['REPO'] + '/bang.py', 'skill', 'install']
result = subprocess.run(command, capture_output=True, text=True, check=True)
print(command, 'rc=', result.returncode, result.stderr)
print(result.stdout)
Path(os.environ['EVIDENCE'], 'install.txt').write_text(result.stdout)
assert '尚未安装任何 skill' in result.stdout
assert str(h / '.agents/skills') in result.stdout
assert str(h / 'my-skills') in result.stdout
assert 'lark' in result.stdout and 'mattpocock' in result.stdout
after = {str(p): ('link', os.readlink(p)) if p.is_symlink() else
         ('dir', '') if p.is_dir() else ('file', hashlib.sha256(p.read_bytes()).hexdigest())
         for base in (h, project) for p in base.rglob('*')}
assert before == after
assert refs == subprocess.check_output(['git', 'for-each-ref'])
print('install-default install-readonly rc=0')
PY
```

- **自定义路径。** 先用 config 配方保存 library/source，再运行相同命令；路径断言改成保存的路径，快照从保存配置后开始。输出的 `personal_resources` 必须是当前源码的 `bang_skills/personal` 可读路径。
- **非法参数。** 执行 `python3 -B "$REPO/bang.py" skill install --source '~/incoming'`；预期退出 2 且显示 `unrecognized arguments`，无文件变化。

## Gotchas

- 输出指南不是完成安装；本验证不授权执行指南里的网络、登录、依赖安装或全局写入。
- 文件/ref 快照不能独自证明没有网络请求；这里只证明可观察本地无写入，网络声明依据本地资源输出实现，独立审计未运行时须明确说明。
- 安装后的归集、项目选择是单独入口，不自动执行。
