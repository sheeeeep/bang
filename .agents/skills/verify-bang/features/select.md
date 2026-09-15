# 为项目选择 skill

用户从个人库勾选 skill，确认预览后，bang 在项目中创建对应的软链接。再次运行并取消勾选，只会移除项目链接，不会删除个人库中的内容。

## Sub-features

- `select-add-remove`：选择、预览、确认、取消选择及 Git 本地排除。
- `select-search`：方向键移动、大小写及 Unicode 搜索、无匹配提示和滚动；搜索隐藏的选项仍保持勾选。
- `select-cancel`：Esc 清空再退出、Ctrl-C、预览输入 n 均不修改。
- `select-numbered`：非 TTY 使用编号切换。
- `select-location`：在 Git 根目录或子目录运行时，链接写入工作树根目录；非 Git 环境则写入当前目录。
- `select-conflict`：已跟踪文件、真实目录和外部链接不覆盖并报告冲突。

## How to get to it (user POV)

在 Git 项目根、任意子目录或非 Git 目录运行 `bang skill select`。TTY 显示选择器，管道输入或输出重定向使用编号交互。

## Driving it with PtySession

Preconditions: 按 Launch 准备独立 HOME 和 Git 项目，个人库中有真实目录 `alpha`，其中包含 `SKILL.md`。使用一键脚本时，这些数据由脚本自动创建。

- **选择并移除。** 执行 `python3 -B "$REPO/.agents/skills/verify-bang/scripts/verify.py" prove --evidence "$EVIDENCE/select"`。脚本在两次 PTY 会话中分别发送 `SPACE ENTER`，等待新增或移除链接的预览及 `执行以上变更？`，再发送 `y ENTER`。报告中的 passed 应为 true：第一次确认后，链接指向个人库且 Git 排除规则生效；第二次确认后，链接消失，个人库内容不变，exclude 恢复原状。
- **搜索与取消。** 在仓库运行 `python3 -B -m unittest -v test_terminal`；覆盖真实 PTY 的搜索/清空/退出、CSI/SS3 方向键、Unicode、隐藏选择、无匹配、小窗口、Ctrl-C 恢复。需要为某项行为保留证据时，参照 `test_terminal.py` 对应测试，记录发送的按键和检查结果。历史缓冲区中出现过的提示，不能证明当前屏幕仍是该状态。
- **编号入口。** 在隔离 bash 执行下面命令；第一次新增，第二次移除。每一步的退出码都应为 0，操作后个人库中的文件仍可读取。

```bash
mkdir -p "$HOME/my-skills/alpha"
printf '# Alpha\n' > "$HOME/my-skills/alpha/SKILL.md"
printf '1\n\ny\n' | python3 -B "$REPO/bang.py" skill select
test -L .agents/skills/alpha
readlink .agents/skills/alpha
git check-ignore .agents/skills/alpha
printf '1\n\ny\n' | python3 -B "$REPO/bang.py" skill select
test ! -L .agents/skills/alpha
test -f "$HOME/my-skills/alpha/SKILL.md"
echo 'select-numbered rc=0'
```

- **其他位置。** 每次重新准备临时环境，分别运行 `mkdir sub && cd sub` 或 `mkdir "$SCRATCH/plain" && cd "$SCRATCH/plain"` 后重复编号选择步骤。子目录入口须从项目根检查 `.agents/skills/alpha` 和 Git exclude（不能照搬上述相对路径断言）；非 Git 入口须看到 `当前目录不是 Git 工程` 且当前目录创建链接、不生成 `.git`。分别保存证据。
- **冲突。** 在新的临时环境中创建个人库 skill alpha，再运行 `mkdir -p .agents/skills/alpha`；发送 `1\n\ny\n`，须报告 `冲突，跳过`、返回 1，原真实目录仍在。已跟踪路径和外部软链接须分别重跑并记录，不能用一次检查代替。

## Gotchas

- 终端至少 5 行 20 列；默认脚本 24×80。管道测试不能证明 curses 行为。
- 只有一级真实 skill 目录会列出；软链接、备份和待清理目录被跳过。
- 搜索不会清除隐藏勾选；旧输出中出现的名称，不一定仍与当前搜索词匹配。
- 默认脚本只验证 Git 根目录下的 PTY 选择和移除流程。冲突时退出码应为 1；按 Esc 或 Ctrl-C 取消时为 130；在预览中输入 n 时为 0。
