import os
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.signal import find_peaks
import arabic_reshaper
from bidi.algorithm import get_display
from matplotlib import font_manager

# تنظیم فونت فارسی استاندارد
available_fonts = {f.name for f in font_manager.fontManager.ttflist}
preferred_fonts = ["Vazirmatn", "Noto Sans Arabic", "Noto Naskh Arabic", "DejaVu Sans"]
selected_font = next((f for f in preferred_fonts if f in available_fonts), "DejaVu Sans")
plt.rcParams["font.family"] = selected_font
plt.rcParams["axes.unicode_minus"] = False

def rtl(text):
    return get_display(arabic_reshaper.reshape(str(text)))

# --- تنظیمات نقاط استان قم ---
LOCATIONS = {
    "Qom": {"name_fa": "قم", "lat": 34.64, "lon": 50.88},
    "Dastjerd": {"name_fa": "دستجرد", "lat": 34.55, "lon": 50.25},
    "Qahan": {"name_fa": "قاهان", "lat": 34.70, "lon": 50.26},
    "Kahak": {"name_fa": "کهک", "lat": 34.38, "lon": 50.86}
}

# دریافت توکن‌ها برای هر دو پلتفرم تلگرام و بله
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID") or os.getenv("BALE_CHAT_ID")

def fetch_gfs_850_data(lat, lon):
    """دریافت داده‌های تراز ۸۵۰ از مدل GFS برای ۷ روز کامل"""
    url = "https://api.open-meteo.com/v1/gfs"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_850hPa", "windspeed_850hPa", "winddirection_850hPa"],
        "wind_speed_unit": "kmh",
        "forecast_days": 7,
        "timezone": "Asia/Tehran"
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["hourly"]

