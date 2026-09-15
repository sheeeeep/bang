# pi 配置备份与设备同步

## 目标

工程保存本机可移植的 pi 插件配置与安装清单；工程脚本支持覆盖更新，新增 `bang pi launch` 将随 bang 分发的备份同步到当前设备后启动 pi。

## 范围与边界

- 分支 `feat/pi-config-sync`，不推送。
- `python3 scripts/backup_pi.py` 从 `PI_CODING_AGENT_DIR` 或默认 `~/.pi/agent` 读取，原子覆盖 `bang_pi/config.json`。备份与脚本位置相对于 bang 工程，不受执行目录影响。
- 自动命名插件当前实现固定读取 HOME 下的 `~/.pi/agent/extensions/pi-session-auto-rename.json`，不遵循 PI_CODING_AGENT_DIR；备份和恢复跟随它的实际位置。
- 明确白名单：主配置的 packages、theme、defaultProvider、defaultModel、defaultThinkingLevel、hideThinkingBlock，以及 `extensions/pi-session-auto-rename.json` 的 provider、id。
- 本机安装清单为 npm/git 字符串；不支持本地来源、含凭据 URL 或包过滤对象，遇到不支持的来源明确拒绝，不丢失清单条目。
- 主配置不复制凭据、代理、shell 命令、绝对路径；不读取 auth.json。未知字段不进入备份；未来插件需单独审查后扩展白名单，不宣称通用密钥识别。
- 桌面软件生成扩展、外部 skill 软链接、prompts、缓存、会话、信任记录和版本专属热修复不属于本次备份。
- 启动前覆盖受管理字段；设备其他字段（包括凭据）及文件保留。备份中删除的受管理字段在目标同步清除，不卸载设备上多余的包或删除本地扩展。
- 使用 pi 自身的启动安装机制恢复缺失插件，不另写安装器，不在每次 launch 强制升级已装插件。沿用原始未固定版本的来源，不保证跨设备版本完全一致。
- 启动保持用户当前目录，转发 pi 参数与退出码；不绕过项目授权提示。pi、Node/npm、Git 由设备预先安装，账号登录由用户完成。离线行为由 pi 自身控制。
- 拒绝对软链接或非普通文件读写，校验所有目标后再发布；逐文件原子替换，不承诺多文件事务或并发编辑保护。失败输出错误，可修复后重跑；不吞掉 pi 失败。

## 验收

1. 本机生成的备份仅包含白名单配置和完整的 14 个包来源。
2. 临时 HOME 中验证备份更新覆盖、凭据排除、输入校验、软链接拒绝、错误反馈。
3. 临时 HOME 中验证 launch 覆盖受管字段、保留凭据、保持 cwd、参数转发、退出码；验证缺少 pi 和无效备份不写配置。
4. 现有 unittest 通过，新增测试通过，打包安装后从非仓库目录运行可读取内置备份。
5. 文档记录原生安装语义与尚未实测的联网/交互行为，不使用本机真实配置做破坏性验收。
