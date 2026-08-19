import os
import json
import time
import math
import asyncio
import sqlite3
import torch
import torch.nn as nn
import numpy as np
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DB_PATH = "crash_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, point_reel REAL,
            point_determine REAL, incertitude REAL, seuil_engage REAL, gain_perte REAL, solde_resultat REAL
        )
    """)
    conn.commit()
    conn.close()
init_db()

state = {
    "crash_count": 0, "last_real": 1.0, "next_pred": 1.0, "uncertainty": 0.0,
    "signal": "🔴 ATTENTE", "seuil_ejection": 1.0, "solde": 1000.0,
    "winrate": 0.0, "trades": 0, "pi_distribution": [100.0, 0.0, 0.0], 
    "balance_history": [1000.0], "success_stats": [0, 0], "crash_history": []
}

class ConnectionManager:
    def __init__(self): self.active_connections = []
    async def connect(self, ws: WebSocket): await ws.accept(); self.active_connections.append(ws)
    def disconnect(self, ws: WebSocket): self.active_connections.remove(ws)
    async def broadcast(self, data: dict):
        for conn in self.active_connections:
            try: await conn.send_json(data)
            except: pass
manager = ConnectionManager()

device = torch.device("cpu")
WINDOW_SIZE = 25
FEATURES_COUNT = 6

class MDNHead(nn.Module):
    def __init__(self, in_features, num_components=3):
        super().__init__()
        self.pi = nn.Linear(in_features, num_components)
        self.mu = nn.Linear(in_features, num_components)
        self.sigma = nn.Linear(in_features, num_components)
    def forward(self, x):
        return torch.softmax(self.pi(x), dim=-1), self.mu(x), torch.nn.functional.softplus(self.sigma(x)) + 1e-4

class TransformerMDN(nn.Module):
    def __init__(self, input_size=6, d_model=128, nhead=8, num_layers=4):
        super().__init__()
        self.d_model = d_model
        self.embedding = nn.Linear(input_size, d_model)
        el = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=256, dropout=0.1, batch_first=True)
        self.transformer = nn.TransformerEncoder(el, num_layers=num_layers)
        self.mdn = MDNHead(d_model, 3)
    def forward(self, x):
        return self.mdn(self.transformer(self.embedding(x) * math.sqrt(self.d_model))[:, -1, :])

model = TransformerMDN(input_size=FEATURES_COUNT).to(device)
model.eval()

raw_history, ts_history, eng_sequences = deque(maxlen=60), deque(maxlen=60), deque(maxlen=WINDOW_SIZE)

def scale(v): return math.log(max(1.0, v))
def descale(v): return math.exp(v)

def process_features(mult, ts):
    raw_history.append(mult)
    ts_history.append(ts)
    dt = (ts_history[-1] - ts_history[-2]) / 1000.0 if len(ts_history) >= 2 else 0.0
    return [scale(mult), scale(np.mean(list(raw_history)[-5:])), scale(np.mean(list(raw_history)[-15:])),
            np.std([scale(x) for x in list(raw_history)[-10:]]) if len(raw_history) >= 10 else 0.0, 0.5, dt]

def sauvegarder_round(ts, reel, pred, unc, seuil, pnl, total):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rounds (timestamp, point_reel, point_determine, incertitude, seuil_engage, gain_perte, solde_resultat) VALUES (?, ?, ?, ?, ?, ?, ?)", (ts, reel, pred, unc, seuil, pnl, total))
    conn.commit()
    conn.close()

async def listen_cdp():
    import websockets
    global state
    cdp_host = os.getenv("CDP_HOST", "ws://127.0.0.1:9030")
    trades_gagnes, seuil_engage = 0, None
    point_exact_determine, incertitude = 1.0, 0.0
    
    while True:
        try:
            async with websockets.connect(cdp_host, timeout=10) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
                async for message in ws:
                    data = json.loads(message)
                    if data.get("method") == "Network.webSocketFrameReceived":
                        payload = data.get("params", {}).get("response", {}).get("payloadData", "")
                        if "OnCrash" in payload:
                            try:
                                args = json.loads(payload).get("arguments", [{}])
                                mult, ts = float(args.get("f")), float(args.get("ts"))
                            except: continue

                            state["crash_count"] += 1
                            state["last_real"] = mult
                            pnl = 0.0

                            if seuil_engage is not None:
                                state["trades"] += 1
                                if mult >= seuil_engage:
                                    pnl = 10.0 * (seuil_engage - 1)
                                    state["solde"] += pnl
                                    trades_gagnes += 1
                                    state["success_stats"][1] += 1
                                else:
                                    pnl = -10.0
                                    state["solde"] += pnl
                                    state["success_stats"][0] += 1
                                state["winrate"] = round((trades_gagnes / state["trades"]) * 100, 1)

                            sauvegarder_round(time.strftime('%H:%M:%S'), mult, point_exact_determine, incertitude, seuil_engage or 0.0, pnl, state["solde"])
                            seuil_engage = None
                            state["balance_history"].append(round(state["solde"], 2))

                            eng_sequences.append(process_features(mult, ts))
                            if len(eng_sequences) == WINDOW_SIZE:
                                with torch.no_grad():
                                    inputs = torch.tensor(list(eng_sequences), dtype=torch.float32).unsqueeze(0).to(device)
                                    pi, mu, sigma = model(inputs)
                                    pi, mu, sigma = pi.squeeze(0).numpy(), mu.squeeze(0).numpy(), sigma.squeeze(0).numpy()
                                
                                point_log_attendu = np.sum(pi * mu)
                                point_exact_determine = descale(point_log_attendu)
                                incertitude = math.sqrt(np.sum(pi * (sigma**2 + (mu - point_log_attendu)**2)))
                                borne_sec = descale(point_log_attendu - (1.44 * incertitude))

                                state["next_pred"] = round(point_exact_determine, 2)
                                state["uncertainty"] = round(incertitude, 4)
                                state["pi_distribution"] = [round(x * 100, 1) for x in pi]

                                if borne_sec >= 1.25 and incertitude < 0.32:
                                    seuil_engage = round(borne_sec, 2)
                                    state["seuil_ejection"] = seuil_engage
                                    state["signal"] = "🟢 ENGAGÉ"
                                else: state["signal"] = "🔴 PASS"
                            
                            await manager.broadcast(state)
        except: await asyncio.sleep(2)


@app.post("/api/crash")
async def receive_crash(data: dict):
    try:
        mult = float(data.get("multiplier"))
        ts = float(data.get("ts", time.time() * 1000))

        state["crash_count"] += 1
        state["last_real"] = mult
        state["crash_history"].append(mult)
        state["crash_history"] = state["crash_history"][-20:]

        eng_sequences.append(process_features(mult, ts))

        if len(eng_sequences) == WINDOW_SIZE:
            with torch.no_grad():
                inputs = torch.tensor(
                    list(eng_sequences),
                    dtype=torch.float32
                ).unsqueeze(0).to(device)

                pi, mu, sigma = model(inputs)

                pi = pi.squeeze(0).numpy()
                mu = mu.squeeze(0).numpy()
                sigma = sigma.squeeze(0).numpy()

            point_log_attendu = np.sum(pi * mu)
            point_exact_determine = descale(point_log_attendu)

            incertitude = math.sqrt(
                np.sum(
                    pi * (
                        sigma**2 +
                        (mu - point_log_attendu)**2
                    )
                )
            )

            state["next_pred"] = round(point_exact_determine, 2)
            state["uncertainty"] = round(incertitude, 4)
            state["pi_distribution"] = [
                round(x * 100, 1) for x in pi
            ]

        await manager.broadcast(state)

        return {
            "ok": True,
            "multiplier": mult
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }

@app.on_event("startup")
async def startup_event(): asyncio.create_task(listen_cdp())

@app.get("/")
async def get_index(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json(state)
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)
