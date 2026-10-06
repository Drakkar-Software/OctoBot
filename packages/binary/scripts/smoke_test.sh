#!/usr/bin/env bash
# Smoke test for a CI-built OctoBot binary. Needs only bash, curl, grep and sed (no Python, no repo checkout).
#
# Usage: smoke_test.sh <path-to-binary> [work-dir]
#
# Boots the binary in an empty work dir, checks the HTTP surface and the setup API, creates a throwaway
# wallet, stops it gracefully, restarts it and checks the wallet is still there.
# Exit code is 0 when every check passes, 1 otherwise. See packages/binary/BINARY_TESTING_INSTRUCTIONS.md.
#
# Environment:
#   TENTACLES_URL_TAG     set to "latest" for builds from branch bin_factory (unreleased version), leave unset otherwise
#   SMOKE_TENTACLES_ZIP   local tentacles zip (with its .signature file next to it) to install before the first
#                         start, for machines where the binary cannot reach the tentacles host directly
#   SMOKE_TIMEOUT         seconds to wait for the node to listen (default 180)
#   SMOKE_KEEP            set to 1 to keep the work dir
set -uo pipefail

BINARY="${1:-}"
if [[ -z "${BINARY}" || ! -x "${BINARY}" ]]; then
  echo "Usage: $0 <path-to-executable-binary> [work-dir]" >&2
  exit 2
fi
BINARY="$(cd "$(dirname "${BINARY}")" && pwd)/$(basename "${BINARY}")"

BASE_URL="http://127.0.0.1:8000"
SMOKE_TIMEOUT="${SMOKE_TIMEOUT:-180}"
PASSPHRASE="smoke-test-passphrase"
KNOWN_ERROR_PATTERN="Error when checking ssl certificates"
STOP_TIMEOUT=30

USER_WORK_DIR="${2:-}"
WORK_DIR="${USER_WORK_DIR:-$(mktemp -d -t octobot-smoke.XXXXXX)}"
mkdir -p "${WORK_DIR}"
WORK_DIR="$(cd "${WORK_DIR}" && pwd)"
BODY_FILE="${WORK_DIR}/.smoke_body"
PID=""
FAILED=0
PASSED=0

pass() { PASSED=$((PASSED + 1)); echo "  ok    $1"; }
fail() { FAILED=$((FAILED + 1)); echo "  FAIL  $1"; }

# Args: description, expected, actual
expect_equal() {
  if [[ "$2" == "$3" ]]; then pass "$1"; else fail "$1 (expected '$2', got '$3')"; fi
}

# Args: description, pattern (grep -E), file
expect_body_matches() {
  if grep -Eiq "$2" "$3"; then pass "$1"; else fail "$1 (pattern '$2' not found in: $(head -c 200 "$3"))"; fi
}

# Prints the HTTP status. Response body goes to BODY_FILE. Extra curl args follow the url.
http() {
  local url="$1"
  shift
  local code
  code="$(curl -sS --noproxy '*' -m 15 -o "${BODY_FILE}" -w '%{http_code}' "$@" "${url}" 2>/dev/null)" || true
  echo "${code:-000}"
}

start_node() {
  (cd "${WORK_DIR}" && exec "${BINARY}" >>"${WORK_DIR}/octobot.log" 2>&1) &
  PID=$!
}

wait_ready() {
  local waited=0
  while (( waited < SMOKE_TIMEOUT )); do
    if ! kill -0 "${PID}" 2>/dev/null; then return 1; fi
    if [[ "$(http "${BASE_URL}/app")" == "200" ]]; then return 0; fi
    sleep 2
    waited=$((waited + 2))
  done
  return 1
}

# Interrupt by PID (never pkill -f: that pattern also matches the shell running this script).
stop_node() {
  [[ -n "${PID}" ]] || return 0
  kill -INT "${PID}" 2>/dev/null || true
  local waited=0
  while kill -0 "${PID}" 2>/dev/null && (( waited < STOP_TIMEOUT )); do
    sleep 1
    waited=$((waited + 1))
  done
  if kill -0 "${PID}" 2>/dev/null; then
    kill -KILL "${PID}" 2>/dev/null || true
    PID=""
    return 1
  fi
  wait "${PID}" 2>/dev/null || true
  PID=""
  return 0
}

cleanup() {
  stop_node >/dev/null 2>&1 || true
  if [[ "${SMOKE_KEEP:-0}" != "1" && -z "${USER_WORK_DIR}" ]]; then rm -rf "${WORK_DIR}"; fi
}
trap 'cleanup' EXIT

echo "OctoBot binary smoke test"
echo "  binary:   ${BINARY}"
echo "  work dir: ${WORK_DIR}"
echo "  tentacles tag: ${TENTACLES_URL_TAG:-<default: binary version>}"

if [[ "$(http "${BASE_URL}/app")" != "000" ]]; then
  echo "Something already answers on ${BASE_URL}. Stop it first." >&2
  exit 2
fi

echo "1. Version"
version_output="$("${BINARY}" --version 2>/dev/null | tail -1)"
if [[ -n "${version_output}" ]]; then pass "--version prints '${version_output}'"; else fail "--version printed nothing"; fi

