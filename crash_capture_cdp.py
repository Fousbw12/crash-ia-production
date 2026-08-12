import json
import time
import urllib.request
import websocket

CDP = "http://127.0.0.1:9030"

print("=" * 70)
print("     CAPTURE CRASH - CDP WEBSOCKET")
print("=" * 70)

def get_targets():
    try:
        with urllib.request.urlopen(CDP + "/json", timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        print("Erreur /json :", e)
        return []

targets = get_targets()

print("\nTargets CDP détectés :")

for t in targets:
    print(
        "TYPE =", t.get("type"),
        "| TITLE =", repr(t.get("title")),
        "| URL =", t.get("url")
    )

# IMPORTANT :
# On prend UNIQUEMENT le vrai target "page" du jeu Crash.
target = None

for t in targets:
    if (
        t.get("type") == "page"
        and "1xbetmaroc.com" in t.get("url", "")
        and "/games/crash" in t.get("url", "")
    ):
        target = t
        break

if not target:
    print("\nERREUR : target Crash introuvable.")
    print("Attente puis nouvelle tentative...")
    time.sleep(5)
    raise SystemExit(1)

ws_url = target["webSocketDebuggerUrl"]

print("\nPAGE CRASH TROUVÉE")
print("URL :", target.get("url"))
print("CDP :", ws_url)

try:
    ws = websocket.create_connection(ws_url, timeout=2)
except Exception as e:
    print("Erreur connexion CDP :", e)
    raise SystemExit(1)

print("\nConnexion CDP : OK")

counter = 0

def send(method, params=None):
    global counter
    counter += 1

    msg = {
        "id": counter,
        "method": method
    }

    if params is not None:
        msg["params"] = params

    ws.send(json.dumps(msg))
    return counter

# Activer Network AVANT le reload.
send("Network.enable", {
    "maxTotalBufferSize": 100000000,
    "maxResourceBufferSize": 10000000
})

send("Page.enable")

# Recharger la page maintenant que Network est activé.
print("\nRechargement de la page Crash...")
send("Page.reload", {
    "ignoreCache": True
})

print("Surveillance WebSocket activée.")
print("=" * 70)

websockets = set()

last_message = time.time()

while True:
    try:
        ws.settimeout(2)

        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            # Évite que le programme s'arrête simplement
            # parce qu'aucun événement n'est arrivé pendant 2 secondes.
            if time.time() - last_message > 10:
                print("Toujours en attente des événements réseau...")
                last_message = time.time()
            continue

        if not raw:
            continue

        last_message = time.time()

        try:
            msg = json.loads(raw)
        except Exception:
            continue

        method = msg.get("method", "")
        params = msg.get("params", {})

        # ==========================================================
        # WEBSOCKET CRÉÉ
        # ==========================================================

        if method == "Network.webSocketCreated":

            url = params.get("url", "")

            print("\n" + "=" * 70)
            print("WEBSOCKET DÉTECTÉ")
            print(url)
            print("=" * 70)

            websockets.add(params.get("requestId"))

            if "sockets/crash" in url.lower():
                print("\n*** WEBSOCKET CRASH TROUVÉ ***")
                print(url)
                print("*** FIN URL ***\n")

        # ==========================================================
        # FRAME WEBSOCKET REÇUE
        # ==========================================================

        elif method == "Network.webSocketFrameReceived":

            request_id = params.get("requestId")

            payload = (
                params
                .get("response", {})
                .get("payloadData", "")
            )

            if request_id not in websockets:
                continue

            print("\nWEBSOCKET FRAME :")
            print(payload[:2000])

            # Recherche OnCrash
            if "OnCrash" in payload:

                print("\n" + "#" * 70)
                print("              ONCRASH DÉTECTÉ")
                print("#" * 70)
                print(payload)
                print("#" * 70)

                try:
                    data = json.loads(payload)

                    args = data.get("arguments", [])

                    if args:
                        game = args[0]

                        if "f" in game:
                            print(
                                "\nMULTIPLICATEUR :",
                                game["f"],
                                "x"
                            )

                        if "l" in game:
                            print(
                                "ID JEU :",
                                game["l"]
                            )

                except Exception:
                    pass

        # ==========================================================
        # ERREUR WEBSOCKET
        # ==========================================================

        elif method == "Network.webSocketFrameError":

            print(
                "\nERREUR WEBSOCKET :",
                params
            )

        elif method == "Network.webSocketClosed":

            request_id = params.get("requestId")

            if request_id in websockets:
                print("\nWebSocket fermé :", request_id)

    except KeyboardInterrupt:
        print("\nArrêt demandé.")
        break

    except Exception as e:
        print("\nErreur capture :", e)
        time.sleep(2)

try:
    ws.close()
except:
    pass
