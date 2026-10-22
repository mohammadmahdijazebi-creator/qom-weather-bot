import os
import time
import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from meteogram_qom import generate_qom_meteogram

# تنظیمات و توکن‌ها از محیط یا پیش‌فرض
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
CHANNEL_ID = os.getenv("CHANNEL_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", os.getenv("BALE_CHAT_ID", ""))

REQ_TIMEOUT = 50

# اهداف مدل‌ها و ایستگاه‌ها
ECMWF_TARGETS = [
    {"lat": 34.64, "lon": 50.86, "name": "Qom", "file": "ecmwf_1_qom.png"},
    {"lat": 34.3938, "lon": 50.8643, "name": "Kahak", "file": "ecmwf_2_kahak.png"},
    {"lat": 34.3949, "lon": 49.9502, "name": "Dastjerd", "file": "ecmwf_3_dastjerd.png"},
    {"lat": 34.4775, "lon": 50.4592, "name": "Salafchegan", "file": "ecmwf_4_salafchegan.png"},
    {"lat": 34.7245, "lon": 50.2632, "name": "Qahan", "file": "ecmwf_5_qahan.png"}
]

TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

YR_TARGETS = [
    {"url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom/Qom", "name": "Qom Table", "file": "yr_1_qom.png"},
    {"url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom/Qom", "name": "Qom Graph", "file": "yr_2_qom.png"},
    {"url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom/Kahak", "name": "Kahak Table", "file": "yr_3_kahak.png"},
    {"url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom/Kahak", "name": "Kahak Graph", "file": "yr_4_kahak.png"},
    {"url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom/Salafchegan", "name": "Salafchegan Table", "file": "yr_5_salafchegan.png"},
    {"url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom/Salafchegan", "name": "Salafchegan Graph", "file": "yr_6_salafchegan.png"},
    {"url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi/Dastjerd", "name": "Dastjerd Table", "file": "yr_7_dastjerd.png"},
    {"url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi/Dastjerd", "name": "Dastjerd Graph", "file": "yr_8_dastjerd.png"},
    {"url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom/Qahan", "name": "Qahan Table", "file": "yr_9_qahan.png"},
    {"url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom/Qahan", "name": "Qahan Graph", "file": "yr_10_qahan.png"}
]

FORECA_TARGETS = [
    {"url": "https://www.foreca.com/100112507/Qom-Iran", "name": "Qom 10d", "file": "foreca_1_qom.png"},
    {"url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran", "name": "Salafchegan 10d", "file": "foreca_2_salafchegan.png"},
    {"url": "https://www.foreca.com/100120681/Qah%C4%81n-Qom-Province-Iran", "name": "Qahan 10d", "file": "foreca_3_qahan.png"}
]

