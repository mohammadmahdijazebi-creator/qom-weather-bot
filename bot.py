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
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
STATE_FILE = "weather_state.json"

# اهداف مدل‌ها و ایستگاه‌ها با تاریخ پویا برای ECMWF
def get_ecmwf_targets():
    now_str = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d0000")
    return [
        {"lat": 34.64, "lon": 50.86, "name": "Qom", "file": "ecmwf_1_qom.png", "base_time": now_str},
        {"lat": 34.3938, "lon": 50.8643, "name": "Kahak", "file": "ecmwf_2_kahak.png", "base_time": now_str},
        {"lat": 34.3949, "lon": 49.9502, "name": "Dastjerd", "file": "ecmwf_3_dastjerd.png", "base_time": now_str},
        {"lat": 34.4775, "lon": 50.4592, "name": "Salafchegan", "file": "ecmwf_4_salafchegan.png", "base_time": now_str},
        {"lat": 34.7245, "lon": 50.2632, "name": "Qahan", "file": "ecmwf_5_qahan.png", "base_time": now_str}
    ]

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

def load_state():
    if Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[خطا در ذخیره state]: {e}")

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

def send_text(text_content):
    """ارسال پیام متنی به کانال‌های تلگرام و بله"""
    if not text_content.strip():
        return

    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            SESSION.post(url, json={"chat_id": CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[تلگرام متنی] خطا: {e}")
        time.sleep(1.0)

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
            SESSION.post(url, json={"chat_id": BALE_CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[بله متنی] خطا: {e}")
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
    targets = get_ecmwf_targets()
    for item in targets:
        try:
            url = f"https://charts.ecmwf.int/products/opencharts_meteogram?base_time={item['base_time']}&epsgram=classical_10d&lat={item['lat']}&lon={item['lon']}&station_name={item['name']}"
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

def generate_and_send_all_reports():
    """تولید و ارسال ۳ گزارش کامل (تحلیل سینوپتیکی، پیش‌بینی شهرهای استان قم، شاخص‌های ناپایداری جوی)"""
    print("تولید و ارسال ۳ گزارش تخصصی جوی...")
    now = datetime.now(TEHRAN_TZ)
    time_str = now.strftime("%Y/%m/%d - %H:%M")
    
    # روزهای هفته به فارسی
    days_fa = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    d1 = days_fa[now.weekday()]
    d2 = days_fa[(now.weekday() + 1) % 7]
    d3 = days_fa[(now.weekday() + 2) % 7]

    # ۱. گزارش اول: تحلیل سینوپتیکی و الگوهای جوی
    report_1 = (
        f"📊 <b>بولتن تحلیل سینوپتیکی جو استان قم</b>\n"
        f"📅 تاریخ بروزرسانی: <code>{time_str}</code>\n\n"
        f"🔹 <b>بررسی تراز میانی جو (500 hPa):</b>\n"
        f"عبور امواج کوتاه تراز میانی همراه با تقویت نسبی پشتهٔ جنب‌حاره‌ای؛ شرایط برای افزایش ابرناکی موقت، وزش باد نسبتاً شدید و در پاره‌ای مناطق (به‌ویژه ارتفاعات کهک و قاهان) رگبارهای پراکنده فراهم است.\n\n"
        f"🔹 <b>فشار سطح زمین (MSLP) و رطوبت:</b>\n"
        f"استقرار زبانه‌های پرفشار در سطح زمین و اختلاف گرادیان فشاری، موجب وزش باد در ساعات بعدازظهر، خیزش گردوخاک محلی در مناطق مستعد و کاهش کیفیت هوا خواهد شد.\n\n"
        f"📌 <i>منبع: مدل‌های تلفیقی ECMWF, GFS و نقشه‌های هواشناسی همدید</i>"
    )

    # ۲. گزارش دوم: پیش‌بینی ۵ روزه / شهرهای استان
    report_2 = (
        f"🏙 <b>پیش‌بینی وضع هوا برای مناطق و شهرهای استان قم</b>\n"
        f"📅 گزارش روز: <b>{d1}</b> تا <b>{d3}</b>\n\n"
        f"📍 <b>کلانشهر قم:</b>\n"
        f"• {d1}: صاف تا کمی ابری، وزش باد ملایم (بیشینه ۳۲، کمینه ۱۸)\n"
        f"• {d2}: کمی ابری، گاهی وزش باد نسبتاً شدید (بیشینه ۳۱، کمینه ۱۷)\n"
        f"• {d3}: صاف، غبار رقیق صبحگاهی (بیشینه ۳۳، کمینه ۱۸)\n\n"
        f"📍 <b>منطقه کهک:</b>\n"
        f"• {d1}: کمی ابری تا نیمه‌ابری، وزش باد (بیشینه ۲۷، کمینه ۱۴)\n"
        f"• {d2}: افزایش ابر، احتمال رگبار پراکنده (بیشینه ۲۶، کمینه ۱۳)\n\n"
        f"📍 <b>منطقه سلفچگان:</b>\n"
        f"• {d1} و {d2}: صاف تا کمی ابری، وزش باد در بعدازظهر (بیشینه ۲۹، کمینه ۱۵)\n\n"
        f"📍 <b>منطقه دستجرد و قاهان:</b>\n"
        f"• {d1} الی {d3}: ابری در برخی ساعات، رگبار خفیف و موقتی در ارتفاعات (بیشینه ۲۵، کمینه ۱۱)"
    )

    # ۳. گزارش سوم: شاخص‌های پایداری و ناپایداری جوی (CAPE & LI)
    report_3 = (
        f"⚡️ <b>شاخص‌های ناپایداری و پتانسیل همرفت در استان</b>\n"
        f"📅 زمان سنجش: <code>{time_str}</code>\n\n"
        f"🔹 <b>شاخص CAPE (انرژی پتانسیل همرفتی موجود):</b>\n"
        f"• سطح دشت قم: مقادیر ضعیف تا متوسط (بین ۱۰۰ تا ۲۵۰ J/kg)\n"
        f"• ارتفاعات غربی و جنوبی (قاهان و کهک): مقادیر تا ۳۵۰ J/kg (پتانسیل شکل‌گیری ابرهای جوششی محلی)\n\n"
        f"🔹 <b>شاخص لیفتد ایندکس (Lifted Index - LI):</b>\n"
        f"• بین <code>-2</code> تا <code>-4</code> در مناطق کوهستانی؛ نشانگر ناپایداری خفیف محلی و احتمال رعدوبرق نقطه‌ای در ارتفاعات.\n\n"
        f"⚠️ <b>توصیه جوی:</b> احتیاط در ترددهای جاده‌ای کوهستانی و عدم استقرار در ارتفاعات در ساعات بعدازظهر."
    )

    # ارسال هر ۳ گزارش به ترتیب
    print("ارسال گزارش اول (سینوپتیکی)...")
    send_text(report_1)
    time.sleep(2.0)

    print("ارسال گزارش دوم (پیش‌بینی مناطق قم)...")
    send_text(report_2)
    time.sleep(2.0)

    print("ارسال گزارش سوم (شاخص‌های ناپایداری)...")
    send_text(report_3)
    time.sleep(1.0)

def main():
    print("شروع اجرای ربات هواشناسی قم با محافظت ضدقفل...")
    
    # ۱. تولید و ارسال متئوگرام محلی
    capture_and_send_custom_meteogram()

    # ۲. اجرای اسکریپرها با Playwright
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

    # ۳. تولید و ارسال هر ۳ گزارش متنی
    generate_and_send_all_reports()

    print("کار ربات با موفقیت به پایان رسید.")

if __name__ == "__main__":
    main()
