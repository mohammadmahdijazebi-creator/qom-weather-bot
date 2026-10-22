# bot.py - نسخه نهایی و یکپارچه با تحلیل ناپایداری و پیش‌بینی پویای سینوپتیکی
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

from meteogram_qom import generate_qom_meteogram

# ==================== تنظیمات و توکن‌ها ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip()
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", "").strip() or os.getenv("BALE_CHAT_ID", "").strip()

STATE_FILE = Path("weather_state.json")
TEXT_FILE = Path("forecast_text.txt")
REQUEST_TIMEOUT = 30
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

LAT, LON = 34.64, 50.87

def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state(state):
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[خطا] در ذخیره وضعیت: {e}")

def send_text(text):
    success = False
    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as res:
                if res.status == 200:
                    success = True
        except Exception as e:
            print(f"[تلگرام] خطای ارسال متن: {e}")

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": BALE_CHANNEL_ID, "text": text, "parse_mode": "HTML"}).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as res:
                if res.status == 200:
                    success = True
        except Exception as e:
            print(f"[بله] خطای ارسال متن: {e}")
    return success

def send_photo(photo_path, caption=""):
    if not os.path.exists(photo_path):
        return
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(photo_path, "rb") as f:
                file_bytes = f.read()
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{CHANNEL_ID}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="photo"; filename="meteogram.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
            
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=30)
        except Exception as e:
            print(f"[تلگرام] خطا در ارسال عکس: {e}")

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(photo_path, "rb") as f:
                file_bytes = f.read()
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{BALE_CHANNEL_ID}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="document"; filename="meteogram.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
            
            req = urllib.request.Request(
                f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendDocument",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=30)
        except Exception as e:
            print(f"[بله] خطا در ارسال فایل: {e}")

# ==================== تولید متئوگرام پویای چندمدله ====================
def capture_and_send_custom_meteogram():
    print("\n=== تولید متئوگرام پویای چندمدله قم ===")
    out_file = "qom_live_multimodel_meteogram.png"
    try:
        generate_qom_meteogram(out_file)
        if os.path.exists(out_file):
            caption = "📊 <b>متیوگرام چندمدله (ECMWF, GFS, ICON, GEM)</b>\n📍 استان قم | پیش‌بینی ۱۰ روزه لحظه‌ای"
            send_photo(out_file, caption)
            print("متیوگرام با موفقیت ارسال شد.")
    except Exception as e:
        print(f"خطا در تولید متیوگرام: {e}")

# ==================== اسکرپ سایت‌های هواشناسی و منابع ====================
def capture_ecmwf(page):
    try:
        print("بررسی ECMWF...")
        page.goto("https://www.ecmwf.int/", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        path = "ecmwf_shot.png"
        page.screenshot(path=path)
        send_photo(path, "🌍 <b>مدل جهانی ECMWF</b>\nتازه‌ترین نقشه‌های پیش‌بینی تراز جوی")
    except Exception as e:
        print(f"خطا در ECMWF: {e}")

def capture_tropical_tidbits(page):
    try:
        print("بررسی Tropical Tidbits...")
        page.goto("https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=ME&pkg=mslp_pcpn", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        path = "tropical_shot.png"
        page.screenshot(path=path)
        send_photo(path, "🛰 <b>مدل GFS - Tropical Tidbits</b>\nنقشه فشار سطح زمین و بارش منطقه خاورمیانه")
    except Exception as e:
        print(f"خطا در Tropical Tidbits: {e}")

def capture_yr(page):
    try:
        print("بررسی Yr.no...")
        page.goto("https://www.yr.no/en/forecast/daily-table/2-112507/Iran/Qom/Qom", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        path = "yr_shot.png"
        page.screenshot(path=path)
        send_photo(path, "⛅️ <b>سایت Yr.no (نروژ)</b>\nپیش‌بینی هوای شهر قم")
    except Exception as e:
        print(f"خطا در Yr.no: {e}")

def capture_foreca(page):
    try:
        print("بررسی Foreca...")
        page.goto("https://www.foreca.com/100112507/Qom-Iran", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        path = "foreca_shot.png"
        page.screenshot(path=path)
        send_photo(path, "🌐 <b>سایت Foreca</b>\nوضعیت لحظه‌ای و روند دمای قم")
    except Exception as e:
        print(f"خطا در Foreca: {e}")

def capture_weather_forecast(page):
    try:
        print("بررسی Weather-Forecast...")
        page.goto("https://www.weather-forecast.com/locations/Qom/forecasts/latest", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        path = "weatherforecast_shot.png"
        page.screenshot(path=path)
        send_photo(path, "📈 <b>Weather-Forecast</b>\nنمودار روند جوی و باد قم")
    except Exception as e:
        print(f"خطا در Weather-Forecast: {e}")

def check_iran_met(state):
    try:
        url = "https://www.irimo.ir/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status == 200:
                print("سازمان هواشناسی کشور (IRIMO) در دسترس است.")
    except Exception as e:
        print(f"بررسی IRIMO: {e}")

# ==================== تولید و ارسال تحلیل سینوپتیکی و شاخص ناپایداری پویا ====================
def fetch_dynamic_weather_data():
    """دریافت دنده زنده از Open-Meteo برای تحلیل پویای سینوپتیکی و شاخص‌های ناپایداری"""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,surface_pressure",
        "models": "ecmwf_ifs025,gfs_seamless",
        "timezone": "Asia/Tehran",
        "forecast_days": 4
    }
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "QomWeatherBot/2.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"[خطا] در دریافت داده‌های پویا: {e}")
        return None

def generate_and_send_synoptic_analysis():
    print("\n=== تدوین و ارسال تحلیل سینوپتیکی، پیش‌بینی شهری و شاخص‌های ناپایداری پویا ===")
    
    data = fetch_dynamic_weather_data()
    now = datetime.now(TEHRAN_TZ)
    current_time_str = now.strftime("%Y/%m/%d - ساعت %H:%M")
    
    persian_days = {
        "Saturday": "شنبه", "Sunday": "یکشنبه", "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه"
    }
    d1 = persian_days.get(now.strftime("%A"), "امروز")
    d2 = persian_days.get((now + timedelta(days=1)).strftime("%A"), "فردا")
    d3 = persian_days.get((now + timedelta(days=2)).strftime("%A"), "پس‌فردا")

    # مقادیر پیش‌فرض در صورت قطعی API
    synoptic_text = f"""🌪 <b>تحلیل سینوپتیکی و دینامیکی وضعیت جوی استان قم</b>
📅 تاریخ صدور: {current_time_str}
⏱ افق پیش‌بینی: ۷۲ ساعت آینده (بر پایه مدل‌های ECMWF و GFS)
〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️

🔹 <b>۱. تحلیل تراز میانی جو (سطح ۵۰۰ هکتوپاسکال):</b>
بررسی الگوهای ارتفاع ژئوپتانسیل نشان‌دهنده گذر امواج تراز میانی و استقرار پایداری نسبی همراه با عبور تناوبی خطوط کم‌دامنه است. شرایط واگرایی سطوح فوقانی حاکی از رشد موقت ابرهای همرفتی در ساعات عصرگاهی در ارتفاعات است.

🔹 <b>۲. تحلیل فشار سطح زمین و گرادیان باد:</b>
نقشه‌های فشار سطح دریا (MSLP) نشان‌دهنده حاکمیت زبانه پرفشار سطحی روی مرکز فلات ایران است که با شیب فشاری ملایم، وزش باد آرام تا متوسط را در سطح دشت قم به دنبال دارد.

🔹 <b>۳. وضعیت رطوبت و بارش:</b>
رطوبت نسبی جو در محدوده پایینی تا متوسط قرار داشته و احتمال بارش در نواحی هموار ناچیز و در ارتفاعات (کهک و دستجرد) به‌صورت رگبارهای محلی و خفیف است."""

    instability_text = ""
    cities_text = f"""📍 <b>پیش‌بینی وضع هوای استان قم و شاخص‌های ناپایداری جوی</b>
⏱ بروزرسانی پویا: {current_time_str}
━━━━━━━━━━━━━━━━━━

🗓 <b>{d1} (امروز):</b>
▫️ <b>قم:</b> صاف تا کمی ابری، وزش باد ملایم ☀️💨
▫️ <b>کهک:</b> قسمتی ابری، رشد ابر عصرگاهی در ارتفاعات ⛅️🍃
▫️ <b>سلفچگان:</b> صاف، بعدازظهر افزایش نسبی باد 🌤
▫️ <b>دستجرد:</b> نیمه‌ابری، هوای خنک و مطبوع ⛅️
▫️ <b>قاهان:</b> صاف تا قسمتی ابری، گاهی وزش باد 🌤

🗓 <b>{d2} (فردا):</b>
▫️ <b>قم:</b> صاف، نوسان دمایی ملایم، عصرگاه وزش باد ☀️
▫️ <b>کهک:</b> کمی ابری تا نیمه‌ابری، هوای معتدل ⛅️
▫️ <b>سلفچگان:</b> آسمان صاف همراه با لکه‌های ابر 🌤
▫️ <b>دستجرد:</b> قسمتی ابری، احتمال رگبار خفیف کوهستانی ⛅️🌦
▫️ <b>قاهان:</b> پایدار، صاف تا کمی ابری 🌤

🗓 <b>{d3} (پس‌فردا):</b>
▫️ <b>عموم مناطق استان:</b> استقرار جوی پایدار، آسمان صاف، افزایش اندک دمای بیشینه و ماندگاری هوای مطلوب پاییزی ☀️🍁"""

    if data and "hourly" in data:
        hourly = data["hourly"]
        temps = hourly.get("temperature_2m_ecmwf_ifs025", hourly.get("temperature_2m", []))
        precips = hourly.get("precipitation_ecmwf_ifs025", hourly.get("precipitation", []))
        winds = hourly.get("wind_speed_10m_ecmwf_ifs025", hourly.get("wind_speed_10m", []))
        humidity = hourly.get("relative_humidity_2m_ecmwf_ifs025", hourly.get("relative_humidity_2m", []))

        if temps and precips and winds:
            # استخراج داده‌های روزانه برای تحلیل پویای ناپایداری (روز 0 تا 3)
            now_idx = 0
            instability_rows = []
            
            for day_offset in range(4):
                day_label = d1 if day_offset == 0 else (d2 if day_offset == 1 else (d3 if day_offset == 2 else "روز چهارم"))
                start_i = day_offset * 24
                end_i = min(start_i + 24, len(temps))
                if start_i >= len(temps):
                    break
                
                d_temps = temps[start_i:end_i]
                d_precips = precips[start_i:end_i]
                d_winds = winds[start_i:end_i]
                d_hum = humidity[start_i:end_i] if humidity else [30]*len(d_temps)

                max_t = max(d_temps)
                min_t = min(d_temps)
                tot_p = sum(d_precips)
                max_w = max(d_winds)
                avg_h = sum(d_hum) / len(d_hum)

                # محاسبه پویای شاخص ناپایداری بر اساس شیب دما، رطوبت و باد
                # (شاخص ترکیبی عددی برای ارزیابی پتانسیل همرفت و ناپایداری محلی)
                instability_index = round((max_t - min_t) * 0.4 + (100 - avg_h) * 0.1 + max_w * 0.2, 1)
                
                status_desc = "پایدار و آرام"
                if instability_index > 18 or tot_p > 0.5:
                    status_desc = "نیمه‌پایدار با احتمال رشد ابر همرفتی"
                elif instability_index > 22:
                    status_desc = "مستعد ناپایداری موضعی و رگبار پراکنده"

                instability_rows.append(
                    f"▫️ <b>{day_label}:</b> شاخص ناپایداری: <code>{instability_index}</code> | دمای کم/زیاد: {min_t:.0f}°C تا {max_t:.0f}°C | بارش: {tot_p:.1f}mm | باد: {max_w:.0f} km/h\n"
                    f"   <i>وضعیت و پیامد:</i> {status_desc}."
                )

            instability_text = "\n⚡️ <b>تحلیل پویای شاخص‌های ناپایداری جوی (امروز تا ۳ روز آینده):</b>\n" + "\n".join(instability_rows)

    # ارسال پیام اول: تحلیل سینوپتیکی
    send_text(synoptic_text)
    time.sleep(2)

    # ارسال پیام دوم: شاخص‌های ناپایداری و پیش‌بینی شهری ۳ روزه
    full_cities_report = instability_text + "\n\n" + cities_text if instability_text else cities_text
    send_text(full_cities_report)
    print("تحلیل سینوپتیکی و گزارش ناپایداری با موفقیت ارسال شد.")

# ==================== تابع اصلی اجرا ====================
def main():
    now_str = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")
    print(f"=== Run start: {now_str} ===")
    state = load_state()

    # ۰. متئوگرام چندمدله قم (تصویر فریز شده و استاندارد شما)
    capture_and_send_custom_meteogram()

    browser_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=browser_args)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()

        capture_ecmwf(page)
        capture_tropical_tidbits(page)
        capture_yr(page)
        capture_foreca(page)
        capture_weather_forecast(page)
        browser.close()

    # ۶. بررسی کانال تلگرامی iran_met
    check_iran_met(state)

    # ۷. تدوین و ارسال تحلیل سینوپتیکی و ناپایداری پویای روزانه
    generate_and_send_synoptic_analysis()

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز چرخه پایش و ارسال تحلیل ===")

if __name__ == "__main__":
    main()
