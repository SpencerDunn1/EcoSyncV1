import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import paho.mqtt.client as mqtt

# ----------- MQTT Setup -------------
MQTT_BROKER = os.getenv("MQTT_HOST", "100.111.203.36")  # Pi’s Tailscale IP or fallback
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "smartbreaker/control"

mqtt_client = mqtt.Client()

def connect_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT ERROR] Could not connect: {e}")

# ----------- FastAPI Setup ----------
app = FastAPI()

# Enable CORS for local testing or cross-origin frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Limit in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    connect_mqtt()

# ----------- Request Model ----------
class ToggleCommand(BaseModel):
    breaker_id: int
    state: bool

# ----------- Routes -----------------
@app.get("/ping")
async def ping():
    return {"status": "alive"}

@app.post("/toggle")
async def toggle_breaker(cmd: ToggleCommand):
    try:
        payload = json.dumps({
            "breaker_id": cmd.breaker_id,
            "state": cmd.state
        })

        result = mqtt_client.publish(MQTT_TOPIC, payload)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[MQTT] Published: {payload}")
            return {"success": True, "message": f"Breaker {cmd.breaker_id} toggled {'on' if cmd.state else 'off'}"}
        else:
            print(f"[MQTT ERROR] Publish failed with code {result.rc}")
            return JSONResponse(status_code=500, content={"success": False, "message": "MQTT publish failed"})

    except Exception as e:
        print(f"[ERROR] {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})