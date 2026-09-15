---
name: verify-bang
description: 验证 bang 的 Python CLI 和终端选择器。修改目录配置、安装指南、归集、项目选择或 agent 模板后，在临时 HOME 中运行真实命令，保存终端记录并核对文件变化。
---

# 验证 bang

bang 是命令行工具，支持 macOS/Linux，需要 Python 3.9+ 和 Git 2.31+，无需安装运行时依赖，也无需启动服务或登录。

`skill select` 在终端中显示 curses 选择界面，在非 TTY 环境中改用编号输入。两种交互方式以及其他子命令都要分别验证。开始前先读[功能地图](features/README.md)，确定本次要检查哪些入口；一个入口通过，不代表整个功能通过。

## Launch

从仓库根目录使用 README 的源码启动方式，不安装全局 `bang`，不下载依赖：

```sh
export REPO="$(pwd -P)"
python3 -B "$REPO/bang.py" --help
python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" doctor
```

`--help` 退出码为 0，且输出包含 `{init,skill}`，说明源码命令可以运行。验证终端界面时，脚本会创建独立的 24×80 PTY；出现 `搜索`、`已选` 和 `alpha` 后才发送按键。不需要保留常驻进程。

一键端到端验收（内部创建临时 HOME、真实 Git 项目及 `alpha/SKILL.md`）：

```sh
export EVIDENCE="$(mktemp -d /tmp/bang-evidence.XXXXXX)"
python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" doctor > "$EVIDENCE/doctor.json"
python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" prove --evidence "$EVIDENCE/select" > "$EVIDENCE/run.log" 2>&1
cat "$EVIDENCE/run.log"
test -s "$EVIDENCE/select/report.json"
```

`prove` 要求证据目录尚不存在。不要使用 `python -O`，否则会跳过验证断言。

退出码为 0 表示：预览时未写入文件，确认后创建了链接，Git 排除规则生效，取消选择后只移除了链接，最后清理了临时数据和进程。失败时先看 `run.log` 和 `report.json`，保留证据。

验证其他功能时，先打开**独立的 bash 子 shell**，按下面的命令准备环境，再执行对应功能文档中的命令。不要修改当前 agent 进程的 HOME：

```bash
# 先从仓库根目录 export REPO 和 EVIDENCE（沿用上方）。
bash
set -euo pipefail
SCRATCH=$(mktemp -d /tmp/bang-drive.XXXXXX)
trap 'rm -rf -- "$SCRATCH"' EXIT
for key in $(compgen -e GIT_); do unset "$key"; done
export HOME="$SCRATCH/home" GIT_CONFIG_NOSYSTEM=1
export TERM=xterm-256color LC_ALL=C.UTF-8 LANG=C.UTF-8 PYTHONIOENCODING=utf-8
mkdir -p "$HOME" "$SCRATCH/project"
git init -q "$SCRATCH/project"
cd "$SCRATCH/project"
# 配方的输出和 set -x 动作轨迹写入证据，而不是 SCRATCH。
exec > >(tee "$EVIDENCE/drive.log") 2>&1
set -x
python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" doctor
# 在此执行 features 中选定的配方；完成后 exit 退出本子 shell。
```

这些临时目录只用于验证，bang 日常运行不要求创建它们。每次验证都使用独立的 HOME、Git 项目和证据目录，彼此独立后才可并行。不要操作用户真实的 `~/my-skills` 或 `~/.agents/skills`，也不要让两个 agent 同时修改同一个项目。这里没有需要 mock 的外部服务。

## Doctor

只读命令：`python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" doctor`。
该命令检查模板、指南和 PTY 驱动文件是否齐全，并输出源码绝对路径、Git HEAD、`bang.py` 的 SHA-256、Python/Git 版本和实际帮助信息。核对 `root`，确认运行的是当前仓库的代码。

