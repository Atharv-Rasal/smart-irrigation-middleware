
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Smart Irrigation Dashboard",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Smart Irrigation Monitoring Dashboard")
st.caption("Real-time sensor monitoring and irrigation decision middleware")

# ==========================================
# 2. API CONFIGURATION
# ==========================================

try:
    API_URL = st.secrets["API_URL"].rstrip("/")
except Exception:
    API_URL = "https://YOUR-RENDER-APP.onrender.com"

# ==========================================
# 3. API DATA FETCHING FUNCTION
# ==========================================

def get_api_data(endpoint):

    try:
        response = requests.get(
            f"{API_URL}/{endpoint}",
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        st.error(f"Could not connect to /{endpoint}: {error}")
        return None

# ==========================================
# 4. FETCH DATA
# ==========================================

health = get_api_data("health")
readings = get_api_data("readings")
decision = get_api_data("decision")
metrics = get_api_data("metrics")
history = get_api_data("history")

# ==========================================
# 5. MIDDLEWARE CONNECTION STATUS
# ==========================================

st.subheader("Middleware Connection")

if health is not None:
    st.success("Middleware API is responding")
else:
    st.error("Middleware API is unavailable")

st.caption(f"API URL: {API_URL}")

st.divider()


# ==========================================
# 6. LATEST SENSOR READINGS
# ==========================================

st.subheader("Latest Sensor Readings")

if isinstance(readings, dict):

    sensor_data = readings.get("latest_reading")

    if isinstance(sensor_data, dict):

        col1, col2, col3, col4 = st.columns(4)

        soil = sensor_data.get("soilMoisture")
        temperature = sensor_data.get("temperature")
        humidity = sensor_data.get("humidity")
        rain = sensor_data.get("rainProbability")

        col1.metric(
            "Soil Moisture",
            f"{soil}%" if soil is not None else "N/A"
        )

        col2.metric(
            "Temperature",
            f"{temperature} °C" if temperature is not None else "N/A"
        )

        col3.metric(
            "Humidity",
            f"{humidity}%" if humidity is not None else "N/A"
        )

        col4.metric(
            "Rain Probability",
            f"{rain}%" if rain is not None else "N/A"
        )

        with st.expander("View raw sensor data"):
            st.json(sensor_data)

    else:
        st.warning("No sensor readings available yet.")

else:
    st.error("Unable to retrieve sensor readings.")

# ==========================================
# 7. IRRIGATION DECISION
# ==========================================

st.subheader("Irrigation Decision")

if isinstance(decision, dict):

    # Supports common decision field names.
    decision_value = (
        decision.get("decision")
        or decision.get("recommendation")
        or decision.get("status")
        or "Decision not available"
    )

    st.info(f"Current Decision: {decision_value}")

    with st.expander("View decision details"):
        st.json(decision)

elif decision is not None:
    st.json(decision)

else:
    st.warning("No irrigation decision available.")

st.divider()

# ==========================================
# 8. MIDDLEWARE PERFORMANCE METRICS
# ==========================================

st.subheader("Middleware Performance Metrics")

if isinstance(metrics, dict) and metrics:

    metric_items = list(metrics.items())

    columns = st.columns(3)

    for index, (key, value) in enumerate(metric_items):

        with columns[index % 3]:
            st.metric(
                label=key.replace("_", " ").title(),
                value=str(value)
            )

else:
    st.info("No middleware metrics available.")

st.divider()

# ==========================================
# 9. SENSOR HISTORY
# ==========================================

st.subheader("Sensor Reading History")

if isinstance(history, dict):

    # Handle APIs that return {"history": [...]}
    history = history.get("history", [])

if isinstance(history, list) and len(history) > 0:

    df = pd.DataFrame(history)

    st.dataframe(
        df,
        use_container_width=True
    )

    # Plot available numeric sensor columns.
    chart_columns = [
        column for column in
        ["soilMoisture", "temperature", "humidity",
         "rainProbability"]
        if column in df.columns
    ]

    if chart_columns:

        st.subheader("Sensor Data Visualization")

        chart_data = df[chart_columns].apply(
            pd.to_numeric,
            errors="coerce"
        )

        st.line_chart(chart_data)

else:
    st.info("No historical sensor data available yet.")

st.divider()

# ==========================================
# 10. MANUAL REFRESH
# ==========================================

if st.button("Refresh Dashboard"):

    st.rerun()

st.caption(
    "Smart Irrigation Middleware | "
    "ESP32 + MQTT + EMQX + FastAPI + Streamlit"
)
