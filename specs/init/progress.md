# 模板选择进度

## 分支提交

- 用户已授权新建分支并提交当前全部改动，解除下文历史记录中的暂未提交状态。
- 分支：`feat/init-agent-templates`；纳入当前实现、模板、测试、打包配置、仓库指南与规格迁移，不推送远端。
- 提交前重跑 `python3 -B -m unittest -q`：39 项通过；`git diff --check` 通过；`lens_diagnostics mode=all` 无问题。

## 追加：可选备份

- 目标已存在时询问是否备份，默认是；支持 y/n（忽略大小写）、q 取消，非法输入重试。新文件不询问。
- 不备份时提示覆盖风险，仍须最终确认；两种路径均保留文件权限，取消不写入、不产生备份。
- `python3 -B -m unittest -q`：39 项全部通过，新增默认备份、不备份、非法输入、取消、EOF 与权限保留检查。
- `lsp_diagnostics`：bang.py、test_bang.py 主语言服务器 0 诊断；`lens_diagnostics mode=all`：本次检查无问题；`git diff --check` 通过。
- 继续保留已有工作区改动；与上一轮相同，本轮依赖尚未提交的 init agent 实现，未混入用户改动创建提交。

## 本轮完成

- `bang init agent` 先选择 common（默认）或 js，支持编号与名称，再选择目标文件名。
- 预览显示模板；沿用确认、备份、取消与安全检查。裸 `bang init` 的 skill 配置行为不变。
- 更新 README 和 SPEC.md；新增 feature_list.json 仅记录本轮功能，不推断既有功能状态。

## 验证

- 基线：`python3 -B -m unittest test_bang.CliTests.test_init_agent_creation_backup_and_cancellation -q` 失败，旧实现引用已不存在的 AGENTS.override.md 模板。
- 修改后：`python3 -B -m unittest -q`，38 项全部通过。覆盖两种模板、两种目标、默认值、名称、非法输入、取消、备份和写入安全。
- `lsp_diagnostics` 主语言服务器检查 bang.py、test_bang.py：0 项诊断。
- `git diff --check`：通过。
- `lens_diagnostics mode=all`：无阻塞错误；SPEC.md 原有 `./CONTEXT.md` 链接不存在的警告，与本轮模板选择无关。

## 工作区与恢复

- 开始时 README.md、bang.py、test_bang.py、pyproject.toml 已修改，根 SPEC.md 已删除，bang_templates/、specs/ 和 AGENTS.md 未跟踪；全部保留。
- 本轮变更依赖尚未提交的 init agent 实现与模板资源，不能独立提交为可用版本；未将用户已有改动纳入提交，保留工作区待统一处理。
- 可继续通过 `python3 bang.py init agent` 使用；模板资源打包配置已有 `*.md` 通配，无需更改。
