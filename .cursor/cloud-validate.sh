#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cloud-shell-lib.sh"
cloud_lib_init "cloud-validate.sh"

EMIT_JSON=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile) CLOUD_PROFILE="$2"; shift 2 ;;
        --json) EMIT_JSON=1; shift ;;
        *) die "ARGS" "unknown argument $1" ;;
    esac
done

VALIDATE_STEPS=()
VALIDATE_OK=1
VALIDATE_FAILED_STEP=""
VALIDATE_MESSAGE=""

validate_record() {
    local name="$1"
    local ok="$2"
    local detail="$3"
    VALIDATE_STEPS+=("${name}|${ok}|${detail}")
    if [[ "${ok}" != "1" ]]; then
        VALIDATE_OK=0
        VALIDATE_FAILED_STEP="${name}"
        VALIDATE_MESSAGE="${detail}"
        return 1
    fi
    return 0
}

validate_emit_json() {
    export VALIDATE_OK="${VALIDATE_OK}"
    export VALIDATE_FAILED_STEP="${VALIDATE_FAILED_STEP}"
    export VALIDATE_MESSAGE="${VALIDATE_MESSAGE}"
    export CLOUD_PROFILE="${CLOUD_PROFILE}"
    export VALIDATE_STEP_LINES
    VALIDATE_STEP_LINES="$(printf '%s\n' "${VALIDATE_STEPS[@]}")"
    python3 - <<'PY'
import json
import os

steps = []
for entry in os.environ.get("VALIDATE_STEP_LINES", "").split("\n"):
    if not entry.strip():
        continue
    name, ok, detail = entry.split("|", 2)
    steps.append({"name": name, "ok": ok == "1", "detail": detail})

failed = os.environ.get("VALIDATE_FAILED_STEP") or None
message = os.environ.get("VALIDATE_MESSAGE") or None
if failed == "":
    failed = None
if message == "":
    message = None

payload = {
    "ok": os.environ.get("VALIDATE_OK") == "1",
    "profile": os.environ.get("CLOUD_PROFILE"),
    "failed_step": failed,
    "message": message,
    "steps": steps,
}
print(json.dumps(payload, indent=2))
PY
}

validate_finish() {
    if [[ "${EMIT_JSON}" == "1" ]]; then
        validate_emit_json | tee "${REPO_ROOT}/cloud-validate.json"
    fi
    if [[ "${VALIDATE_OK}" != "1" ]]; then
        die "${VALIDATE_FAILED_STEP}" "${VALIDATE_MESSAGE}"
    fi
    exit 0
}

[[ -f "${REPO_ROOT}/.cursor/env.sh" ]] || die "VALIDATE_ENV" "missing .cursor/env.sh — run cloud-install.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/.cursor/env.sh"

log_step "VALIDATE_PYTHON_VERSION" "python 3.13.x"
pyver="$(python --version 2>&1)" || die "VALIDATE_PYTHON_VERSION" "python not runnable"
if [[ "${pyver}" != *"3.13"* ]]; then
    validate_record "VALIDATE_PYTHON_VERSION" 0 "${pyver}" || validate_finish
fi
validate_record "VALIDATE_PYTHON_VERSION" 1 "ok" || validate_finish

log_step "VALIDATE_OCTOBOT_CLI" "OctoBot on PATH"
if ! OctoBot --version >/dev/null; then
    validate_record "VALIDATE_OCTOBOT_CLI" 0 "OctoBot CLI failed" || validate_finish
fi
validate_record "VALIDATE_OCTOBOT_CLI" 1 "ok" || validate_finish

log_step "VALIDATE_IMPORT_OCTOBOT" "import octobot"
if ! python -c "import octobot"; then
    validate_record "VALIDATE_IMPORT_OCTOBOT" 0 "import failed" || validate_finish
fi
validate_record "VALIDATE_IMPORT_OCTOBOT" 1 "ok" || validate_finish

needs_tentacles=false
[[ "${CLOUD_PROFILE}" != "package-only" ]] && needs_tentacles=true

if [[ "${needs_tentacles}" == "true" ]]; then
    log_step "VALIDATE_TENTACLES_DIR" "repo-root tentacles/"
    if [[ ! -d tentacles ]] || [[ -z "$(ls -A tentacles 2>/dev/null)" ]]; then
        validate_record "VALIDATE_TENTACLES_DIR" 0 "missing or empty" || validate_finish
    fi
    validate_record "VALIDATE_TENTACLES_DIR" 1 "ok" || validate_finish

    log_step "VALIDATE_IMPORT_TENTACLES" "import tentacles"
    if ! python -c "import tentacles"; then
        validate_record "VALIDATE_IMPORT_TENTACLES" 0 "import failed" || validate_finish
    fi
    validate_record "VALIDATE_IMPORT_TENTACLES" 1 "ok" || validate_finish

    client_dist="packages/client/octobot_client_ts/dist/index.js"
    log_step "VALIDATE_CLIENT_BUILD" "${client_dist}"
    if [[ ! -f "${client_dist}" ]]; then
        validate_record "VALIDATE_CLIENT_BUILD" 0 "missing" || validate_finish
    fi
    validate_record "VALIDATE_CLIENT_BUILD" 1 "ok" || validate_finish
fi

log_step "VALIDATE_SENTINEL_OCTOBOT" "pytest collect-only"
if ! pytest --collect-only tests/unit_tests/test_octobot_version.py >/dev/null; then
    validate_record "VALIDATE_SENTINEL_OCTOBOT" 0 "collect failed" || validate_finish
fi
validate_record "VALIDATE_SENTINEL_OCTOBOT" 1 "ok" || validate_finish

log_step "VALIDATE_SENTINEL_COMMONS" "pytest collect-only"
if ! (cd packages/commons && pytest --collect-only tests/test_copy_util.py >/dev/null); then
    validate_record "VALIDATE_SENTINEL_COMMONS" 0 "collect failed" || validate_finish
fi
validate_record "VALIDATE_SENTINEL_COMMONS" 1 "ok" || validate_finish

if [[ "${needs_tentacles}" == "true" ]]; then
    log_step "VALIDATE_SENTINEL_FLOW_COLLECT" "pytest collect-only with PYTHONPATH"
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.cursor/pythonpath.sh"
    if ! pytest --collect-only packages/flow/tests/protocol/test_wire_compat.py >/dev/null; then
        validate_record "VALIDATE_SENTINEL_FLOW_COLLECT" 0 "collect failed" || validate_finish
    fi
    validate_record "VALIDATE_SENTINEL_FLOW_COLLECT" 1 "ok" || validate_finish
fi

if [[ "${CLOUD_PROFILE}" == "ui-node-web" ]]; then
    ui_dist="packages/tentacles/Services/Interfaces/node_web_interface/dist"
    log_step "VALIDATE_UI_BUILD" "${ui_dist}"
    if [[ ! -d "${ui_dist}" ]]; then
        validate_record "VALIDATE_UI_BUILD" 0 "missing" || validate_finish
    fi
    validate_record "VALIDATE_UI_BUILD" 1 "ok" || validate_finish
fi

validate_finish
