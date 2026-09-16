#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cloud-shell-lib.sh"
cloud_lib_init "cloud-install.sh"

echo "OCTOBOT_CLOUD_PROFILE=${CLOUD_PROFILE}"
log_step "INIT" "repo=${REPO_ROOT}"

if cloud_profile_includes_layer "L1"; then
    log_step "L1" "Toolchain (Pants, optional Rust)"
    if ! command -v pants >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 -fsSL https://static.pantsbuild.org/setup/get-pants.sh | bash
    fi
    export PATH="${HOME}/.local/bin:${PATH}"
    if compgen -G "packages/*/crates/*/Cargo.toml" >/dev/null 2>&1; then
        if ! command -v cargo >/dev/null 2>&1; then
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
            # shellcheck disable=SC1091
            source "${HOME}/.cargo/env"
        fi
    fi
fi

if cloud_profile_includes_layer "L2"; then
    log_step "L2" "Pants package OctoBot wheel"
    export PATH="${HOME}/.local/bin:${PATH}"
    pants package :OctoBot $(pants list --filter-target-type=package_shell_command ::)
fi

if cloud_profile_includes_layer "L3"; then
    log_step "L3" "Python venv and OctoBot wheel"
    python3 -m venv "${REPO_ROOT}/.cursor/venv"
    cloud_write_env_files
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.cursor/env.sh"
    pip install --upgrade pip setuptools wheel
    pip install -r dev_requirements.txt
    pip install dist/*.whl
    if compgen -G "packages/*/crates/*/Cargo.toml" >/dev/null 2>&1; then
        pip install maturin
    fi
fi

if cloud_profile_includes_layer "L4"; then
    cloud_npm_client_build
fi

if cloud_profile_includes_layer "L5"; then
    cloud_tentacles_pack_and_install
fi

if [[ "${CLOUD_PROFILE}" == "ui-node-web" ]]; then
    cloud_node_web_interface_build
fi

echo "OCTOBOT_CLOUD_INSTALL_OK profile=${CLOUD_PROFILE}"
