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
export SCHEDULER_SQLITE_FILE="${NODE_SQLITE_FILE}"

AGENT_SEED_BASE_URL="${AGENT_SEED_BASE_URL:-http://127.0.0.1:8000}"
NODE_LOG_FILE="${OCTOBOT_AGENT_SEED_USER_FOLDER}/agent-seed-node.log"
NODE_PID_FILE="${OCTOBOT_AGENT_SEED_USER_FOLDER}/.agent-seed-node.pid"

run_seed() {
  local clear_flag=()
  if [[ "${1:-}" == "--clear" ]]; then
    clear_flag=(--clear)
  fi
  python -m tools.agent_seed seed --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}" "${clear_flag[@]}"
}

run_bootstrap() {
  python -m tools.agent_seed bootstrap --base-url "${AGENT_SEED_BASE_URL}" "$@"
}

run_prepare_node_start() {
  python -m tools.agent_seed prepare-node-start \
    --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}" \
    --base-url "${AGENT_SEED_BASE_URL}"
}

run_stop_node() {
  python -m tools.agent_seed stop-node \
    --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}" \
    --base-url "${AGENT_SEED_BASE_URL}"
}

run_start() {
  export EXIT_BEFORE_TENTACLES_AUTO_REINSTALL=true
  python start.py --master --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}"
}

run_start_background() {
  run_prepare_node_start
  mkdir -p "${OCTOBOT_AGENT_SEED_USER_FOLDER}"
  export EXIT_BEFORE_TENTACLES_AUTO_REINSTALL=true
  # Redirect all node I/O to a log file so callers with captured stdout/stderr are not blocked.
  setsid python start.py --master --user-folder "${OCTOBOT_AGENT_SEED_USER_FOLDER}" \
    </dev/null >>"${NODE_LOG_FILE}" 2>&1 &
  local node_pid=$!
  echo "${node_pid}" >"${NODE_PID_FILE}"
  echo "Agent-seed node started in background (pid ${node_pid})."
  echo "Node log: ${NODE_LOG_FILE}"
}

wait_for_node_ready() {
  python -m tools.agent_seed wait-for-base-url --base-url "${AGENT_SEED_BASE_URL}"
}

case "${1:-}" in
  seed)
    run_seed "${2:-}"
    ;;
  bootstrap)
    shift
    run_bootstrap "$@"
    ;;
  start)
    run_start
    ;;
  --stop)
    run_stop_node
    ;;
  --full)
    run_seed
    run_start_background
    wait_for_node_ready
    run_bootstrap
    ;;
  --clear)
    run_seed --clear
    ;;
  *)
    echo "Usage: $0 {seed [--clear]|bootstrap [--scenario grid|index|completed|lifecycle|all]|start|--full|--clear|--stop}" >&2
    exit 1
    ;;
esac
