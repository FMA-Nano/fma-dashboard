#!/bin/bash

set -e

echo "================================="
echo " FMA Dashboard Installer"
echo "================================="

PROJECT_DIR="/home/pi/fma-dashboard"
REPO="https://github.com/FMA-Nano/fma-dashboard.git"


echo ""
echo "[1/6] Checking system packages..."

# Check Git
if ! command -v git >/dev/null 2>&1; then
    echo "Git not found. Installing..."
    sudo apt install -y git
else
    echo "Git installed:"
    git --version
fi

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python3 not found. Installing..."
    sudo apt install -y python3
else
    echo "Python installed:"
    python3 --version
fi

# Install Python tools
echo "Installing Python environment tools..."
sudo apt install -y \
    python3-venv \


echo ""
echo "[2/6] Checking repository..."

if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "Checking GitHub access..."
    if ! git ls-remote "$REPO" >/dev/null 2>&1; then
        echo ""
        echo "ERROR:"
        echo "Cannot access repository:"
        echo "$REPO"
        echo ""
        exit 1
    fi
    echo "Cloning FMA Dashboard..."
    git clone "$REPO" "$PROJECT_DIR"
else
    echo "Repository already exists."
fi

cd "$PROJECT_DIR"


echo ""
echo "[3/6] Creating virtual environment..."

if [ ! -d ".venv" ]; then
    echo "Creating .venv..."
    python3 -m venv .venv
else
    echo ".venv already exists."
fi


echo ""
echo "[4/6] Installing Python requirements..."

source .venv/bin/activate
echo "Updating pip..."
python -m pip install --upgrade pip
echo "Installing Textual..."
python -m pip install textual==0.38.1 --no-deps
echo "Installing requirements..."
python -m pip install -r requirements.txt
deactivate


echo ""
echo "[5/6] Creating global menu command..."

sudo tee /usr/local/bin/menu > /dev/null <<'EOF'
#!/bin/bash

cd /home/pi/fma-dashboard || exit 1

exec /home/pi/fma-dashboard/.venv/bin/python app.py
EOF

sudo chmod +x /usr/local/bin/menu


echo ""
echo "[6/6] Complete"


echo ""
echo "================================="
echo " Installation Complete"
echo "================================="
echo ""

echo "System packages installed:"
echo "  ✓ Git"
echo "  ✓ Python3 venv support"
echo ""

echo "Project installed:"
echo "  ✓ FMA Dashboard"
echo "    Location: /home/pi/fma-dashboard"
echo ""

echo "Virtual environment:"
echo "  ✓ Created: .venv"
echo "  ✓ Installed Python packages:"
echo "      - Textual 0.38.1"
echo "      - Requirements from requirements.txt"
echo ""

echo "System commands:"
echo "  ✓ Installed global command:"
echo "      menu"
echo ""

echo "================================="
echo " Dashboard Ready"
echo "================================="
echo ""

echo "The dashboard can be opened from any terminal"
echo "by typing: menu"
echo ""