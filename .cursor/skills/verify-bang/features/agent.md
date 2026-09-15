# 创建 agent 指引文件

用户选择 common/js 模板和 AGENTS.md/AGENTS.override.md 文件名，确认后写到当前目录；覆盖已有文件时可选择是否备份。

## Sub-features

- `agent-create`：两模板、两文件名，默认或数字/名称输入。
- `agent-backup`：默认备份旧文件再覆盖。
- `agent-overwrite`：明确不备份后确认覆盖。
- `agent-cancel`：q、Ctrl-C 或拒绝最终确认不写入。
- `agent-conflict`：软链接与非普通文件拒绝覆盖。

## How to get to it (user POV)

在希望写入文件的目录运行 `bang init agent`；目标是当前目录，不查 Git 根，Git 子目录和非 Git 目录都支持。不接受 library/source 参数。

## Driving it with CLI pipes

Preconditions: Launch 全新隔离 bash，无目标文件。

- **默认创建。** 执行以下命令，核对完整模板字节而非只看“已写入”。

```bash
printf '\n\ny\n' | python3 -B "$REPO/bang.py" init agent
cmp AGENTS.md "$REPO/bang_templates/AGENTS.common.md"
# 名称模板 + 数字目标：js/override。
printf 'js\n2\ny\n' | python3 -B "$REPO/bang.py" init agent
cmp AGENTS.override.md "$REPO/bang_templates/AGENTS.js.md"
# 默认备份：将 AGENTS.md 换成 js，旧 common 字节保留。
printf '2\n1\n\ny\n' | python3 -B "$REPO/bang.py" init agent
cmp AGENTS.md "$REPO/bang_templates/AGENTS.js.md"
cmp AGENTS.md.bak-* "$REPO/bang_templates/AGENTS.common.md"
# 不备份，但最终拒绝：仍为 js。
printf 'common\n1\nn\nn\n' | python3 -B "$REPO/bang.py" init agent
cmp AGENTS.md "$REPO/bang_templates/AGENTS.js.md"
# 不备份并确认：变回 common，历史备份不动。
printf 'common\n1\nn\ny\n' | python3 -B "$REPO/bang.py" init agent
cmp AGENTS.md "$REPO/bang_templates/AGENTS.common.md"
cmp AGENTS.md.bak-* "$REPO/bang_templates/AGENTS.common.md"
cp AGENTS* "$EVIDENCE/"
echo 'agent-create agent-backup agent-cancel agent-overwrite rc=0'
```

- **位置入口。** 全新基线分别进入 `mkdir sub && cd sub` 或 `mkdir "$SCRATCH/plain" && cd "$SCRATCH/plain"`，重跑默认创建并检查只在该目录有 AGENTS.md，父目录不新增文件。
- **冲突与取消。** 全新基线 `ln -s "$REPO/README.md" AGENTS.md`，发送两个回车后预期退出 1，输出 `拒绝覆盖软链接或非普通文件`；原链接及 README 字节不变。另用空基线发送 `q\n`，预期 130 且无目标/备份。

## Gotchas

- 已存在时多一道备份提示，不能重用新建时的三行输入。
- 备份名随机；新基线才可用单个 `AGENTS.md.bak-*` 比较，历史备份不自动删除。
- 不备份是实际覆盖，只在隔离目录执行。地图首轮未声称所有模板/文件名笛卡尔组合都通过。
