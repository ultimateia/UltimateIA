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

latest_position = None

@app.post("/api/position")
async def receive_position(data: dict):
    global latest_position
    data["timestamp"] = datetime.utcnow().isoformat()
    latest_position = data
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

@app.get("/ping")
async def ping():
    return {"status": "alive", "time": datetime.utcnow().isoformat()}

@app.get("/api/position")
async def get_latest():
    return latest_position or {"status": "no_data_yet"}

# ====================== NOUVELLE ROUTE ======================
@app.delete("/api/positions/clear")
async def clear_all_positions():
    """Supprime toutes les positions enregistrées (latest + historique)"""
    global latest_position, positions_history
    latest_position = None
    positions_history.clear()
    print("🗑️ Toutes les positions ont été supprimées")
    return {"status": "success", "message": "Toutes les positions ont été supprimées"}
