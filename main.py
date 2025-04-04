import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import paho.mqtt.client as mqtt

# ---------- MQTT Configuration ----------
MQTT_BROKER = os.getenv("MQTT_HOST", "localhost")  # Tailscale IP of Pi
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "smartbreaker/control"

mqtt_client = mqtt.Client()

def connect_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"[MQTT] Connected to broker at {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT ERROR] Could not connect to {MQTT_BROKER}:{MQTT_PORT} -> {e}")

# ---------- FastAPI Setup ----------
app = FastAPI()

# Mount static files
#app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory=".")

# Enable CORS (optional: limit origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    connect_mqtt()

# ---------- Request Model ----------
class ToggleCommand(BaseModel):
    breaker_id: int
    state: bool

# ---------- Routes ----------
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

        print(f"[MQTT] Sending to {MQTT_TOPIC} → {payload}")
        result = mqtt_client.publish(MQTT_TOPIC, payload)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            return {"success": True, "message": f"Breaker {cmd.breaker_id} toggled {'on' if cmd.state else 'off'}"}
        else:
            return JSONResponse(status_code=500, content={"success": False, "message": "MQTT publish failed"})

    except Exception as e:
        print(f"[ERROR] {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# Add these new routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})