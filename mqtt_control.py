import paho.mqtt.publish as publish
import json
import os
import socket

# Broker details
MQTT_BROKER = os.getenv("MQTT_BROKER", "100.110.222.33")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", None)  # Add if you have auth enabled
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)  # Add if you have auth enabled
MQTT_TOPIC = "shellyplus1pm-cc7b5c8426cc/rpc"
MQTT_TIMEOUT = 10  # seconds

def send_switch_command(breaker_id: int, state: bool):
    """
    Publishes a Switch.Set command to the Shelly breaker via MQTT
    :param breaker_id: Usually 0
    :param state: True for ON, False for OFF
    :returns: tuple (success: bool, message: str)
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

    # Prepare auth if credentials are provided
    auth = None
    if MQTT_USERNAME and MQTT_PASSWORD:
        auth = {'username': MQTT_USERNAME, 'password': MQTT_PASSWORD}

    try:
        # First check if broker is reachable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(MQTT_TIMEOUT)
        result = sock.connect_ex((MQTT_BROKER, MQTT_PORT))
        sock.close()
        
        if result != 0:
            raise ConnectionError(f"Cannot connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")

        # Send MQTT message
        publish.single(
            topic=MQTT_TOPIC,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            auth=auth,
            client_id=f"ecosync_web_{os.getpid()}",
            keepalive=MQTT_TIMEOUT,
        )
        
        return True, f"Successfully sent {'ON' if state else 'OFF'} command to breaker {breaker_id}"

    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        print(f"❌ MQTT error: {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Failed to send MQTT message: {str(e)}"
        print(f"❌ MQTT error: {error_msg}")
        return False, error_msg