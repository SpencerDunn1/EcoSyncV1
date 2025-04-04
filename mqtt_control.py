import paho.mqtt.publish as publish
import json
import os

# Broker details (Raspberry Pi running Mosquitto — reachable via Tailscale IP)
MQTT_BROKER = os.getenv("MQTT_BROKER", "100.110.222.33")  # Replace with your actual Tailscale IP
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "shellyplus1pm/rpc"

def send_switch_command(breaker_id: int, state: bool):
    """
    Publishes a Switch.Set command to the Shelly breaker via MQTT
    :param breaker_id: Usually 0
    :param state: True for ON, False for OFF
    """
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
        print(f"Sending to broker {MQTT_BROKER}:{MQTT_PORT}")
        print("Payload:", json.dumps(payload, indent=2))
        publish.single(
            topic=MQTT_TOPIC,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT
        )
        print(f"✅ Sent {'ON' if state else 'OFF'} command to breaker {breaker_id}")
    except Exception as e:
        print("❌ MQTT publish error:", e)