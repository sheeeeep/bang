# 配置本机目录

用户选择个人库和全局入口路径，预览后保存配置；配置操作不迁移或创建 skill 目录。

## Sub-features

- `config-interactive`：无参数提问，回车保留值。
- `config-flags`：显式指定 library/source。
- `config-cancel`：拒绝保存保持原配置。
- `config-invalid`：相同/嵌套/相对路径或软链接祖先拒绝保存。

## How to get to it (user POV)

运行 `bang init`，或 `bang init --library '~/my-skills' --source '~/.agents/skills'`。两者均在任意当前目录使用 HOME 中的配置。

## Driving it with CLI pipes

Preconditions: Launch 全新隔离 bash，无 `.config/bang/config.json`。

- **参数入口并保存。** 运行下方命令，查看完整 JSON，核对存储路径且管理目录未创建。

```bash
printf 'y\n' | python3 -B "$REPO/bang.py" init --library '~/library' --source '~/incoming'
python3 -B - <<'PY'
import json, os
from pathlib import Path
h = Path(os.environ['HOME'])
assert json.loads((h / '.config/bang/config.json').read_text()) == {'library': '~/library', 'source': '~/incoming'}
assert not (h / 'library').exists() and not (h / 'incoming').exists()
PY
cp "$HOME/.config/bang/config.json" "$EVIDENCE/config-before.json"
# 交互入口：保留当前值，拒绝保存。
printf '\n\nn\n' | python3 -B "$REPO/bang.py" init
cmp "$HOME/.config/bang/config.json" "$EVIDENCE/config-before.json"
# 交互入口：修改两个值并确认。
printf '~/next-library\n~/next-source\ny\n' | python3 -B "$REPO/bang.py" init
python3 -B - <<'PY'
import json, os
from pathlib import Path
h = Path(os.environ['HOME'])
assert json.loads((h / '.config/bang/config.json').read_text()) == {'library': '~/next-library', 'source': '~/next-source'}
assert not (h / 'next-library').exists() and not (h / 'next-source').exists()
PY
cp "$HOME/.config/bang/config.json" "$EVIDENCE/config-after.json"
echo 'config-flags config-interactive config-cancel rc=0'
```

- **非法路径。** 执行 `python3 -B "$REPO/bang.py" init --library relative --source '~/incoming'`，预期退出 1，显示绝对路径错误且配置逐字节不变。相同目录、嵌套目录、管理目录祖先软链接分别用新基线重跑并记录，不把一个错误代替全部边界。

## Gotchas

- 引号保留 `~/` 给应用处理；不要让真实 shell HOME 意外展开。
- 修改配置不会迁移旧项目链接；不能用配置保存成功证明链接已更新。
- 非法路径在确认前报错，不能继续发送 y。
