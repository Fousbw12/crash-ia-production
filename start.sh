#!/bin/bash
set -u

echo "=========================================="
echo "   CRASH IA - RAILWAY 24/7"
echo "=========================================="

PORT="${PORT:-8080}"

echo "Démarrage du dashboard sur le port $PORT..."

uvicorn app:app \
    --host 0.0.0.0 \
    --port "$PORT" &

APP_PID=$!

echo "Dashboard PID : $APP_PID"

echo "Démarrage de Chromium..."

chromium \
    --headless=new \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --enable-logging=stderr \
    --v=1 \
    --disable-software-rasterizer \
    --disable-background-networking \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-features=Translate,BackForwardCache,OptimizationHints,MediaRouter \
    --remote-debugging-port=9030 \
    --remote-debugging-address=127.0.0.1 \
    --remote-allow-origins=* \
    --user-data-dir=/tmp/chrome-profile \
    "https://1xbetmaroc.com/fr/games/crash" \
    > /tmp/chromium.log 2>&1 &

CHROME_PID=$!

echo "Chromium PID : $CHROME_PID"

echo "Attente de Chromium..."

for i in $(seq 1 60)
do
    if curl -sf http://127.0.0.1:9030/json >/dev/null; then
        echo "Chromium CDP : OK"
        break
    fi
    sleep 1
done

echo "Vérification de la page..."

curl -s http://127.0.0.1:9030/json > /tmp/cdp_pages.json || true

echo "Pages CDP :"
cat /tmp/cdp_pages.json

echo
echo "Démarrage du captureur..."

while true
do
    echo
    echo "=========================================="
    echo "Lancement du captureur"
    echo "=========================================="

    python3 crash_capture_cdp.py

    CODE=$?

    echo "Captureur arrêté avec le code : $CODE"
    echo "Redémarrage dans 5 secondes..."

    sleep 5
done
