import os
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# تنظیمات مناطق (قم، دستجرد، قاهان، کهک) با کلیدهای انگلیسی استاندارد برای جلوگیری از خطای انکودینگ
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
        print("Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})
        print("Telegram response:", resp.status_code, resp.text)

def send_to_bale(photo_path, caption):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        print("Bale credentials missing.")
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        resp = requests.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})
        print("Bale response:", resp.status_code, resp.text)

def generate_meteograms():
    for name, coords in LOCATIONS.items():
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}"
               f"&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m&forecast_days=3")
        res = requests.get(url).json()
        
        if "hourly" not in res:
            print(f"Error fetching data for {name}: {res}")
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
        
        # رسم نمودار مشابه YR / Open-Meteo با نمایش مقادیر کمینه و بیشینه
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True, gridspec_kw={'height_ratios': [3, 1.5, 1]})
        fig.patch.set_facecolor('#ffffff')
        
        # ۱. نمودار دما
        ax1.plot(times, temps, color='#d9534f', linewidth=2.5, label=f'دما (ماکزیمم: {max_temp}°C | مینیمم: {min_temp}°C)')
        ax1.fill_between(times, temps, min(temps)-1, color='#d9534f', alpha=0.1)
        ax1.set_ylabel('دما (°C)', fontsize=11, fontweight='bold', color='#333333')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.set_title(f"پیش‌بینی سطحی ۳ روزه - {name}", fontsize=13, fontweight='bold', color='#222222', pad=12)
        ax1.legend(loc='upper left', fontsize=10)
        
        # ۲. نمودار بارش
        ax2.bar(times, precip, width=0.03, color='#337ab7', alpha=0.8, label=f'بارش (مجموع: {total_precip:.1f} mm)')
        ax2.set_ylabel('بارش (mm)', fontsize=11, fontweight='bold', color='#333333')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper left', fontsize=10)
        
        # ۳. نمودار سرعت باد
        ax3.plot(times, wind_speed, color='#6f42c1', linewidth=1.8, label=f'سرعت باد (حداکثر: {max_wind} km/h)')
        ax3.set_ylabel('باد (km/h)', fontsize=11, fontweight='bold', color='#333333')
        ax3.grid(True, linestyle='--', alpha=0.5)
        ax3.legend(loc='upper left', fontsize=10)
        
        # تنظیم محور زمان
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d %b - %H:%00'))
        plt.xticks(rotation=25, fontsize=9)
        
        plt.tight_layout()
        filename = f"surface_meteogram_{coords['lat']}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        caption = (f"📊 **متئوگرام سطحی ۳ روزه**\n"
                   f"📍 منطقه: {name}\n"
                   f"🌡 بیشینه: {max_temp}°C | کمینه: {min_temp}°C\n"
                   f"🌧 مجموع بارش: {total_precip:.1f} mm\n"
                   f"💨 حداکثر باد: {max_wind} km/h\n"
                   f"⏰ به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        send_to_telegram(filename, caption)
        send_to_bale(filename, caption)

if __name__ == "__main__":
    generate_meteograms()
