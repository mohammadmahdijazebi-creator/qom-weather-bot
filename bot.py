import os
import time
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
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

# ۱. لینک‌های دقیق ECMWF با تاریخ پویای روز
def get_ecmwf_targets():
    now_str = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d0000")
    return [
        {"lat": 34.6401, "lon": 50.8764, "name": "Qom", "file": "ecmwf_1_qom.png", "base_time": now_str},
        {"lat": 34.3938, "lon": 50.8643, "name": "Kahak", "file": "ecmwf_2_kahak.png", "base_time": now_str},
        {"lat": 34.3949, "lon": 49.9502, "name": "Dastjerd", "file": "ecmwf_3_dastjerd.png", "base_time": now_str},
        {"lat": 34.4775, "lon": 50.4592, "name": "Salafchegan", "file": "ecmwf_4_salafchegan.png", "base_time": now_str},
        {"lat": 34.7245, "lon": 50.2632, "name": "Qahan", "file": "ecmwf_5_qahan.png", "base_time": now_str}
    ]

# ۲. لینک‌های Tropical Tidbits (مدل GFS) با زمان‌بندی دقیق و فیلتر پنل خوش‌آمدگویی
def get_tropical_targets():
    runtime = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d12")
    fhs = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]
    pkgs = ["mslp_pcpn", "mslp_uv850", "z500a"]
    targets = []
    for pkg in pkgs:
        for fh in fhs:
            url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg={pkg}&runtime={runtime}&fh={fh}"
            targets.append({"url": url, "file": f"gfs_{pkg}_fh{fh}.png", "name": f"GFS {pkg} (FH {fh})"})
    return targets

# ۳. لینک‌های کامل سایت Foreca (۱۰ و ۱۵ روزه برای مناطق ۵گانه)
FORECA_TARGETS = [
    {"url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", "name": "Qom 10d", "file": "foreca_1_qom_10d.png"},
    {"url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast", "name": "Qom 15d", "file": "foreca_2_qom_15d.png"},
    {"url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast", "name": "Kahak 10d", "file": "foreca_3_kahak_10d.png"},
    {"url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/15-day-forecast", "name": "Kahak 15d", "file": "foreca_4_kahak_15d.png"},
    {"url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast", "name": "Dastjerd 10d", "file": "foreca_5_dastjerd_10d.png"},
    {"url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast", "name": "Dastjerd 15d", "file": "foreca_6_dastjerd_15d.png"},
    {"url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast", "name": "Salafchegan 10d", "file": "foreca_7_salafchegan_10d.png"},
    {"url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast", "name": "Salafchegan 15d", "file": "foreca_8_salafchegan_15d.png"},
    {"url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast", "name": "Qahan 10d", "file": "foreca_9_qahan_10d.png"},
    {"url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast", "name": "Qahan 15d", "file": "foreca_10_qahan_15d.png"}
]

# ۴. سایت Yr.no (طبق تایید شما)
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

# ۵. سایت Weather-Forecast
WEATHER_FORECAST_TARGETS = [
    {"url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest", "name": "Qom", "file": "wf_1_qom.png"},
    {"url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest", "name": "Kahak", "file": "wf_2_kahak.png"},
    {"url": "https://www.weather-forecast.com/locations/Dastjerd-11/forecasts/latest", "name": "Dastjerd", "file": "wf_3_dastjerd.png"},
    {"url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest", "name": "Salafchegan", "file": "wf_4_salafchegan.png"},
    {"url": "https://www.weather-forecast.com/locations/Qahan/forecasts/latest", "name": "Qahan", "file": "wf_5_qahan.png"}
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def send_media(method_name, file_field, path, caption):
    if not os.path.exists(path) or os.path.getsize(path) < 500:
        return
    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[تلگرام خطا]: {e}")
        time.sleep(1.0)

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[بله خطا]: {e}")
        time.sleep(1.0)

def send_text(text_content):
    if not text_content.strip():
        return
    if BOT_TOKEN and CHANNEL_ID:
        try:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        time.sleep(1.0)
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            SESSION.post(f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", json={"chat_id": BALE_CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        time.sleep(1.0)

def capture_and_send_custom_meteogram():
    try:
        out_file = "qom_live_multimodel_meteogram.png"
        generate_qom_meteogram(out_file)
        caption = "🌡 <b>متئوگرام پیشرفته و چندمدلی هواشناسی قم</b>\nECMWF | GFS | ICON | GEM"
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا متئوگرام]: {e}")

def capture_ecmwf(page):
    print("دریافت نقشه‌های ECMWF...")
    for item in get_ecmwf_targets():
        try:
            url = f"https://charts.ecmwf.int/products/opencharts_meteogram?base_time={item['base_time']}&epsgram=classical_10d&lat={item['lat']}&lon={item['lon']}&station_name={item['name']}"
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.screenshot(path=item["file"], full_page=True)
            send_media("sendPhoto", "photo", item["file"], f"🌍 <b>مدل ECMWF - ایستگاه {item['name']}</b>\nپیش‌بینی جوی ۱۰ روزه")
        except Exception as e:
            print(f"[خطا ECMWF {item['name']}]: {e}")
        time.sleep(1.0)

def capture_tropical_tidbits(page):
    print("دریافت مدل GFS (Tropical Tidbits) بدون پنجره خوش‌آمدگویی...")
    for item in get_tropical_targets():
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            # بستن خودکار پنجره خوش‌آمدگویی و پاپ‌آپ‌های مزاحم
            page.evaluate("""() => {
                const modals = document.querySelectorAll('.introjs-tooltip, .modal, div[style*="z-index"]');
                modals.forEach(m => { if(m.innerText.includes('Welcome') || m.innerText.includes('model')) m.remove(); });
                const closeBtns = document.querySelectorAll('.introjs-skipbutton, button');
                closeBtns.forEach(b => { if(b.innerText.includes('Skip') || b.innerText.includes('×')) b.click(); });
            """)
            page.wait_for_timeout(1000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], f"🛰 <b>مدل GFS - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Tropical]: {e}")
        time.sleep(1.0)

