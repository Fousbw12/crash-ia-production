#!/data/data/com.termux/files/usr/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "     CRASH LOCAL - APPLICATION + CDP"
echo "========================================"

# Arrêter les anciennes instances
pkill -f "local_app.py" 2>/dev/null || true
pkill -f "local_crash.py" 2>/dev/null || true

sleep 2

echo "[1/2] Démarrage de l'application..."
python local_app.py > app.log 2>&1 &
APP_PID=$!

sleep 2

echo "[2/2] Démarrage de la capture CDP..."
python local_crash.py

echo "Capture arrêtée."
echo "Application PID : $APP_PID"
