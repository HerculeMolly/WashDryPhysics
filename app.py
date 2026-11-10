import base64
from datetime import datetime, timedelta
import math
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
import streamlit as st

# 1. Page Configuration & Branding
st.set_page_config(
    page_title="WashDry — Outdoor Drying Index", page_icon="🧺", layout="centered"
)

logo_base64 = ""
logo_path = Path("logo.png")
if logo_path.exists():
    try:
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
    except Exception:
        pass

tz = ZoneInfo("Europe/London")
now = datetime.now(tz)
update_str = now.strftime("%H%M %a %d-%b-%y").lower()

if "fabric_mode" not in st.session_state:
    st.session_state.fabric_mode = "Normal"

# 2. Automatic IP Geolocation (Real-time lookup)
@st.cache_data(ttl=3600)
def get_user_location():
    try:
        res = requests.get("https://ipapi.co/json/", timeout=3)
        data = res.json()
        if "latitude" in data and "longitude" in data:
            city = data.get("city", "Local Area")
            return data["latitude"], data["longitude"], city
    except Exception:
        pass
    return 52.5785, -0.1285, "Peterborough"

lat, lon, city_name = get_user_location()

# 3. Optimized Screen Layout & CSS (Slightly larger physics row font size)
st.markdown(
    f"""
    <style>
    header {{display: none !important;}}
    .stAppHeader {{display: none !important;}}
    #MainMenu {{visibility: hidden !important;}}
    footer {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        max-width: 600px;
        margin: 0 auto;
    }}
    /* Force absolute horizontal centering on the radio wrapper */
    .stRadio {{
        display: flex;
        justify-content: center;
        margin-bottom: -15px !important;
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
        padding: 3px 12px !important;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        white-space: nowrap;
    }}
    /* Hide actual radio bullet / checkbox inputs completely */
    .stRadio div[role="radiogroup"] input[type="radio"] {{
        display: none !important;
    }}
    /* Selected pill button color change */
    .stRadio div[role="radiogroup"] label:has(input[type="radio"]:checked) {{
        background-color: rgba(40, 167, 69, 0.2) !important;
        border-color: #28a745 !important;
        color: #2b8a3e !important;
    }}
    .slot-card {{
        background-color: rgba(128, 128, 128, 0.08);
        border: 1.5px solid rgba(128, 128, 128, 0.35);
        border-radius: 6px;
        padding: 6px 8px;
        margin-bottom: 4px;
    }}
    .expired-card {{
        opacity: 0.5;
    }}
    .rating-badge {{
        font-size: 0.6rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        text-align: right;
        line-height: 1.1;
    }}
    .rating-score {{
        font-size: 0.9rem;
        font-weight: 900;
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
        margin-top: 2px;
    }}
    .metric-box {{
        flex: 1;
        padding: 0 2px;
    }}
    .metric-label {{
        font-size: 0.52rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 1px;
        font-weight: 700;
        opacity: 0.7;
    }}
    .metric-val {{
        font-size: 0.77rem;
        font-weight: 700;
        line-height: 1.15;
        white-space: nowrap;
    }}
    .physics-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.79rem;
        margin-top: 2px;
        padding-top: 2px;
        border-top: 1px dashed rgba(128, 128, 128, 0.2);
        opacity: 0.9;
    }}
    .footer-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 6px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        margin-top: 6px;
        margin-bottom: 10px;
    }}
    .brand-left {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .brand-logo {{
        width: 28px;
        height: 28px;
        border-radius: 50%;
        object-fit: cover;
    }}
    .brand-text {{
        display: flex;
        flex-direction: column;
        line-height: 1.15;
    }}
    .brand-name {{
        text-decoration: none;
        color: inherit;
        font-weight: 700;
        font-size: 0.78rem;
    }}
    .brand-sub {{
        font-size: 0.6rem;
        opacity: 0.7;
        font-weight: 500;
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
        .rating-badge {{ font-size: 0.7rem !important; padding: 3px 7px; }}
        .rating-score {{ font-size: 1rem !important; }}
        .metric-label {{ font-size: 0.6rem !important; }}
        .metric-val {{ font-size: 0.88rem !important; }}
        .footer-container {{ padding-top: 6px; margin-top: 8px; }}
        .brand-logo {{ width: 32px !important; height: 32px !important; }}
        .brand-name {{ font-size: 0.82rem !important; }}
        .brand-sub {{ font-size: 0.65rem !important; }}
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# 4. Header Row: WashDry, Timestamp, and Location on the same line
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
        <div style="display: flex; align-items: baseline; gap: 8px;">
            <h1 style="margin: 0; font-size: 1.3rem; font-weight: 800; line-height: 1.1;">WashDry</h1>
            <span style="font-size: 0.7rem; opacity: 0.7; font-weight: 600; letter-spacing: -0.2px;">{update_str}</span>
        </div>
        <div style="font-size: 0.8rem; font-weight: 600; opacity: 0.8;">📍 {city_name}</div>
    </div>
""",
    unsafe_allow_html=True,
)

# Determine multipliers based on session state fabric mode
if "Light" in st.session_state.fabric_mode:
    fabric_multiplier = 1.3
    fabric_label_tag = "Light Load"
elif "Heavy" in st.session_state.fabric_mode:
    fabric_multiplier = 0.75
    fabric_label_tag = "Heavy Load"
else:
    fabric_multiplier = 1.0
    fabric_label_tag = "Normal Wash"


@st.cache_data(ttl=1800)
def fetch_weather_data(latitude, longitude):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,direct_radiation"
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
solar_rads = hourly.get("direct_radiation", [0] * len(times))


