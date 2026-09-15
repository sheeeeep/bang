# 创建 agent 指引文件

用户选择 common 或 js 模板，再选择写入 AGENTS.md 或 AGENTS.override.md。确认后，bang 将模板写入当前目录；目标文件已存在时，会先询问是否备份。

## Sub-features

- `agent-create`：选择模板和文件名，可接受默认值，也可输入编号或名称。
- `agent-backup`：默认备份旧文件再覆盖。
- `agent-overwrite`：明确不备份后确认覆盖。
- `agent-cancel`：q、Ctrl-C 或拒绝最终确认不写入。
- `agent-conflict`：软链接与非普通文件拒绝覆盖。

## How to get to it (user POV)

在希望保存指引文件的目录运行 `bang init agent`。文件始终写入当前目录，不会改写到 Git 根目录；在 Git 子目录或非 Git 目录中也可运行。此命令不接受 library/source 参数。

## Driving it with CLI pipes

Preconditions: 按 Launch 准备新的独立 bash 环境，确认当前目录中没有目标文件。

- **默认创建。** 执行以下命令，逐字节比较目标文件和模板，不能只看“已写入”提示。

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

- **位置入口。** 每次都重新准备临时环境，再分别运行 `mkdir sub && cd sub` 或 `mkdir "$SCRATCH/plain" && cd "$SCRATCH/plain"`，重跑默认创建并检查只在该目录有 AGENTS.md，父目录不新增文件。
- **冲突与取消。** 在新的临时环境中运行 `ln -s "$REPO/README.md" AGENTS.md`，发送两个回车后预期退出 1，输出 `拒绝覆盖软链接或非普通文件`；原链接和 README 内容必须不变。另开一个没有目标文件的临时环境，发送 `q\n`，预期 130 且无目标/备份。

## Gotchas

- 已存在时多一道备份提示，不能重用新建时的三行输入。
- 备份文件名含随机标识。只有确认本次环境中仅有一个备份时，才能用 `AGENTS.md.bak-*` 比较内容；bang 不会自动删除历史备份。
- 选择不备份后会直接覆盖原文件，只能在临时目录中验证。上面的步骤没有遍历模板和文件名的所有组合，不要将其全部标为通过。
