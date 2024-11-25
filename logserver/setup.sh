#!/bin/bash
sudo apt update
command -v go >/dev/null 2>&1 || { echo >&2 "I require golang but it's not installed."; sudo apt install -y golang-go;}

rm go.mod go.sum
go mod init logserver
go mod tidy
go build -o ./build/server

wd="$(pwd)"
usr="$(whoami)"

if [ ! -f "./config.yaml" ]; then
    echo "File with configuration (config.yaml) not found!"
    /bin/bash ./create_config.sh
fi

systemctl stop logserver.service > /dev/null

echo -n "Do you want to create user 'logserver' and install service for it ('y') or store files in current directory ($wd) and run service from current user ($usr)?"
read ans
if [[ "$ans" == "y" ]]
then
sudo useradd -m logserver
wd="/home/logserver"
usr="logserver"
sudo mkdir $wd/build
sudo cp ./build/server $wd/build/server
sudo cp ./config.yaml $wd/config.yaml

sudo chown logserver:logserver $wd
fi

sudo cat > /lib/systemd/system/logserver.service <<EOL
[Unit]
Description=GoLang Log distributor

[Service]
User=$usr
WorkingDirectory=$wd
Environment=PATH=$PATH
ExecStart=$wd/build/server
Restart=always
RestartSec=5
RuntimeMaxSec=2h
[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable logserver.service
sudo systemctl start logserver.service
