import datetime
import math
import os
import requests
import streamlit as st
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
page_title="WashDry Global Weather",
page_icon="☀️",
layout="centered",
initial_sidebar_state="collapsed",
)

st.markdown(
"""
<style>
.main { max-width: 700px; margin: 0 auto; }
.stButton button { width: 100%; border-radius: 8px; font-weight: 600; }
.estimate-badge { background-color: #f0f2f6; color: #31333f; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; border: 1px solid #d0d5dd; }
.warning-banner { padding: 10px 14px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 500; }
</style>
""",
unsafe_allow_html=True,
)


# ==========================================
# 1. HELPER FUNCTIONS: IP GEOLOCATION & GEOCODING
# ==========================================
def get_ip_location():
"""Silently detect user location via IP address on first load."""
try:
res = requests.get("https://ipapi.co/json/", timeout=3)
if res.status_code == 200:
data = res.json()
if "latitude" in data and "longitude" in data:
lat = float(data["latitude"])
lon = float(data["longitude"])
city = data.get(
"city", data.get("region", "Current Location")
) + f", {data.get('country_code', '')}"
tz = data.get("timezone", "UTC")
country = data.get("country_code", "GB")
return lat, lon, city, tz, country
except Exception:
pass

# Default fallback (Peterborough, UK)
return 52.5785, -0.1285, "Peterborough, UK", "Europe/London", "GB"


def search_global_location(query):
"""Supports raw lat/lon, UK postcodes, or global city/town search."""
query = query.strip()

# Check if query is raw lat, lon (e.g. "52.57, -0.12" or "35.22,-80.84")
if "," in query:
try:
parts = query.split(",")
lat, lon = float(parts[0]), float(parts[1])
if -90 <= lat <= 90 and -180 <= lon <= 180:
return lat, lon, f"Coordinates ({lat:.2f}, {lon:.2f})", "UTC"
except ValueError:
pass

# Check if UK Postcode format (basic heuristic)
if any(char.isdigit() for char in query) and len(query) <= 8:
try:
res = requests.get(
f"https://api.postcodes.io/postcodes/{query}", timeout=3
)
if res.status_code == 200:
data = res.json()["result"]
return (
data["latitude"],
data["longitude"],
f"{data['postcode']}, {data.get('admin_district', 'UK')}",
"Europe/London",
)
except Exception:
pass

# Global City / Town Search via Open-Meteo Geocoding API
try:
url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(query)}&count=1"
res = requests.get(url, timeout=4)
if res.status_code == 200:
results = res.json().get("results")
if results:
match = results[0]
lat = match["latitude"]
lon = match["longitude"]
name = f"{match.get('name')}, {match.get('admin1', match.get('country', ''))}"
tz = match.get("timezone", "UTC")
return lat, lon, name, tz
except Exception:
pass

return None, None, None, None


# ==========================================
# 2. WEATHER FETCHING (3-TIER RESILIENCY)
# ==========================================
def fetch_weather_data(lat, lon):
"""Tier 1: Open-Meteo | Tier 2: Met Norway | Tier 3: Session Cache / Estimate"""
now_utc = datetime.datetime.now(datetime.timezone.utc)

# --- TIER 1: OPEN-METEO ---
try:
url = (
f"https://api.open-meteo.com/v1/forecast?lat={lat}&lon={lon}"
"&hourly=temperature_2m,relative_humidity_2m,precipitation,"
"wind_speed_10m,shortwave_radiation,cloud_cover"
"&wind_speed_unit=ms&timezone=auto"
)
res = requests.get(url, timeout=5)
if res.status_code == 200:
data = res.json()
tz_str = data.get("timezone", "UTC")
hourly = data.get("hourly", {})

# Store in session state as last good data
st.session_state["last_good_data"] = {
"source": "Open-Meteo",
"hourly": hourly,
"timezone": tz_str,
"timestamp": now_utc,
}
return hourly, tz_str, False, "Live (Open-Meteo)"
except Exception:
pass

