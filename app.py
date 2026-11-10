import numpy as np
import streamlit as st


def get_heuristic_drying_score(temp, humidity, rain_prob, wind_speed):
  """Your original rule-based score (1 to 5)."""
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
  """Calculates physics-based score (VPD + Dalton) and estimated hours."""
  if rain_prob > 40:
    return 1, "N/A (Rain)"

  # Tetens Equation for Saturation Vapor Pressure (kPa)
  es = 0.61121 * np.exp((17.502 * temp) / (temp + 240.97))
  ea = es * (humidity / 100.0)
  vpd = max(0.0, es - ea)

  # Dalton's Wind Factor (mph converted to m/s)
  wind_ms = wind_speed * 0.44704
  evaporation_potential = vpd * (1.0 + 0.5 * wind_ms)

  # Map physical evaporation potential to a 1-5 scale
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

  p_score = int(np.clip(p_score, 1, 5))

  # Estimated hours calculation
  if evaporation_potential < 0.1:
    est_time = "N/A"
  else:
    hours = np.clip(3.5 / evaporation_potential, 1.5, 10.0)
    est_time = f"~{round(hours * 2) / 2} hrs"

  return p_score, est_time


# --- Implementation for Tomorrow 12:00 - 16:00 Slot ---
# (Replace these variables with your actual weather API data variables)
slot_temp = 15.0  # °C
slot_humidity = 65.0  # %
slot_rain = 10.0  # %
slot_wind = 12.0  # mph

# Calculate scores
h_score = get_heuristic_drying_score(
    slot_temp, slot_humidity, slot_rain, slot_wind
)
p_score, est_time = get_physics_drying_score_and_time(
    slot_temp, slot_humidity, slot_rain, slot_wind
)

# Compact 3-column layout matching your original footprint
col1, col2, col3 = st.columns(3)

with col1:
  st.metric(label="Heuristic", value=f"{h_score}/5")

with col2:
  st.metric(label="Physics", value=f"{p_score}/5")

with col3:
  st.metric(label="Est. Time", value=est_time)
