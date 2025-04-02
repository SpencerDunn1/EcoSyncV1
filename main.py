from fastapi import FastAPI, Header, HTTPException
import paho.mqtt.publish as publish
import json
import os

app = FastAPI()

# Environment variables for API key and MQTT broker config
API_KEY = os.getenv("API_KEY", "supersecurekey")
MQTT_HOST = os.getenv("MQTT_HOST", "100.x.x.x")  # Replace with your Pi's Tailscale IP
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "shellyplus1pm/rpc"  # Topic the Shelly device subscribes to

# API key validation
def verify_token(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Endpoint to turn ON the breaker
@app.post("/breaker/on")
def turn_on(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {"id": 0, "on": True}
    }
    publish.single(
        MQTT_TOPIC,
        json.dumps(payload),
        hostname=MQTT_HOST,
        port=MQTT_PORT
    )
    return {"status": "sent_on"}

# Endpoint to turn OFF the breaker
@app.post("/breaker/off")
def turn_off(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {"id": 0, "on": False}
    }
    publish.single(
        MQTT_TOPIC,
        json.dumps(payload),
        hostname=MQTT_HOST,
        port=MQTT_PORT
    )
    return {"status": "sent_off"}
