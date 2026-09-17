#!/usr/bin/env bash
# Demo agent-seed orchestration: sync seed, optional node start, HTTP bootstrap.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/env.sh"
set -a
source "${SCRIPT_DIR}/agent-seed.env"
set +a

export OCTOBOT_AGENT_SEED_USER_FOLDER="${REPO_ROOT}/${OCTOBOT_AGENT_SEED_USER_FOLDER}"
export NODE_SQLITE_FILE="${REPO_ROOT}/${NODE_SQLITE_FILE}"

run_seed() {
  local clear_flag=()
  if [[ "${1:-}" == "--clear" ]]; then
    clear_flag=(--clear)
  fi
  python -m tools.agent_seed seed --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}" "${clear_flag[@]}"
}

run_bootstrap() {
  python -m tools.agent_seed bootstrap --base-url "${AGENT_SEED_BASE_URL:-http://127.0.0.1:8000}"
}

run_start() {
  export EXIT_BEFORE_TENTACLES_AUTO_REINSTALL=true
  python start.py --master --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}"
}

case "${1:-}" in
  seed)
    run_seed "${2:-}"
    ;;
  bootstrap)
    run_bootstrap
    ;;
  start)
    run_start
    ;;
  --full)
    run_seed
    run_start &
    run_bootstrap
    ;;
  --clear)
    run_seed --clear
    ;;
  *)
    echo "Usage: $0 {seed [--clear]|bootstrap|start|--full|--clear}" >&2
    exit 1
    ;;
esac
