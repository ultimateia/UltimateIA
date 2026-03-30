from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

# Charger le fichier .env au démarrage
load_dotenv()

app = FastAPI(title="Robot Live Tracking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Récupération du mot de passe depuis .env
CLEAR_PASSWORD = os.getenv("CLEAR_PASSWORD")
if not CLEAR_PASSWORD:
    print("⚠️ Attention : CLEAR_PASSWORD n'est pas défini dans le fichier .env !")

latest_position = None
positions_history = []

# 🔥 Liste globale d'événements pour SSE
events = []

@app.post("/api/position")
async def receive_position(data: dict):
    global latest_position
    data["timestamp"] = datetime.utcnow().isoformat()
    latest_position = data
    positions_history.append(data)

    # Ajouter un événement pour le stream
    events.append({
        "type": "position",
        "data": data
    })

    print(f"✅ Position reçue → Lat: {data.get('lat')}, Lon: {data.get('lon')}")
    return {"status": "ok"}

@app.get("/api/position")
async def get_latest():
    return latest_position or {"status": "no_data_yet"}

@app.get("/api/position-stream")
async def position_stream(request: Request):
    async def event_generator():
        last_event_index = 0
        while True:
            if await request.is_disconnected():
                break

            # Envoyer les nouveaux événements
            while last_event_index < len(events):
                event = events[last_event_index]
                yield f"data: {json.dumps(event)}\n\n"
                last_event_index += 1

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ====================== HISTORIQUE ======================
@app.get("/api/positions/history")
async def get_positions_history():
    if not positions_history:
        return {"positions": []}
    
    return {
        "positions": positions_history,
        "count": len(positions_history)
    }

# ✅ FIX PRINCIPAL : support GET + HEAD
@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {
        "status": "alive",
        "time": datetime.utcnow().isoformat()
    }

# ====================== ROUTE CLEAR ======================
@app.delete("/api/positions/clear")
@app.get("/api/positions/clear")
async def clear_all_positions(password: str = Query(..., description="Mot de passe requis")):
    if not CLEAR_PASSWORD:
        raise HTTPException(status_code=500, detail="Configuration du mot de passe manquante sur le serveur")
   
    if password != CLEAR_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect. Accès refusé.")
   
    global latest_position, positions_history, events
    
    # Nettoyage complet
    latest_position = None
    positions_history.clear()
    
    # 🔥 SOLUTION : On vide complètement les events ET on ajoute un nouveau clear
    events.clear()
    events.append({
        "type": "clear",
        "timestamp": datetime.utcnow().timestamp()   # timestamp pour éviter les doublons
    })
    
    print("🗑️ Clear effectué - events vidés et nouveau clear ajouté")
    
    return {
        "status": "success",
        "message": "Toutes les positions ont été supprimées avec succès.",
        "cleared": True
    }
