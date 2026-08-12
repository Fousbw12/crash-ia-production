import requests
import websocket
import json
import time
import re
import sys

CDP_HTTP = "http://127.0.0.1:9030"

print("=" * 70)
print("     CAPTURE CRASH - CHROMIUM + CDP")
print("=" * 70)

# ------------------------------------------------------------
# Recherche de la page Chromium
# ------------------------------------------------------------

try:
    pages = requests.get(
        CDP_HTTP + "/json",
        timeout=5
    ).json()
except Exception as e:
    print("\nERREUR : Chromium n'est pas accessible.")
    print("Vérifie que Chromium est lancé sur le port 9030.")
    print("Détail :", e)
    sys.exit(1)

page = None

for p in pages:
    if p.get("type") == "page":
        page = p
        break

if page is None:
    print("\nAucune page Chromium trouvée.")
    sys.exit(1)

print("\nPage Chromium détectée")
print("URL    :", page.get("url"))
print("Titre  :", page.get("title"))
print("CDP    :", page.get("webSocketDebuggerUrl"))

# ------------------------------------------------------------
# Connexion CDP
# ------------------------------------------------------------

try:
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        origin="http://127.0.0.1:9030",
        timeout=5
    )
except Exception as e:
    print("\nERREUR : connexion CDP impossible.")
    print(e)
    sys.exit(1)

print("\nConnexion CDP : OK")

# ------------------------------------------------------------
# Active Network
# ------------------------------------------------------------

counter = 0

def send_cdp(method, params=None):
    global counter

    counter += 1

    msg = {
        "id": counter,
        "method": method
    }

    if params is not None:
        msg["params"] = params

    ws.send(json.dumps(msg))


send_cdp("Network.enable")

print("\nSurveillance réseau activée.")
print("Ouvre maintenant le jeu Crash dans Chromium.")
print("=" * 70)

# ------------------------------------------------------------
# Variables
# ------------------------------------------------------------

crash_websockets = set()
crash_count = 0

# ------------------------------------------------------------
# Extraction du multiplicateur
# ------------------------------------------------------------

def extraire_multiplicateur(payload):

    # Cherche le champ JSON "f"
    match = re.search(
        r'"f"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        payload
    )

    if match:
        return match.group(1)

    return None


# ------------------------------------------------------------
# Boucle principale
# ------------------------------------------------------------

while True:

    try:

        message = ws.recv()

        if not message:
            continue

        data = json.loads(message)

        method = data.get("method", "")
        params = data.get("params", {})

        # ====================================================
        # NOUVEAU WEBSOCKET
        # ====================================================

        if method == "Network.webSocketCreated":

            url = params.get("url", "")

            if "sockets/crash" in url.lower():

                if url not in crash_websockets:

                    crash_websockets.add(url)

                    print("\n")
                    print("=" * 70)
                    print("WEBSOCKET CRASH DÉTECTÉ")
                    print("=" * 70)
                    print(url)
                    print("=" * 70)

        # ====================================================
        # FRAME WEBSOCKET REÇUE
        # ====================================================

        elif method == "Network.webSocketFrameReceived":

            response = params.get(
                "response",
                {}
            )

            payload = response.get(
                "payloadData",
                ""
            )

            if "OnCrash" in payload:

                crash_count += 1

                multiplicateur = extraire_multiplicateur(
                    payload
                )

                heure = time.strftime("%H:%M:%S")

                print(
                    f"\n[{heure}] CRASH #{crash_count}"
                )

                if multiplicateur:
                    print(
                        f"MULTIPLICATEUR : {multiplicateur}x"
                    )
                else:
                    print(
                        "MULTIPLICATEUR : non extrait"
                    )

                print("DONNÉE :", payload)

        # ====================================================
        # FRAME ENVOYÉE
        # ====================================================

        elif method == "Network.webSocketFrameSent":

            response = params.get(
                "response",
                {}
            )

            payload = response.get(
                "payloadData",
                ""
            )

            if "OnCrash" in payload:

                print("\n[ONCRASH ENVOYÉ]")
                print(payload)

    except websocket.WebSocketTimeoutException:
        continue

    except KeyboardInterrupt:

        print("\n\nArrêt du programme.")

        try:
            ws.close()
        except:
            pass

        break

    except Exception as e:

        print("\nErreur :", e)
        time.sleep(1)
