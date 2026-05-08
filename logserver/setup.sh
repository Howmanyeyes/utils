#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-logserver}"
SERVICE_USER="${SERVICE_USER:-logserver}"
SERVICE_GROUP="${SERVICE_GROUP:-$SERVICE_USER}"
INSTALL_DIR="${INSTALL_DIR:-/opt/logserver}"
CONFIG_DIR="${CONFIG_DIR:-/etc/logserver}"
CONFIG_FILE="${CONFIG_FILE:-$CONFIG_DIR/config.yaml}"
SOURCE_CONFIG="${SOURCE_CONFIG:-}"
GO_MIN_VERSION="${GO_MIN_VERSION:-1.21}"
GO_VERSION="${GO_VERSION:-1.22.12}"
GO_INSTALL_DIR="${GO_INSTALL_DIR:-/usr/local/go}"
GO_BIN=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

if [[ "$(id -u)" -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

run_as_root() {
    if [[ -n "$SUDO" ]]; then
        sudo "$@"
    else
        "$@"
    fi
}

version_ge() {
    [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n 1)" == "$2" ]]
}

go_arch() {
    case "$(uname -m)" in
        x86_64 | amd64)
            echo "amd64"
            ;;
        aarch64 | arm64)
            echo "arm64"
            ;;
        *)
            echo "Unsupported architecture: $(uname -m)" >&2
            exit 1
            ;;
    esac
}

detect_go() {
    local candidate

    for candidate in "$GO_INSTALL_DIR/bin/go" "$(command -v go || true)"; do
        if [[ -x "$candidate" ]]; then
            local version
            version="$("$candidate" version | awk '{print $3}' | sed 's/^go//')"
            if version_ge "$version" "$GO_MIN_VERSION"; then
                GO_BIN="$candidate"
                echo "Using Go $version from $GO_BIN"
                return 0
            fi
            echo "Found Go $version at $candidate, but $SERVICE_NAME requires Go $GO_MIN_VERSION or newer."
        fi
    done

    return 1
}

install_golang() {
    if detect_go; then
        return
    fi

    local archive
    local download_url
    archive="go${GO_VERSION}.linux-$(go_arch).tar.gz"
    download_url="https://go.dev/dl/$archive"

    echo "Installing Go $GO_VERSION to $GO_INSTALL_DIR..."
    run_as_root apt-get update
    run_as_root apt-get install -y ca-certificates curl tar

    curl -fsSL "$download_url" -o "$BUILD_DIR/$archive"
    run_as_root rm -rf "$GO_INSTALL_DIR"
    run_as_root tar -C "$(dirname "$GO_INSTALL_DIR")" -xzf "$BUILD_DIR/$archive"

    if ! detect_go; then
        echo "Installed Go, but could not find a usable Go $GO_MIN_VERSION+ binary." >&2
        exit 1
    fi
}

create_service_user() {
    if getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
        echo "Group '$SERVICE_GROUP' already exists."
    else
        echo "Creating system group '$SERVICE_GROUP'..."
        run_as_root groupadd --system "$SERVICE_GROUP"
    fi

    if id "$SERVICE_USER" >/dev/null 2>&1; then
        echo "User '$SERVICE_USER' already exists."
        return
    fi

    echo "Creating system user '$SERVICE_USER'..."
    run_as_root useradd --system --create-home --shell /usr/sbin/nologin --gid "$SERVICE_GROUP" "$SERVICE_USER"
}

prepare_config() {
    run_as_root install -d -m 0750 -o root -g "$SERVICE_GROUP" "$CONFIG_DIR"

    if [[ -n "$SOURCE_CONFIG" ]]; then
        if [[ ! -f "$SOURCE_CONFIG" ]]; then
            echo "SOURCE_CONFIG does not exist: $SOURCE_CONFIG" >&2
            exit 1
        fi
        echo "Installing config from $SOURCE_CONFIG..."
        run_as_root install -m 0640 -o root -g "$SERVICE_GROUP" "$SOURCE_CONFIG" "$CONFIG_FILE"
        return
    fi

    if [[ -f "$CONFIG_FILE" ]]; then
        echo "Existing config found at $CONFIG_FILE. Leaving it unchanged."
        return
    fi

    if [[ -f "$SCRIPT_DIR/config.yaml" ]]; then
        echo "Installing config from $SCRIPT_DIR/config.yaml..."
        run_as_root install -m 0640 -o root -g "$SERVICE_GROUP" "$SCRIPT_DIR/config.yaml" "$CONFIG_FILE"
        return
    fi

    echo "No config found. Starting interactive config generator..."
    (
        cd "$SCRIPT_DIR"
        bash ./create_config.sh
    )

    if [[ ! -f "$SCRIPT_DIR/config.yaml" ]]; then
        echo "Config was not created. Run ./create_config.sh or set SOURCE_CONFIG=/path/config.yaml and retry." >&2
        exit 1
    fi

    run_as_root install -m 0640 -o root -g "$SERVICE_GROUP" "$SCRIPT_DIR/config.yaml" "$CONFIG_FILE"
}

build_server() {
    echo "Building $SERVICE_NAME..."
    cp "$SCRIPT_DIR/main.go" "$BUILD_DIR/main.go"
    cp -R "$SCRIPT_DIR/outputs" "$BUILD_DIR/outputs"

    (
        cd "$BUILD_DIR"
        "$GO_BIN" mod init logserver >/dev/null
        "$GO_BIN" mod tidy
        "$GO_BIN" build -o server
    )
}

install_server() {
    run_as_root install -d -m 0755 -o root -g root "$INSTALL_DIR"
    run_as_root install -m 0755 -o root -g root "$BUILD_DIR/server" "$INSTALL_DIR/server"
}

install_systemd_service() {
    local service_file="/etc/systemd/system/${SERVICE_NAME}.service"

    echo "Installing systemd service at $service_file..."
    run_as_root tee "$service_file" >/dev/null <<EOF
[Unit]
Description=GoLang Log distributor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CONFIG_DIR
ExecStart=$INSTALL_DIR/server
Restart=always
RestartSec=5
RuntimeMaxSec=2h
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=$CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF

    run_as_root systemctl daemon-reload
    run_as_root systemctl enable "$SERVICE_NAME.service"
    run_as_root systemctl restart "$SERVICE_NAME.service"
}

main() {
    if [[ ! -f "$SCRIPT_DIR/main.go" || ! -d "$SCRIPT_DIR/outputs" ]]; then
        echo "Run this script from the project checkout; expected logserver sources near $SCRIPT_DIR." >&2
        exit 1
    fi

    install_golang
    create_service_user
    prepare_config
    build_server
    install_server
    install_systemd_service

    echo
    echo "$SERVICE_NAME installed and started."
    echo "Service: systemctl status $SERVICE_NAME.service"
    echo "Config:  $CONFIG_FILE"
    echo "Binary:  $INSTALL_DIR/server"
}

main "$@"