# --- TIER 2: MET NORWAY ---
try:
url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={round(lat, 4)}&lon={round(lon, 4)}"
headers = {"User-Agent": "WashDryApp/2.6 github.com/washdry"}
res = requests.get(url, headers=headers, timeout=5)
if res.status_code == 200:
met_json = res.json()
timeseries = met_json.get("properties", {}).get("timeseries", [])

# Parse Met Norway into Open-Meteo style hourly dict
times, temps, hums, precip, winds, rads = [], [], [], [], [], []
for entry in timeseries:
t_str = entry["time"]
details = entry["data"]["instant"]["details"]
precip_val = (
entry.get("data", {})
.get("next_1_hours", {})
.get("details", {})
.get("precipitation_amount", 0.0)
)
cloud_val = details.get("cloud_area_fraction", 50.0)

times.append(t_str)
temps.append(details.get("air_temperature", 15.0))
hums.append(details.get("relative_humidity_percent", 60.0))
precip.append(precip_val)
winds.append(details.get("wind_speed", 3.0))
# Estimate shortwave solar radiation from cloud cover roughly
rads.append(max(0.0, 500.0 * (1.0 - (cloud_val / 100.0))))

hourly = {
"time": times,
"temperature_2m": temps,
"relative_humidity_2m": hums,
"precipitation": precip,
"wind_speed_10m": winds,
"shortwave_radiation": rads,
}
tz_str = "UTC" # Met Norway is UTC, will convert via ZoneInfo

st.session_state["last_good_data"] = {
"source": "Met Norway",
"hourly": hourly,
"timezone": tz_str,
"timestamp": now_utc,
}
return hourly, tz_str, False, "Live (Met Norway Backup)"
except Exception:
pass

# --- TIER 3: LAST-GOOD-DATA CACHE OR SYNTHETIC ESTIMATE ---
if "last_good_data" in st.session_state:
cached = st.session_state["last_good_data"]
return (
cached["hourly"],
cached["timezone"],
True,
f"ESTIMATE (Using cached data from {cached['source']})",
)

# Ultimate Safety Net: Synthetic Diurnal Sine-Wave Baseline
times, temps, hums, precip, winds, rads = [], [], [], [], [], []
base_time = now_utc.replace(minute=0, second=0, microsecond=0)
for i in range(48):
dt = base_time + datetime.timedelta(hours=i)
hour = dt.hour
# Sine wave peaking at 3 PM (15:00)
temp_est = 12.0 + 6.0 * math.sin((hour - 9) * (2 * math.pi / 24))
hum_est = max(30.0, min(95.0, 80.0 - (temp_est - 10) * 2.5))

times.append(dt.isoformat())
temps.append(round(temp_est, 1))
hums.append(round(hum_est, 1))
precip.append(0.0)
winds.append(3.5)
rads.append(
max(0.0, 400.0 * math.sin(hour * (math.pi / 24)))
if 6 <= hour <= 18
else 0.0
)

synthetic_hourly = {
"time": times,
"temperature_2m": temps,
"relative_humidity_2m": hums,
"precipitation": precip,
"wind_speed_10m": winds,
"shortwave_radiation": rads,
}
return synthetic_hourly, "UTC", True, "ESTIMATE (Synthetic Baseline Model)"


# ==========================================
# 3. SESSION STATE & URL PARAMS INITIALIZATION
# ==========================================
query_params = st.query_params

if "lat" not in st.session_state:
if "lat" in query_params and "lon" in query_params:
try:
st.session_state["lat"] = float(query_params["lat"])
st.session_state["lon"] = float(query_params["lon"])
st.session_state["location_name"] = query_params.get(
"city", "Custom Location"
)
st.session_state["timezone"] = query_params.get("tz", "UTC")
except ValueError:
pass

if "lat" not in st.session_state:
lat, lon, city, tz, country = get_ip_location()
st.session_state["lat"] = lat
st.session_state["lon"] = lon
st.session_state["location_name"] = city
st.session_state["timezone"] = tz
st.session_state["country"] = country