def plot_meteogram_850(city_key, info, data):
    times = pd.to_datetime(data["time"])
    temps = np.array(data["temperature_850hPa"], dtype=float)
    winds = np.array(data["windspeed_850hPa"], dtype=float)
    dirs = np.array(data["winddirection_850hPa"], dtype=float)

    fig, (ax_temp, ax_wind) = plt.subplots(
        2, 1, figsize=(14, 8.8), sharex=True, dpi=200,
        gridspec_kw={'height_ratios': [1.3, 1]}
    )
    fig.patch.set_facecolor('#0b1329')

    # ==================== ۱. پنل دما (850hPa) ====================
    ax_temp.set_facecolor('#131e3a')
    ax_temp.plot(times, temps, color='#ff7a18', lw=2.6, label='850 hPa Temp (°C)', zorder=3)
    ax_temp.fill_between(times, temps, temps.min() - 3, color='#ff7a18', alpha=0.15)

    # پیدا کردن قله‌ها و دره‌ها با فاصله مناسب دوره ۷ روزه
    temp_peaks, _ = find_peaks(temps, distance=8, prominence=0.5)
    temp_troughs, _ = find_peaks(-temps, distance=8, prominence=0.5)

    abs_max_idx = int(np.argmax(temps))
    abs_min_idx = int(np.argmin(temps))
    all_peaks = set(temp_peaks.tolist() + [abs_max_idx])
    all_troughs = set(temp_troughs.tolist() + [abs_min_idx])

    for p in all_peaks:
        ax_temp.scatter(times[p], temps[p], color='#ef4444', s=35, zorder=6)
        ax_temp.annotate(
            f"{temps[p]:.1f}°",
            (times[p], temps[p]),
            textcoords="offset points", xytext=(0, 6),
            ha='center', va='bottom',
            color='#fef08a', fontsize=8.5, fontweight='bold'
        )

    for t in all_troughs:
        ax_temp.scatter(times[t], temps[t], color='#38bdf8', s=35, zorder=6)
        ax_temp.annotate(
            f"{temps[t]:.1f}°",
            (times[t], temps[t]),
            textcoords="offset points", xytext=(0, -14),
            ha='center', va='top',
            color='#7dd3fc', fontsize=8.5, fontweight='bold'
        )

    ax_temp.set_ylabel(rtl("دما (°C) تراز ۸۵۰"), color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_temp.tick_params(colors='#94a3b8', labelsize=9)
    ax_temp.grid(True, linestyle='--', alpha=0.22, color='#64748b')
    ax_temp.set_title(
        rtl(f"پیش‌بینی ۷ روزه تراز ۸۵۰ هکتوپاسکال مدل GFS — ایستگاه {info['name_fa']}"),
        color='#f8fafc', fontsize=13, fontweight='bold', pad=12
    )
    ax_temp.set_ylim(temps.min() - 2.5, temps.max() + 2.5)

    # ==================== ۲. پنل باد (850hPa) ====================
    ax_wind.set_facecolor('#131e3a')
    ax_wind.bar(times, winds, width=0.035, color='#0284c7', alpha=0.75, label='Wind Speed (km/h)', zorder=2)

    wind_peaks, _ = find_peaks(winds, distance=8, prominence=4.0)
    abs_wind_max_idx = int(np.argmax(winds))
    all_wind_peaks = set(wind_peaks.tolist() + [abs_wind_max_idx])

    for wp in all_wind_peaks:
        w_val = winds[wp]
        if w_val >= 15:
            ax_wind.annotate(
                f"{w_val:.0f}",
                (times[wp], w_val),
                textcoords="offset points", xytext=(0, 4),
                ha='center', va='bottom',
                color='#fef08a', fontsize=8.5, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#38bdf8", lw=0.8, alpha=0.9)
            )

    # رسم پیکان‌های جهت باد (هر ۴ ساعت برای خوانایی در ۷ روز)
    step = 4
    u = -np.sin(np.radians(dirs[::step]))
    v = -np.cos(np.radians(dirs[::step]))
    ax_wind.quiver(
        times[::step], winds[::step] + 4, u, v,
        color='#facc15', scale=26, width=0.003, headwidth=4, headlength=5, zorder=5
    )

    ax_wind.set_ylabel(rtl("سرعت باد (km/h)"), color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_wind.tick_params(colors='#94a3b8', labelsize=9)
    ax_wind.grid(True, linestyle='--', alpha=0.22, color='#64748b')
    ax_wind.set_ylim(0, max(winds) * 1.35 + 8)

    # تنظیم فواصل زمانی روی محور افقی
    ax_wind.xaxis.set_major_locator(mdates.DayLocator())
    ax_wind.xaxis.set_major_formatter(mdates.DateFormatter('%a\n%m/%d'))
    ax_wind.xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))
    ax_wind.tick_params(axis='x', which='minor', labelsize=7.5, colors='#64748b')

    plt.tight_layout()
    output_filename = f"gfs_850_{city_key.lower()}.png"
    plt.savefig(output_filename, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return output_filename

def broadcast_photo(photo_path, caption):
    # تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    files={'photo': photo},
                    data={'chat_id': CHANNEL_ID, 'caption': caption},
                    timeout=35
                )
        except Exception as e:
            print(f"Telegram error: {e}")

    # بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    files={'photo': photo},
                    data={'chat_id': BALE_CHANNEL_ID, 'caption': caption},
                    timeout=35
                )
        except Exception as e:
            print(f"Bale error: {e}")

def main():
    print("Fetching GFS 850hPa 7-day forecasts...")
    for key, info in LOCATIONS.items():
        try:
            print(f"Processing {key}...")
            raw_data = fetch_gfs_850_data(info["lat"], info["lon"])
            img_path = plot_meteogram_850(key, info, raw_data)
            caption = (
                f"📊 پیش‌بینی ۷ روزه تراز ۸۵۰ هکتوپاسکال (GFS)\n"
                f"📍 ایستگاه: {info['name_fa']}\n"
                f"🌡 شامل کلیه قله‌ها و دره‌های دمایی و پیک باد\n"
                f"⏱ صدور: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            broadcast_photo(img_path, caption)
        except Exception as e:
            print(f"Error processing {key}: {e}")

if __name__ == "__main__":
    main()
