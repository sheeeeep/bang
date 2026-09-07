# skillctl

个人本机的 skill 管理 CLI，Python 3.9+ 标准库实现，无运行时依赖。需要 Git 2.31+；面向 macOS / Linux。

## 使用

```sh
# 在新项目根目录或其子目录运行
python3 /Users/bytedance/agent-workspace/my-skill-cli/skillctl.py select

# 手动下载／复制 skill 到 ~/.agents/skills 后，在任意目录运行
python3 /Users/bytedance/agent-workspace/my-skill-cli/skillctl.py collect
```

可选：给可执行脚本建立命令链接（确保 `~/.local/bin` 在 PATH 中）：

```sh
mkdir -p ~/.local/bin
ln -s /Users/bytedance/agent-workspace/my-skill-cli/skillctl.py ~/.local/bin/skillctl
skillctl select
skillctl collect
```

### select：同步项目选择

- 扫描 `~/my-skills` 的一级真实目录，只列出含 `SKILL.md` 的 skill；忽略隐藏目录和来源软链接。
- `[x]` 为已选项。输入编号切换，可一次输入 `1 3 5`；回车查看预览，再输入 `y` 执行。`q`、Ctrl-C 或输入结束均停止。
- 创建 `.agents/skills/<名称>` → `~/my-skills/<名称>` 的链接；取消已有选项只移除项目链接。
- 用 Git 定位当前工作树根目录，不以当前子目录充当项目根目录。非 Git 或 bare 仓库报错且不修改。
- 使用 Git 返回的本地 `info/exclude` 路径，支持 `.git` 为文件的 worktree；同仓库多个 worktree 共享该排除文件。
- 仅在带 `skillctl` 标记的区块中维护具体链接规则，不改 `.gitignore` 或 Git 索引。不要手动编辑该区块。
- 同名真实文件／目录、外部软链接、已跟踪路径均报告并跳过；其他可用项继续执行。失效的个人库链接仍可取消选择并移除。
- 为避免写到意外位置，不接受管理目录或其祖先为软链接的布局（HOME 自身会先规范化）。

### collect：归集全局入口

- 仅从 `~/.agents/skills` 归集，来源软链接跳过；不扫描其他 agent 的目录，不处理安装器锁文件。
- 同名真实 skill 逐项询问是否升级，默认跳过；同名普通文件、无 `SKILL.md` 的目录或软链接不会覆盖。
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
