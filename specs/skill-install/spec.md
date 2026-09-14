# 安装指南命令

本规格记录模型驱动的 skill 安装入口及其与归集的边界。
用户执行 install 时，命令只提供指南和本机路径，由当前模型继续操作。
实现不启动 agent、不安装内容、不修改配置；用户自行 collect 后再 select。

## 已确认行为

- `bang skill install` 无目录参数，复用现有配置读取与路径验证；未配置时沿用默认 source/library。
- stdout 输出完整安装 skill 以及 source、library、内置个人资源绝对路径。无需交互、网络、Git 仓库或额外运行时依赖。
- 模型从指南展示 lark、mattpocock、个人，以及独立条目，不使用“其它”分类。尊重各渠道的整包/单项安装粒度。
- 模型确认清单后安装到 source；覆盖前确认并备份，工具依赖安装单独确认，登录授权由用户完成。模型不代为 collect/select。
- 个人 chinese-writing-coach 和定制 personal-to-spec 随安装包分发；目录、frontmatter 和展示名称一致，不依赖原机器路径。Matt to-spec 保持原名。
- 对来源待确认的 writing-great-skills 显式说明、展示但不猜测安装命令；提供可信来源后才安装。

## 清单与来源证据

完整名称清单与渠道以 `bang_skills/install/SKILL.md` 为准。扫描识别 59 个一级 skill，另有嵌套 show-me；其中 to-spec 的来源记录指向 Matt，但用户确认本地内容是个人定制版，因此分发为独立名称。

- 全局 `.skill-lock.json`：27 个 lark well-known 来源、25 个 Matt GitHub 来源、faster-chrome-devtools-skill、find-skills。
- 个人库 skills-lock.json：show-me 来自 humanlayer/skills，目录 plugins/show-me/skills/show-me。
- visual-plan、visual-recap 的 agent-native-skill.json：各自 `npx @agent-native/core@latest skills add <name>`。
- 飞书官方索引 `https://open.feishu.cn/.well-known/skills/index.json`：实际获取成功，包含逐项 files，支持完整下载。
- Matt 官方 README：实际获取成功，区分整包插件与允许单项选择的 Skills CLI；采用文件渠道以供归集。
- npm `@lark-base-open/base-site-cli` 0.3.9：实际读取 registry 元数据和 tarball，README 有 skill install，包中存在完整 skills/base-site-building/。没有执行 npm 安装器。
- writing-great-skills：本地无安装来源记录，Matt 当前 README 无该名称；历史 GitHub API 查询被 403 限流，不能推断历史归属或当前可安装性。

## 验收

- 默认/自定义配置下命令成功且 HOME 内容与目录状态不变；无配置时不创建配置或入口。
- 损坏配置显式报错，不输出误导性的默认上下文。
- 输出包含完整指南，可定位随包的两个个人 skill 及 agents 元数据。
- wheel 包中资源完整；在临时环境安装 wheel 并从仓库之外运行命令，资源仍可读取。
- 现有 collect/select/init 测试继续通过。

## 范围之外

模型调用集成、自动安装器、自动归集/选择、真实本机 skill 安装与全局环境变更。模型实际执行上游安装受网络、工具版本和用户授权影响，CLI 测试不代表这些动作已执行成功。
