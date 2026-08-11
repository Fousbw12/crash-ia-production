#!/bin/bash

set -u

echo "=========================================="
echo "   CRASH IA - RAILWAY 24/7"
echo "=========================================="

echo "Démarrage du dashboard..."

uvicorn app:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" &

APP_PID=$!

echo "Dashboard PID : $APP_PID"

echo "Démarrage de Chromium..."

chromium \
    --headless \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --remote-debugging-port=9030 \
    --remote-debugging-address=127.0.0.1 \
    --remote-allow-origins=* \
    --user-data-dir=/tmp/chrome-profile \
    "https://1xbetmaroc.com/fr/games/crash" \
    > /tmp/chromium.log 2>&1 &

CHROME_PID=$!

echo "Chromium PID : $CHROME_PID"

echo "Attente du démarrage de Chromium..."

for i in $(seq 1 30)
do
    if curl -s http://127.0.0.1:9030/json > /dev/null; then
        echo "Chromium CDP : OK"
        break
    fi

    sleep 1
done

echo "Démarrage du captureur..."

while true
do
    python3 crash_capture_cdp.py

    echo "Captureur arrêté."
    echo "Redémarrage dans 5 secondes..."

    sleep 5
done
