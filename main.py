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
notifications_history = []

# Variable pour gérer le clear dans le stream
clear_pending = False

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
# @app.post("/api/notification")
# async def send_notification(notif: dict):
#     global latest_notification
#     notif["timestamp"] = datetime.utcnow().isoformat()
#     latest_notification = notif
    
#     print(f"🔔 Notification envoyée : {notif.get('message')}")
#     return {"status": "sent"}

@app.post("/api/notification")
async def send_notification(notif: dict):
    global latest_notification
    
    if latest_notification:
        notif["id"] = latest_notification["id"]+1
    else:
        notif["id"] = 0
    notif["seen"] = []                         
    notif["timestamp"] = datetime.utcnow().isoformat()
    
    latest_notification = notif
    
    print(f"🔔 Notification envoyée → ID: {notif['id']} | Message: {notif.get('message')}")
    
    return {
        "status": "sent",
        "notification_id": notif["id"]
    }

@app.post("/api/notification/add-to-history")
async def add_notification_to_history(notif: dict):
    if notif not in notifications_history:
        notifications_history.append(notif)
        print(notif)
        print(notifications_history)
    else:
        print("already exists")

@app.get("/api/notifications/history")
async def get_notifications_history():
    return {
        "notifications": notifications_history,
        "count": len(notifications_history)
    }

# ====================== MARQUER UNE NOTIFICATION COMME VUE ======================
@app.post("/api/notifications/{notification_id}/seen")
async def mark_notification_as_seen(notification_id: int, user: dict):    
    """Ajoute un utilisateur dans la liste 'seen' d'une notification de l'historique"""
    
    # Recherche de la notification dans l'historique
    print(notifications_history)
    print("-----------")
    print(dict(notifications_history))
    notification = next((n for n in dict(notifications_history)["notif"] if n.get("id") == notification_id), None)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    
    if "seen" not in notification:
        notification["seen"] = []
    
    new_entry = {
        "user_id": user.get("user_id"),
        "username": user.get("username", "unknown"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Évite les doublons
    if not any(entry.get("user_id") == user.get("user_id") for entry in notification["seen"]):
        notification["seen"].append(new_entry)
        print(f"👁️ Notification {notification_id} marquée comme vue par {user.get('username')}")
        print(notification)
    else:
        print(f"Notification {notification_id} déjà vue par cet utilisateur")
    
    return {
        "status": "success",
        "message": f"Notification {notification_id} marquée comme vue",
        "seen_count": len(notification["seen"])
    }

# ====================== STREAM NOTIFICATIONS ======================
@app.get("/api/notifications-stream")
async def notifications_stream(request: Request):
   
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
           
            # Envoi normal de la dernière notification
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
    notifications_history.clear()
    
    print("🗑️ Clear effectué - Signal envoyé dans le notifications-stream")
    
    return {
        "status": "success",
        "message": "Toutes les notifications ont été supprimées avec succès."
    }
