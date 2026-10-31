# Smart Irrigation Decision Middleware

## Project Description
An IoT-based smart irrigation system using ESP32 sensor simulation, MQTT communication, Python middleware and a web dashboard.

## Architecture
Wokwi ESP32 → EMQX MQTT Broker → Python Middleware → FastAPI REST API → Streamlit Dashboard

## Sensors
- Potentiometer: Soil moisture simulation
- DHT22: Temperature and humidity
- Pushbutton: Rain probability simulation

## Middleware Functions
- MQTT message reception
- Sensor data validation
- FIFO message queue
- Duplicate message detection
- Irrigation decision engine
- Performance monitoring

## Irrigation Decision Rules
- Soil moisture below 30% and rain below 60%: IRRIGATE
- Soil moisture below 30% and rain at least 60%: DEFER IRRIGATION
- Soil moisture from 30% to 45%: MONITOR
- Soil moisture above 45%: NO IRRIGATION
- Invalid data: DATA UNAVAILABLE

## Technologies
- ESP32
- Wokwi
- MQTT
- EMQX Cloud
- Python
- FastAPI
- Render
- Streamlit

## API Endpoints
- /
- /health
- /readings
- /decision
- /metrics
- /history
- /decision/evaluate
