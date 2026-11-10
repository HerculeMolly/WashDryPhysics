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
update_str = now.strftime("updated-%H%M %a %d-%b-%y").lower()

# 2. Optimized Screen Layout & CSS
st.markdown(
    f"""
    <style>
    header {{display: none !important;}}
    .stAppHeader {{display: none !important;}}
    #MainMenu {{visibility: hidden !important;}}
    footer {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 600px;
        margin: 0 auto;
    }}
    .washdry-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 2px;
        padding: 0 2px;
    }}
    .update-stamp {{
        font-size: 0.58rem;
        opacity: 0.55;
        font-weight: 500;
        margin-bottom: 8px;
        padding-left: 2px;
        letter-spacing: -0.2px;
    }}
    .slot-card {{
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 6px;
    }}
    .expired-card {{
        opacity: 0.5;
    }}
    .rating-badge {{
        font-size: 0.65rem;
        font-weight: 600;
        padding: 3px 7px;
        border-radius: 4px;
        text-align: right;
        line-height: 1.2;
    }}
    .rating-score {{
        font-size: 0.95rem;
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
        margin-top: 4px;
    }}
    .metric-box {{
        flex: 1;
        padding: 0 2px;
    }}
    .metric-label {{
        font-size: 0.55rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 1px;
        font-weight: 700;
        opacity: 0.7;
    }}
    .metric-val {{
        font-size: 0.75rem;
        font-weight: 700;
        line-height: 1.2;
    }}
    .physics-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.7rem;
        margin-top: 6px;
        padding-top: 4px;
        border-top: 1px dashed rgba(128, 128, 128, 0.2);
        opacity: 0.85;
    }}
    .footer-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 8px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        margin-top: 8px;
        margin-bottom: 16px;
    }}
    .brand-left {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .brand-logo {{
        width: 30px;
        height: 30px;
        border-radius: 50%;
        object-fit: cover;
    }}
    .brand-text {{
        display: flex;
        flex-direction: column;
        line-height: 1.2;
    }}
    .brand-name {{
        text-decoration: none;
        color: inherit;
        font-weight: 700;
        font-size: 0.8rem;
    }}
    .brand-sub {{
        font-size: 0.62rem;
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
        .block-container {{ max-width: 768px !important; padding-top: 1.5rem; }}
        .washdry-header h1 {{ font-size: 1.8rem !important; }}
        .washdry-header span.location {{ font-size: 1.1rem !important; }}
        .slot-card {{ padding: 10px 14px; margin-bottom: 8px; }}
        .slot-title {{ font-size: 1rem !important; }}
        .rating-badge {{ font-size: 0.75rem !important; padding: 4px 8px; }}
        .rating-score {{ font-size: 1.1rem !important; }}
        .metric-label {{ font-size: 0.65rem !important; }}
        .metric-val {{ font-size: 0.9rem !important; }}
        .rain-subtext {{ font-size: 0.9rem !important; }}
        .footer-container {{ padding-top: 8px; margin-top: 10px; }}
        .brand-logo {{ width: 34px !important; height: 34px !important; }}
        .brand-name {{ font-size: 0.85rem !important; }}
        .brand-sub {{ font-size: 0.7rem !important; }}
    }}
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="washdry-header">
        <h1 style="margin: 0; font-size: 1.4rem; font-weight: 800; line-height: 1;">WashDry</h1>
        <span class="location" style="font-size: 0.9rem; font-weight: 600; opacity: 0.8;">📍 Peterborough</span>
    </div>
    <div class="update-stamp">{update_str}</div>
""",
    unsafe_allow_html=True,
)

@st.cache_data(ttl=1800)
def fetch_weather_data():
    lat, lon = 52.5785, -0.1285
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,direct_radiation"
        "&timezone=Europe/London&forecast_days=2"
    )
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception:
        return None

loading_placeholder = st.empty()
loading_placeholder.markdown('<div class="instant-loader">Fetching latest weather data...</div>', unsafe_allow_html=True)

data = fetch_weather_data()
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
solar_rads = hourly.get("direct_radiation", [0]*len(times))

def get_drying_score(temp, hum, rain_prob, wind):
    score = 3
    if temp > 18:
        score += 1
    elif temp < 10:
        score -= 1
    if hum < 60:
        score += 1
    elif hum > 85:
        score -= 1
    if rain_prob > 40:
        score -= 2
    if wind > 10:
        score += 1
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
    total_mm = round(sum(block_mm), 1)
    avg_wind = round(sum(block_winds) / len(block_winds), 1)
    avg_solar = sum(block_solar) / len(block_solar)

    eval_temp = high_temp
    eval_hum = avg_hum
    eval_rain = max_rain_prob
    eval_wind = avg_wind

    es = 0.61078 * math.exp((17.27 * eval_temp) / (eval_temp + 237.3))
    ea = es * (eval_hum / 100.0)
    vpd = max(0.0, es - ea)
    evap_rate = (0.05 + 0.08 * eval_wind) * vpd + (0.0002 * avg_solar)

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
        score = get_drying_score(eval_temp, eval_hum, eval_rain, eval_wind)
        num_str, label_text = score_labels[score]
        badge_class = "rating-good" if score >= 3 else "rating-bad"
        badge_html = f'<div class="rating-badge {badge_class}"><span class="rating-score">{num_str}</span> {label_text}</div>'
        physics_html = f'<div class="physics-row"><span>⚡ Physics Est. Time: <strong>{est_time_str}</strong></span><span style="opacity: 0.6;">VPD: {vpd:.2f} kPa</span></div>'

    st.markdown(
        f"""<div class="{card_class}"><div style="display: flex; justify-content: space-between; align-items: center;"><div class="slot-title" style="font-size: 0.85rem; font-weight: 800; letter-spacing: -0.2px;">{day_label} &nbsp;<span style="opacity: 0.4; font-weight: 400;">|</span>&nbsp; {block_label}</div><div>{badge_html}</div></div><hr style="margin: 4px 0 6px 0; border: none; border-top: 1px solid rgba(128,128,128,0.2);"><div class="metrics-row"><div class="metric-box"><div class="metric-label">Temp</div><div class="metric-val">{high_temp}°C<br>{low_temp}°C</div></div><div class="metric-box"><div class="metric-label">Humidity</div><div class="metric-val">{avg_hum}%</div></div><div class="metric-box"><div class="metric-label">Rain</div><div class="metric-val">{max_rain_prob}%<br><span class="rain-subtext" style="font-size:0.75rem; font-weight:700;">{total_mm}mm</span></div></div><div class="metric-box"><div class="metric-label">Wind</div><div class="metric-val">{avg_wind} mph</div></div></div>{physics_html}</div>""",
        unsafe_allow_html=True,
    )

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
            <a href="https://buymeacoffee.com/herculemolly" target="_blank" style="text-decoration: none; background-color: #ffdd00; color: #000; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.75rem; white-space: nowrap;">☕ Buy me a coffee</a>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)
