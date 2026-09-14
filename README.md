# bang

个人 AI 环境初始化工具，目前提供 skill 选择与归集。Python 3.9+ 标准库实现，无运行时依赖；需要 Git 2.31+，支持 macOS / Linux。

## 在其它设备安装

### 1. 安装基础 CLI

macOS（已安装 Homebrew）：

```sh
brew install git gh uv python
```

Ubuntu / Debian（发行版提供的 Git 需 >= 2.31）：

```sh
sudo apt update
sudo apt install -y git gh python3 python3-venv curl
# uv 官方安装脚本；也可以先下载审阅再执行
curl -LsSf https://astral.sh/uv/install.sh | sh
. "$HOME/.local/bin/env"
```

### 2. 登录、下载、安装 bang

仓库是私有的，每台设备都需要自己的 GitHub 授权。浏览器登录不等于 CLI 登录：

```sh
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
mkdir -p ~/agent-workspace
gh repo clone sheeeeep/bang ~/agent-workspace/bang -- --branch feat-bang
cd ~/agent-workspace/bang
uv tool install .
uv tool update-shell
# 按提示重开终端，或临时执行：
export PATH="$HOME/.local/bin:$PATH"
bang --help
bang init
```

从已认证的本地克隆安装，不从 PyPI 安装同名包。合并到主分支后可省略 `-- --branch feat-bang`。

可选：为这个仓库设置 GitHub 隐私提交身份（不修改全局 Git 配置）：

```sh
git config --local user.name "$(gh api user --jq .login)"
git config --local user.email "$(gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"')"
```

更新：

```sh
cd ~/agent-workspace/bang
git pull --ff-only
uv tool install --reinstall .
```

不使用 uv 也可以直接运行 `python3 ~/agent-workspace/bang/bang.py --help`。
旧的 `skill` 链接不再使用；确认它指向旧工程后可自行移除。

## 设备配置与使用

```sh
bang init                    # 输入目录、预览，确认后保存
bang init --library '~/my-skills' --source '~/.agents/skills'
bang skill select            # 在项目根目录或子目录选择 skill
bang skill collect           # 在任意目录归集全局入口
```

配置保存在 `~/.config/bang/config.json`，默认：

```json
{
  "library": "~/my-skills",
  "source": "~/.agents/skills"
}
```

- 未运行 init 时使用上述默认值，兼容已有个人库。重复 init 会显示当前值，回车保留；最后仍需确认。
- 支持绝对路径和 `~/`；后者在运行时按当前设备 HOME 展开。拒绝相对路径、软链接管理目录、相互包含的来源与个人库，以及无效配置；错误时不悄悄退回默认值。
- init 只原子保存配置，不移动、下载、同步或创建 skill 库。不保存 GitHub token，不自动安装其他 agent。配置有误时可直接修正 JSON 文件。
- 项目内 `.agents/skills` 是 agent 约定，不做配置项。旧 Git 排除标记与恢复目录名保留 `skillctl`，避免破坏已有数据。
- 更改个人库路径不会迁移已有项目链接。先用旧配置取消项目选择，再修改配置并重新选择，或自行迁移链接。
- **多设备复用的是工具，不是 skill 内容**：每台设备另行复制个人库，或将个人库作为独立私有 Git 仓库同步；不要跨设备复制绝对路径的项目软链接，在各项目重新执行 `bang skill select`。
- 配置位于仓库外，不随提交上传。路径一致时可以复制配置；否则在新设备重新 `bang init`。

### select：同步项目选择

以下路径以默认配置举例，实际使用 init 保存的目录。

- 扫描 `~/my-skills` 的一级真实目录，只列出含 `SKILL.md` 的 skill（支持点号开头的名称）；忽略来源软链接，以及保留的 `.backups`、`.skillctl-cleanup-*` 恢复目录。
- 当 stdin 和 stdout 都是 TTY 时，使用 Python 标准库 `curses` 键盘界面，无新依赖：
  - ↑ / ↓ 移动焦点，不改变勾选；长列表可滚动显示。
  - 空格切换当前项；已隐藏的勾选项会保留，并计入最终预览。
  - 直接输入文字按 skill 名称实时包含搜索，大小写不敏感，并兼容 Unicode 等价编码；Backspace 编辑搜索词。
  - Enter 进入变更预览；预览后仍需单独输入 `y` 确认才会执行。
  - Esc 在搜索词非空时先清空搜索；搜索词为空时取消退出，不修改文件系统或 Git 排除规则。
  - Ctrl-C 取消退出，不修改。
  - 窗口至少需要 5 行、20 列；不足时明确报错并恢复终端状态，不执行变更。
