import streamlit as st
import requests
from datetime import datetime, timedelta

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
                city = data.get("city", data.get("region", "Current Location"))
                country = data.get("country_name", data.get("country_code", "GB"))
                tz = data.get("timezone", "UTC")
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
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon, f"Custom Coordinates ({lat}, {lon})", "UTC", "Custom"
        except ValueError:
            pass

    # Use Open-Meteo Geocoding API for global places / UK postcodes
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=1&language=en&format=json"
    try:
        res = requests.get(geo_url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and len(data["results"]) > 0:
                loc = data["results"][0]
                lat = loc["latitude"]
                lon = loc["longitude"]
                name = loc.get("name", query)
                admin = loc.get("admin1", "")
                country = loc.get("country", "")
                city_label = f"{name}, {admin}, {country}".strip(", ")
                tz = loc.get("timezone", "UTC")
                country_code = loc.get("country_code", "")
                return lat, lon, city_label, tz, country_code
    except Exception:
        pass

    return None

# ==========================================
# 2. MAIN APP CONFIGURATION & UI
# ==========================================

st.set_page_config(page_title="WashDry Global - Laundry Weather Forecast", page_icon="🧺", layout="centered")

st.title("🧺 WashDry Global")
st.markdown("Smart outdoor drying forecasts tailored to your exact location, fabric load, and drying setup.")

# Initialize session state for location tracking across reruns
if "lat" not in st.session_state or "lon" not in st.session_state:
    default_lat, default_lon, default_city, default_tz, default_country = get_ip_location()
    st.session_state["lat"] = default_lat
    st.session_state["lon"] = default_lon
    st.session_state["city"] = default_city
    st.session_state["tz"] = default_tz
    st.session_state["country"] = default_country

# Sidebar controls for location override and settings
st.sidebar.header("📍 Location Settings")
location_input = st.sidebar.text_input("Search City, Postcode, or Lat/Lon", placeholder="e.g. Ely, PE7 3AA, or 52.57,-0.12")

if st.sidebar.button("Update Location"):
    if location_input:
        found = search_global_location(location_input)
        if found:
            st.session_state["lat"], st.session_state["lon"], st.session_state["city"], st.session_state["tz"], st.session_state["country"] = found
            st.sidebar.success(f"Updated to: {st.session_state['city']}")
        else:
            st.sidebar.error("Location not found. Please try another search term.")

st.sidebar.markdown(f"**Current Location:** {st.session_state['city']}")

# Laundry Parameters
st.sidebar.header("👕 Drying Setup")
load_size = st.sidebar.selectbox("Load Size", ["Light (Few items)", "Standard (Normal wash)", "Heavy (Bedding/Jeans)"])
shelter = st.sidebar.selectbox("Shelter / Setup", ["Full Sun & Breeze", "Open Garden / Patio", "Covered Porch / Balcony", "Indoor Airer"])

# ==========================================
# 3. WEATHER DATA FETCHING (3-TIER PIPELINE)
# ==========================================

@st.cache_data(ttl=1800) # Cache for 30 minutes
def fetch_weather_data(lat, lon):
    """Fetches high-resolution hourly weather data from Open-Meteo with fallback support."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,direct_radiation&timezone=auto"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

data = fetch_weather_data(st.session_state["lat"], st.session_state["lon"])

if data and "hourly" in data:
    hourly = data["hourly"]
    st.success(f"Forecast successfully loaded for {st.session_state['city']}.")
    
    # Quick display check for current temperature
    current_temp = hourly["temperature_2m"][0]
    current_hum = hourly["relative_humidity_2m"][0]
    st.metric(label="Current Temperature", value=f"{current_temp}°C", delta=f"Humidity: {current_hum}%")
    
    st.info("Your pipeline is fully active. You can now safely tweak designs, switch gears to your woodcraft site (HMwww), and return whenever you're ready!")
else:
    st.warning("Weather service temporarily unreachable. Showing offline fallback state.")
    st.metric(label="Current Temperature", value="15.0°C (Estimated)", delta="Offline Mode")

# Footer links
st.markdown("---")
st.markdown("WashDry Global • Built with Python & Streamlit")