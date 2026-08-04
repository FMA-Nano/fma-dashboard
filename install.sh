#!/bin/bash

set -e

echo "================================="
echo " FMA Dashboard Installer"
echo "================================="

PROJECT_DIR="$(pwd)"

echo "[1/5] Installing Python venv support..."
sudo apt install -y python3-venv

echo "[2/5] Creating virtual environment..."
python3 -m venv .venv

echo "[3/5] Activating venv..."
source .venv/bin/activate

echo "[4/6] Upgrading pip..."
python -m pip install --upgrade pip

echo "[5/6] Installing dashboard requirements..."
python -m pip install textual==0.38.1 --no-deps
python -m pip install -r requirements.txt

deactivate

echo "[6/6] Creating global 'menu' command..."
sudo rm -rf /usr/local/bin/menu
sudo cp menu /usr/local/bin/menu
sudo chmod +x /usr/local/bin/menu
cat /usr/local/bin/menu

echo ""
echo ""
echo "================================="
echo " Installation complete"
echo "================================="
echo ""
echo "You can now start the dashboard from anywhere by typing:"
echo ""
echo "    menu"
echo ""
