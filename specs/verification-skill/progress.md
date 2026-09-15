# 验证技能进度

## 已完成的工作

- 阅读 README、pyproject.toml、bang.py 和 test_terminal.py，确认 bang 通过 CLI/TUI 提供交互，非 TTY 环境使用编号输入，无需安装运行时依赖。
- 创建验证技能、五项功能地图和可执行脚本 `scripts/verify.py`，未修改产品代码或既有测试。
- 首次提交位于 `.cursor/skills/verify-bang/`。本轮开始时，工作区已将文件移至 `.agents/skills/verify-bang/`；本轮保留该调整，润色 Markdown，并将使用说明中的路径改为新位置。

## 首次生成时的验证结果

- 启动检查：`python3 -B bang.py --help` 成功。
- 基线测试：`python3 -B -m unittest -q`，41 项通过。
- 按 Launch 运行旧位置的 `scripts/verify.py doctor` 和 `prove --evidence /tmp/bang-evidence.MW1DR4/select`，均通过。
- 两次真实 PTY 会话分别验证新增和移除链接：预览时文件未变，确认后链接按预期变化，个人库内容保持不变，`git check-ignore` 检查通过，移除后 exclude 恢复，未创建 `.gitignore`。
- 提取五份功能文档中的 bash 代码块，分别在独立临时 HOME 和 Git 项目中执行 `bash -euxo pipefail -c`。select、collect、config、agent、install 均返回 0，每轮临时目录均已清理。
- 使用 `lens_diagnostics source=lsp scope=paths` 主动检查脚本：1 个文件，0 条诊断。frontmatter、技能章节、地图 H2、相对链接、脚本执行权限和证据文件检查均通过；`git diff --check` 通过。

## 证据位置

证据保存在 `/tmp/bang-evidence.MW1DR4/`：

- `doctor.json`、`run.log`：运行环境和脚本输出。
- `select/report.json`、`select/terminal-{0,1}.txt`：PTY 操作及检查结果。
- 各功能子目录：bash 执行日志和结果文件副本；编号选择的记录位于 `select/recipes`。

首次验证清理后，上述文件仍在。报告中的 `passed`、`scratch_removed` 和 `children_stopped` 均为 true。

## 本轮文案检查

- 比较润色前后的 9 份 Markdown：代码块仅更新技能目录路径，命令和断言未变；frontmatter、章节结构和相对链接检查通过。
- 在新目录运行 `python3 -B .agents/skills/verify-bang/scripts/verify.py doctor`，通过；`git diff --check` 通过。本轮只改文档，未重跑全部功能测试。
- 检查发现工作区脚本已有格式调整，因此与上次提交逐字节比较不一致；改用 AST 比较后确认逻辑一致。保留这些既有改动，未修改脚本。
- 文档润色与工作区已有的目录迁移重叠，未将迁移或脚本格式调整代为提交。本轮修改保留在工作区。

## PR 提交前复核

- 用户已授权提交目录迁移、文案修改和既有脚本格式调整，并通过 PR 合入 master。
- 在 `.agents/skills/verify-bang/` 运行 `scripts/verify.py doctor` 和 `prove`，均通过；临时目录及子进程已清理，证据仍在 `/tmp/bang-pr-evidence.0tuZLQ/`。
- 重跑 `python3 -B -m unittest -q`，41 项通过，日志为上述目录中的 `tests.log`。

## 尚未验证的范围

主流程的 bash 步骤已跑通，但未逐一验证子目录、非 Git 目录、所有冲突和非法输入变体，以及自定义安装路径的输出。后续按功能地图补充，不能用已有的 41 项基线测试代替各入口的操作证据。

未运行独立网络审计。安装指南验证只确认了本地文件和 Git refs 未变。

## 恢复与维护

本次验证没有保留常驻服务，没有全局安装，也没有修改用户真实的 HOME。仍可按 README 运行 `python3 -B bang.py --help`。

证据位于临时目录，长期保留前须复制到持久存储。后续使用 `/maintain-verification-skill` 更新文档与脚本。

README 指向的根目录 SPEC.md 不存在；本任务依据实际源码和现有 specs，未修改这一无关链接。
