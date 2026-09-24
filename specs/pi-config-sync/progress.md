# pi 配置迁移进度

## 实现

- 分支：`feat/pi-config-sync`；开始时工作区干净。
- `scripts/backup_pi.py` 调用共享白名单逻辑覆盖 `bang_pi/config.json`，本机实际备份包含 14 个 npm/git 来源、可移植主设置和自动命名插件模型设置。
- `bang pi launch` 使用随包快照，不依赖原仓库；覆盖受管字段、保留其他字段与凭据，保持 cwd、转发参数和 pi 退出码。
- 配置路径跟随实际读取行为：主配置支持 PI_CODING_AGENT_DIR；当前自动命名插件固定使用 HOME 下的配置。
- 使用 pi 启动时的原生缺失包安装机制，无自制安装器、安装回执或强制升级。
- 所有目标先校验；逐文件原子写入；错误输出至终端。同步提示输出 stderr，不污染 RPC stdout。
- 更新 README、打包数据声明和 pyright 检查范围。未安装或修改本机 pi 插件、凭据与全局 bang 命令；没有推送。

## 验证证据

- 基线：`python3 -B -m unittest -q`，41 项通过。
- 最终：`python3 -B -m unittest -q`，52 项通过（新增 11 项）；覆盖备份更新、无 packages 默认空清单、脚本跨目录调用、保留凭据、参数/cwd/退出码、可重复同步、无效 JSON/来源/类型、软链接、写失败清理与自定义根目录。
- `uvx --from pyright pyright --project pyproject.toml`：0 errors / warnings / informations。
- `lens_diagnostics source=lsp scope=paths serverScope=primary` 检查 bang.py、test_pi.py、scripts/backup_pi.py、bang_pi/__init__.py：4 个文件均 clean，0 诊断。
- Semgrep 关于 importlib.resources 不兼容 Python <3.7 的提示已标记误报；本项目要求 Python >=3.9，原实现已使用该模块。脚本最终不带 shebang、权限 0644，使用文档中的 python3 命令执行；`uvx ruff check --select EXE scripts/backup_pi.py` 通过。
- `uvx ruff format bang.py test_pi.py scripts/backup_pi.py bang_pi/__init__.py` 已执行；`git diff --check` 通过。
- `python3 -B scripts/backup_pi.py` 实际运行并再次覆盖更新，备份不含 auth、代理或命令字段；未修改来源配置。

### 安装包验收

在 `/private/tmp/bang-pi-clean.WozdCS/source` 复制当前模块、pyproject、README 与资源包，避免已有 build 缓存混入旧文件：

```sh
uv build --wheel --out-dir /private/tmp/bang-pi-clean.WozdCS/dist /private/tmp/bang-pi-clean.WozdCS/source
uv venv --python /usr/bin/python3 /private/tmp/bang-pi-clean.WozdCS/venv
uv pip install --reinstall --refresh --python /private/tmp/bang-pi-clean.WozdCS/venv/bin/python /private/tmp/bang-pi-clean.WozdCS/dist/bang-0.1.0-py3-none-any.whl
```

- 从工程外 `project/` 目录运行 venv 内 `bang pi launch --version`，HOME 与 PI_CODING_AGENT_DIR 均设为临时绝对真实目录：两个配置文件同步成功，真实 pi 输出 `0.85.1`，退出 0。
- 从工程外用 importlib.resources 读取已安装资源，断言清单 14 项通过。最终代码重新构建、安装后再次通过。
- 首次验收使用 `/tmp/...` 被软链接安全检查拒绝（macOS `/tmp` 指向 `/private/tmp`）；改用真实路径后通过，未放宽路径检查。
- setuptools 对已有 bang_skills.install/personal 的显式 packages 配置有非阻塞警告；现有资源和本次新增资源均实际包含在 wheel 中，本次未修改旧 skill 打包策略。

### 真实原生插件恢复与失败验收

仅将临时安装包的快照改为 `{"settings.json":{"packages":["npm:@ogulcancelik/pi-herdr"]}}`；使用全新临时 HOME（不继承凭据），运行安装后的命令：

```sh
bang pi launch --mode rpc --no-session --no-extensions --no-skills
```

- stdin 为空、不发送模型请求；PATH 指向现有 pi/Node；设置 PI_SKIP_VERSION_CHECK=1、PI_TELEMETRY=0、NPM_CONFIG_IGNORE_SCRIPTS=true、临时 NPM_CONFIG_CACHE 与公共 npm registry。
- 真实 pi 原生安装缺失包，npm 显示 added 1 package；验证临时 `npm/node_modules/@ogulcancelik/pi-herdr/package.json` 存在，RPC 启动退出 0，stdout 无 bang 提示。
- 第二个空 HOME，将 registry 改为 `http://127.0.0.1:9`，fetch retries=0、timeout=2000；真实 npm 安装失败，bang 输出失败并返回 1。同步文件保留，可修复网络后重跑。
- 以上试验后重新安装最终完整 14 项快照的 wheel。测试目录内的实验数据不提交。

## 边界与恢复

- 未对全部 14 个插件逐一联网安装，也未验证各插件交互功能；真实联网验收覆盖一个 npm 插件的恢复及安装失败，Git 来源恢复依据已检查的 pi 原生实现。没有请求模型 API 或进行登录。
- 白名单不是完整用户目录镜像，也不是通用秘密扫描器；不支持的来源明确失败，独立插件新增配置需审查后扩展白名单。不要将凭据填写在模型/主题标识中。
- 插件当前未固定版本；新设备安装结果可能不同。桌面集成、skill 链接与本机版本热修复另行准备。
- 多文件不是事务、没有并发编辑保护。配置错误或网络失败时先看终端日志，修复后重跑；恢复旧受管值需使用用户自己的备份，auth.json 始终不读写。
- 标准使用：源码可 `python3 bang.py pi launch`；安装命令需自行 `uv tool install --reinstall .`（本轮未做全局安装）。
