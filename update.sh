#!/bin/bash

set -e

echo "================================="
echo " FMA Dashboard Update"
echo "================================="

# PROJECT_DIR="/home/pi/fma-dashboard"

# echo "[1/5] Going to project folder..."

# cd "$PROJECT_DIR" || exit 1


# echo "[2/5] Updating code..."

# git pull


# echo "[3/5] Updating Python packages..."

# source .venv/bin/activate

# python -m pip install -r requirements.txt

# deactivate


echo "[4/5] Updating menu command..."

sudo tee /usr/local/bin/menu > /dev/null <<'EOF'
#!/bin/bash

cd /home/pi/fma-dashboard || exit 1

exec /home/pi/fma-dashboard/.venv/bin/python app.py
EOF

sudo chmod +x /usr/local/bin/menu


echo "[5/5] Complete"

echo ""
echo "================================="
echo " Update complete"
echo "================================="
echo ""
echo "Run dashboard:"
echo ""
echo "    menu"
echo ""