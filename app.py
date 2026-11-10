from datetime import datetime, timedelta
import numpy as np
import requests
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="WashDry Weather", page_icon="🧺", layout="centered"
)


# --- RATING FUNCTIONS ---
def get_heuristic_drying_score(temp, humidity, rain_prob, wind_speed):
  """Original rule-based drying score (1 to 5)."""
  score = 3
  if temp > 18:
    score += 1
  elif temp < 10:
    score -= 1

  if humidity < 60:
    score += 1
  elif humidity > 85:
    score -= 1

  if rain_prob > 40:
    score -= 2

  if wind_speed > 10:
    score += 1

  return int(np.clip(score, 1, 5))


def get_physics_drying_score_and_time(temp, humidity, rain_prob, wind_speed):
  """Physics-based score using Vapor Pressure Deficit (VPD) & Dalton's Law."""
  if rain_prob > 40:
    return 1, "N/A (Rain)"

  # 1. Tetens Equation for Saturation Vapor Pressure (kPa)
  es = 0.61121 * np.exp((17.502 * temp) / (temp + 240.97))
  ea = es * (humidity / 100.0)
  vpd = max(0.0, es - ea)

  # 2. Dalton's Wind Factor (convert mph to m/s)
  wind_ms = wind_speed * 0.44704
  evaporation_potential = vpd * (1.0 + 0.5 * wind_ms)

  # 3. Map Evaporation Potential to 1-5 Scale
  if evaporation_potential < 0.3:
    p_score = 1
  elif evaporation_potential < 0.8:
    p_score = 2
  elif evaporation_potential < 1.5:
    p_score = 3
  elif evaporation_potential < 2.5:
    p_score = 4
  else:
    p_score = 5

  # 4. Estimate Drying Time in Hours
  if evaporation_potential < 0.1:
    est_time = "N/A"
  else:
    hours = np.clip(3.5 / evaporation_potential, 1.5, 10.0)
    est_time = f"~{round(hours * 2) / 2} hrs"

  return p_score, est_time


# --- WEATHER DATA FETCHING ---
@st.cache_data(ttl=1800)
def fetch_weather_data():
  """Fetch hourly forecast for Whittlesey (52.556, -0.130)."""
  url = "https://api.open-meteo.com/v1/forecast"
  params = {
      "latitude": 52.556,
      "longitude": -0.130,
      "hourly": [
          "temperature_2m",
          "relative_humidity_2m",
          "precipitation_probability",
          "wind_speed_10m",
      ],
      "wind_speed_unit": "mph",
      "timezone": "Europe/London",
  }
  try:
    response = requests.get(url, params=params, timeout=5)
    response.raise_for_status()
    return response.json()
  except Exception:
    return None


# --- HELPER TO CALCULATE SLOT METRICS ---
def process_slot(hourly, times, target_date_str, start_hour, end_hour):
  target_hours = [
      f"{target_date_str}T{hour:02d}:00"
      for hour in range(start_hour, end_hour)
  ]
  indices = [i for i, t in enumerate(times) if t in target_hours]

  if not indices:
    return None

  avg_temp = float(np.mean([hourly["temperature_2m"][i] for i in indices]))
  avg_humidity = float(
      np.mean([hourly["relative_humidity_2m"][i] for i in indices])
  )
  max_rain = float(
      max([hourly["precipitation_probability"][i] for i in indices])
  )
  avg_wind = float(np.mean([hourly["wind_speed_10m"][i] for i in indices]))

  h_score = get_heuristic_drying_score(
      avg_temp, avg_humidity, max_rain, avg_wind
  )
  p_score, est_time = get_physics_drying_score_and_time(
      avg_temp, avg_humidity, max_rain, avg_wind
  )

  return {
      "temp": avg_temp,
      "humidity": avg_humidity,
      "rain": max_rain,
      "wind": avg_wind,
      "h_score": h_score,
      "p_score": p_score,
      "est_time": est_time,
  }


# --- MAIN APP INTERFACE ---
st.title("🧺 WashDry Weather")

data = fetch_weather_data()

if data and "hourly" in data:
  hourly = data["hourly"]
  times = hourly.get("time", [])

  today_str = datetime.now().strftime("%Y-%m-%d")
  tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

  # Define slots to display
  slots = [
      ("Morning (08:00 – 12:00)", 8, 12),
      ("Afternoon (12:00 – 16:00)", 12, 16),
  ]

  days = [("Today", today_str), ("Tomorrow", tomorrow_str)]

  for day_label, date_str in days:
    st.subheader(f"📅 {day_label} ({date_str})")

    for slot_label, start_h, end_h in slots:
      result = process_slot(hourly, times, date_str, start_h, end_h)

      if result:
        st.markdown(f"**{slot_label}**")
        col1, col2, col3 = st.columns(3)
        with col1:
          st.metric(label="Heuristic", value=f"{result['h_score']} / 5")
        with col2:
          st.metric(label="Physics", value=f"{result['p_score']} / 5")
        with col3:
          st.metric(label="Est. Time", value=result["est_time"])

        st.caption(
            f"Temp: {result['temp']:.1f}°C | Humidity:"
            f" {result['humidity']:.0f}% | Rain Risk: {result['rain']:.0f}% |"
            f" Wind: {result['wind']:.1f} mph"
        )
        st.divider()
      else:
        st.info(f"Data for {day_label} {slot_label} not yet available.")
else:
  st.error("Unable to load weather data.")
