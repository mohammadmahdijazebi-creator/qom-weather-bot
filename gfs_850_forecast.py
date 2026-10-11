import os
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from datetime import datetime

# --- تنظیمات نقاط استان قم ---
LOCATIONS = {
    "Qom": {"name_fa": "قم", "lat": 34.64, "lon": 50.88},
    "Dastjerd": {"name_fa": "دستجرد", "lat": 34.55, "lon": 50.25},
    "Qahan": {"name_fa": "قاهان", "lat": 34.70, "lon": 50.26},
    "Kahak": {"name_fa": "کهک", "lat": 34.38, "lon": 50.86}
}

# --- دریافت خودکار توکن و شناسه چت از انواع نام‌گذاری‌های محیطی ---
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
    """دریافت داده‌های تراز ۸۵۰ از مدل GFS برای ۳ روز آینده"""
    url = "https://api.open-meteo.com/v1/gfs"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_850hPa", "windspeed_850hPa", "winddirection_850hPa"],
        "wind_speed_unit": "kmh",
        "forecast_days": 3,
        "timezone": "Asia/Tehran"
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()["hourly"]

def plot_meteogram_850(city_key, info, data):
    times = pd.to_datetime(data["time"])
    temps = np.array(data["temperature_850hPa"])
    winds = np.array(data["windspeed_850hPa"])
    dirs = np.array(data["winddirection_850hPa"])

    fig, (ax_temp, ax_wind) = plt.subplots(
        2, 1, figsize=(11, 7.5), sharex=True, dpi=160,
        gridspec_kw={'height_ratios': [1.2, 1]}
    )
    fig.patch.set_facecolor('#0f172a')  # پس‌زمینه تیره مدرن

    # --- نمودار دما (850hPa) ---
    ax_temp.set_facecolor('#1e293b')
    ax_temp.plot(times, temps, color='#f97316', lw=2.5, label='دمای تراز ۸۵۰ هکتوپاسکال (°C)')
    ax_temp.fill_between(times, temps, temps.min() - 2, color='#f97316', alpha=0.15)

    # نمایش بیشینه و کمینه دما
    max_idx = np.argmax(temps)
    min_idx = np.argmin(temps)
    ax_temp.scatter([times[max_idx], times[min_idx]], [temps[max_idx], temps[min_idx]], color='#ef4444', s=40, zorder=5)
    ax_temp.annotate(
        f"Max: {temps[max_idx]:.1f}°C", (times[max_idx], temps[max_idx]),
        textcoords="offset points", xytext=(0, 8), ha='center', color='#fde047', fontsize=9, fontweight='bold'
    )
    ax_temp.annotate(
        f"Min: {temps[min_idx]:.1f}°C", (times[min_idx], temps[min_idx]),
        textcoords="offset points", xytext=(0, -14), ha='center', color='#38bdf8', fontsize=9, fontweight='bold'
    )

    ax_temp.set_ylabel("دما (°C)", color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_temp.tick_params(colors='#94a3b8')
    ax_temp.grid(True, linestyle='--', alpha=0.25, color='#64748b')
    ax_temp.set_title(
        f"پیش‌بینی ۳ روزه تراز ۸۵۰ هکتوپاسکال (مدل GFS) — ایستگاه {info['name_fa']} ({city_key})",
        color='#f8fafc', fontsize=13, fontweight='bold', pad=12
    )

    # --- نمودار سرعت باد (850hPa) ---
    ax_wind.set_facecolor('#1e293b')
    ax_wind.bar(times, winds, width=0.03, color='#38bdf8', alpha=0.75, label='سرعت باد (km/h)')

    # رسم فلش‌های جهت باد هر ۳ ساعت یک‌بار
    step = 3
    u = -np.sin(np.radians(dirs[::step]))
    v = -np.cos(np.radians(dirs[::step]))
    ax_wind.quiver(
        times[::step], winds[::step] + 4, u, v,
        color='#fde047', scale=22, width=0.0035, headwidth=4, headlength=5
    )

    ax_wind.set_ylabel("سرعت باد (km/h)", color='#e2e8f0', fontsize=11, fontweight='bold')
    ax_wind.tick_params(colors='#94a3b8')
    ax_wind.grid(True, linestyle='--', alpha=0.25, color='#64748b')
    ax_wind.set_ylim(0, max(winds) * 1.35 + 5)

    # برچسب‌های زمانی محور افقی
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
        print(f"[Warning] Telegram credentials missing. Bot Token: {bool(TELEGRAM_BOT_TOKEN)}, Chat ID: {bool(TELEGRAM_CHAT_ID)}")
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
                f"📊 پیش‌بینی ۳ روزه تراز ۸۵۰ هکتوپاسکال\n"
                f"📍 ایستگاه: {info['name_fa']}\n"
                f"🌀 مدل: GFS\n"
                f"⏱ زمان صدور: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            send_telegram_photo(img_path, caption)
        except Exception as e:
            print(f"Error processing {key}: {e}")

if __name__ == "__main__":
    main()
