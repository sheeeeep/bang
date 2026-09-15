# 配置本机目录

用户填写个人库和全局入口的路径，确认预览后保存配置。bang 只保存路径，不迁移或创建 skill 目录。

## Sub-features

- `config-interactive`：无参数提问，回车保留值。
- `config-flags`：显式指定 library/source。
- `config-cancel`：拒绝保存保持原配置。
- `config-invalid`：拒绝相同、相互包含或相对路径；管理目录及其祖先也不能是软链接。

## How to get to it (user POV)

运行 `bang init`，或 `bang init --library '~/my-skills' --source '~/.agents/skills'`。两种方式都可在任意目录运行，配置均保存在 `~/.config/bang/config.json`。

## Driving it with CLI pipes

Preconditions: 按 Launch 准备新的独立 bash 环境，临时 HOME 中尚无 `.config/bang/config.json`。

- **通过参数指定路径并保存。** 运行下方命令，检查配置 JSON 中的路径是否正确，并确认个人库和全局入口目录尚未创建。

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

- **非法路径。** 执行 `python3 -B "$REPO/bang.py" init --library relative --source '~/incoming'`，预期退出 1，显示绝对路径错误且配置逐字节不变。相同目录、相互包含的目录、祖先为软链接的目录，要分别在新环境中验证并记录结果。不能只验证一种非法路径，就判定所有路径校验都通过。

## Gotchas

- 用单引号保留 `~/`，交给 bang 展开，避免 shell 提前将其替换成错误的 HOME 路径。
- 修改配置不会迁移旧项目链接；不能用配置保存成功证明链接已更新。
- 非法路径在确认前报错，不能继续发送 y。
