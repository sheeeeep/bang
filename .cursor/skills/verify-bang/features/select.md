# 为项目选择 skill

用户从个人库勾选 skill，预览后确认创建项目软链接；再次取消勾选只移除链接，保留库内容。

## Sub-features

- `select-add-remove`：选择、预览、确认、取消选择及 Git 本地排除。
- `select-search`：方向键、大小写/Unicode 搜索、隐藏勾选保留、无匹配和滚动。
- `select-cancel`：Esc 清空再退出、Ctrl-C、预览输入 n 均不修改。
- `select-numbered`：非 TTY 使用编号切换。
- `select-location`：Git 根目录/子目录定位到工作树根；非 Git 使用当前目录。
- `select-conflict`：已跟踪文件、真实目录和外部链接不覆盖并报告冲突。

## How to get to it (user POV)

在 Git 项目根、任意子目录或非 Git 目录运行 `bang skill select`。TTY 显示选择器，管道输入或输出重定向使用编号交互。

## Driving it with PtySession

Preconditions: 依照 Launch 使用独立 HOME 和 Git 项目；库内真实目录 `alpha/SKILL.md`。一键脚本自行准备。

- **选择并移除。** 执行 `python3 -B "$REPO/.cursor/skills/verify-bang/scripts/verify.py" prove --evidence "$EVIDENCE/select"`。两轮真实 PTY 分别发送 `SPACE ENTER`，等 `新增链接: alpha` 或 `移除链接: alpha` 与 `执行以上变更？` 后发 `y ENTER`；报告 passed 为 true，第一轮链接目标及 Git 排除生效，第二轮链接消失、库内容不变、exclude 恢复。
- **搜索与取消。** 在仓库运行 `python3 -B -m unittest -v test_terminal`；覆盖真实 PTY 的搜索/清空/退出、CSI/SS3 方向键、Unicode、隐藏选择、无匹配、小窗口、Ctrl-C 恢复。需要单项证明时参照 `test_terminal.py` 对应测试，在发送动作和检查状态处保存日志，不以历史缓冲区旧提示证明当前屏幕。
- **编号入口。** 在隔离 bash 执行下面命令；第一次新增，第二次移除。每一步必须 exit 0，原库仍可读。

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

- **其他位置。** 在全新基线分别 `mkdir sub && cd sub`、或 `mkdir "$SCRATCH/plain" && cd "$SCRATCH/plain"` 后重复编号配方。子目录入口须从项目根检查 `.agents/skills/alpha` 和 Git exclude（不能照搬上述相对路径断言）；非 Git 入口须看到 `当前目录不是 Git 工程` 且当前目录创建链接、不生成 `.git`。分别保存证据。
- **冲突。** 全新基线创建库 alpha，并 `mkdir -p .agents/skills/alpha`；发送 `1\n\ny\n`，须报告 `冲突，跳过`、返回 1，原真实目录仍在。已跟踪路径和外部软链接各自重跑，不合并为一次证明。

## Gotchas

- 终端至少 5 行 20 列；默认 helper 24×80。管道测试不能证明 curses 行为。
- 只有一级真实 skill 目录会列出；软链接、备份和待清理目录被跳过。
- 搜索不会清除隐藏勾选；旧输出里的名字不等于当前屏幕匹配。
- 默认 helper 仅证明 Git 根目录 PTY 增删，不证明其余入口；冲突预期退出 1，取消 Esc/Ctrl-C 为 130，预览 n 为 0。