if [[ -n "${SMOKE_TENTACLES_ZIP:-}" ]]; then
  echo "2. Install tentacles from ${SMOKE_TENTACLES_ZIP}"
  if (cd "${WORK_DIR}" && "${BINARY}" tentacles --install --all --force --location "${SMOKE_TENTACLES_ZIP}" >"${WORK_DIR}/tentacles_install.log" 2>&1); then
    pass "tentacles installed from local package"
  else
    fail "tentacles install failed (see ${WORK_DIR}/tentacles_install.log)"
  fi
fi

echo "3. First start"
start_node
if wait_ready; then
  pass "node listens on ${BASE_URL}"
else
  fail "node did not become ready within ${SMOKE_TIMEOUT}s (or exited)"
  echo "---- last log lines ----"
  tail -20 "${WORK_DIR}/octobot.log" | sed 's/\x1b\[[0-9;]*m//g'
  echo "Result: ${PASSED} passed, ${FAILED} failed"
  SMOKE_KEEP=1
  exit 1
fi

echo "4. HTTP surface"
expect_equal "GET / redirects" "307" "$(http "${BASE_URL}/")"
code="$(http "${BASE_URL}/app")"
expect_equal "GET /app" "200" "${code}"
expect_body_matches "/app is the Node UI" "<title>OctoBot Node</title>" "${BODY_FILE}"
assets="$(grep -Eo '/app/assets/[^"]+\.(js|css)' "${BODY_FILE}" | sort -u)"
if [[ -z "${assets}" ]]; then fail "no js/css assets referenced by /app"; fi
for asset in ${assets}; do
  expect_equal "GET ${asset}" "200" "$(http "${BASE_URL}${asset}")"
done
expect_equal "GET /api/v1/openapi.json" "200" "$(http "${BASE_URL}/api/v1/openapi.json")"
expect_equal "GET /docs" "200" "$(http "${BASE_URL}/docs")"

echo "5. Setup API on a fresh node"
expect_equal "GET /api/v1/setup/status" "200" "$(http "${BASE_URL}/api/v1/setup/status")"
expect_body_matches "node is not configured yet" '"configured": ?false' "${BODY_FILE}"
expect_equal "GET /api/v1/wallets/" "200" "$(http "${BASE_URL}/api/v1/wallets/")"
expect_body_matches "no wallet yet" '^\[\]$' "${BODY_FILE}"
expect_equal "GET /api/v1/nodes/config before setup" "503" "$(http "${BASE_URL}/api/v1/nodes/config")"
expect_body_matches "typed not-configured error" "auth_node_not_configured" "${BODY_FILE}"

echo "6. Create a throwaway wallet"
code="$(http "${BASE_URL}/api/v1/setup/init" -X POST -H 'Content-Type: application/json' \
  -d "{\"passphrase\":\"${PASSPHRASE}\",\"node_type\":\"standalone\"}")"
expect_equal "POST /api/v1/setup/init" "200" "${code}"
address="$(grep -Eo '0x[0-9a-fA-F]{40}' "${BODY_FILE}" | head -1)"
if [[ -n "${address}" ]]; then pass "wallet address returned (${address})"; else fail "no wallet address in the setup response"; fi
http "${BASE_URL}/api/v1/setup/status" >/dev/null
expect_body_matches "node is configured" '"configured": ?true' "${BODY_FILE}"
http "${BASE_URL}/api/v1/wallets/" >/dev/null
expect_body_matches "wallet is listed" "${address:-0xMISSING}" "${BODY_FILE}"

echo "7. Debug API"
expect_equal "GET /api/v1/debug/ without credentials" "401" "$(http "${BASE_URL}/api/v1/debug/")"
code="$(http "${BASE_URL}/api/v1/debug/" -u "${address}:${PASSPHRASE}")"
expect_equal "GET /api/v1/debug/ with the wallet passphrase" "200" "${code}"
expect_body_matches "debug state has automations" '"automations"' "${BODY_FILE}"

echo "8. Log"
clean_log="$(sed 's/\x1b\[[0-9;]*m//g' "${WORK_DIR}/octobot.log")"
if grep -q "Traceback" <<<"${clean_log}"; then fail "Traceback in the log"; else pass "no Traceback in the log"; fi
unexpected_errors="$(grep -E ' ERROR ' <<<"${clean_log}" | grep -v "${KNOWN_ERROR_PATTERN}" || true)"
if [[ -z "${unexpected_errors}" ]]; then
  pass "no ERROR lines besides the known ssl pre-check"
else
  fail "unexpected ERROR lines:"
  echo "${unexpected_errors}" | cut -c1-220 | head -5
fi

echo "9. Graceful stop"
if stop_node; then pass "stopped within ${STOP_TIMEOUT}s"; else fail "did not stop within ${STOP_TIMEOUT}s, killed"; fi

echo "10. Restart without TENTACLES_URL_TAG"
unset TENTACLES_URL_TAG
start_node
if wait_ready; then
  pass "node listens again"
  http "${BASE_URL}/api/v1/wallets/" >/dev/null
  expect_body_matches "wallet survived the restart" "${address:-0xMISSING}" "${BODY_FILE}"
else
  fail "node did not come back after restart"
fi
stop_node >/dev/null 2>&1 || true

echo
echo "Result: ${PASSED} passed, ${FAILED} failed"
if (( FAILED > 0 )); then
  echo "Work dir kept for inspection: ${WORK_DIR}"
  SMOKE_KEEP=1
  exit 1
fi
exit 0
