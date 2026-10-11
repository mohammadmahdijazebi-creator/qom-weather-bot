import os
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.signal import find_peaks

# --- تنظیمات نقاط استان قم ---
LOCATIONS = {
    "Qom": {"name_fa": "Qom (قم)", "lat": 34.64, "lon": 50.88},
    "Dastjerd": {"name_fa": "Dastjerd (دستجرد)", "lat": 34.55, "lon": 50.25},
    "Qahan": {"name_fa": "Qahan (قاهان)", "lat": 34.70, "lon": 50.26},
    "Kahak": {"name_fa": "Kahak (کهک)", "lat": 34.38, "lon": 50.86}
}

# --- دریافت خودکار توکن و شناسه چت تلگرام ---
TELEGRAM_BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
)
TELEGRAM_CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or os.getenv("CHANNEL_ID")
)

def fetch_gfs_850_data(lat, lon):
    """دریافت داده‌های تراز ۸۵۰ از مدل GFS"""
    url = "https://api.open-meteo.com/v1/gfs"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_850hPa", "windspeed_850hPa", "winddirection_850hPa"],
        "wind_speed_unit": "kmh",
        "forecast_days": 3,
        "timezone": "Asia/Tehran"
    }
    resp = requests.get(url, params=params, timeout=25)
    resp.raise_for_status()
    return resp.json()["hourly"]

def plot_meteogram_850(city_key, info, data):
    times = pd.to_datetime(data["time"])
    temps = np.array(data["temperature_850hPa"])
    winds = np.array(data["windspeed_850hPa"])
    dirs = np.array(data["winddirection_850hPa"])

    fig, (ax_temp, ax_wind) = plt.subplots(
        2, 1, figsize=(12, 8.2), sharex=True, dpi=180,
        gridspec_kw={'height_ratios': [1.25, 1]}
    )
    fig.patch.set_facecolor('#0b1329')

    # ==================== ۱. پنل دما (850hPa) ====================
    ax_temp.set_facecolor('#131e3a')
    ax_temp.plot(times, temps, color='#ff7a18', lw=2.8, label='850 hPa Temp (°C)', zorder=3)
    ax_temp.fill_between(times, temps, temps.min() - 3, color='#ff7a18', alpha=0.18)

    # پیدا کردن همه قله‌ها و دره‌های محلی دما
    temp_peaks, _ = find_peaks(temps, distance=6, prominence=0.4)
    temp_troughs, _ = find_peaks(-temps, distance=6, prominence=0.4)

    # اطمینان از ثبت ماکزیمم و مینیمم مطلق در صورت عدم تشخیص در قله‌های فرعی
    abs_max_idx = int(np.argmax(temps))
    abs_min_idx = int(np.argmin(temps))
    all_peaks = set(temp_peaks.tolist() + [abs_max_idx])
    all_troughs = set(temp_troughs.tolist() + [abs_min_idx])

    # درج مقادیر روی قله‌های دما
    for p in all_peaks:
        ax_temp.scatter(times[p], temps[p], color='#ef4444', s=35, zorder=6)
        ax_temp.annotate(
            f"{temps[p]:.1f}°",
            (times[p], temps[p]),
            textcoords="offset points", xytext=(0, 7),
            ha='center', va='bottom',
            color='#fef08a', fontsize=9.5, fontweight='bold'
        )

    # درج مقادیر روی دره‌ها (کف‌های) دما
    for t in all_troughs:
        ax_temp.scatter(times[t], temps[t], color='#38bdf8', s=35, zorder=6)
        ax_temp.annotate(
            f"{temps[t]:.1f}°",
            (times[t], temps[t]),
            textcoords="offset points", xytext=(0, -15),
            ha='center', va='top',
            color='#7dd3fc', fontsize=9.5, fontweight='bold'
        )

    ax_temp.set_ylabel("Temperature (°C)", color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_temp.tick_params(colors='#94a3b8', labelsize=9.5)
    ax_temp.grid(True, linestyle='--', alpha=0.22, color='#64748b')
    ax_temp.set_title(
        f"GFS 850 hPa Forecast (3 Days) — {info['name_fa']}",
        color='#f8fafc', fontsize=13.5, fontweight='bold', pad=12
    )
    ax_temp.set_ylim(temps.min() - 2.5, temps.max() + 2.5)

    # ==================== ۲. پنل باد (850hPa) ====================
    ax_wind.set_facecolor('#131e3a')
    bars = ax_wind.bar(times, winds, width=0.033, color='#0284c7', alpha=0.78, label='Wind Speed (km/h)', zorder=2)

    # تشخیص قله‌های باد و نوشتن ماکزیمم‌ها
    wind_peaks, _ = find_peaks(winds, distance=5, prominence=3.0)
    abs_wind_max_idx = int(np.argmax(winds))
    all_wind_peaks = set(wind_peaks.tolist() + [abs_wind_max_idx])

    for wp in all_wind_peaks:
        w_val = winds[wp]
        if w_val >= 12:  # فقط برای بادهای قابل توجه برچسب بزند
            ax_wind.annotate(
                f"{w_val:.0f}",
                (times[wp], w_val),
                textcoords="offset points", xytext=(0, 4),
                ha='center', va='bottom',
                color='#fef08a', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="#38bdf8", lw=0.8, alpha=0.9)
            )

    # رسم فلش‌های جهت وزش باد
    step = 3
    u = -np.sin(np.radians(dirs[::step]))
    v = -np.cos(np.radians(dirs[::step]))
    ax_wind.quiver(
        times[::step], winds[::step] + 4, u, v,
        color='#facc15', scale=22, width=0.0035, headwidth=4, headlength=5, zorder=5
    )

    ax_wind.set_ylabel("Wind Speed (km/h)", color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_wind.tick_params(colors='#94a3b8', labelsize=9.5)
    ax_wind.grid(True, linestyle='--', alpha=0.22, color='#64748b')
    ax_wind.set_ylim(0, max(winds) * 1.35 + 8)

    # تنظیمات محور زمان (ساعات و روزها)
    ax_wind.xaxis.set_major_locator(mdates.DayLocator())
    ax_wind.xaxis.set_major_formatter(mdates.DateFormatter('%a\n%m/%d'))
    ax_wind.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
    ax_wind.xaxis.set_minor_formatter(mdates.DateFormatter('%H:00'))
    ax_wind.tick_params(axis='x', which='minor', labelsize=8, colors='#64748b')

    plt.tight_layout()
    output_filename = f"gfs_850_{city_key.lower()}.png"
    plt.savefig(output_filename, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return output_filename

def send_telegram_photo(photo_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Warning] Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        resp = requests.post(url, files=files, data=data, timeout=30)
        if resp.status_code == 200:
            print(f"Successfully sent {photo_path} to Telegram")
        else:
            print(f"Failed to send to Telegram: {resp.text}")

def main():
    print("Fetching GFS 850hPa forecasts...")
    for key, info in LOCATIONS.items():
        try:
            print(f"Processing {key}...")
            raw_data = fetch_gfs_850_data(info["lat"], info["lon"])
            img_path = plot_meteogram_850(key, info, raw_data)
            caption = (
                f"📊 پیش‌بینی ۳ روزه تراز ۸۵۰ هکتوپاسکال (GFS)\n"
                f"📍 ایستگاه: {info['name_fa']}\n"
                f"🌡 شامل کلیه قله‌ها و دره‌های دمایی و پیک باد\n"
                f"⏱ صدور: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            send_telegram_photo(img_path, caption)
        except Exception as e:
            print(f"Error processing {key}: {e}")

if __name__ == "__main__":
    main()
