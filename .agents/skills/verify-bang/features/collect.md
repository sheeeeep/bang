# 把全局入口归集到个人库

用户确认预览后，bang 将 skill 从全局入口搬入个人库。个人库中已有同名 skill 时，先备份旧版，再整份替换。成功后会移除全局入口中的原目录，不留下软链接。

## Sub-features

- `collect-new`：搬入新 skill，移除来源。
- `collect-replace`：同名旧版备份，不合并文件。
- `collect-cancel`：拒绝确认不修改。
- `collect-conflict`：目标非真实 skill 时报告并跳过。

## How to get to it (user POV)

在任意目录运行 `bang skill collect`。bang 根据配置中的 source 和 library 确定来源与目标，不要求当前目录属于 Git 项目。

## Driving it with CLI pipes

Preconditions: 按 Launch 准备新的独立 bash 环境，使用默认配置。所有来源和目标目录都必须位于临时 HOME 中。

- **搬入。** 运行下方命令，须看到 `搬入: alpha`、`成功: alpha`；目标内容相同，来源不存在。

```bash
mkdir -p "$HOME/.agents/skills/alpha"
printf 'new\n' > "$HOME/.agents/skills/alpha/SKILL.md"
printf 'y\n' | python3 -B "$REPO/bang.py" skill collect
test ! -e "$HOME/.agents/skills/alpha"
printf 'new\n' | cmp - "$HOME/my-skills/alpha/SKILL.md"
# 同名升级：旧版 new，新版 newer。
mkdir -p "$HOME/.agents/skills/alpha"
printf 'newer\n' > "$HOME/.agents/skills/alpha/SKILL.md"
printf 'n\n' | python3 -B "$REPO/bang.py" skill collect
printf 'new\n' | cmp - "$HOME/my-skills/alpha/SKILL.md"
printf 'newer\n' | cmp - "$HOME/.agents/skills/alpha/SKILL.md"
test -z "$(find "$HOME/my-skills/.backups" -type f)"
printf 'y\n' | python3 -B "$REPO/bang.py" skill collect
test ! -e "$HOME/.agents/skills/alpha"
printf 'newer\n' | cmp - "$HOME/my-skills/alpha/SKILL.md"
find "$HOME/my-skills/.backups" -type f -print -exec cat {} \;
printf 'new\n' | cmp - "$HOME"/my-skills/.backups/skill-*/old/SKILL.md
cp -R "$HOME/my-skills" "$EVIDENCE/collect-library"
echo 'collect-new collect-cancel collect-replace rc=0'
```

- **冲突。** 在新的临时环境中准备来源 alpha，再用 `mkdir -p "$HOME/my-skills/alpha"` 创建目标目录，但不要创建 SKILL.md。运行归集命令并输入 y，预期退出码为 1，输出 `冲突，跳过非真实 skill 目标`，来源内容应保持不变，目标目录仍为空。将错误输出与退出码单独保存。

## Gotchas

- collect 是搬入，不是复制；只能在临时 HOME 验证。
- 备份在 `.backups/skill-*/old`，清理前须将旧版备份复制到证据目录。
- 没有配置文件时使用默认值。配置损坏时应报错，此时先处理错误，不要继续发送输入。
