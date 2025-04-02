from fastapi import FastAPI, Header, HTTPException
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from fastapi.responses import HTMLResponse
import json
import os
import threading

app = FastAPI()

# 🔐 Environment-secured config
API_KEY = os.getenv("API_KEY", "supersecurekey")
MQTT_HOST = os.getenv("MQTT_HOST", "100.x.x.x")  # Your Pi's Tailscale IP
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

# 📡 MQTT Topics
MQTT_TOPIC_COMMAND = "shellyplus1pm/rpc"
MQTT_TOPIC_STATUS = "shellyplus1pm/events/rpc"

# 🧠 Live status store
latest_status = {"status": "unknown"}

# 🔄 MQTT listener to update status
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("method") == "NotifyStatus" and "params" in payload:
            latest_status.update(payload["params"])
    except Exception as e:
        print("Error parsing MQTT message:", e)

def start_mqtt_listener():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.subscribe(MQTT_TOPIC_STATUS)
    client.loop_start()

# Start the MQTT listener thread
mqtt_thread = threading.Thread(target=start_mqtt_listener, daemon=True)
mqtt_thread.start()

# 🔐 Auth helper
def verify_token(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    with open("index.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

# 🔌 Turn ON breaker
@app.post("/breaker/on")
def turn_on(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {"id": 0, "on": True}
    }
    publish.single(MQTT_TOPIC_COMMAND, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)
    return {"status": "sent_on"}

# 🔌 Turn OFF breaker
@app.post("/breaker/off")
def turn_off(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {"id": 0, "on": False}
    }
    publish.single(MQTT_TOPIC_COMMAND, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)
    return {"status": "sent_off"}

# 📊 Get real-time breaker status
@app.get("/breaker/status")
def get_status(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    return latest_status
