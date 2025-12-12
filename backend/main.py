from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session as DbSession, select
from contextlib import asynccontextmanager
import asyncio
import json
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from .models import create_db_and_tables, engine, Slot, Session
from .serial_bridge import SerialBridge

# --- CONFIGURATION ---
TOTAL_SLOTS_DEFAULT = 4
QR_TOKEN_TTL = 90  # seconds
SESSION_TTL = 12 * 3600  # 12 hours
SERIAL_PORT = "COM3" # CHANGE THIS TO YOUR ARDUINO PORT

# --- STATE ---
serial_bridge = SerialBridge(port=SERIAL_PORT)
active_websockets: List[WebSocket] = []
# Sensor State (True = Car Present/Blocked, False = Clear)
sensor_state = {
    "entry": False,
    "exit": False
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    
    # Initialize slots if empty
    with DbSession(engine) as db:
        slots = db.exec(select(Slot)).all()
        if not slots:
            for i in range(1, TOTAL_SLOTS_DEFAULT + 1):
                db.add(Slot(id=i, status="free"))
            db.commit()
            
    global app_loop
    app_loop = asyncio.get_running_loop()
    
    serial_bridge.start(handle_serial_event)
    # Wait for Arduino to boot (DTR reset)
    await asyncio.sleep(2)
    # Query initial sensor state
    serial_bridge.send_command("CMD:SENSORS")
    yield
    serial_bridge.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC MOUNTS ---
app.mount("/operator", StaticFiles(directory="operator_ui", html=True), name="operator")
app.mount("/pwa", StaticFiles(directory="pwa_app", html=True), name="pwa")

@app.get("/")
async def root():
    return RedirectResponse(url="/operator")

# --- MODELS ---
class QREntryResponse(BaseModel):
    token: str
    expires_at: str
    url: str

class ClaimEntryRequest(BaseModel):
    token: str
    device_id: Optional[str] = None

class ClaimExitRequest(BaseModel):
    token: Optional[str] = None
    session: Optional[str] = None

class SetSlotsRequest(BaseModel):
    total_slots: int

# --- HELPERS ---
async def broadcast_event(event_type: str, data: dict = {}):
    message = {"type": event_type, **data}
    json_msg = json.dumps(message)
    to_remove = []
    for ws in active_websockets:
        try:
            await ws.send_text(json_msg)
        except:
            to_remove.append(ws)
    for ws in to_remove:
        active_websockets.remove(ws)

# Global loop reference
app_loop = None

def handle_serial_event(line: str):
    # Run in event loop if needed, or just broadcast
    # Since this is called from a thread, we need to be careful with async
    if app_loop:
        asyncio.run_coroutine_threadsafe(broadcast_serial_event(line), app_loop)

async def broadcast_serial_event(line: str):
    if "EVENT:GATE_OPENED" in line:
        await broadcast_event("gate_opened")
    elif "EVENT:GATE_CLOSED" in line:
        await broadcast_event("gate_closed")
    elif "EVENT:BEAM:ENTRY:LOW" in line:
        sensor_state["entry"] = True
        await broadcast_event("beam_entry", {"state": "blocked"})
    elif "EVENT:BEAM:ENTRY:HIGH" in line:
        sensor_state["entry"] = False
        await broadcast_event("beam_entry", {"state": "clear"})
    elif "EVENT:BEAM:EXIT:LOW" in line:
        sensor_state["exit"] = True
        await broadcast_event("beam_exit", {"state": "blocked"})
    elif "EVENT:BEAM:EXIT:HIGH" in line:
        sensor_state["exit"] = False
        await broadcast_event("beam_exit", {"state": "clear"})
    elif "INFO:SENSORS:" in line:
        # Format: INFO:SENSORS:ENTRY:LOW:EXIT:HIGH
        try:
            parts = line.split(":")
            # parts[0]=INFO, [1]=SENSORS, [2]=ENTRY, [3]=VAL, [4]=EXIT, [5]=VAL
            entry_val = parts[3]
            exit_val = parts[5]
            
            sensor_state["entry"] = (entry_val == "LOW")
            sensor_state["exit"] = (exit_val == "LOW")
            
            # Broadcast initial state
            await broadcast_event("beam_entry", {"state": "blocked" if sensor_state["entry"] else "clear"})
            await broadcast_event("beam_exit", {"state": "blocked" if sensor_state["exit"] else "clear"})
        except:
            pass

# --- API ---

@app.post("/api/admin/set_slots")
def set_slots(req: SetSlotsRequest):
    with DbSession(engine) as db:
        db.exec(Slot.__table__.delete())
        for i in range(1, req.total_slots + 1):
            db.add(Slot(id=i, status="free"))
        db.commit()
    return {"ok": True}

class GateControlRequest(BaseModel):
    command: str # "open" or "close"

@app.post("/api/admin/gate")
def control_gate(req: GateControlRequest):
    cmd = "CMD:OPEN" if req.command == "open" else "CMD:CLOSE"
    if serial_bridge.send_command(cmd):
        return {"ok": True}
    return {"ok": False, "reason": "Failed to send command"}

@app.get("/api/slots")
def get_slots():
    with DbSession(engine) as db:
        slots = db.exec(select(Slot)).all()
        total = len(slots)
        free = len([s for s in slots if s.status == "free"])
        return {"total": total, "free": free, "slots": slots}

# In-memory token store for simplicity (or use DB)
# Token -> {expires: datetime, type: 'entry'|'exit'}
pending_tokens = {}

@app.get("/api/qr/entry", response_model=QREntryResponse)
def get_qr_entry():
    token = secrets.token_urlsafe(16)
    expires = datetime.now() + timedelta(seconds=QR_TOKEN_TTL)
    pending_tokens[token] = {"expires": expires, "type": "entry"}
    
    # Clean up old tokens
    now = datetime.now()
    to_del = [k for k, v in pending_tokens.items() if v["expires"] < now]
    for k in to_del: del pending_tokens[k]
    
    return {
        "token": token,
        "expires_at": expires.isoformat(),
        "url": f"http://localhost:8000/claim?tk={token}" # Placeholder
    }

@app.get("/api/qr/exit", response_model=QREntryResponse)
def get_qr_exit():
    token = secrets.token_urlsafe(16)
    expires = datetime.now() + timedelta(seconds=QR_TOKEN_TTL)
    pending_tokens[token] = {"expires": expires, "type": "exit"}
    return {
        "token": token,
        "expires_at": expires.isoformat(),
        "url": f"http://localhost:8000/exit?tk={token}"
    }

@app.post("/api/claim/entry")
async def claim_entry(req: ClaimEntryRequest):
    print(f"DEBUG: claim_entry called with token={req.token}")
    # Validate Token
    if req.token not in pending_tokens:
        raise HTTPException(400, "Invalid or expired token")
    
    data = pending_tokens[req.token]
    if datetime.now() > data["expires"]:
        del pending_tokens[req.token]
        raise HTTPException(400, "Token expired")
    
    if data["type"] != "entry":
        raise HTTPException(400, "Invalid token type")

    # Check Sensor LIVE
    snapshot = serial_bridge.get_sensor_snapshot()
    if not snapshot:
        return {"ok": False, "reason": "Sensor Check Failed (Timeout)"}
    
    if not snapshot["entry"]:
        return {"ok": False, "reason": "Please drive up to the Entry Gate first."}

    # Assign Slot
    with DbSession(engine) as db:
        # Find first free slot
        slot = db.exec(select(Slot).where(Slot.status == "free").order_by(Slot.id)).first()
        if not slot:
            return {"ok": False, "reason": "FULL"}
        
        # Create Session
        session_id = secrets.token_urlsafe(16)
        new_session = Session(id=session_id, token=req.token, slot_id=slot.id)
        db.add(new_session)
        
        # Reserve Slot
        slot.status = "reserved"
        slot.session_id = session_id
        db.add(slot)
        db.commit()
        db.refresh(slot)
        
        # Consume token
        del pending_tokens[req.token]
        
        # Open Gate
        if not serial_bridge.send_command("CMD:OPEN"):
             # Fallback if gate offline, still allow logic but warn?
             # Spec says return GATE_OFFLINE
             # But we already reserved... rollback?
             # For prototype, let's assume we want to proceed but warn.
             # Actually spec says: respond {ok:false, reason:"GATE_OFFLINE"}
             # So we should rollback.
             slot.status = "free"
             slot.session_id = None
             db.delete(new_session)
             db.commit()
             return {"ok": False, "reason": "GATE_OFFLINE"}

        await broadcast_event("slot_reserved", {"slot": slot.id, "session": session_id})
        
        return {
            "ok": True,
            "slot": slot.id,
            "session": session_id,
            "ttl_seconds": SESSION_TTL
        }

@app.post("/api/session/{sid}/confirm_parked")
async def confirm_parked(sid: str):
    with DbSession(engine) as db:
        session = db.exec(select(Session).where(Session.id == sid)).first()
        if not session:
            raise HTTPException(404, "Session not found")
        
        slot = db.exec(select(Slot).where(Slot.id == session.slot_id)).first()
        if slot:
            slot.status = "occupied"
            db.add(slot)
            db.commit()
            await broadcast_event("slot_occupied", {"slot": slot.id})
            return {"ok": True}
    raise HTTPException(400, "Slot not found")

@app.post("/api/claim/exit")
async def claim_exit(req: ClaimExitRequest):
    # Either token (scan exit QR) or session (app button)
    # If token, just validate it allows exit, but we still need to know WHICH session/slot to free.
    # The spec says: "scan exit QR or press Exit if authenticated".
    # If scanning exit QR, the phone must send the session_id it holds.
    
    if not req.session:
        raise HTTPException(400, "Session ID required")

    with DbSession(engine) as db:
        session = db.exec(select(Session).where(Session.id == req.session)).first()
        if not session or not session.is_active:
             raise HTTPException(400, "Invalid session")
        
        # If token provided, validate it
        if req.token:
            if req.token not in pending_tokens:
                 raise HTTPException(400, "Invalid exit token")
            del pending_tokens[req.token]

        # Check Sensor LIVE
        snapshot = serial_bridge.get_sensor_snapshot()
        if not snapshot:
            return {"ok": False, "reason": "Sensor Check Failed (Timeout)"}
            
        if not snapshot["exit"]:
            return {"ok": False, "reason": "Please drive up to the Exit Gate first."}

        # Open Gate
        if not serial_bridge.send_command("CMD:OPEN"):
            return {"ok": False, "reason": "GATE_OFFLINE"}
            
        # Free slot immediately or wait for beam?
        # Spec: "Backend will mark slot free once it receives confirmation (EVENT:BEAM...) or after successful exit confirmation"
        # For simplicity in this prototype, let's mark it free here or have a separate confirm endpoint.
        # Let's auto-free here for simplicity as "Exit confirmation" from app might be this call itself.
        
        slot = db.exec(select(Slot).where(Slot.id == session.slot_id)).first()
        if slot:
            slot.status = "free"
            slot.session_id = None
            db.add(slot)
        
        session.is_active = False
        session.end_time = datetime.now()
        db.add(session)
        db.commit()
        
        await broadcast_event("slot_freed", {"slot": slot.id if slot else 0})
        
        return {"ok": True, "slot": slot.id if slot else 0}

@app.get("/api/debug/sensors")
def debug_sensors():
    return sensor_state

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
