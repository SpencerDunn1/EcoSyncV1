from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import threading
import json
import paho.mqtt.client as mqtt

from db import get_db, SessionLocal
from models import PowerReading, BreakerAction
from auth import get_current_user
from users import router as user_router
from mqtt_control import send_switch_command

app = FastAPI()

# Secure session handling
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

# Include user auth routes
app.include_router(user_router)

API_KEY = os.getenv("API_KEY", "supersecurekey")
MQTT_TOPIC_STATUS = "shellyplus1pm-cc7b5c8426cc/events/rpc"

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
    mqtt_host = "localhost"  # local broker on Pi
    client.connect(mqtt_host, 1883)
    client.subscribe(MQTT_TOPIC_STATUS)
    client.loop_start()

# Uncomment to run locally on Pi
# threading.Thread(target=start_mqtt_listener, daemon=True).start()

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
    send_switch_command(breaker_id, True)
    return {"status": f"sent_on_breaker_{breaker_id}"}

@app.post("/breaker/{breaker_id}/off")
def turn_off(breaker_id: int, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    send_switch_command(breaker_id, False)
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

@app.get("/breaker/{breaker_id}/readings")
def get_readings(breaker_id: int, db: Session = Depends(get_db)):
    return db.query(PowerReading).filter_by(breaker_id=breaker_id).order_by(PowerReading.timestamp.desc()).limit(100).all()