# 安装指南进度

记录本轮实现、验证证据及恢复边界。
用户已确认命令只输出指南，模型安装到 source，用户自行 collect/select。
状态以 feature_list.json 为准，尚未执行的上游安装不记为通过。

## 实现

- 增加只读 install 子命令、完整安装指南和随包个人资源；README 与领域术语同步。
- personal-to-spec 改名以避免与 Matt 版本冲突；原始个人库内容未修改。
- 来源核查详见 spec.md；writing-great-skills 已明确显示来源待确认，不阻断其他选择。

## 验证结果

- `python3 -B -m unittest -q`：41 项全部通过（Python 3.9）。新增默认/自定义 source、无写入、完整指南与个人资源、损坏配置报错检查。
- `lsp_diagnostics` 检查 bang.py、test_bang.py、bang_skills/__init__.py：主语言服务器 0 诊断。
- `uv build --wheel --out-dir <临时目录>/dist` 成功；`uv venv` 和 `uv pip install --python <临时环境>/bin/python --no-deps <wheel>` 安装成功（Python 3.13.5）。
- 在仓库之外、空临时 HOME 下运行临时环境中的 `bang skill install`：成功；HOME 与运行目录保持空；输出定位到 site-packages 中的两个个人资源。逐字节比较 wheel 中全部 Markdown/YAML 资源与源码一致。
- wheel 与验证输出位于 `/private/var/folders/9s/6bsy2zz96rbd6r50ct6c6r1h0000gn/T/tmp.SzrJ4c8Mxs/`，仅为本机临时证据，不是运行依赖。
- `git diff --check` 通过；`lens_diagnostics mode=all` 无阻塞错误。个人原文中的反馈标签被 Markdown 当成标题提出 6 项风格警告，属于模板输出格式而非缺陷，已记录误报处置并保留原格式；spec XML 式提示边界同样是有意格式。

## 验证中修正

- 首次新增测试发现 macOS Python 会在临时 HOME/Library 写解释器字节码缓存，不是 install 的文件操作。测试对子进程设置 PYTHONDONTWRITEBYTECODE，排除解释器缓存后仍严格比较整个 HOME 的目录元数据；两项针对测试及全部回归重跑通过。
- 首次 wheel 检查误将 `/var` 与规范化的 `/private/var` 当成不同 HOME；按现有 config_paths 的 HOME 规范化规则修正断言，重新构建最终 wheel 并验证通过。未降低资源或无写入检查。
- 未执行任何上游真实安装；网络/权限/安装器版本问题由模型执行时按指南报告。writing-great-skills 来源待确认是用户接受的显式不可安装状态。

## 工作区边界

- 开始时 bang_templates/AGENTS.common.md、bang_templates/AGENTS.js.md 已有用户改动；保留且不纳入本任务提交。
- 不执行真实 skill 安装、collect、select 或依赖工具安装；仅只读获取官方说明与包内容。
- 临时验证失败时保留证据并说明恢复步骤；标准启动仍为 python3 bang.py 或已安装的 bang。
