# bang

AI Code Agent的初始化工具

把常用的 AI skill 集中保存，按项目选择启用，不必到处复制。

- **选择**：在项目里勾选 skill，通过软链接引用个人库；取消选择不删除个人库内容。
- **归集**：把全局入口里的 skill 搬到个人库，后续按项目使用。

支持 macOS / Linux，需要 Python 3.9+ 和 Git 2.31+，没有 Python 运行时依赖。

## 快速开始

### 安装为 `bang` 命令（推荐）

已有 [uv](https://docs.astral.sh/uv/getting-started/installation/) 和 Git 时，一条命令安装：

```sh
uv tool install 'git+https://github.com/sheeeeep/bang.git@master'
```

然后运行 `bang --help`。如果提示找不到命令，执行 `uv tool update-shell` 并按提示重开终端。

仓库已公开，无需 GitHub 登录、SSH 授权或手动克隆。目前尚未发布到 PyPI 或 Homebrew，**不要从 PyPI 安装同名包**。

### 不使用 uv：下载后直接运行

已有 Python 和 Git 即可：

```sh
git clone https://github.com/sheeeeep/bang.git
cd bang
python3 bang.py --help
```

下文以 `bang` 为例；直接运行时将它替换为 `python3 /你的路径/bang/bang.py`。

## 日常使用

### 1. 准备个人 skill 库

默认目录如下，无需先运行初始化命令：

| 目录 | 用途 |
| -------------------- | ------------------ |
| `~/my-skills` | 保存你要复用的 skill |
| `~/.agents/skills` | 待归集的全局入口 |
| 项目内 `.agents/skills` | 存放当前项目选择的 skill 链接 |

每个 skill 是一个包含 `SKILL.md` 的目录，例如：

```text
~/my-skills/
├── review/
│   └── SKILL.md
└── research/
    └── SKILL.md
```

可以直接把已有 skill 放入个人库。若它们已在全局入口中，在任意目录运行：

```sh
bang skill collect
```

命令会先展示变更，输入 `y` 后才执行。

**注意：归集是搬入，不是单纯复制。** 成功后会移除全局入口中的原 skill，依赖旧位置的 agent 可能需要调整。同名 skill 会整份替换个人库旧版，并先备份旧版，不会合并文件。

### 2. 为项目选择 skill

进入你的项目根目录或任意子目录：

```sh
bang skill select
```

- `↑` / `↓` 移动，空格勾选或取消。
- 直接输入名称搜索；搜索不会取消隐藏项的勾选。
- Enter 查看变更，再输入 `y` 执行。
- Esc 清空搜索，再按一次退出；Ctrl-C 也可取消。

再次运行即可调整选择。取消选择只删除项目链接，不删除个人库中的 skill。个人库内容更新后，已有链接直接引用新内容。

Git 项目自动使用当前工作树根目录，并维护本地 Git 排除规则，不修改 `.gitignore`。非 Git 目录会先提示，再以当前目录作为项目目录。同名真实文件、外部链接或已跟踪路径不会被覆盖，会报告并跳过。

### 3. 创建 agent 指引文件

在需要放置文件的目录执行：

```sh
bang init agent
```

先选择模板：`1` / `common`（默认，通用）或 `2` / `js`（JavaScript）。再选择 `1`（默认）创建 `AGENTS.md`，或选择 `2` 创建 `AGENTS.override.md`，最后输入 `y` 确认；`q` 或 Ctrl-C 取消。目标是**执行命令时的当前目录**，不查找 Git 根目录，也不需要 Git 或 skill 配置。

- 模板内置于 `bang_templates/AGENTS.common.md` 和 `bang_templates/AGENTS.js.md`；按选择完整写入，安装后不依赖原机器路径。
- 目标已存在时，先询问是否备份：回车或 `y` 备份，`n` 不备份，`q` 取消。选择后仍须确认写入；不备份会直接覆盖旧内容。新文件不询问备份。
- 选择备份时，旧文件保存为同目录的 `<文件名>.bak-<随机标识>`；历史备份和另一个指引文件不动，不合并内容。
- 拒绝覆盖软链接和非普通文件；取消不修改文件。失败时查看输出的备份路径，保全现有内容后可用备份恢复。
- 不修改 Git 排除规则，备份由你确认无用后手动清理。执行期间请勿同时编辑目标文件。

### 可选：更换目录

```sh
bang init
# 或指定目录，预览后确认保存：
bang init --library '~/my-skills' --source '~/.agents/skills'
```

配置保存在 `~/.config/bang/config.json`。重复运行可修改，回车保留当前值。

- 路径须为绝对路径或 `~/` 开头；个人库与全局入口不能相同或相互包含。
- 管理目录及其祖先不能是软链接（HOME 本身会先规范化）。
- 初始化只保存配置，不创建、下载或迁移 skill 库，也不安装其他 agent。
- 更换个人库位置前，先用旧配置取消项目选择，再迁移个人库、修改配置并重新选择；否则旧项目链接仍指向旧位置。

## 更新

通过 uv 从 GitHub 安装的用户，重新安装最新 `master`：

```sh
uv tool install --reinstall --refresh 'git+https://github.com/sheeeeep/bang.git@master'
```

直接运行源码的用户，在下载的 bang 仓库目录执行 `git pull --ff-only`。如果此前通过 `uv tool install .` 安装，拉取后再执行 `uv tool install --reinstall .`。

## 常见问题

### 新设备需要重新准备什么？

下载 bang，并另行复制个人 skill 库，或用独立私有 Git 仓库同步个人库。bang 不负责跨设备同步。

路径不同时运行 `bang init`。不要复制旧设备的项目软链接，在各项目重新运行 `bang skill select`。

### 为什么没有列出某个 skill？

只扫描个人库的一级真实目录，且目录内必须有 `SKILL.md`。来源软链接、备份目录和待清理目录会被跳过。

### 找不到 `bang` 命令？

通过 uv 安装后运行 `uv tool update-shell`，按提示重开终端。也可以直接使用 `python3 /你的路径/bang/bang.py`，不依赖 PATH 配置。

### 选择界面无法使用？

交互界面需要至少 5 行、20 列的终端。管道输入或输出重定向时会改用编号选择：输入如 `1 3 5` 切换勾选，回车预览，输入 `y` 确认，`q` 退出。

### 归集失败或需要恢复旧版？

先查看命令输出中的失败原因和备份路径，不要直接删除恢复目录。

- 复制失败时，原来源和个人库旧版保持完整，修复问题后可重试。
- 旧版备份后发布失败时，会在目标仍空缺的情况下尝试恢复，并输出旧版备份位置。
- 新版已发布但来源清理失败时，个人库新版仍可用；按输出检查全局入口中的隐藏 `.skillctl-cleanup-*` 目录，不要把残缺内容再次用于归集。
- 旧版位于个人库 `.backups/skill-<随机标识>/old/`。恢复时先保全当前版本，再把 `old/` 放回对应 skill 路径。

备份不会自动删除，确认不再需要后可手动清理。操作不保证断电恢复；执行期间不要同时手动修改这些目录。

## 开发与详细规格

实现约定和边界见 [SPEC.md](SPEC.md)，术语见 [CONTEXT.md](CONTEXT.md)。

测试使用临时 HOME 和临时 Git 仓库，不操作本机个人库：

```sh
python3 -B -m unittest -v
uvx --from pyright pyright --project pyproject.toml
```
