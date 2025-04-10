from fastapi import FastAPI, Header, HTTPException, Depends, Request, APIRouter
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import json
import os
import threading
import json
import ssl
from db import get_db, SessionLocal
from models import PowerReading, BreakerAction
from auth import get_current_user
from users import router as user_router
from pydantic import BaseModel
from decimal import Decimal

class SwitchRequest(BaseModel):
    breaker_id: str
    state: str  # expects "true" or "false" as strings

class PowerReading(BaseModel):
    breaker_id: str
    power: float
    voltage: float
    current: float
app = FastAPI()
router = APIRouter()

# Add secure session middleware for login handling
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

# Mount static folder if needed (e.g., for JS/CSS/images)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Include auth routes for login, signup, logout
app.include_router(user_router)

API_KEY = os.getenv("API_KEY", "supersecurekey")
MQTT_HOST = os.getenv("MQTT_HOST", "100.x.x.x")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

MQTT_TOPIC_COMMAND = "shellyplus1pm/rpc"
MQTT_TOPIC_STATUS = "shellyplus1pm/events/rpc"

# Store status separately for two breakers
latest_status = {
    0: {"status": "unknown"},
    1: {"status": "unknown"}
}

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("method") == "NotifyStatus" and "params" in payload:
            breaker_id = payload["params"].get("id", 0)
            latest_status[breaker_id] = payload["params"]

            # Store the reading in the database
            db = SessionLocal()
            reading = PowerReading(
                breaker_id=breaker_id,
                power=payload["params"].get("apower"),
                voltage=payload["params"].get("voltage"),
                current=payload["params"].get("current")
            )
            db.add(reading)
            db.commit()
            db.close()

    except Exception as e:
        print("Error parsing MQTT message:", e)

def start_mqtt_listener():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.subscribe(MQTT_TOPIC_STATUS)
    client.loop_start()

# Uncomment this to enable MQTT connection after setup
# mqtt_thread = threading.Thread(target=start_mqtt_listener, daemon=True)
# mqtt_thread.start()

def verify_token(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/login")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    with open("index.html", "r") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@app.post("/breaker/{breaker_id}/on")
def turn_on(breaker_id: int, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {"id": breaker_id, "on": True}
    }
    publish.single(MQTT_TOPIC_COMMAND, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)
    return {"status": f"sent_on_breaker_{breaker_id}"}

@app.post("/breaker/{breaker_id}/off")
def turn_off(breaker_id: int, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {"id": breaker_id, "on": False}
    }
    publish.single(MQTT_TOPIC_COMMAND, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)
    return {"status": f"sent_off_breaker_{breaker_id}"}

@app.get("/breaker/{breaker_id}/status")
def get_status(breaker_id: int, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    return latest_status.get(breaker_id, {"status": "not_found"})

@app.post("/breaker/{breaker_id}/log")
def log_reading(breaker_id: int, data: dict, db: Session = Depends(get_db)):
    reading = PowerReading(
        breaker_id=breaker_id,
        power=data.get("power"),
        voltage=data.get("voltage"),
        current=data.get("current")
    )
    db.add(reading)
    db.commit()
    return {"status": "reading_logged"}


@app.post("/switch")
async def switch_breaker(req: SwitchRequest):
    breaker_id = req.breaker_id
    state = req.state

    if state not in ["true", "false"]:
        raise HTTPException(status_code=400, detail="State must be 'true' or 'false'")

    payload = {
        "id": breaker_id,
        "state": state
    }

    try:
        publish.single(
            topic="smartbreaker/control",
            payload=json.dumps(payload),
            hostname="bbe5ab48ebc248ef8d25d63ffc55c86d.s1.eu.hivemq.cloud",
            port=8883,
            auth={
                'username': 'testuser',
                'password': 'TestPassword123'
            },
            tls=ssl.create_default_context()
        )
        return {"message": f"Sent {state} command to breaker {breaker_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MQTT publish failed: {e}")
    
@router.post("/api/switch")
def switch_breaker(breaker_id: str, state: str):
    if state not in ["true", "false"]:
        raise HTTPException(status_code=400, detail="Invalid state: must be 'true' or 'false'")

    payload = {
        "id": breaker_id,
        "state": state
    }

    try:
        publish.single(
            topic="smartbreaker/control",
            payload=json.dumps(payload),
            hostname="bbe5ab48ebc248ef8d25d63ffc55c86d.s1.eu.hivemq.cloud",
            port=8883,
            auth={
                'username': 'testuser',
                'password': 'TestPassword123'
            },
            tls=ssl.create_default_context()
        )
        return {"message": f"Sent {state} command to breaker {breaker_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MQTT publish failed: {e}")
    
@app.get("/breaker/{breaker_id}/readings")
def get_readings(breaker_id: int, db: Session = Depends(get_db)):
    return db.query(PowerReading).filter_by(breaker_id=breaker_id).order_by(PowerReading.timestamp.desc()).limit(100).all()

latest_readings = {}  # Store in memory for now

@app.post("/reading")
async def receive_reading(data: PowerReading):
    latest_readings[data.breaker_id] = data
    return {"status": "received"}

@app.get("/reading/latest")
async def get_latest(breaker_id: str):
    reading = latest_readings.get(breaker_id)
    return reading if reading else {"error": "No data yet"}
