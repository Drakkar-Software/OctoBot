#!/bin/sh
set -e

REPO="Drakkar-Software/OctoBot"
BINARY="octobot-launcher"
DEFAULT_INSTALL_DIR="$HOME/.local/bin"

main() {
    # Parse flags
    INSTALL_SERVICE=0
    for arg in "$@"; do
        case "$arg" in
            --service) INSTALL_SERVICE=1 ;;
            --help|-h)
                echo "Usage: install.sh [--service]"
                echo "  --service   Also run 'octobot-launcher service install --user' after installing"
                echo "Env vars:"
                echo "  OCTOBOT_LAUNCHER_VERSION     Pin a specific version (e.g. 0.1.0)"
                echo "  OCTOBOT_LAUNCHER_INSTALL_DIR Override install directory"
                exit 0
                ;;
        esac
    done

    INSTALL_DIR="${OCTOBOT_LAUNCHER_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

    # Detect OS
    OS="$(uname -s)"
    case "$OS" in
        Darwin) OS_NAME="darwin" ;;
        Linux)  OS_NAME="linux"  ;;
        *)
            echo "error: unsupported OS: $OS" >&2
            exit 1
            ;;
    esac

    # Detect architecture
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64|amd64)  ARCH_NAME="x86_64"  ;;
        arm64|aarch64) ARCH_NAME="aarch64" ;;
        *)
            echo "error: unsupported architecture: $ARCH" >&2
            exit 1
            ;;
    esac

    # Map to Rust target triple
    case "${OS_NAME}-${ARCH_NAME}" in
        darwin-aarch64) TRIPLE="aarch64-apple-darwin"     ;;
        darwin-x86_64)  TRIPLE="x86_64-apple-darwin"      ;;
        linux-x86_64)   TRIPLE="x86_64-unknown-linux-gnu"  ;;
        linux-aarch64)  TRIPLE="aarch64-unknown-linux-gnu" ;;
        *)
            echo "error: no prebuilt binary for ${OS_NAME}-${ARCH_NAME}" >&2
            exit 1
            ;;
    esac

    # Resolve version
    if [ -n "$OCTOBOT_LAUNCHER_VERSION" ]; then
        VERSION="$OCTOBOT_LAUNCHER_VERSION"
    else
        echo "Fetching latest launcher release..."
        # Find the most recent tag that starts with launcher-v
        RELEASES_JSON="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases")"
        VERSION="$(printf '%s' "$RELEASES_JSON" \
            | grep '"tag_name"' \
            | grep '"launcher-v' \
            | head -1 \
            | sed 's/.*"launcher-v\([^"]*\)".*/\1/')"
        if [ -z "$VERSION" ]; then
            echo "error: could not determine latest launcher release" >&2
            exit 1
        fi
    fi

    ARCHIVE="${BINARY}-${VERSION}-${TRIPLE}.tar.gz"
    BASE_URL="https://github.com/${REPO}/releases/download/launcher-v${VERSION}"
    TMPDIR="$(mktemp -d)"
    trap 'rm -rf "$TMPDIR"' EXIT

    echo "Installing octobot-launcher v${VERSION} (${TRIPLE})..."

    # Download
    curl -fL --progress-bar \
        "${BASE_URL}/${ARCHIVE}"        -o "${TMPDIR}/${ARCHIVE}"
    curl -fsSL \
        "${BASE_URL}/${ARCHIVE}.sha256" -o "${TMPDIR}/${ARCHIVE}.sha256"

    # Verify checksum
    EXPECTED="$(awk '{print $1}' "${TMPDIR}/${ARCHIVE}.sha256")"
    if command -v shasum >/dev/null 2>&1; then
        ACTUAL="$(shasum -a 256 "${TMPDIR}/${ARCHIVE}" | awk '{print $1}')"
    elif command -v sha256sum >/dev/null 2>&1; then
        ACTUAL="$(sha256sum "${TMPDIR}/${ARCHIVE}" | awk '{print $1}')"
    else
        echo "warning: neither shasum nor sha256sum found; skipping checksum verification" >&2
        ACTUAL="$EXPECTED"
    fi
    if [ "$ACTUAL" != "$EXPECTED" ]; then
        echo "error: checksum mismatch" >&2
        echo "  expected: $EXPECTED" >&2
        echo "  actual:   $ACTUAL"   >&2
        exit 1
    fi

    # Extract
    tar -xzf "${TMPDIR}/${ARCHIVE}" -C "$TMPDIR"

    # Install
    mkdir -p "$INSTALL_DIR"
    mv "${TMPDIR}/${BINARY}" "${INSTALL_DIR}/${BINARY}"
    chmod +x "${INSTALL_DIR}/${BINARY}"

    echo ""
    echo "Installed: ${INSTALL_DIR}/${BINARY}"
    echo ""

    # PATH hint
    case ":${PATH}:" in
        *":${INSTALL_DIR}:"*) ;;
        *)
            echo "  ${INSTALL_DIR} is not on your PATH."
            echo "  Add it with one of:"
            echo "    fish:  fish_add_path ${INSTALL_DIR}"
            echo "    bash:  echo 'export PATH=\"\$PATH:${INSTALL_DIR}\"' >> ~/.bashrc"
            echo "    zsh:   echo 'export PATH=\"\$PATH:${INSTALL_DIR}\"' >> ~/.zshrc"
            echo ""
            ;;
    esac

    # Service install
    if [ "$INSTALL_SERVICE" -eq 1 ]; then
        "${INSTALL_DIR}/${BINARY}" service install --user
        echo "Service installed. Start it with:"
        echo "  octobot-launcher service start"
    else
        echo "Next steps:"
        echo "  octobot-launcher service install --user"
        echo "  octobot-launcher service start"
    fi
}

main "$@"
