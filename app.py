from datetime import datetime, timedelta
import math
import re
from zoneinfo import ZoneInfo
import requests
import streamlit as st

# 1. Page Configuration & Branding
st.set_page_config(
    page_title="WashDry — Outdoor Drying Index", page_icon="🧺", layout="centered"
)

tz = ZoneInfo("Europe/London")
now = datetime.now(tz)
update_str = now.strftime("updated %H%M %d-%b-%y").lower()

if "fabric_mode" not in st.session_state:
    st.session_state.fabric_mode = "Normal"

# 2. Geolocation & Persistent State (URL Query + Session State fallback)
if "lat" in st.query_params and "lon" in st.query_params:
    try:
        st.session_state.lat = float(st.query_params["lat"])
        st.session_state.lon = float(st.query_params["lon"])
        st.session_state.city = st.query_params.get("city", "Custom Location")
    except Exception:
        pass

if "lat" not in st.session_state:
    st.session_state.lat = 52.5785
    st.session_state.lon = -0.1285
    st.session_state.city = "Peterborough"

lat = st.session_state.lat
lon = st.session_state.lon
city_name = st.session_state.city

# 3. Optimized Screen Layout & CSS
st.markdown(
    f"""
    <style>
    header {{display: none !important;}}
    .stAppHeader {{display: none !important;}}
    #MainMenu {{visibility: hidden !important;}}
    footer {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 0.2rem;
        padding-bottom: 0.1rem;
        max-width: 600px;
        margin: 0 auto;
    }}
    
    /* Force header columns to stay side-by-side and pin logo flush right */
    [data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        width: 100% !important;
    }}
    [data-testid="stColumn"]:nth-of-type(1) {{
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }}
    [data-testid="stColumn"]:nth-of-type(2) {{
        flex: 0 0 50px !important;
        width: 50px !important;
        min-width: 50px !important;
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
        padding-right: 0px !important;
    }}
    [data-testid="stColumn"] img {{
        max-width: 44px !important;
        width: 44px !important;
        height: auto !important;
        margin-left: auto !important;
        margin-right: 0px !important;
    }}

    .stExpander {{
        margin-top: -6px !important;
        margin-bottom: -12px !important;
    }}
    .stRadio {{
        display: flex;
        justify-content: center;
        margin-bottom: -12px !important;
    }}
    .stRadio > div {{
        display: flex;
        justify-content: center;
        width: 100%;
    }}
    .stRadio div[role="radiogroup"] {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        margin: 0 auto !important;
        margin-bottom: 0px !important;
    }}
    .stRadio div[role="radiogroup"] label {{
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 14px;
        padding: 2px 10px !important;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        white-space: nowrap;
    }}
    .stRadio div[role="radiogroup"] input[type="radio"] {{
        display: none !important;
    }}
    .stRadio div[role="radiogroup"] label:has(input[type="radio"]:checked) {{
        background-color: rgba(40, 167, 69, 0.2) !important;
        border-color: #28a745 !important;
        color: #2b8a3e !important;
    }}
    .slot-card {{
        background-color: rgba(128, 128, 128, 0.08);
        border-radius: 6px;
        padding: 4px 6px;
        margin-bottom: 3px;
    }}
    .today-card {{
        border: 2px solid rgba(128, 128, 128, 0.65);
    }}
    .tomorrow-card {{
        border: 1px solid rgba(128, 128, 128, 0.25);
    }}
    .expired-card {{
        opacity: 0.5;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }}
    .rating-badge {{
        font-size: 0.72rem;
        font-weight: 600;
        padding: 1px 5px;
        border-radius: 4px;
        text-align: right;
        line-height: 1.1;
    }}
    .rating-score {{
        font-size: 0.95rem;
        font-weight: 900;
    }}
    .rating-text {{
        font-size: 0.85rem;
        font-weight: 700;
    }}
    .rating-expired {{
        background-color: rgba(108, 117, 125, 0.2);
        color: #adb5bd;
    }}
    .rating-good {{
        background-color: rgba(40, 167, 69, 0.15);
        color: #2b8a3e;
    }}
    .rating-bad {{
        background-color: rgba(220, 53, 69, 0.15);
        color: #e03131;
    }}
    .metrics-row {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        text-align: center;
        margin-top: 1px;
    }}
    .metric-box {{
        flex: 1;
        padding: 0 2px;
    }}
    .metric-label {{
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0px;
        font-weight: 500;
        opacity: 0.7;
    }}
    .metric-val {{
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 1.1;
        white-space: nowrap;
    }}
    .footer-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 3px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        margin-top: 2px;
        margin-bottom: 2px;
    }}
    .brand-text {{
        display: flex;
        flex-direction: column;
        line-height: 1.15;
        text-align: right;
    }}
    .brand-name {{
        text-decoration: none;
        color: inherit;
        font-weight: 700;
        font-size: 0.88rem;
    }}
    .brand-sub {{
        font-size: 0.7rem;
        opacity: 0.8;
        font-weight: 600;
    }}
    .instant-loader {{
        text-align: center;
        padding: 2rem 0;
        font-size: 0.9rem;
        font-weight: 600;
        opacity: 0.6;
    }}

    @media (min-width: 768px) {{
        .block-container {{ max-width: 768px !important; padding-top: 1rem; }}
        .slot-card {{ padding: 8px 12px; margin-bottom: 6px; }}
        .slot-title {{ font-size: 0.95rem !important; }}
        .rating-badge {{ font-size: 0.78rem !important; padding: 3px 7px; }}
        .rating-score {{ font-size: 1.1rem !important; }}
        .rating-text {{ font-size: 0.98rem !important; }}
        .metric-label {{ font-size: 0.76rem !important; font-weight: 500 !important; }}
        .metric-val {{ font-size: 1.05rem !important; }}
        .footer-container {{ padding-top: 4px; margin-top: 2px; }}
        .brand-name {{ font-size: 0.98rem !important; }}
        .brand-sub {{ font-size: 0.78rem !important; }}
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# 4. Header Row with Native Columns (Left: Stacked Info, Right: logo.png)
col_head, col_logo = st.columns([5, 1])

with col_head:
    st.markdown(
        f"""
        <div style="display: flex; align-items: baseline; gap: 4px; flex-wrap: wrap;">
            <h1 style="margin: 0; font-size: 1.3rem; font-weight: 800; line-height: 1.1;">WashDry</h1>
            <span style="font-size: 0.74rem; opacity: 0.7; font-weight: 600; letter-spacing: -0.2px;">{update_str}</span>
        </div>
        <div style="font-size: 0.78rem; font-weight: 600; opacity: 0.8; margin-top: 1px;">📍 {city_name}</div>
        <div style="font-size: 0.64rem; opacity: 0.55; font-weight: 500; line-height: 1.2;">Global weather model (may differ from Met Office app)</div>
    """,
        unsafe_allow_html=True,
    )

with col_logo:
    try:
        st.image("logo.png", width=44)
    except Exception:
        st.markdown(
            '<div style="border: 2px dashed rgba(128,128,128,0.4); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-size: 0.6rem; opacity: 0.6; margin-left: auto;">Logo</div>',
            unsafe_allow_html=True,
        )

# Fabric mode multipliers
if "Light" in st.session_state.fabric_mode:
    fabric_multiplier = 1.3
elif "Heavy" in st.session_state.fabric_mode:
    fabric_multiplier = 0.75
else:
    fabric_multiplier = 1.0


@st.cache_data(ttl=1800)
def fetch_weather_data(latitude, longitude):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,shortwave_radiation"
        "&timezone=Europe/London&forecast_days=2"
    )
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception:
        return None


loading_placeholder = st.empty()
loading_placeholder.markdown(
    '<div class="instant-loader">Fetching latest weather data...</div>',
    unsafe_allow_html=True,
)

data = fetch_weather_data(lat, lon)
loading_placeholder.empty()

if not data or "hourly" not in data:
    st.error("Unable to load live weather data. Please check your connection.")
    st.stop()

hourly = data["hourly"]
times = hourly["time"]
temps = hourly["temperature_2m"]
humidities = hourly["relative_humidity_2m"]
precip_probs = hourly["precipitation_probability"]
precips = hourly["precipitation"]
wind_speeds = hourly["wind_speed_10m"]
solar_rads = hourly.get("shortwave_radiation", [0] * len(times))


# Tetens-Aligned Scoring Engine
def get_hybrid_drying_score(evap, rain_prob, peak_mm, hum, high_temp):
    if evap > 0.45 and high_temp >= 16:
        score = 5
    elif evap > 0.32 and high_temp >= 12:
        score = 4
    elif evap > 0.18:
        score = 3
    elif evap > 0.08:
        score = 2
    else:
        score = 1

    if high_temp < 12:
        score = min(score, 3)
    if high_temp < 6:
        score = min(score, 2)

    if rain_prob > 35 or peak_mm > 0.3:
        score = min(score, 2)
    if hum > 85:
        score = min(score, 2)

    return max(1, min(5, score))


score_labels = {
    5: ("5/5", "Perfect"),
    4: ("4/5", "Good"),
    3: ("3/5", "Fair"),
    2: ("2/5", "Slow"),
    1: ("1/5", "Not Good"),
}

target_blocks = []
for day_offset in [0, 1]:
    d = now.date() + timedelta(days=day_offset)
    target_blocks.append(
        (
            datetime(d.year, d.month, d.day, 8, 0, tzinfo=tz),
            "0800-1200",
            [8, 9, 10, 11],
        )
    )
    target_blocks.append(
        (
            datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz),
            "1200-1600",
            [12, 13, 14, 15],
        )
    )

for target_dt, block_label, block_hours in target_blocks:
    block_indices = []
    date_str = target_dt.strftime("%Y-%m-%d")
    for i, t in enumerate(times):
        if t.startswith(date_str):
            h = int(t.split("T")[1][:2])
            if h in block_hours:
                block_indices.append(i)

    if not block_indices:
        continue

    block_temps = [temps[i] for i in block_indices]
    block_hums = [humidities[i] for i in block_indices]
    block_rains = [precip_probs[i] for i in block_indices]
    block_mm = [precips[i] for i in block_indices]
    block_winds = [wind_speeds[i] for i in block_indices]
    block_solar = [solar_rads[i] for i in block_indices]

    high_temp = max(block_temps)
    low_temp = min(block_temps)
    avg_hum = round(sum(block_hums) / len(block_hums))
    max_rain_prob = max(block_rains)
    max_hourly_mm = round(max(block_mm), 1) if block_mm else 0.0
    
    avg_wind_10m = sum(block_winds) / len(block_winds)
    avg_wind = round(avg_wind_10m * ((2.0 / 10.0) ** 0.25), 1)
    
    avg_solar = sum(block_solar) / len(block_solar)

    eval_temp = high_temp
    eval_hum = avg_hum
    eval_rain = max_rain_prob

    es = 0.61078 * math.exp((17.27 * eval_temp) / (eval_temp + 237.3))
    ea = es * (eval_hum / 100.0)
    vpd = max(0.0, es - ea)
    
    evap_rate = ((0.05 + 0.08 * avg_wind) * vpd + (0.0002 * avg_solar)) * fabric_multiplier

    dt_slot = target_dt
    end_dt = dt_slot + timedelta(hours=4)
    is_expired = end_dt < now

    if dt_slot.date() == now.date():
        day_label = "TODAY"
    elif (dt_slot.date() - now.date()).days == 1:
        day_label = "TOMORROW"
    else:
        day_label = dt_slot.strftime("%A").upper()

    if is_expired:
        card_class = "slot-card expired-card"
    else:
        weight_class = "today-card" if day_label == "TODAY" else "tomorrow-card"
        card_class = f"slot-card {weight_class}"

    if is_expired:
        badge_html = "<div class='rating-badge rating-expired'>EXPIRED</div>"
    else:
        score = get_hybrid_drying_score(evap_rate, eval_rain, max_hourly_mm, eval_hum, high_temp)
        num_str, label_text = score_labels[score]
        badge_class = "rating-good" if score >= 3 else "rating-bad"
        badge_html = f'<div class="rating-badge {badge_class}"><span class="rating-score">{num_str}</span> <span class="rating-text">{label_text}</span></div>'

    rain_color = (
        "opacity: 0.5;"
        if is_expired
        else ("color: #e03131;" if score < 3 else "color: #2b8a3e;")
    )

    if max_hourly_mm > 0.0:
        rain_val_html = f"{max_rain_prob}%<br><span class='rain-subtext' style='font-size:0.72rem; font-weight:700; {rain_color}'>{max_hourly_mm}mm peak</span>"
    else:
        rain_val_html = f"{max_rain_prob}%"

    st.markdown(
        f"""<div class="{card_class}"><div style="display: flex; justify-content: space-between; align-items: center;"><div class="slot-title" style="font-size: 0.8rem; font-weight: 800; letter-spacing: -0.2px;">{day_label} &nbsp;<span style="opacity: 0.4; font-weight: 400;">|</span>&nbsp; {block_label}</div><div>{badge_html}</div></div><hr style="margin: 2px 0 3px 0; border: none; border-top: 1px solid rgba(128,128,128,0.2);"><div class="metrics-row"><div class="metric-box"><div class="metric-label">Temp</div><div class="metric-val">{high_temp}°C<br>{low_temp}°C</div></div><div class="metric-box"><div class="metric-label">Humidity</div><div class="metric-val">{avg_hum}%</div></div><div class="metric-box"><div class="metric-label">Rain</div><div class="metric-val">{rain_val_html}</div></div><div class="metric-box"><div class="metric-label">Wind</div><div class="metric-val">{avg_wind} mph</div></div></div></div>""",
        unsafe_allow_html=True,
    )

# 5. Fabric Pill Buttons
st.radio(
    "Load Type",
    ["Light", "Normal", "Heavy"],
    key="fabric_mode",
    horizontal=True,
    label_visibility="collapsed",
)

# 6. Integrated Microclimate & UK Postcode Form Expander
with st.expander("🌤️ Drying Guide & Location Settings"):
    st.markdown("### 📍 UK Postcode Search")
    
    with st.form(key="postcode_form"):
        postcode_query = st.text_input("Enter UK Postcode or Outward Code", placeholder="e.g. PE7 or PE7 1AA")
        submitted = st.form_submit_button("Set Location", use_container_width=True)
        
        if submitted and postcode_query:
            query_clean = postcode_query.strip().upper()
            try:
                res = requests.get(f"https://api.postcodes.io/postcodes/{query_clean}", timeout=3)
                data = res.json()
                
                if res.status_code == 200 and data.get("result"):
                    r = data["result"]
                    district = r.get("admin_district", query_clean)
                    resolved_city = f"{district} ({query_clean})"
                    
                    st.session_state.lat = r["latitude"]
                    st.session_state.lon = r["longitude"]
                    st.session_state.city = resolved_city
                    
                    st.query_params["lat"] = str(r["latitude"])
                    st.query_params["lon"] = str(r["longitude"])
                    st.query_params["city"] = resolved_city
                    st.rerun()
                else:
                    res_out = requests.get(f"https://api.postcodes.io/outcodes/{query_clean}", timeout=3)
                    data_out = res_out.json()
                    if res_out.status_code == 200 and data_out.get("result"):
                        r = data_out["result"]
                        resolved_city = f"Area {query_clean}"
                        
                        st.session_state.lat = r["latitude"]
                        st.session_state.lon = r["longitude"]
                        st.session_state.city = resolved_city
                        
                        st.query_params["lat"] = str(r["latitude"])
                        st.query_params["lon"] = str(r["longitude"])
                        st.query_params["city"] = resolved_city
                        st.rerun()
                    else:
                        st.error("UK postcode not found. Please enter a valid UK postcode or outward code (e.g. PE7).")
            except Exception:
                st.error("Search failed. Check connection and try again.")

    if st.session_state.city != "Peterborough":
        col_reset1, col_reset2 = st.columns([2, 1])
        with col_reset1:
            st.success(f"Active location: **{st.session_state.city}**")
        with col_reset2:
            if st.button("Reset Default", use_container_width=True):
                st.session_state.lat = 52.5785
                st.session_state.lon = -0.1285
                st.session_state.city = "Peterborough"
                st.query_params.clear()
                st.rerun()

    st.markdown(
        """
---
Your app calculates a reliable regional baseline, but your backyard layout and what you're hanging out to dry dictate the real-world timeline.

### 1. Garden Layout (The 20–30% Swing)
*Physics view: Boundary-layer decoupling & thermal mass radiation.*
* **The Slower Yard (Shelter Trap):** Fences, walls, and dense hedges block the wind, creating a "dead air" bubble where humidity gets trapped. If your yard is heavily walled-in, expect drying times to run slower than the app suggests.
* **The Faster Yard (Sun-Trap Bonus):** Hard landscaping (patios, brick walls) acts as a solar radiator, re-radiating warmth and dropping local humidity to accelerate drying.

### 2. Fabric Density & Load Weight
*Physics view: Internal moisture diffusion & falling-rate drying phases.*
* **Light Loads (Synthetics / Shirts):** Water sits mostly on surface fibers and evaporates rapidly.
* **Normal Loads (Mixed Everyday Wash):** Standard cotton tees and garments take moderate time.
* **Heavy Loads (Jeans, Hoodies & Towels):** Dense fibers trap moisture deep inside, requiring significantly more thermal energy and time. Always mentally add extra time for thick cottons!

---
**Quick Rule of Thumb:** Trust "Bad" and "Perfect" forecasts implicitly (rain and high humidity beat everything). For "Steady" or "Fair" days, mentally adjust your expectations: round up for heavy towels in a shady yard, or round down for light sportswear in an open sun-trap!
        """
    )

# 7. Footer Branding
st.markdown(
    """
    <div class="footer-container">
        <div>
            <a href="https://buymeacoffee.com/herculemolly" target="_blank" style="text-decoration: none; background-color: #ffdd00; color: #000; padding: 3px 7px; border-radius: 6px; font-weight: 700; font-size: 0.72rem; white-space: nowrap;">☕ Buy me a coffee</a>
        </div>
        <div class="brand-text">
            <a href="https://herculemolly.co.uk" target="_blank" class="brand-name">Hercule Molly</a>
            <span class="brand-sub">Quality Woodcraft Gifts</span>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)
