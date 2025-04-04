import paho.mqtt.publish as publish
import json
import os

# Load broker details from environment or use fallback
MQTT_BROKER = os.getenv("MQTT_BROKER", "100.100.100.100")  # Replace with Pi's Tailscale IP
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "shellyplus1pm/rpc"

def send_switch_command(breaker_id: int, state: bool):
    payload = {
        "id": 1,
        "src": "cloud",
        "method": "Switch.Set",
        "params": {
            "id": breaker_id,
            "on": state
        }
    }
    try:
        publish.single(MQTT_TOPIC, json.dumps(payload), hostname=MQTT_BROKER, port=MQTT_PORT)
        print(f"Sent {'ON' if state else 'OFF'} command to breaker {breaker_id}")
    except Exception as e:
        print("MQTT publish error:", e)