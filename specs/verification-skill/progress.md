# 进度

- 调查 README、pyproject.toml、bang.py 全部实现及 test_terminal.py；主表面为 CLI/TUI，支持非 TTY 编号输入，无运行时依赖。
- 基线：`python3 -B bang.py --help` 成功；`python3 -B -m unittest -q` 41 项通过。
- 已生成 `.cursor/skills/verify-bang/SKILL.md`、五项地图和可执行的 `scripts/verify.py`；不修改产品或既有测试。
- 按 Launch 执行 `python3 -B .cursor/skills/verify-bang/scripts/verify.py doctor` 及 `prove --evidence /tmp/bang-evidence.MW1DR4/select`：通过。两次真实 PTY 验证预览无写入、确认新增/移除链接、个人库内容保持、Git check-ignore 有效、exclude 恢复和未创建 .gitignore。
- 证据：`/tmp/bang-evidence.MW1DR4/doctor.json`、`run.log`、`select/report.json`、`select/terminal-{0,1}.txt`；清理后文件仍在，report 的 passed、scratch_removed、children_stopped 均为 true。
- 从五份地图提取 bash 代码块，分别在独立临时 HOME/Git 项目中以 `bash -euxo pipefail -c` 执行：select、collect、config、agent、install 全部返回 0；日志及结果副本在上述证据目录的各功能子目录（编号选择在 select/recipes）。每轮临时目录均清理。
- `lens_diagnostics source=lsp scope=paths` 主动检查新脚本：1 文件、0 诊断。Python 断言检查 frontmatter、六个技能章节、地图四个 H2、相对链接、可执行权限和证据留存均通过；`git diff --check` 通过。
- 已覆盖地图的主 bash 配方，不声称所有入口都已证明：子目录/非 Git、全部冲突与非法输入变体、自定义安装上下文等仍按地图按需验证；已有 41 项基线测试通过不替代各入口的独立证据。未运行网络审计，安装指南仅核对本地文件/ref 无变化。
- 恢复：无常驻服务或全局安装，无用户 HOME 改动；仍可按 README 用 `python3 -B bang.py --help` 启动。证据位于临时存储，跨重启留存需复制到持久目录；后续使用 `/maintain-verification-skill` 维护。
- README 链接的根目录 SPEC.md 不存在；本任务依据实际源码和现有 specs，不修改无关文档。