检查不会创建配置、打开交互界面或访问网络。bang 没有常驻服务，因此无需检查端口归属或登录状态。doctor 通过只说明运行前提满足；终端界面是否可用，还要看 PTY 是否出现预期提示。遇到异常先重跑 doctor，不要反复发送按键。

## Drive

脚本复用 `test_terminal.PtySession`，通过真实命令和按键操作 bang，不直接修改内部状态，也不 mock curses。

`prove` 按以下顺序验证：

1. 启动 `python3 -B bang.py skill select`，等待选择界面出现。
2. 发送空格和 Enter，等待 `新增链接: alpha` 和 `执行以上变更？`。
3. 检查链接和 Git 排除文件尚未变化，再发送 `y` 和 Enter 确认。
4. 在第二个 PTY 中重新打开选择器，取消勾选，等待 `移除链接: alpha`，确认后检查链接已移除。

其他终端路径直接复用现有验收：

```sh
(cd "$REPO" && python3 -B -m unittest -v test_terminal) > "$EVIDENCE/terminal-tests.log" 2>&1
```

这组测试检查按键、搜索、滚动、取消和终端恢复。若要提交某个入口的验证证据，还需保留操作记录和文件变化，不能只附 unittest 汇总。具体操作和预期结果见功能地图。

## Evidence

- 将证据保存在本次创建的 `/tmp/bang-evidence.XXXXXX` 中，不要放进待清理的应用数据目录。交付时写出绝对路径；需要长期保留时，将整个目录复制到用户指定的持久存储。
- `doctor.json` 记录检出身份；`run.log` 保存异常栈和脚本输出；`select/terminal-0.txt`、`terminal-1.txt` 是含 ANSI 控制序列的原始终端记录；`select/report.json` 记录入口、命令、HOME/cwd、按键、退出码、链接目标、exclude 内容和清理结果。
- 同时记录操作和结果。命令执行后，还要检查链接是否指向个人库、原 skill 是否保留、Git 排除规则是否生效，以及 `.gitignore` 是否未改。不能只凭“成功”提示判定通过。
- 验证其他功能时，用 `set -x` 将命令、输入、输出和断言写入 `drive.log`，并将配置、模板或备份清单复制到 EVIDENCE。注明功能 ID 和入口；失败时记录退出码及原因，未执行的检查标为“未验证”。
- `skill install` 只输出指南，不执行安装，也不是安装的 dry-run。比较运行前后临时 HOME、项目文件和 Git refs，确认本地状态未变；不要执行指南中的下载、登录或安装步骤。文件未变不能证明没有网络请求：代码层面的判断须检查 `install_guide` 是否只读取本地资源；需要独立证据时，另做系统网络审计。

## Cleanup

`prove` 在成功/异常时关闭自己创建的 PTY 子进程（先 terminate、超时后 kill 并 wait），再删除本次 TemporaryDirectory。`report.json` 中 `scratch_removed` 和 `children_stopped` 必须均为 true。不按进程名杀进程，不触碰其他 agent。

手动验证结束后执行 `exit`，由 EXIT trap 删除本次 SCRATCH。即使验证失败，也应退出该子 shell；重试时重新准备临时环境，不沿用失败后留下的数据。

进程收到 SIGKILL 或机器断电时，finally/trap 无法执行。恢复后先根据 HOME/cwd 记录核对残留目录和进程，确认属于本次验证，再逐项清理。不要使用按名称批量杀进程或删除目录的命令。

清理后执行 `test -s "$EVIDENCE/select/report.json" && test -s "$EVIDENCE/select/terminal-0.txt"` 确认证据仍在；不要删除 EVIDENCE。

## Helpers

唯一随附脚本是可执行的 `scripts/verify.py`：

- `python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" doctor`：只读诊断。
- `python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" prove --evidence "$EVIDENCE/select"`：验证选择和移除，并自动清理临时环境。

依赖仓库已有 `test_terminal.py`，只支持其 macOS/Linux PTY 环境。功能变化后使用 `/maintain-verification-skill` 更新地图和驱动。
