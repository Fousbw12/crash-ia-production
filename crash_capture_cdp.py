import json
import time
import urllib.request
import websocket
import sys
import re

CDP_HTTP = "http://127.0.0.1:9030"

print("=" * 70, flush=True)
print("     CRASH CAPTURE - RAILWAY CDP", flush=True)
print("=" * 70, flush=True)


def trouver_page():
    try:
        with urllib.request.urlopen(
            CDP_HTTP + "/json",
            timeout=10
        ) as r:
            pages = json.loads(r.read())

    except Exception as e:
        print("ERREUR CDP :", e, flush=True)
        return None

    # Cherche UNIQUEMENT la vraie page Crash.
    # Ne prend jamais /block ni chrome://...
    for p in pages:
        url = p.get("url", "")

        if (
            p.get("type") == "page"
            and "1xbetmaroc.com" in url
            and "/games/crash" in url
        ):
            return p

    print("Aucune page /games/crash trouvée.", flush=True)

    for p in pages:
        print(
            "PAGE :",
            p.get("type"),
            p.get("url"),
            flush=True
        )

    return None


# ------------------------------------------------------------
# Recherche de la page Crash
# ------------------------------------------------------------

page = trouver_page()

if page is None:
    print("ERREUR : page Crash introuvable.", flush=True)
    sys.exit(1)

print("PAGE :", page.get("url"), flush=True)
print("CDP  :", page.get("webSocketDebuggerUrl"), flush=True)


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
    print("ERREUR connexion CDP :", e, flush=True)
    sys.exit(1)

print("Connexion CDP : OK", flush=True)


# ------------------------------------------------------------
# Active Network
# ------------------------------------------------------------

counter = 0


def send_cdp(method, params=None):
    global counter

    counter += 1

    message = {
        "id": counter,
        "method": method
    }

    if params is not None:
        message["params"] = params

    ws.send(json.dumps(message))


send_cdp("Network.enable")

print("Network.enable : OK", flush=True)
print("ATTENTE DES WEBSOCKETS...", flush=True)


# ------------------------------------------------------------
# Variables
# ------------------------------------------------------------

crash_websockets = set()
crash_count = 0


def extraire_multiplicateur(payload):
    match = re.search(
        r'"f"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        payload
    )

    if match:
        return match.group(1)

    return None


# ------------------------------------------------------------
# Surveillance
# ------------------------------------------------------------

dernier_message = time.time()

while True:

    try:
        message = ws.recv()

        if not message:
            continue

        dernier_message = time.time()

        data = json.loads(message)

        method = data.get("method", "")
        params = data.get("params", {})


        # ----------------------------------------------------
        # WebSocket créé
        # ----------------------------------------------------

        if method == "Network.webSocketCreated":

            url = params.get("url", "")

            if "sockets/crash" in url.lower():

                if url not in crash_websockets:

                    crash_websockets.add(url)

                    print("", flush=True)
                    print("=" * 70, flush=True)
                    print("WEBSOCKET CRASH DÉTECTÉ", flush=True)
                    print(url, flush=True)
                    print("=" * 70, flush=True)


        # ----------------------------------------------------
        # Frame reçue
        # ----------------------------------------------------

        elif method == "Network.webSocketFrameReceived":

            response = params.get("response", {})

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
                    f"[{heure}] CRASH #{crash_count}",
                    flush=True
                )

                if multiplicateur:

                    print(
                        f"MULTIPLICATEUR : {multiplicateur}x",
                        flush=True
                    )

                else:

                    print(
                        "MULTIPLICATEUR : non extrait",
                        flush=True
                    )

                print(
                    "DONNÉE :",
                    payload,
                    flush=True
                )


        # ----------------------------------------------------
        # Frame envoyée
        # ----------------------------------------------------

        elif method == "Network.webSocketFrameSent":

            response = params.get("response", {})

            payload = response.get(
                "payloadData",
                ""
            )

            if "OnCrash" in payload:

                print(
                    "[ONCRASH ENVOYÉ]",
                    payload,
                    flush=True
                )


    except websocket.WebSocketTimeoutException:

        if time.time() - dernier_message >= 30:

            print(
                "[INFO] Toujours en attente du WebSocket...",
                flush=True
            )

            dernier_message = time.time()

        continue


    except KeyboardInterrupt:

        print(
            "\nArrêt du captureur.",
            flush=True
        )

        try:
            ws.close()
        except Exception:
            pass

        break


    except Exception as e:

        print(
            "Erreur captureur :",
            e,
            flush=True
        )

        time.sleep(2)
