from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime

app = FastAPI(title="Robot Live Tracking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== STOCKAGE ======================
latest_position = None
positions_history = []  # ✅ FIX ajouté

# ====================== ROUTES ======================

@app.post("/api/position")
async def receive_position(data: dict):
    global latest_position, positions_history
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
                yield f"data: {json.dumps(latest_position)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ✅ FIX PRINCIPAL : support GET + HEAD
@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {
        "status": "alive",
        "time": datetime.utcnow().isoformat()
    }


@app.get("/api/position")
async def get_latest():
    return latest_position or {"status": "no_data_yet"}


# ====================== ADMIN ======================
from fastapi import HTTPException, Query

# Mot de passe de protection (change-le par quelque chose de plus fort !)
CLEAR_PASSWORD = "UltimateIA_ntm"   # ← À modifier selon ce que tu veux

@app.delete("/api/positions/clear")
@app.get("/api/positions/clear")   # On garde GET pour faciliter les tests
async def clear_all_positions(password: str = Query(..., description="Mot de passe requis pour effacer les positions")):
    """Supprime toutes les positions seulement si le bon mot de passe est fourni"""
    
    if password != CLEAR_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Mot de passe incorrect. Accès refusé."
        )
    
    global latest_position, positions_history
    latest_position = None
    positions_history.clear()
    
    print("🗑️ Toutes les positions ont été supprimées (mot de passe validé)")
    
    return {
        "status": "success",
        "message": "Toutes les positions ont été supprimées avec succès."
    }
