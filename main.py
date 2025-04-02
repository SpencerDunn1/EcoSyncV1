from fastapi import FastAPI, Header, HTTPException
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from fastapi.responses import HTMLResponse
import json
import os
import threading

app = FastAPI()

API_KEY = os.getenv("API_KEY", "supersecurekey")
MQTT_HOST = os.getenv("MQTT_HOST", "100.x.x.x")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

MQTT_TOPIC_COMMAND = "shellyplus1pm/rpc"
MQTT_TOPIC_STATUS = "shellyplus1pm/events/rpc"

# Store status separately for two breakers (id 0 and id 1)
latest_status = {
    0: {"status": "unknown"},
    1: {"status": "unknown"}
}

# MQTT listener updates status dict
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("method") == "NotifyStatus" and "params" in payload:
            breaker_id = payload["params"].get("id", 0)
            latest_status[breaker_id] = payload["params"]
    except Exception as e:
        print("Error parsing MQTT message:", e)

def start_mqtt_listener():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.subscribe(MQTT_TOPIC_STATUS)
    client.loop_start()

mqtt_thread = threading.Thread(target=start_mqtt_listener, daemon=True)
mqtt_thread.start()

def verify_token(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/", response_class=HTMLResponse)
def serve_index():
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
