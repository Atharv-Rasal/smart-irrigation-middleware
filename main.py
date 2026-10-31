
import os
import json
import time
import queue
import threading
from collections import deque
from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from fastapi import FastAPI

# MQTT configuration from Render environment variables
MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC = "farm/zone1/sensors"

# Middleware storage
message_queue = queue.Queue(maxsize=200)
history = deque(maxlen=100)
latest_reading = None
latest_decision = None

lock = threading.Lock()
seen_messages = set()

metrics = {
    "received": 0,
    "processed": 0,
    "invalid": 0,
    "duplicates": 0,
    "dropped": 0,
    "queue_depth": 0,
    "mqtt_connected": False,
    "average_latency_ms": 0
}

latency_total = 0
mqtt_client = None


def validate_message(data):
    required = [
        "nodeId", "sequence", "soilMoisture",
        "temperature", "humidity", "rainProbability"
    ]

    if not isinstance(data, dict):
        return False

    if not all(key in data for key in required):
        return False

    try:
        moisture = float(data["soilMoisture"])
        temperature = float(data["temperature"])
        humidity = float(data["humidity"])
        rain = float(data["rainProbability"])
        sequence = int(data["sequence"])

        if not str(data["nodeId"]).strip():
            return False
        if sequence < 0:
            return False
        if not 0 <= moisture <= 100:
            return False
        if not -20 <= temperature <= 80:
            return False
        if not 0 <= humidity <= 100:
            return False
        if not 0 <= rain <= 100:
            return False

        return True

    except (ValueError, TypeError):
        return False


def make_decision(data):
    moisture = float(data["soilMoisture"])
    rain = float(data["rainProbability"])

    if moisture < 30:
        if rain < 60:
            return "IRRIGATE"
        return "DEFER IRRIGATION"

    if moisture <= 45:
        return "MONITOR"

    return "NO IRRIGATION"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        metrics["mqtt_connected"] = True
        client.subscribe(MQTT_TOPIC, qos=1)
        print("Connected to MQTT broker")
        print("Subscribed to:", MQTT_TOPIC)
    else:
        metrics["mqtt_connected"] = False
        print("MQTT connection failed:", reason_code)


def on_disconnect(client, userdata, disconnect_flags,
                  reason_code, properties):
    metrics["mqtt_connected"] = False
    print("MQTT disconnected:", reason_code)


def on_message(client, userdata, msg):
    metrics["received"] += 1

    try:
        data = json.loads(msg.payload.decode("utf-8"))

        if not validate_message(data):
            metrics["invalid"] += 1
            return

        message_id = (str(data["nodeId"]), int(data["sequence"]))

        with lock:
            if message_id in seen_messages:
                metrics["duplicates"] += 1
                return

            seen_messages.add(message_id)

            if len(seen_messages) > 10000:
                seen_messages.clear()
                seen_messages.add(message_id)

        item = {
            "data": data,
            "received_at": time.time()
        }

        try:
            message_queue.put_nowait(item)
        except queue.Full:
            metrics["dropped"] += 1

        metrics["queue_depth"] = message_queue.qsize()

    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        metrics["invalid"] += 1


def worker():
    global latest_reading, latest_decision, latency_total

    while True:
        item = message_queue.get()

        try:
            data = item["data"]
            latency = (time.time() - item["received_at"]) * 1000

            decision = make_decision(data)

            with lock:
                latest_reading = data
                latest_decision = decision

                history.append({
                    **data,
                    "decision": decision,
                    "latency_ms": round(latency, 2)
                })

                metrics["processed"] += 1
                latency_total += latency
                metrics["average_latency_ms"] = round(
                    latency_total / metrics["processed"], 2
                )

        finally:
            message_queue.task_done()
            metrics["queue_depth"] = message_queue.qsize()


def start_mqtt():
    global mqtt_client

    if not MQTT_HOST:
        print("MQTT_HOST not configured")
        return

    mqtt_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv311
    )

    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.tls_set()

    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)

    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=worker, daemon=True).start()

    try:
        start_mqtt()
    except Exception as error:
        print("MQTT startup error:", error)

    yield

    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


app = FastAPI(
    title="Smart Irrigation Middleware API",
    description="MQTT-based smart irrigation monitoring system",
    version="1.0",
    lifespan=lifespan
)


@app.get("/")
def home():
    return {
        "message": "Smart Irrigation Middleware is running",
        "version": "1.0"
    }


@app.get("/health")
def health():
    return {
        "api_status": "running",
        "mqtt_connected": metrics["mqtt_connected"]
    }


@app.get("/readings")
def readings():
    return {
        "latest_reading": latest_reading
    }


@app.get("/decision")
def decision():
    return {
        "decision": latest_decision
    }


@app.get("/metrics")
def get_metrics():
    return {
        **metrics,
        "queue_depth": message_queue.qsize()
    }


@app.get("/history")
def get_history():
    with lock:
        return list(history)


@app.post("/decision/evaluate")
def evaluate(data: dict):
    if not validate_message(data):
        return {
            "status": "error",
            "decision": "DATA UNAVAILABLE",
            "message": "Invalid sensor data"
        }

    return {
        "status": "success",
        "decision": make_decision(data)
    }