if "unit_mode" not in st.session_state:
# Auto-default units based on country
c_code = st.session_state.get("country", "GB")
if c_code in ["US", "LR", "MM"]:
st.session_state["unit_mode"] = "Imperial (°F / mph)"
else:
st.session_state["unit_mode"] = "Metric (°C / km/h)"


# ==========================================
# 4. HEADER & CONTROLS
# ==========================================
col1, col2 = st.columns([4, 1])
with col1:
st.subheader(f"📍 {st.session_state.get('location_name', 'Local Weather')}")
with col2:
if st.button("🔄 Refresh"):
st.rerun()

# Fetch weather data for current session coords
hourly, tz_name, is_estimate, status_msg = fetch_weather_data(
st.session_state["lat"], st.session_state["lon"]
)

# Display Warning Banner if fallback is active
if is_estimate:
st.markdown(
f'<div class="warning-banner">⚠️ Live weather services busy. Displaying estimated baseline conditions. ({status_msg})</div>',
unsafe_allow_html=True,
)

# ==========================================
# 5. EXPANDER: SETTINGS & GLOBAL SEARCH
# ==========================================
with st.expander("🌤️ Location Settings & Search"):
search_input = st.text_input(
"Search Location",
placeholder="Enter UK postcode, US ZIP, City name, or Lat,Lon",
)
if st.button("Search"):
if search_input:
lat, lon, name, tz = search_global_location(search_input)
if lat is not None:
st.session_state["lat"] = lat
st.session_state["lon"] = lon
st.session_state["location_name"] = name
st.session_state["timezone"] = tz
st.query_params["lat"] = lat
st.query_params["lon"] = lon
st.query_params["city"] = name
st.success(f"Updated location to {name}!")
st.rerun()
else:
st.error(
"Could not find that location. Try a city name or coordinates."
)

st.divider()

# Unit Selector
unit_choice = st.selectbox(
"Display Units",
["Metric (°C / km/h)", "Imperial (°F / mph)", "Metric (°C / mph)"],
index=(
0
if st.session_state["unit_mode"].startswith("Metric")
else 1
),
)
st.session_state["unit_mode"] = unit_choice


# ==========================================
# 6. CALCULATIONS & UI RENDERING
# ==========================================
try:
local_tz = ZoneInfo(st.session_state["timezone"])
except (ZoneInfoNotFoundError, Exception):
local_tz = ZoneInfo("UTC")

# Unit conversion helpers
use_fahrenheit = "°F" in st.session_state["unit_mode"]
use_mph = "mph" in st.session_state["unit_mode"]


def format_temp(celsius):
if use_fahrenheit:
return f"{(celsius * 9/5) + 32:.0f}°F"
return f"{celsius:.0f}°C"


def format_wind(ms):
if use_mph:
return f"{ms * 2.23694:.1f} mph"
return f"{ms * 3.6:.1f} km/h"


# Simple drying score logic based on temperature, humidity, and wind (Metric core)
st.markdown("### Today's Drying Outlook")

if is_estimate:
st.markdown(
'<span class="estimate-badge">STATUS: ESTIMATE</span>',
unsafe_allow_html=True,
)
else:
st.markdown(
'<span style="color: green; font-weight: 600; font-size: 0.85rem;">● Live Data Active</span>',
unsafe_allow_html=True,
)

# Render sample metric summary cards
current_temp_c = hourly["temperature_2m"][0] if hourly["temperature_2m"] else 15.0
current_hum = (
hourly["relative_humidity_2m"][0]
if hourly["relative_humidity_2m"]
else 60.0
)
current_wind_ms = (
hourly["wind_speed_10m"][0] if hourly["wind_speed_10m"] else 3.0
)

col_a, col_b, col_c = st.columns(3)
col_a.metric("Temperature", format_temp(current_temp_c))
col_b.metric("Humidity", f"{current_hum:.0f}%")
col_c.metric("Wind Speed", format_wind(current_wind_ms))

st.info(
"💡 Tip: Bookmark this page or add it to your device home screen for instant local forecasts anywhere in the world."
)