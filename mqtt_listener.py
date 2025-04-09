import paho.mqtt.client as mqtt
import subprocess
import json
import ssl

# ==== Configuration ====
BROKER = "bbe5ab48ebc248ef8d25d63ffc55c86d.s1.eu.hivemq.cloud"  # Replace with your actual HiveMQ Cloud hostname
PORT = 8883
USERNAME = "testuser"             # From HiveMQ Cloud
PASSWORD = "TestPassword123"
TOPIC = "smartbreaker/control"              # You decide what topic to use

# ==== Callback when connection is established ====
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to HiveMQ Cloud.")
        client.subscribe(TOPIC)
        print(f"📡 Subscribed to topic: {TOPIC}")
    else:
        print(f"❌ Failed to connect. Return code: {rc}")

# ==== Callback when message is received ====
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        breaker_id = payload.get("id")
        state = payload.get("state")

        if breaker_id is None or state not in ["on", "off"]:
            print("⚠️ Invalid message format:", payload)
            return

        print(f"🔔 Command received → Breaker {breaker_id}: {state.upper()}")

        # Call mqtt_control.py with the breaker ID and state
        subprocess.run(["python3", "mqtt_control.py", "--id", str(breaker_id), "--state", state])

    except Exception as e:
        print("❗Error processing message:", e)

# ==== MQTT Client Setup ====
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(tls_version=ssl.PROTOCOL_TLS)

client.on_connect = on_connect
client.on_message = on_message

print("🚀 Connecting to HiveMQ Cloud...")
client.connect(BROKER, PORT, keepalive=60)
client.loop_forever()