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

# Variable pour les notifications (dernière notification)
latest_notification = None

@app.post("/api/position")
async def receive_position(data: dict):
    global latest_position
    data["timestamp"] = datetime.utcnow().isoformat()
    latest_position = data
    positions_history.append(data)
   
    print(f"✅ Position reçue → Lat: {data.get('lat')}, Lon: {data.get('lon')}")
    return {"status": "ok"}


@app.get("/api/position-stream")
async def position_stream(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            if latest_position:
                yield f"data: {json.dumps({'type': 'position', 'data': latest_position})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'no_data'})}\n\n"
            
            await asyncio.sleep(1)
   
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ====================== NOTIFICATIONS (même principe que position) ======================
@app.post("/api/notifications")
async def send_notification(notif: dict):
    global latest_notification
    notif["timestamp"] = datetime.utcnow().isoformat()
    latest_notification = notif
    
    print(f"🔔 Notification envoyée : {notif.get('message')}")
    return {"status": "sent"}


@app.get("/api/notifications-stream")
async def notifications_stream(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            if latest_notification:
                yield f"data: {json.dumps(latest_notification)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'no_notification'})}\n\n"
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
