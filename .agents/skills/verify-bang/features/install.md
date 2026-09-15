# 输出 skill 安装指南

用户运行命令后，将输出的指南交给 agent。agent 展示可安装的 skill，由用户选择并确认。bang 本身只输出本地指南和当前配置的路径，不下载、不安装，也不修改配置。

## Sub-features

- `install-default`：默认 source/library 与内置指南。
- `install-configured`：指南中的路径与用户保存的自定义配置一致。
- `install-readonly`：输出前后 HOME、项目及 Git refs 不变。
- `install-arguments`：不接受目录参数，返回 argparse 错误。

## How to get to it (user POV)

在 agent 会话或普通终端运行 `bang skill install`；普通终端需要手动把输出交给 agent。更换目录先运行 `bang init`，不能给 install 传路径。

## Driving it with CLI pipes

Preconditions: 按 Launch 准备新的独立 bash 环境，不创建配置文件。输出文件保存在 EVIDENCE 中，不写入临时 HOME 或项目目录。

- **默认指南和只读性。** 运行以下命令，预期退出码为 0。输出应说明尚未安装任何 skill，并列出默认路径；运行前后的文件清单、文件内容和 Git refs 应一致。

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

- **自定义路径。** 先按 config 文档保存 library/source，再运行上面的命令。将路径断言改为已保存的路径，并在配置保存后再获取运行前快照。输出的 `personal_resources` 必须是当前源码的 `bang_skills/personal` 可读路径。
- **非法参数。** 执行 `python3 -B "$REPO/bang.py" skill install --source '~/incoming'`；预期退出 2 且显示 `unrecognized arguments`，无文件变化。

## Gotchas

- 输出指南不是完成安装；本验证不授权执行指南里的网络、登录、依赖安装或全局写入。
- 文件和 Git refs 没变，不代表没有网络请求。本步骤只验证本地状态未变；“不访问网络”的代码依据是命令只读取本地资源。未做独立网络审计时，应明确说明。
- 安装后的归集、项目选择是单独入口，不自动执行。
