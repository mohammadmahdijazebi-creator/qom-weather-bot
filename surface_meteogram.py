import os
import requests
import matplotlib
matplotlib.use('Agg') # غیرفعال کردن رابط گرافیکی برای اجرا در گیت‌هاب
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# تنظیم فونت فارسی در صورت وجود در سیستم لینوکس گیت‌هاب
plt.rcParams['font.family'] = 'DejaVu Sans' # سازگار با کاراکترها، برای فارسی از متن انگلیسی استاندارد یا سیستم استفاده می‌شود

# ۴ منطقه کامل مورد نظر مهدی عزیز
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
    try:
        with open(photo_path, 'rb') as photo:
            resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=30)
            print("Telegram response:", resp.status_code, resp.text)
    except Exception as e:
        print("Telegram send error:", e)

def send_to_bale(photo_path, caption):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        print("Bale credentials missing.")
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            resp = requests.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=30)
            print("Bale response:", resp.status_code, resp.text)
    except Exception as e:
        print("Bale send error:", e)

def generate_meteograms():
    for name, coords in LOCATIONS.items():
        print(f"Processing forecast for {name}...")
        try:
            url = (f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}"
                   f"&hourly=temperature_2m,precipitation,wind_speed_10m&forecast_days=3")
            res = requests.get(url, timeout=20).json()
            
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
            max_temp_time = times[temps.index(max_temp)]
            min_temp_time = times[temps.index(min_temp)]
            
            max_wind = max(wind_speed)
            total_precip = sum(precip)
            
            # رسم نمودار سه بخشی
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True, gridspec_kw={'height_ratios': [3, 1.5, 1]})
            fig.patch.set_facecolor('#ffffff')
            
            # ۱. نمودار دما همراه با آنوتیشن مقادیر کمینه و بیشینه روی نمودار
            ax1.plot(times, temps, color='#d9534f', linewidth=2.2, label='Temperature (°C)')
            ax1.fill_between(times, temps, min(temps)-2, color='#d9534f', alpha=0.1)
            
            # ثبت نقاط مکس و مین روی نمودار دما
            ax1.annotate(f'Max: {max_temp}°C', xy=(max_temp_time, max_temp), xytext=(max_temp_time, max_temp + 1.5),
                         arrowprops=dict(facecolor='#d9534f', shrink=0.05, width=1, headwidth=5),
                         fontsize=9, fontweight='bold', color='#d9534f', ha='center')
            ax1.annotate(f'Min: {min_temp}°C', xy=(min_temp_time, min_temp), xytext=(min_temp_time, min_temp - 2.5),
                         arrowprops=dict(facecolor='#337ab7', shrink=0.05, width=1, headwidth=5),
                         fontsize=9, fontweight='bold', color='#337ab7', ha='center')

            ax1.set_ylabel('Temperature (°C)', fontsize=10, fontweight='bold')
            ax1.grid(True, linestyle='--', alpha=0.5)
            ax1.set_title(f"3-Day Surface Meteogram - {name}", fontsize=12, fontweight='bold', pad=10)
            ax1.legend(loc='upper right', fontsize=9)
            
            # ۲. نمودار بارش
            ax2.bar(times, precip, width=0.03, color='#337ab7', alpha=0.85, label=f'Precipitation (Total: {total_precip:.1f} mm)')
            ax2.set_ylabel('Precip (mm)', fontsize=10, fontweight='bold')
            ax2.grid(True, linestyle='--', alpha=0.5)
            ax2.legend(loc='upper right', fontsize=9)
            
            # ۳. نمودار سرعت باد
            ax3.plot(times, wind_speed, color='#6f42c1', linewidth=1.6, label=f'Wind Speed (Max: {max_wind} km/h)')
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
            print(f"Successfully processed and sent for {name}")
            
        except Exception as e:
            print(f"Error processing {name}: {e}")

if __name__ == "__main__":
    generate_meteograms()