# Hybrid Scoring Engine (Physics-driven base score + safety heuristic guardrails)
def get_hybrid_drying_score(evap, rain_prob, peak_mm, hum):
    if evap > 0.40:
        score = 5
    elif evap > 0.30:
        score = 4
    elif evap > 0.20:
        score = 3
    elif evap > 0.10:
        score = 2
    else:
        score = 1
        
    # Heuristic guardrails for precipitation threat and air saturation
    if rain_prob > 40 or peak_mm > 0.4:
        score = min(score, 2)
    if hum > 88:
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
    avg_wind = round((sum(block_winds) / len(block_winds)) * 0.65, 1)
    avg_solar = sum(block_solar) / len(block_solar)

    eval_temp = high_temp
    eval_hum = avg_hum
    eval_rain = max_rain_prob
    eval_wind = avg_wind

    es = 0.61078 * math.exp((17.27 * eval_temp) / (eval_temp + 237.3))
    ea = es * (eval_hum / 100.0)
    vpd = max(0.0, es - ea)
    
    evap_rate = ((0.05 + 0.08 * eval_wind) * vpd + (0.0002 * avg_solar)) * fabric_multiplier

    if evap_rate > 0.4:
        est_hours = round(max(1.5, 3.5 - evap_rate * 2), 1)
        est_time_str = f"~{est_hours} hrs (Fast)"
    elif evap_rate > 0.2:
        est_hours = round(max(3.0, 6.0 - evap_rate * 3), 1)
        est_time_str = f"~{est_hours} hrs (Steady)"
    else:
        est_time_str = "6h+ (Slow / Indoor)"

    dt_slot = target_dt
    end_dt = dt_slot + timedelta(hours=4)
    is_expired = end_dt < now

    if dt_slot.date() == now.date():
        day_label = "TODAY"
    elif (dt_slot.date() - now.date()).days == 1:
        day_label = "TOMORROW"
    else:
        day_label = dt_slot.strftime("%A").upper()

    card_class = "slot-card expired-card" if is_expired else "slot-card"

    if is_expired:
        badge_html = "<div class='rating-badge rating-expired'>EXPIRED</div>"
        physics_html = ""
    else:
        score = get_hybrid_drying_score(evap_rate, eval_rain, max_hourly_mm, eval_hum)
        num_str, label_text = score_labels[score]
        badge_class = "rating-good" if score >= 3 else "rating-bad"
        badge_html = f'<div class="rating-badge {badge_class}"><span class="rating-score">{num_str}</span> {label_text}</div>'
        physics_html = f'<div class="physics-row"><span>⚡ {fabric_label_tag}: <strong>{est_time_str}</strong></span><span style="opacity: 0.7;">VPD: {vpd:.2f} kPa</span></div>'

    rain_color = (
        "opacity: 0.5;"
        if is_expired
        else ("color: #e03131;" if score < 3 else "color: #2b8a3e;")
    )

    if max_hourly_mm > 0.0:
        rain_val_html = f"{max_rain_prob}%<br><span class='rain-subtext' style='font-size:0.68rem; font-weight:700; {rain_color}'>{max_hourly_mm}mm peak</span>"
    else:
        rain_val_html = f"{max_rain_prob}%"

    st.markdown(
        f"""<div class="{card_class}"><div style="display: flex; justify-content: space-between; align-items: center;"><div class="slot-title" style="font-size: 0.8rem; font-weight: 800; letter-spacing: -0.2px;">{day_label} &nbsp;<span style="opacity: 0.4; font-weight: 400;">|</span>&nbsp; {block_label}</div><div>{badge_html}</div></div><hr style="margin: 3px 0 4px 0; border: none; border-top: 1px solid rgba(128,128,128,0.2);"><div class="metrics-row"><div class="metric-box"><div class="metric-label">Temp</div><div class="metric-val">{high_temp}°C<br>{low_temp}°C</div></div><div class="metric-box"><div class="metric-label">Humidity</div><div class="metric-val">{avg_hum}%</div></div><div class="metric-box"><div class="metric-label">Rain</div><div class="metric-val">{rain_val_html}</div></div><div class="metric-box"><div class="metric-label">Wind</div><div class="metric-val">{avg_wind} mph</div></div></div>{physics_html}</div>""",
        unsafe_allow_html=True,
    )

# 5. Fabric Pill Buttons (Strictly centered horizontally)
st.radio(
    "Load Type",
    ["Light", "Normal", "Heavy"],
    key="fabric_mode",
    horizontal=True,
    label_visibility="collapsed",
)

# 6. Integrated Microclimate & Fabric Guide Expander (Native Markdown)
with st.expander("🌤️ Drying Guide: Microclimates & Fabric Weight"):
    st.markdown(
        """
Your app calculates a reliable regional baseline, but your backyard layout and what you're hanging out to dry dictate the real-world timeline.

---

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
logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else "logo.png"

st.markdown(
    f"""
    <div class="footer-container">
        <div class="brand-left">
            <img src="{logo_src}" class="brand-logo" alt="Hercule Molly Logo" />
            <div class="brand-text">
                <a href="https://herculemolly.co.uk" target="_blank" class="brand-name">Hercule Molly</a>
                <span class="brand-sub">Quality Woodcraft Gifts</span>
            </div>
        </div>
        <div>
            <a href="https://buymeacoffee.com/herculemolly" target="_blank" style="text-decoration: none; background-color: #ffdd00; color: #000; padding: 3px 7px; border-radius: 6px; font-weight: 700; font-size: 0.72rem; white-space: nowrap;">☕ Buy me a coffee</a>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)