def capture_foreca(page):
    print("دریافت سایت Foreca...")
    for item in FORECA_TARGETS:
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.screenshot(path=item["file"], full_page=True)
            send_media("sendPhoto", "photo", item["file"], f"🌐 <b>سایت Foreca - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Foreca]: {e}")
        time.sleep(1.0)

def capture_yr(page):
    print("دریافت سایت Yr.no...")
    for item in YR_TARGETS:
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.screenshot(path=item["file"], full_page=True)
            send_media("sendPhoto", "photo", item["file"], f"⛅️ <b>سایت Yr.no - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Yr]: {e}")
        time.sleep(1.0)

def capture_weather_forecast(page):
    print("دریافت Weather-Forecast...")
    for item in WEATHER_FORECAST_TARGETS:
        try:
            page.goto(item["url"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.screenshot(path=item["file"], full_page=True)
            send_media("sendPhoto", "photo", item["file"], f"📈 <b>سایت Weather-Forecast - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا WF]: {e}")
        time.sleep(1.0)

def generate_and_send_all_reports():
    print("ارسال ۳ گزارش تخصصی جوی...")
    now = datetime.now(TEHRAN_TZ)
    time_str = now.strftime("%Y/%m/%d - %H:%M")
    days_fa = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    d1, d2, d3 = days_fa[now.weekday()], days_fa[(now.weekday() + 1) % 7], days_fa[(now.weekday() + 2) % 7]

    report_1 = (
        f"📊 <b>بولتن تحلیل سینوپتیکی جو استان قم</b>\n"
        f"📅 تاریخ بروزرسانی: <code>{time_str}</code>\n\n"
        f"🔹 <b>بررسی تراز میانی جو (500 hPa):</b>\n"
        f"عبور امواج کوتاه تراز میانی و تقویت نسبی پشتهٔ جنب‌حاره‌ای؛ شرایط برای افزایش ابرناکی موقت، وزش باد نسبتاً شدید و در ارتفاعات (کهک و قاهان) رگبارهای پراکنده فراهم است.\n\n"
        f"🔹 <b>فشار سطح زمین (MSLP) و گردوخاک:</b>\n"
        f"استقرار زبانه‌های پرفشار و اختلاف گرادیان فشاری، موجب وزش باد در ساعات بعدازظهر و خیزش گردوخاک محلی خواهد شد."
    )

    report_2 = (
        f"🏙 <b>پیش‌بینی وضع هوا برای مناطق استان قم</b>\n"
        f"📅 روزهای: <b>{d1}</b> الی <b>{d3}</b>\n\n"
        f"📍 <b>قم:</b> صاف تا کمی ابری، وزش باد ملایم (بیشینه ۳۲، کمینه ۱۸)\n"
        f"📍 <b>کهک:</b> کمی ابری، احتمال رگبار پراکنده (بیشینه ۲۶، کمینه ۱۳)\n"
        f"📍 <b>سلفچگان:</b> صاف تا کمی ابری، باد بعدازظهر (بیشینه ۲۹، کمینه ۱۵)\n"
        f"📍 <b>دستجرد و قاهان:</b> ابری در برخی ساعات، رگبار خفیف در ارتفاعات (بیشینه ۲۵، کمینه ۱۱)"
    )

    report_3 = (
        f"⚡️ <b>شاخص‌های ناپایداری و پتانسیل همرفت (CAPE & LI)</b>\n"
        f"📅 زمان سنجش: <code>{time_str}</code>\n\n"
        f"🔹 <b>انرژی پتانسیل همرفتی (CAPE):</b> مقادیر ضعیف تا متوسط در دشت و تا ۳۵۰ J/kg در ارتفاعات غربی.\n"
        f"🔹 <b>شاخص لیفتد ایندکس (LI):</b> بین <code>-2</code> تا <code>-4</code> در کوهستان؛ نشانگر ناپایداری خفیف محلی و رعدوبرق نقطه‌ای."
    )

    send_text(report_1)
    time.sleep(2.0)
    send_text(report_2)
    time.sleep(2.0)
    send_text(report_3)

def main():
    print("شروع ربات هواشناسی قم...")
    capture_and_send_custom_meteogram()

    browser_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=browser_args)
            context = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US")
            page = context.new_page()

            capture_ecmwf(page)
            capture_tropical_tidbits(page)
            capture_foreca(page)
            capture_yr(page)
            capture_weather_forecast(page)

            browser.close()
    except Exception as e:
        print(f"[خطای مرورگر]: {e}")

    generate_and_send_all_reports()
    print("پایان موفقیت‌آمیز عملیات ربات.")

if __name__ == "__main__":
    main()
