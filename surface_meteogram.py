import os
import time
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from scipy.signal import find_peaks

LOCATIONS = {
    "Qom (قم)": {"lat": 34.64, "lon": 50.88},
    "Dastjerd (دستجرد)": {"lat": 34.55, "lon": 50.25},
    "Qahan (قاهان)": {"lat": 34.70, "lon": 50.26},
    "Kahak (کهک)": {"lat": 34.38, "lon": 50.86}
}

TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("CHANNEL_ID") or os.environ.get("TELEGRAM_CHAT_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def send_to_telegram(photo_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=30)
    except Exception as e:
        print("Telegram error:", e)

def send_to_bale(photo_path, caption):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=30)
    except Exception as e:
        print("Bale error:", e)

def fetch_weather_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation,wind_speed_10m&forecast_days=3"
    for attempt in range(3):
        try:
            res = requests.get(url, timeout=25).json()
            if "hourly" in res:
                return res
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return None

def generate_meteograms():
    for name, coords in LOCATIONS.items():
        print(f"Processing forecast for {name}...")
        res = fetch_weather_data(coords['lat'], coords['lon'])
        if not res:
            print(f"Failed to fetch data for {name} after retries.")
            continue
            
        hourly = res["hourly"]
        times = [datetime.fromisoformat(t) for t in hourly["time"]]
        temps = hourly["temperature_2m"]
        precip = hourly["precipitation"]
        wind_speed = hourly["wind_speed_10m"]
        
        max_temp = max(temps)
        min_temp = min(temps)
        max_wind = max(wind_speed)
        total_precip = sum(precip)
        
        # رسم نمودار سه بخشی
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1.5, 1]})
        fig.patch.set_facecolor('#ffffff')
        
        # ۱. نمودار دما و برچسب‌گذاری قله‌ها و دره‌ها
        ax1.plot(times, temps, color='#d9534f', linewidth=2, label='Temperature (°C)')
        ax1.fill_between(times, temps, min(temps)-2, color='#d9534f', alpha=0.08)
        
        # پیدا کردن اوج‌ها (قله‌ها و دره‌ها) برای نمایش اعداد روی نمودار دما
        import numpy as np
        temps_arr = np.array(temps)
        peaks, _ = find_peaks(temps_arr, distance=12) # قله‌های روزانه
        valleys, _ = find_peaks(-temps_arr, distance=12) # دره‌های شبانه
        
        for p in peaks:
            ax1.annotate(f"{temps[p]}°C", xy=(times[p], temps[p]), xytext=(times[p], temps[p] + 1.2),
                         fontsize=8, fontweight='bold', color='#b52b27', ha='center',
                         arrowprops=dict(arrowstyle="-", color='#d9534f', lw=0.5))
        for v in valleys:
            ax1.annotate(f"{temps[v]}°C", xy=(times[v], temps[v]), xytext=(times[v], temps[v] - 1.8),
                         fontsize=8, fontweight='bold', color='#1d6fa5', ha='center',
                         arrowprops=dict(arrowstyle="-", color='#337ab7', lw=0.5))

        ax1.set_ylabel('Temperature (°C)', fontsize=10, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.set_title(f"3-Day Surface Meteogram - {name}", fontsize=13, fontweight='bold', pad=12)
        ax1.legend(loc='upper right', fontsize=9)
        
        # ۲. نمودار بارش
        ax2.bar(times, precip, width=0.03, color='#337ab7', alpha=0.85, label=f'Precipitation (Total: {total_precip:.1f} mm)')
        ax2.set_ylabel('Precip (mm)', fontsize=10, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper right', fontsize=9)
        
        # ۳. نمودار باد و برچسب قله‌های باد
        ax3.plot(times, wind_speed, color='#6f42c1', linewidth=1.5, label='Wind Speed (km/h)')
        wind_peaks, _ = find_peaks(np.array(wind_speed), distance=16, height=max(wind_speed)*0.6)
        for wp in wind_peaks:
            ax3.annotate(f"{wind_speed[wp]}", xy=(times[wp], wind_speed[wp]), xytext=(times[wp], wind_speed[wp] + 3),
                         fontsize=7, fontweight='bold', color='#5a32a3', ha='center')

        ax3.set_ylabel('Wind (km/h)', fontsize=10, fontweight='bold')
        ax3.grid(True, linestyle='--', alpha=0.5)
        ax3.legend(loc='upper right', fontsize=9)
        
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d %b - %H:%00'))
        plt.xticks(rotation=20, fontsize=8)
        
        plt.tight_layout()
        filename = f"surface_meteogram_{coords['lat']}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        caption = (f"📊 *متئوگرام سطحی ۳ روزه*\n"
                   f"📍 منطقه: `{name}`\n"
                   f"🌡 بیشینه: `{max_temp}°C` | کمینه: `{min_temp}°C`\n"
                   f"🌧 مجموع بارش: `{total_precip:.1f} mm`\n"
                   f"💨 حداکثر باد: `{max_wind} km/h`\n"
                   f"⏰ به‌روزرسانی: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`")
        
        send_to_telegram(filename, caption)
        send_to_bale(filename, caption)
        print(f"Successfully sent for {name}")
        time.sleep(2) # وقفه کوتاه بین درخواست شهرها برای جلوگیری از Timeout

if __name__ == "__main__":
    generate_meteograms()
