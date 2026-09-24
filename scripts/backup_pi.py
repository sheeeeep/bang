"""把本机 pi 的可移植插件配置保存到 bang 工程。
通过 python3 手动运行，读取 pi 与插件实际使用的用户配置路径。
复用 bang 的白名单校验，原子覆盖工程内快照，不导出认证文件。
更新快照后重新安装 bang，已安装命令才会使用新备份。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bang import backup_pi

if __name__ == "__main__":
    try:
        backup_pi(ROOT / "bang_pi/config.json")
    except (OSError, ValueError, TypeError) as error:
        print(f"备份失败: {error}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\n已取消备份。", file=sys.stderr)
        raise SystemExit(130)
