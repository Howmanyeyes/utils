#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-logserver}"
SERVICE_USER="${SERVICE_USER:-logserver}"
SERVICE_GROUP="${SERVICE_GROUP:-$SERVICE_USER}"
INSTALL_DIR="${INSTALL_DIR:-/opt/logserver}"
CONFIG_DIR="${CONFIG_DIR:-/etc/logserver}"
CONFIG_FILE="${CONFIG_FILE:-$CONFIG_DIR/config.yaml}"
SOURCE_CONFIG="${SOURCE_CONFIG:-}"

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

install_golang() {
    if command -v go >/dev/null 2>&1; then
        echo "Go is already installed: $(go version)"
        return
    fi

    echo "Go is not installed. Installing golang-go with apt..."
    run_as_root apt-get update
    run_as_root apt-get install -y golang-go
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
        go mod init logserver >/dev/null
        go mod tidy
        go build -o server
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
