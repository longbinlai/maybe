#!/bin/bash
# 周度复盘定时任务包装脚本。
#
# 由 launchd (com.maybe.weekly-review) 每周触发。launchd 不会加载用户 shell
# 配置，因此这里显式从仓库根目录的 .env 载入 MAYBE_API_KEY / MAYBE_URL /
# OLLAMA_HOST 等，再调用 `memory review --weekly`。
#
# 额外参数会透传给 memory review（例如手动测试时加 --dry-run）。
set -uo pipefail

# 定位仓库根目录（脚本在 tools/openclaw-skills/finance-memory/scripts/ 下，向上 4 层）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# 载入运行时环境（密钥不写在本脚本里，从未入库的 .env 读取）
if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_ROOT/.env"
  set +a
else
  echo "Warning: $REPO_ROOT/.env not found; relying on existing environment" >&2
fi

MEMORY_BIN="${MEMORY_BIN:-$HOME/pyenv/maybe/bin/memory}"
if [ ! -x "$MEMORY_BIN" ]; then
  echo "Error: memory CLI not found at $MEMORY_BIN" >&2
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] running weekly review..."
exec "$MEMORY_BIN" review --weekly "$@"
