#!/bin/bash

set -e

echo "================================="
echo " FMA Dashboard Update"
echo "================================="

PROJECT_DIR="/home/pi/fma-dashboard"
VENV="$PROJECT_DIR/.venv"


echo "[1/5] Entering project folder..."

cd "$PROJECT_DIR" || exit 1


echo ""
echo "[2/5] Current version:"
git log -1 --oneline


echo ""
echo "Pulling latest code..."

git pull origin main


echo ""
echo "New version:"
git log -1 --oneline


echo ""
echo "[3/5] Updating Python packages..."

if [ -d "$VENV" ]; then

    source "$VENV/bin/activate"

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

    deactivate

else

    echo "WARNING: Virtual environment not found"

fi


echo ""
echo "[4/5] Updating menu command..."

sudo tee /usr/local/bin/menu > /dev/null <<'EOF'
#!/bin/bash

cd /home/pi/fma-dashboard || exit 1

exec /home/pi/fma-dashboard/.venv/bin/python app.py
EOF


sudo chmod +x /usr/local/bin/menu


echo ""
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