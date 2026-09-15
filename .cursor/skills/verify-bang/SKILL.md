---
name: verify-bang
description: 验证 bang Python CLI 和真实 PTY 终端选择器；修改目录配置、skill 安装指南、归集、项目选择或 agent 模板后，用隔离 HOME 驱动用户路径并保存文件与终端证据。
---

# 验证 bang

bang 是 macOS/Linux Python 3.9+ CLI，需要 Git 2.31+，无运行时安装步骤、端口、服务、认证或浏览器。主界面是 `skill select` 的 curses TUI；编号输入和其他子命令也是独立用户入口。先读 [features/README.md](features/README.md)，不要把一个入口的通过当成整张地图通过。

## Launch

从仓库根目录使用 README 的源码启动方式，不安装全局 `bang`，不下载依赖：

```sh
export REPO="$(pwd -P)"
python3 -B "$REPO/bang.py" --help
python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" doctor
```

`--help` 返回 0 且显示 `{init,skill}` 即源码入口可用。每次 TUI 驱动创建独立 24×80 PTY，等待 `搜索`、`已选`、`alpha`；不启动长期服务。

一键端到端验收（内部创建临时 HOME、真实 Git 项目及 `alpha/SKILL.md`）：

```sh
export EVIDENCE="$(mktemp -d /tmp/bang-evidence.XXXXXX)"
python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" doctor > "$EVIDENCE/doctor.json"
python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" prove --evidence "$EVIDENCE/select" > "$EVIDENCE/run.log" 2>&1
cat "$EVIDENCE/run.log"
test -s "$EVIDENCE/select/report.json"
```

`prove` 的目标目录必须不存在；不得使用 `python -O` 禁用断言。退出 0 表示选择、预览无写入、确认后链接、Git 排除、取消选择及清理均通过。失败先查看 `run.log` 和 `report.json`，不要删除证据。

其他地图中的管道命令在**单独 bash 子 shell**内执行以下准备，再粘贴目标配方；勿修改当前 agent 的 HOME：

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
python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" doctor
# 在此执行 features 中选定的配方；完成后 exit 退出本子 shell。
```

临时目录是验证脚手架，不是应用初始化要求。不同运行的 HOME、Git 项目、证据目录全部独立，可以并行；禁止操作真实 `~/my-skills`、`~/.agents/skills` 或两个 agent 共用同一个项目。无外部服务需要 mock。

## Doctor

只读命令：`python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" doctor`。
输出包含绝对源码路径、Git HEAD、`bang.py` SHA-256、Python/Git 版本及真实帮助输出；检查模板、指南和 PTY 驱动存在。它不创建配置，不启动交互、不访问网络。核对 `root` 是否本次检出；无常驻实例，端口所有权和认证不适用。doctor 不证明 TUI 可用，PTY 的提示等待才是交互就绪信号。环境异常先重跑 doctor，不反复盲发按键。

## Drive

复用 `test_terminal.PtySession`，不调用 bang 内部 setter、不 mock curses。脚本 `prove` 启动真实 `python3 -B bang.py skill select`，等待提示，发送空格、Enter，等待 `新增链接: alpha` / `执行以上变更？`，核对尚未写入，再发送 `y`、Enter。第二个 PTY 重走取消选择，核对 `移除链接: alpha`。

其他终端路径直接复用现有验收：

```sh
(cd "$REPO" && python3 -B -m unittest -v test_terminal) > "$EVIDENCE/terminal-tests.log" 2>&1
```

这覆盖按键、搜索、滚动、取消、终端恢复等，但 unittest 汇总不能替代需要动作和副作用记录的单项证据。具体入口及可观察结果见功能地图。

## Evidence

- 证据保存到调用者创建的 `/tmp/bang-evidence.XXXXXX`，与临时应用数据分开；交付必须写出本次绝对路径。需要跨系统重启留存时将整个目录复制到用户指定的持久存储。
- `doctor.json` 记录检出身份；`run.log` 保存异常栈和脚本输出；`select/terminal-0.txt`、`terminal-1.txt` 是含 ANSI 控制序列的原始终端记录；`select/report.json` 记录入口、命令、HOME/cwd、按键、退出码、链接目标、exclude 内容和清理结果。
- 证据须包含动作和结果；真实用户路径通过后另查磁盘：链接目标、原 skill 保留、Git 排除有效且 `.gitignore` 未改。只看到“成功”不能判通过。
- 其他功能在 `drive.log` 保存 `set -x` 命令、输入、输出和断言；额外复制配置、模板、备份清单等结果到 EVIDENCE，注明功能 ID 和入口。失败记录退出码及未满足前提，不把跳过写为通过。
- `skill install` 不是安装或 dry-run：仅输出指南。检查临时 HOME/项目的前后文件与 Git refs；不得执行输出中的下载、登录或安装步骤。网络无调用的结论还须结合 `install_guide` 的本地资源读取实现；如需独立网络证据，用系统网络审计另行记录，不能仅凭名称宣称验证过。

## Cleanup

`prove` 在成功/异常时关闭自己创建的 PTY 子进程（先 terminate、超时后 kill 并 wait），再删除本次 TemporaryDirectory。`report.json` 中 `scratch_removed` 和 `children_stopped` 必须均为 true。不按进程名杀进程，不触碰其他 agent。

手动配方执行 `exit`，EXIT trap 只删除自己的 SCRATCH。失败亦退出该子 shell，重新开全新实例，不复用半成品。SIGKILL/机器掉电无法运行 finally/trap；遇到这种情况先核对记录的 HOME/cwd、进程和路径归属，再处理本次残留，不使用宽泛清理命令。

清理后执行 `test -s "$EVIDENCE/select/report.json" && test -s "$EVIDENCE/select/terminal-0.txt"` 确认证据存活；不要删除 EVIDENCE。

## Helpers

唯一随附脚本是可执行的 `scripts/verify.py`：

- `python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" doctor`：只读诊断。
- `python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" prove --evidence "$EVIDENCE/select"`：完整选择/移除证明并自动清理。

依赖仓库已有 `test_terminal.py`，只支持其 macOS/Linux PTY 环境。功能变化后使用 `/maintain-verification-skill` 更新地图和驱动。