WEATHER_FORECAST_TARGETS = [
    {"url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest", "name": "Qom", "file": "wf_1_qom.png"},
    {"url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest", "name": "Kahak", "file": "wf_2_kahak.png"},
    {"url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest", "name": "Salafchegan", "file": "wf_3_salafchegan.png"},
    {"url": "https://www.weather-forecast.com/locations/Dastjerd/forecasts/latest", "name": "Dastjerd", "file": "wf_4_dastjerd.png"},
    {"url": "https://www.weather-forecast.com/locations/Qahan/forecasts/latest", "name": "Qahan", "file": "wf_5_qahan.png"}
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def send_media(method_name, file_field, path, caption):
    """ارسال عکس به تلگرام و بله با مدیریت خطا و تایم‌اوت ایمن"""
    if not os.path.exists(path) or os.path.getsize(path) < 500:
        print(f"[هشدار] فایل {path} نامعتبر یا خالی است. از ارسال صرف‌نظر شد.")
        return

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                resp = SESSION.post(url, data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
            if resp.status_code != 200:
                print(f"[تلگرام] خطا در ارسال {path}: {resp.text}")
        except Exception as e:
            print(f"[تلگرام] خطای ارتباطی برای {path}: {e}")
        time.sleep(1.0)

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                resp = SESSION.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
            if resp.status_code != 200:
                print(f"[بله] خطا در ارسال {path}: {resp.text}")
        except Exception as e:
                    print(f"[بله] خطای ارتباطی برای {path}: {e}")
        time.sleep(1.0)

def capture_and_send_custom_meteogram():
    try:
        print("تولید و ارسال متئوگرام تخصصی چندمدلی قم...")
        out_file = "qom_live_multimodel_meteogram.png"
        generate_qom_meteogram(out_file)
        caption = "🌡 <b>متئوگرام پیشرفته و چندمدلی هواشناسی قم</b>\nECMWF | GFS | ICON | GEM\n📅 به‌روزرسانی خودکار"
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا] در تولید متئوگرام سفارشی: {e}")

def capture_ecmwf(page):
    print("بررسی و دریافت نقشه‌های ECMWF...")
    for item in ECMWF_TARGETS:
        try:
            url = f"https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat={item['lat']}&lon={item['lon']}&station_name={item['name']}"
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            path = item["file"]
            page.screenshot(path=path, full_page=True)
            caption = f"🌍 <b>مدل ECMWF - ایستگاه {item['name']}</b>\nپیش‌بینی جوی ۱۰ روزه"
            send_media("sendPhoto", "photo", path, caption)
        except Exception as e:
            print(f"[هشدار] عبور از ECMWF برای {item['name']}: {e}")
        time.sleep(1.5)

def capture_tropical_tidbits(page):
    print("بررسی و دریافت مدل GFS (Tropical Tidbits)...")
    for fh in [12, 24, 48, 72]:
        try:
            url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn&fh={fh}"
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"tropical_pcpn_fh{fh}.png"
            page.screenshot(path=path)
            caption = f"🛰 <b>مدل GFS (بارش و فشار) - افق {fh} ساعته</b>"
            send_media("sendPhoto", "photo", path, caption)
        except Exception as e:
            print(f"[هشدار] عبور از Tropical Tidbits (fh={fh}): {e}")
        time.sleep(1.5)

def capture_yr(page):
    print("بررسی و دریافت اطلاعات سایت Yr.no...")
    for item in YR_TARGETS:
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            path = item["file"]
            page.screenshot(path=path, full_page=True)
            caption = f"⛅️ <b>سایت Yr.no - {item['name']}</b>"
            send_media("sendPhoto", "photo", path, caption)
        except Exception as e:
            print(f"[هشدار] عبور از Yr.no برای {item['name']}: {e}")
        time.sleep(1.5)

def capture_foreca(page):
    print("بررسی و دریافت اطلاعات سایت Foreca...")
    for item in FORECA_TARGETS:
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            path = item["file"]
            page.screenshot(path=path, full_page=True)
            caption = f"🌐 <b>سایت Foreca - {item['name']}</b>"
            send_media("sendPhoto", "photo", path, caption)
        except Exception as e:
            print(f"[هشدار] عبور از Foreca برای {item['name']}: {e}")
        time.sleep(1.5)

def capture_weather_forecast(page):
    print("بررسی و دریافت Weather-Forecast...")
    for item in WEATHER_FORECAST_TARGETS:
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            path = item["file"]
            page.screenshot(path=path, full_page=True)
            caption = f"📈 <b>سایت Weather-Forecast - {item['name']}</b>"
            send_media("sendPhoto", "photo", path, caption)
        except Exception as e:
            print(f"[هشدار] عبور از Weather-Forecast برای {item['name']}: {e}")
        time.sleep(1.5)

def main():
    print("شروع اجرای ربات هواشناسی قم با محافظت ضدقفل...")
    
    # اول متئوگرام محلی را تولید و ارسال کن
    capture_and_send_custom_meteogram()

    # حالا اسکرپ با پلی‌ورایت با تایم‌اوت‌های کاملاً ایمن ۱۵ ثانیه‌ای
    browser_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=browser_args)
            context = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US")
            page = context.new_page()

            capture_ecmwf(page)
            capture_tropical_tidbits(page)
            capture_yr(page)
            capture_foreca(page)
            capture_weather_forecast(page)

            browser.close()
    except Exception as e:
        print(f"[خطای کلی مرورگر] {e}")

    print("کار ربات با موفقیت به پایان رسید.")

if __name__ == "__main__":
    main()
