import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import paho.mqtt.client as mqtt

# --- MQTT Setup ---
MQTT_BROKER = os.getenv("MQTT_HOST", "100.111.203.36")  # Replace with your Pi's Tailscale IP
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "smartbreaker/control"

mqtt_client = mqtt.Client()

def connect_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT ERROR] Connection failed: {e}")

# --- FastAPI App ---
app = FastAPI()

# --- CORS Middleware (for frontend access) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    connect_mqtt()

# --- Health Check ---
@app.get("/ping")
async def ping():
    return {"status": "alive"}

# --- Toggle Endpoint ---
@app.post("/toggle")
async def toggle_breaker(request: Request):
    try:
        data = await request.json()
        breaker_id = data.get("breaker_id")
        state = data.get("state")

        if breaker_id is None or state is None:
            return JSONResponse(status_code=400, content={"success": False, "message": "Missing breaker_id or state"})

        payload = json.dumps({
            "breaker_id": breaker_id,
            "state": state
        })

        result = mqtt_client.publish(MQTT_TOPIC, payload)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[MQTT] Sent to {MQTT_TOPIC}: {payload}")
            return {"success": True, "message": f"Breaker {breaker_id} toggled {'on' if state else 'off'}"}
        else:
            print("[MQTT ERROR] Publish failed")
            return JSONResponse(status_code=500, content={"success": False, "message": "MQTT publish failed"})

    except Exception as e:
        print(f"[ERROR] {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})