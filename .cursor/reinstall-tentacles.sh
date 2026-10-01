#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cloud-shell-lib.sh"
cloud_lib_init "reinstall-tentacles.sh"
# shellcheck disable=SC1091
[[ -f "${REPO_ROOT}/.cursor/env.sh" ]] || die "INIT" "run cloud-install.sh first"
source "${REPO_ROOT}/.cursor/env.sh"
cloud_tentacles_pack_and_install
if [[ "${CLOUD_PROFILE}" == "ui-node-web" ]]; then
    cloud_node_web_interface_build
fi
echo "OCTOBOT_CLOUD_INSTALL_OK profile=${CLOUD_PROFILE} script=reinstall-tentacles"
