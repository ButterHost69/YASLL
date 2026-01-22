#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup.sh)"
  exit 1
fi

echo "Updating and upgrading system"
apt update
apt upgrade -y

echo "Installing Python dependencies"
apt install -y python3-pip python3-dev python3-venv build-essential

APP_DIR=/opt/LabelStudio

echo "Setting up Label Studio in $APP_DIR"
mkdir -p "$APP_DIR"

python3 -m venv "$APP_DIR/.venv"

echo "Installing Label Studio"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install label-studio

echo "Setting up permision for 'autostart.sh'"
chmod +x /opt/LabelStudio/autostart.sh

echo "Installing label_backend.service"
install -m 644 ./label_backend.service /etc/systemd/system/label_backend.service
cp ./start_n_stop.py /opt/LabelStudio/start_n_stop.py


echo "Reloading systemd"
systemctl daemon-reload
systemctl enable label_backend.service
systemctl start label_backend.service

echo "Setup complete ✅"