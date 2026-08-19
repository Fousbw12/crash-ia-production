import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8090
history = []
lock = threading.Lock()

HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crash — Historique</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 20px;
    background: #070a12;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 900px;
    margin: auto;
}

h1 {
    text-align: center;
    color: #38bdf8;
}

.card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
}

.title {
    color: #94a3b8;
    font-size: 14px;
    text-transform: uppercase;
}

#last {
    text-align: center;
    font-size: 55px;
    font-weight: bold;
    margin: 15px 0;
}

#count {
    text-align: center;
    color: #94a3b8;
}

#history {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.mult {
    background: #1e293b;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 18px;
    font-weight: bold;
}

button {
    width: 100%;
    padding: 14px;
    border: 0;
    border-radius: 10px;
    background: #ef4444;
    color: white;
    font-size: 16px;
    font-weight: bold;
}
</style>
</head>

<body>

<div class="container">

<h1>⚡ CRASH HISTORIQUE</h1>

<div class="card">
    <div class="title">Dernier multiplicateur</div>
    <div id="last">--</div>
    <div id="count">0 multiplicateur</div>
</div>

<div class="card">
    <div class="title">Historique</div>
    <br>
    <div id="history"></div>
</div>

<div class="card">
    <button onclick="clearHistory()">
        Effacer l'historique
    </button>
</div>

</div>

<script>

async function update() {

    try {

        const response = await fetch("/data");
        const data = await response.json();

        const list = data.history || [];

        document.getElementById("count").innerText =
            list.length + " multiplicateur(s)";

        if (list.length > 0) {

            document.getElementById("last").innerText =
                Number(list[list.length - 1]).toFixed(2) + "x";
        }

        const box = document.getElementById("history");

        box.innerHTML = "";

        list.slice().reverse().forEach(function(value) {

            const element = document.createElement("span");

            element.className = "mult";

            element.innerText =
                Number(value).toFixed(2) + "x";

            box.appendChild(element);
        });

    } catch (error) {

        console.log(error);
    }
}

async function clearHistory() {

    await fetch("/clear", {
        method: "POST"
    });

    update();
}

setInterval(update, 1000);

update();

</script>

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/":

            data = HTML.encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.end_headers()

            self.wfile.write(data)

            return

        if self.path == "/data":

            with lock:
                values = list(history)

            data = json.dumps({
                "history": values
            }).encode()

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.end_headers()

            self.wfile.write(data)

            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):

        if self.path == "/crash":

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            try:
                data = json.loads(body)
                mult = float(data["multiplier"])

                with lock:
                    history.append(mult)

                    if len(history) > 50:
                        del history[:-50]

                print(f"[APP] Multiplicateur reçu : {mult:.2f}x", flush=True)

                response = json.dumps({
                    "ok": True,
                    "multiplier": mult
                }).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            except Exception as e:

                response = json.dumps({
                    "ok": False,
                    "error": str(e)
                }).encode("utf-8")

                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            return

        if self.path == "/clear":

            with lock:
                history.clear()

            self.send_response(200)
            self.end_headers()

            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass


def main():

    server = ThreadingHTTPServer(
        ("127.0.0.1", PORT),
        Handler
    )

    print(
        f"Application disponible sur http://127.0.0.1:{PORT}",
        flush=True
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