- 当 stdin 或 stdout 不是 TTY（例如管道输入、重定向、自动化脚本）时，保留旧的编号选择界面：`[x]` 为已选项，输入编号切换，可一次输入 `1 3 5`；回车查看预览，再输入 `y` 执行。`q`、Ctrl-C 或输入结束均停止。
- 创建 `.agents/skills/<名称>` → `~/my-skills/<名称>` 的链接；取消已有选项只移除项目链接。
- Git 工程使用当前工作树根目录，不以当前子目录充当项目根目录。非 Git 工程提示后以当前目录继续执行，跳过 Git exclude 及其他 Git 检查；bare 仓库或其他 Git 错误仍报错且不修改。
- 使用 Git 返回的本地 `info/exclude` 路径，支持 `.git` 为文件的 worktree；同仓库多个 worktree 共享该排除文件。
- 仅在带 `skillctl` 标记的区块中维护具体链接规则，不改 `.gitignore` 或 Git 索引。不要手动编辑该区块。规则按实际成功的链接操作更新；若更高优先级的 `.gitignore` 规则阻止排除，会报告失败，由你决定如何处理这些规则。
- 同名真实文件／目录、外部软链接、已跟踪路径均报告并跳过；其他可用项继续执行。失效的个人库链接仍可取消选择并移除。
- 为避免写到意外位置，不接受管理目录或其祖先为软链接的布局（HOME 自身会先规范化）。

### collect：归集全局入口

- 仅从配置的 `source`（默认 `~/.agents/skills`）归集，来源软链接跳过；不扫描其他 agent 的目录，不处理安装器锁文件。
- 同名真实 skill 默认备份旧版并整份替换，不再逐项询问；同名普通文件、无 `SKILL.md` 的目录或软链接不会覆盖。
- 最后统一预览确认，取消时不创建任何目录或备份。
- 先将新内容复制到 `~/my-skills/.backups/skill-<随机标识>/incoming`，成功后才发布；升级旧版保存在该目录的 `old/`，每次独立备份。
- 完整替换而非合并，已有项目链接保持有效。成功归集后全局入口消失，不留全局软链接；其他 agent 对旧位置的引用可能失效，需自行处理。
- 发布后先将来源移到全局入口中的隐藏 `.skillctl-cleanup-*` 目录，再删除；若清理失败，不会把残缺来源再次当成升级输入。

## 失败与恢复

输出逐项标明成功、跳过或失败。退出码：`0` 成功／主动拒绝确认，`1` 冲突或操作失败，`2` 参数错误，`130` 中断／输入结束／`q`。

- 复制失败：原来源和旧版保持完整，恢复目录可能含未完成的 `incoming/`；修复错误后可重试。
- 旧版已备份但发布失败：仅在目标仍空缺时尝试恢复旧版；若有新目标出现，绝不覆盖它，输出旧版备份位置。
- 新版发布后清理失败：目标已完整可用，按输出检查隐藏待清理目录；不要把残缺清理内容重新作为升级输入。
- 备份和失败暂存不自动过期。确认目标有效后可手动删除；恢复旧版时先保全当前版本，再将 `old/` 放回原 skill 路径。
- 操作不是跨目录事务，也不保证断电恢复。运行期间不要并发手动编辑管理目录；命令会检查预览后和复制期间的路径变化，但不是恶意并发文件系统操作的隔离沙箱。

## 开发验证

所有验收测试使用临时 HOME、真实临时 Git 仓库，不操作本机个人库。

```sh
python3 -B -m unittest -v
uvx --from pyright pyright --project pyproject.toml
```

规格：[SPEC.md](SPEC.md)；术语：[CONTEXT.md](CONTEXT.md)。
