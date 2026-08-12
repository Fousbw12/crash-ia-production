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

rm -rf /tmp/chrome-profile

chromium \
    --headless=new \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --disable-software-rasterizer \
    --disable-blink-features=AutomationControlled \
    --disable-features=Translate,BackForwardCache,OptimizationHints,MediaRouter \
    --enable-network-service \
    --enable-features=NetworkServiceInProcess \
    --remote-debugging-port=9030 \
    --remote-debugging-address=127.0.0.1 \
    --remote-allow-origins=* \
    --user-data-dir=/tmp/chrome-profile \
    --window-size=1920,1080 \
    --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36" \
    "https://1xbetmaroc.com/fr/games/crash" \
    > /tmp/chromium.log 2>&1 &

CHROME_PID=$!

echo "Chromium PID : $CHROME_PID"
echo "Attente de Chromium..."

CDP_OK=0

for i in $(seq 1 60)
do
    if curl -sf http://127.0.0.1:9030/json >/dev/null; then
        echo "Chromium CDP : OK"
        CDP_OK=1
        break
    fi
    sleep 1
done

if [ "$CDP_OK" -eq 0 ]; then
    echo "ERREUR : Chromium CDP n'a pas démarré."
    cat /tmp/chromium.log | tail -100 || true
    exit 1
fi

echo "Vérification de la page..."

curl -s http://127.0.0.1:9030/json > /tmp/cdp_pages.json || true

echo "Pages CDP :"
cat /tmp/cdp_pages.json

echo
echo "=========================================="
echo "DIAGNOSTIC PAGE CRASH"
echo "=========================================="

python3 - <<'PY'
import requests

try:
    pages = requests.get(
        "http://127.0.0.1:9030/json",
        timeout=5
    ).json()

    for p in pages:
        if p.get("type") == "page":
            print("URL   :", p.get("url"))
            print("Titre :", repr(p.get("title")))
            print("CDP   :", p.get("webSocketDebuggerUrl"))

except Exception as e:
    print("Erreur CDP :", e)
PY

echo
echo "=========================================="
echo "LOG CHROMIUM"
echo "=========================================="

grep -iE \
"websocket|sharedworker|error|failed|exception|blocked|refused|denied" \
/tmp/chromium.log | tail -100 || true

echo
echo "=========================================="
echo "DÉMARRAGE DU CAPTUREUR"
echo "=========================================="

while true
do
    echo
    echo "=========================================="
    echo "Lancement du captureur"
    echo "=========================================="

    python3 crash_capture_cdp.py

    CODE=$?

    echo "Captureur arrêté : $CODE"
    echo "Redémarrage dans 5 secondes..."

    sleep 5
done
