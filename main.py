from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Robot Live Tracking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLEAR_PASSWORD = os.getenv("CLEAR_PASSWORD")
if not CLEAR_PASSWORD:
    print("⚠️ Attention : CLEAR_PASSWORD n'est pas défini dans le fichier .env !")

# Variables globales
latest_position = None
positions_history = []
latest_notification = None

# Variable pour gérer le clear dans le stream
clear_pending = False
notification_clear_pending = False


@app.post("/api/position")
async def receive_position(data: dict):
    global latest_position
    data["timestamp"] = datetime.utcnow().isoformat()
    latest_position = data
    positions_history.append(data)
   
    print(f"✅ Position reçue → Lat: {data.get('lat')}, Lon: {data.get('lon')}")
    return {"status": "ok"}


@app.get("/api/position")
async def get_latest():
    return latest_position or {"status": "no_data_yet"}


# ====================== STREAM POSITION ======================
@app.get("/api/position-stream")
async def position_stream(request: Request):
    global clear_pending
    
    async def event_generator():
        global clear_pending
        while True:
            if await request.is_disconnected():
                break
            
            # Si un clear est en attente, on l'envoie en priorité
            if clear_pending:
                yield f"data: {json.dumps({'type': 'clear'})}\n\n"
                clear_pending = False
                await asyncio.sleep(0.5)
                continue
            
            # Envoi normal de la dernière position en boucle
            if latest_position:
                yield f"data: {json.dumps({'type': 'position', 'data': latest_position})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'no_data'})}\n\n"
            
            await asyncio.sleep(1)
   
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ====================== NOTIFICATIONS ======================
@app.post("/api/notifications")
async def send_notification(notif: dict):
    global latest_notification
    notif["timestamp"] = datetime.utcnow().isoformat()
    latest_notification = notif
    
    print(f"🔔 Notification envoyée : {notif.get('message')}")
    return {"status": "sent"}


@app.get("/api/notifications-stream")
async def notifications_stream(request: Request):
    global notification_clear_pending
    
    async def event_generator():
        global notification_clear_pending
        while True:
            if await request.is_disconnected():
                break
            
            # Si un clear est en attente, on l'envoie en priorité
            if notification_clear_pending:
                yield f"data: {json.dumps({'type': 'clear'})}\n\n"
                notification_clear_pending = False
                await asyncio.sleep(0.5)
                continue
            
            if latest_notification:
                yield f"data: {json.dumps(latest_notification)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'no_notification'})}\n\n"
            
            await asyncio.sleep(1)
   
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/positions/history")
async def get_positions_history():
    return {
        "positions": positions_history,
        "count": len(positions_history)
    }


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "alive", "time": datetime.utcnow().isoformat()}

# ====================== ROUTE CLEAR ======================
@app.delete("/api/positions/clear")
@app.get("/api/positions/clear")
async def clear_all_positions(password: str = Query(..., description="Mot de passe requis")):
    if not CLEAR_PASSWORD:
        raise HTTPException(status_code=500, detail="Configuration du mot de passe manquante")
  
    if password != CLEAR_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
  
    global latest_position, positions_history, clear_pending
    
    latest_position = None
    positions_history.clear()
    clear_pending = True          # ← Important : active le clear dans le stream
    
    print("🗑️ Clear effectué - Signal envoyé dans le position-stream")
    
    return {
        "status": "success",
        "message": "Toutes les positions ont été supprimées avec succès."
    }

# ====================== ROUTE CLEAR NOTIFICATIONS ======================
@app.delete("/api/notifications/clear")
@app.get("/api/notifications/clear")
async def clear_all_notifications(password: str = Query(..., description="Mot de passe requis")):
    if not CLEAR_PASSWORD:
        raise HTTPException(status_code=500, detail="Configuration du mot de passe manquante")
  
    if password != CLEAR_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
  
    global latest_notification
    
    latest_notification = None
    notification_clear_pending = True
    
    print("🗑️ Clear effectué - Signal envoyé dans le notifications-stream")
    
    return {
        "status": "success",
        "message": "Toutes les notifications ont été supprimées avec succès."
    }
