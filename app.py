import streamlit as st
import requests
import datetime
import numpy as np

# Page config for clean, compact mobile/tablet display
st.set_page_config(page_title="WashDry Physics", page_icon="🌤️", layout="centered")

# Custom styling for a streamlined, minimal interface
st.markdown("""
<style>
    .main { max-width: 700px; padding-top: 1rem; }
    .slot-box { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; }
    h1 { font-size: 1.8rem !important; margin-bottom: 0.2rem !important; }
    h3 { font-size: 1.2rem !important; margin-top: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)

st.header("WashDry: Whittlesey Forecast")
st.caption("Heuristic & Physics-Based Laundry Drying Engine")

@st.cache_data(ttl=1800)
-def fetch_weather():
    # Whittlesey coordinates
    lat, lon = 52.556, -0.130
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,direct_radiation&timezone=Europe/London"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        return None

data = fetch_weather()

if not data:
    st.error("Unable to fetch weather data from Open-Meteo.")
else:
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humidities = hourly.get("relative_humidity_2m", [])
    winds = hourly.get("wind_speed_10m", [])
    solar = hourly.get("direct_radiation", [])

    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    def analyze_slot(target_date, start_hour, end_hour):
        indices = [
            i for i, t in enumerate(times) 
            if t.startswith(target_date) and start_hour <= datetime.datetime.fromisoformat(t).hour < end_hour
        ]
        if not indices:
            return None, None, None, "No data"

        slot_temp = np.mean([temps[i] for i in indices])
        slot_hum = np.mean([humidities[i] for i in indices])
        slot_wind = np.mean([winds[i] for i in indices])
        slot_solar = np.mean([solar[i] for i in indices])

        # 1. Tetens Equation for Vapor Pressure Deficit (VPD in kPa)
        es = 0.61078 * np.exp((17.27 * slot_temp) / (slot_temp + 237.3))
        ea = es * (slot_hum / 100.0)
        vpd = max(0.0, es - ea)

        # 2. Dalton's Law Mass Transfer Factor
        evap_rate = (0.05 + 0.08 * slot_wind) * vpd + (0.0002 * slot_solar)

        # 3. Heuristic Rating
        if slot_hum < 65 and slot_wind > 8 and vpd > 0.6:
            heuristic = "🟢 Excellent"
        elif slot_hum < 80 and vpd > 0.3:
            heuristic = "🟡 Moderate"
        else:
            heuristic = "🔴 Poor"

        # 4. Physics Rating & Est Time
        if evap_rate > 0.4:
            physics = "🟢 Fast Evaporation"
            est_hours = round(max(1.5, 3.5 - evap_rate * 2), 1)
        elif evap_rate > 0.2:
            physics = "🟡 Steady Evaporation"
            est_hours = round(max(3.0, 6.0 - evap_rate * 3), 1)
        else:
            physics = "🔴 Low Evaporation"
            est_hours = "6h+"

        return heuristic, physics, f"{est_hours} hrs" if isinstance(est_hours, float) else est_hours, f"Temp: {slot_temp:.1f}°C | Hum: {slot_hum:.0f}% | Wind: {slot_wind:.1f} km/h"

    # Display Tabs for Today and Tomorrow
    tab_today, tab_tomorrow = st.tabs(["Today", "Tomorrow"])

    with tab_today:
        st.subheader("Today's Windows")
        for label, start, end in [("Morning (08:00 - 12:00)", 8, 12), ("Afternoon (12:00 - 16:00)", 12, 16)]:
            h, p, t, details = analyze_slot(today_str, start, end)
            st.markdown(f"""
            <div class="slot-box">
                <strong>{label}</strong><br>
                <span>Heuristic: {h} &nbsp;|&nbsp; Physics: {p} &nbsp;|&nbsp; Est: <strong>{t}</strong></span><br>
                <small style="color: #6c757d;">{details}</small>
            </div>
            """, unsafe_allow_html=True)

    with tab_tomorrow:
        st.subheader("Tomorrow's Windows")
        for label, start, end in [("Morning (08:00 - 12:00)", 8, 12), ("Afternoon (12:00 - 16:00)", 12, 16)]:
            h, p, t, details = analyze_slot(tomorrow_str, start, end)
            st.markdown(f"""
            <div class="slot-box">
                <strong>{label}</strong><br>
                <span>Heuristic: {h} &nbsp;|&nbsp; Physics: {p} &nbsp;|&nbsp; Est: <strong>{t}</strong></span><br>
                <small style="color: #6c757d;">{details}</small>
            </div>
            """, unsafe_allow_html=True)
