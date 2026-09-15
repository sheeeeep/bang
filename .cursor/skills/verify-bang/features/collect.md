# 把全局入口归集到个人库

用户预览并确认搬入 skill；同名旧版先备份再整份替换，成功后全局入口不再保留原目录或链接。

## Sub-features

- `collect-new`：搬入新 skill，移除来源。
- `collect-replace`：同名旧版备份，不合并文件。
- `collect-cancel`：拒绝确认不修改。
- `collect-conflict`：目标非真实 skill 时报告并跳过。

## How to get to it (user POV)

任意目录运行 `bang skill collect`，读取配置的 source/library；不要求在 Git 项目内。

## Driving it with CLI pipes

Preconditions: Launch 的全新隔离 bash；默认配置，不使用用户全局目录。

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

- **冲突。** 全新基线准备来源 alpha，目标 `mkdir -p "$HOME/my-skills/alpha"` 但不创建 SKILL.md，再输入 y；返回 1、输出 `冲突，跳过非真实 skill 目标`，来源保持、目标仍为空。将错误输出与退出码单独保存。

## Gotchas

- collect 是搬入，不是复制；只能在临时 HOME 验证。
- 备份在 `.backups/skill-*/old`，升级后的旧版证据须在清理前复制出。
- 无配置使用默认值；配置损坏应返回错误，不应继续驱动。
