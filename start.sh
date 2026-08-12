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

echo
echo "=========================================="
echo "DIAGNOSTIC PAGE CRASH"
echo "=========================================="

python3 - <<'PY2'
import requests
import json

try:
    pages = requests.get("http://127.0.0.1:9030/json", timeout=5).json()

    for p in pages:
        if p.get("type") == "page":
            print("URL :", p.get("url"))
            print("Titre :", repr(p.get("title")))
            print("CDP :", p.get("webSocketDebuggerUrl"))
except Exception as e:
    print("Erreur CDP :", e)
PY2

echo
echo "LOG CHROMIUM - SharedWorker / WebSocket / erreurs :"

grep -iE "SharedWorker|WebSocket|error|failed|exception|blocked|refused|denied" \
    /tmp/chromium.log | tail -100 || true

echo
echo "FIN DU DIAGNOSTIC"
echo "=========================================="

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
