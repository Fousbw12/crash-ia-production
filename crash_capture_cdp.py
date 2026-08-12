import json
import time
import urllib.request
import websocket
import sys
import re

CDP = "http://127.0.0.1:9030"

print("=" * 70, flush=True)
print("     CRASH CAPTURE - RAILWAY CDP", flush=True)
print("=" * 70, flush=True)

def get_page():
    try:
        with urllib.request.urlopen(CDP + "/json", timeout=10) as r:
            pages = json.loads(r.read())
        for p in pages:
            if p.get("type") == "page" and "1xbetmaroc.com" in p.get("url", ""):
                return p
        for p in pages:
            if p.get("type") == "page":
                return p
    except Exception as e:
        print("Erreur CDP :", e, flush=True)
    return None

page = get_page()

if not page:
    print("Aucune page Chromium trouvée.", flush=True)
    sys.exit(1)

print("PAGE :", page.get("url"), flush=True)
print("CDP  :", page.get("webSocketDebuggerUrl"), flush=True)

try:
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        origin="http://127.0.0.1:9030",
        timeout=30
    )
except Exception as e:
    print("Connexion CDP impossible :", e, flush=True)
    sys.exit(1)

print("Connexion CDP : OK", flush=True)

counter = 0

def send(method, params=None):
    global counter
    counter += 1
    msg = {"id": counter, "method": method}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))

send("Network.enable")

print("Network.enable : OK", flush=True)
print("ATTENTE DES WEBSOCKETS...", flush=True)
print("=" * 70, flush=True)

crash_urls = set()
crash_count = 0

def multiplier(payload):
    m = re.search(r'"f"\s*:\s*([0-9]+(?:\.[0-9]+)?)', payload)
    return m.group(1) if m else None

while True:
    try:
        msg = ws.recv()

        if not msg:
            continue

        data = json.loads(msg)
        method = data.get("method", "")
        params = data.get("params", {})

        if method == "Network.webSocketCreated":
            url = params.get("url", "")

            print("\nWEBSOCKET CRÉÉ :", url, flush=True)

            if "sockets/crash" in url.lower():
                crash_urls.add(url)
                print("=" * 70, flush=True)
                print("WEBSOCKET CRASH DÉTECTÉ", flush=True)
                print(url, flush=True)
                print("=" * 70, flush=True)

        elif method == "Network.webSocketFrameReceived":
            response = params.get("response", {})
            payload = response.get("payloadData", "")

            if "OnCrash" in payload:
                crash_count += 1
                value = multiplier(payload)

                print("\n" + "=" * 70, flush=True)
                print("CRASH #", crash_count, flush=True)
                print(
                    "MULTIPLICATEUR : "
                    + (str(value) + "x" if value else "NON EXTRAIT"),
                    flush=True
                )
                print("DONNÉE :", payload, flush=True)
                print("=" * 70, flush=True)

        elif method == "Network.webSocketClosed":
            print(
                "WebSocket fermé :",
                params.get("reason", ""),
                flush=True
            )

    except websocket.WebSocketTimeoutException:
        print(
            "[",
            time.strftime("%H:%M:%S"),
            "] Toujours en attente du WebSocket...",
            flush=True
        )
        continue

    except KeyboardInterrupt:
        print("\nArrêt.", flush=True)
        break

    except Exception as e:
        print("Erreur capture :", e, flush=True)
        time.sleep(2)
