import os
import sys
import time
import json
import re
from datetime import datetime
import pytz
import requests
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------
# فراخوانی ماژول متئوگرام چندمدله قم (ECMWF, GFS, ICON, GEM)
# -------------------------------------------------------------
from meteogram_qom import generate_qom_meteogram

# -------------------------------------------------------------
# تنظیمات تلگرام و بله از Secrets
# -------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "").strip()
BALE_CHAT_ID = os.environ.get("BALE_CHAT_ID", "").strip()

STATE_FILE = "weather_state.json"
REQ_TIMEOUT = 35

# -------------------------------------------------------------
# 1. تنظیمات ECMWF ENS Meteogram (پیش‌بینی ۱۰ روزه)
# -------------------------------------------------------------
ECMWF_TARGETS = [
    {
        "name": "قم",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.64&lon=50.87&station_name=Qom",
        "file": "ecmwf_ens_qom.png",
        "caption": "📊 متئوگرام ۱۰ روزه انسامبل ECMWF (پیش‌بینی جامع دما، بارش، ابرناکی و باد)\n📍 ایستگاه: قم\n🌐 منبع: مرکز پیش‌بینی میان‌مدت اروپا (ECMWF)"
    },
    {
        "name": "کهک",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.3938&lon=50.8643&station_name=Kahak",
        "file": "ecmwf_ens_kahak.png",
        "caption": "📊 متئوگرام ۱۰ روزه انسامبل ECMWF (پیش‌بینی جامع دما، بارش، ابرناکی و باد)\n📍 ایستگاه: کهک\n🌐 منبع: مرکز پیش‌بینی میان‌مدت اروپا (ECMWF)"
    },
    {
        "name": "سلفچگان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.4775&lon=50.4592&station_name=Salafchegan",
        "file": "ecmwf_ens_salafchegan.png",
        "caption": "📊 متئوگرام ۱۰ روزه انسامبل ECMWF (پیش‌بینی جامع دما، بارش، ابرناکی و باد)\n📍 ایستگاه: سلفچگان\n🌐 منبع: مرکز پیش‌بینی میان‌مدت اروپا (ECMWF)"
    },
    {
        "name": "دستجرد",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "file": "ecmwf_ens_dastjerd.png",
        "caption": "📊 متئوگرام ۱۰ روزه انسامبل ECMWF (پیش‌بینی جامع دما، بارش، ابرناکی و باد)\n📍 ایستگاه: دستجرد\n🌐 منبع: مرکز پیش‌بینی میان‌مدت اروپا (ECMWF)"
    },
    {
        "name": "کهندان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.7245&lon=50.2632&station_name=Koohandan",
        "file": "ecmwf_ens_koohandan.png",
        "caption": "📊 متئوگرام ۱۰ روزه انسامبل ECMWF (پیش‌بینی جامع دما، بارش، ابرناکی و باد)\n📍 ایستگاه: کهندان (قاهان)\n🌐 منبع: مرکز پیش‌بینی میان‌مدت اروپا (ECMWF)"
    }
]

# -------------------------------------------------------------
# 2. تنظیمات نقشه‌های همدیدی Tropical Tidbits (مدل GFS - تا ۷۲ ساعت)
# -------------------------------------------------------------
TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

# -------------------------------------------------------------
# 3. تنظیمات Weather-Forecast (نقشه‌های تحلیلی آب‌وهوا)
# -------------------------------------------------------------
WF_TARGETS = [
    {
        "name": "نمودار هفتگی وضع هوا و بارندگی قم",
        "url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest",
        "file": "wf_qom.png",
        "selector": ".forecast-cont, .location-summary, .wf-responsive-table",
        "caption": "📈 جدول و نمودار پیش‌بینی وضع هوای قم (منبع: Weather-Forecast)"
    }
]

# -------------------------------------------------------------
# 4. تنظیمات Foreca (پیش‌بینی دمای تفکیکی قم)
# -------------------------------------------------------------
FORECA_TARGETS = [
    {
        "name": "پیش‌بینی دمایی و روند آب‌وهوای قم (Foreca)",
        "url": "https://www.foreca.com/100125000/Qom-Iran/10-day-forecast",
        "file": "foreca_qom.png",
        "selector": ".forecast-container, .charts-container, .meteogram",
        "caption": "🌡 پیش‌بینی ۱۰ روزه دما و روند جوی قم (منبع: Foreca)"
    }
]

# -------------------------------------------------------------
# 5. تنظیمات Yr.no (پیش‌بینی نروژ برای قم)
# -------------------------------------------------------------
YR_TARGETS = [
    {
        "name": "نمودار متئوگرام نروژ (Yr.no)",
        "url": "https://www.yr.no/en/forecast/graph/2-125000/Iran/Qom/Qom",
        "file": "yr_qom.png",
        "selector": ".meteogram__svg, .meteogram, .chart-wrapper",
        "caption": "🇳🇴 نمودار متئوگرام اختصاصی سازمان هواشناسی نروژ (Yr.no) برای قم"
    }
]

# -------------------------------------------------------------
# 6. بولتن‌های پیش‌بینی اداره کل هواشناسی قم (irimo.ir)
# -------------------------------------------------------------
QOM_IRIMO_URLS = [
    {
        "title": "بولتن پیش‌بینی و تحلیل وضع هوای استان قم",
        "url": "https://www.qommet.ir/",
        "file": "irimo_qom_bulletin.png",
        "caption": "📋 بولتن تحلیل و پیش‌بینی وضعیت جوی اداره کل هواشناسی استان قم"
    }
]

# -------------------------------------------------------------
# مدیریت وضعیت آخرین پیام‌ها (state persistence)
# -------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[هشدار]: عدم خواندن فایل state: {e}")
    return {"last_run": "", "sent_hashes": []}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[هشدار]: عدم ذخیره فایل state: {e}")

# -------------------------------------------------------------
# دریافت جدیدترین ران فعال تروپیکال تیدبیتس (GFS)
# -------------------------------------------------------------
def get_latest_gfs_run():
    now_utc = datetime.now(pytz.utc)
    day_str = now_utc.strftime("%Y%m%d")
    hour = now_utc.hour
    if hour >= 18:
        run = "12"
    elif hour >= 12:
        run = "06"
    elif hour >= 6:
        run = "00"
    else:
        # روز گذشته ساعت ۱۸
        yesterday = now_utc.date() - pytz.datetime.timedelta(days=1)
        day_str = yesterday.strftime("%Y%m%d")
        run = "18"
    return day_str, run

# -------------------------------------------------------------
# توابع ارسال پیام به تلگرام و بله
# -------------------------------------------------------------
def send_telegram_media(method, media_type, file_path, caption=""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[رد شد]: متغیرهای TELEGRAM تنظیم نشده‌اند.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        with open(file_path, "rb") as f:
            files = {media_type: f}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            resp = requests.post(url, data=data, files=files, timeout=REQ_TIMEOUT)
            if not resp.ok:
                print(f"[خطای ارسال تلگرام]: {resp.status_code} - {resp.text}")
            else:
                print(f"[تلگرام]: {file_path} با موفقیت ارسال شد.")
    except Exception as e:
        print(f"[خطای اتصال تلگرام]: {e}")

def send_bale_media(method, media_type, file_path, caption=""):
    if not BALE_BOT_TOKEN or not BALE_CHAT_ID:
        print("[رد شد]: متغیرهای BALE تنظیم نشده‌اند.")
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method}"
    try:
        with open(file_path, "rb") as f:
            files = {media_type: f}
            data = {"chat_id": BALE_CHAT_ID, "caption": caption}
            resp = requests.post(url, data=data, files=files, timeout=REQ_TIMEOUT)
            if not resp.ok:
                print(f"[خطای ارسال بله]: {resp.status_code} - {resp.text}")
            else:
                print(f"[بله]: {file_path} با موفقیت ارسال شد.")
    except Exception as e:
        print(f"[خطای اتصال بله]: {e}")

def send_media(method, media_type, file_path, caption=""):
    send_telegram_media(method, media_type, file_path, caption)
    send_bale_media(method, media_type, file_path, caption)
    time.sleep(2.0)

def send_telegram_text(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=REQ_TIMEOUT)
        if not resp.ok:
            print(f"[خطای متن تلگرام]: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[خطای اتصال متن تلگرام]: {e}")

def send_bale_text(text):
    if not BALE_BOT_TOKEN or not BALE_CHAT_ID:
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": BALE_CHAT_ID, "text": text}, timeout=REQ_TIMEOUT)
        if not resp.ok:
            print(f"[خطای متن بله]: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[خطای اتصال متن بله]: {e}")

def send_text(text):
    send_telegram_text(text)
    send_bale_text(text)
    time.sleep(1.5)

# -------------------------------------------------------------
# ۰. متئوگرام چندمدله پیش‌بینی ۱۰ روزه ایستگاه‌های قم
# -------------------------------------------------------------
def capture_and_send_custom_meteogram():
    print("\n=== ۰. تولید و ارسال متئوگرام چندمدله ایستگاه‌های قم ===")
    targets = [
        {"fa": "قم", "en": "Qom", "file": "meteogram_qom.png"},
        {"fa": "کهک", "en": "Kahak", "file": "meteogram_kahak.png"},
        {"fa": "دستجرد", "en": "Dastjerd", "file": "meteogram_dastjerd.png"},
        {"fa": "سلفچگان", "en": "Salafchegan", "file": "meteogram_salafchegan.png"},
        {"fa": "قهان", "en": "Qahan", "file": "meteogram_qahan.png"},
    ]
    try:
        print("تولید فایل‌های متئوگرام با generate_qom_meteogram...")
        generate_qom_meteogram()
        for target in targets:
            fpath = target["file"]
            if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
                caption = (
                    f"📊 متئوگرام چندمدله ۱۰ روزه ایستگاه {target['fa']} ({target['en']})\n"
                    f"📍 مقایسه ۴ مدل معتبر: ECMWF, GFS, ICON, GEM\n"
                    f"⏱ تفکیک ساعتی، دمای هوا، بارش تجمعی و باد ۱۰ متری\n"
                    f"📎 منبع داده: Open-Meteo | علی جزبی"
                )
                send_media("sendPhoto", "photo", fpath, caption)
            else:
                print(f"[هشدار]: فایل متئوگرام یافت نشد: {fpath}")
    except Exception as e:
        print(f"[خطا در متئوگرام چندمدله]: {e}")

# -------------------------------------------------------------
# اسکرین‌شات از متئوگرام‌های ECMWF
# -------------------------------------------------------------
def capture_ecmwf(page):
    print("\n=== ۱. اسکرین‌شات از متئوگرام‌های ECMWF ENS ===")
    for item in ECMWF_TARGETS:
        try:
            print(f"بارگذاری: {item['name']} -> {item['url']}")
            page.goto(item["url"], timeout=70000, wait_until="load")
            page.wait_for_timeout(12000)

            chart_img = page.query_selector("img[src*='render-worker'], img[src*='opencharts'], .chart-container img")
            if chart_img:
                chart_img.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"], full_page=False)

            if os.path.exists(item["file"]) and os.path.getsize(item["file"]) > 5000:
                send_media("sendPhoto", "photo", item["file"], item["caption"])
            else:
                print(f"[هشدار]: حجم فایل {item['file']} معتبر نیست.")
        except Exception as e:
            print(f"[خطا در ECMWF {item['name']}]: {e}")

# -------------------------------------------------------------
# اسکرین‌شات از نقشه‌های تروپیکال تیدبیتس (بارش و Z500a)
# -------------------------------------------------------------
def capture_tropical_tidbits(page):
    print("\n=== ۲. اسکرین‌شات از نقشه‌های GFS خاورمیانه (Tropical Tidbits) ===")
    date_str, run_hour = get_latest_gfs_run()
    run_param = f"{date_str}{run_hour}"

    # الف) بارش تجمیعی و فشار سطح دریا
    for fh in TROPICAL_HOURS:
        url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=mideast&pkg=mslp_pcpn&runtime={run_param}&fh={fh}"
        file_name = f"tropical_pcpn_fh{fh}.png"
        caption = (
            f"🌧 پیش‌بینی بارش تجمیعی و فشار سطح دریا (MSLP)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits"
        )
        try:
            page.goto(url, timeout=60000, wait_until="load")
            page.wait_for_timeout(4000)
            img_elem = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_elem:
                img_elem.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            if os.path.exists(file_name) and os.path.getsize(file_name) > 5000:
                send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"[خطا تروپیکال بارش ساعت {fh}]: {e}")

    # ب) آنومالی ارتفاع ژئوپتانسیلی تراز ۵۰۰ هکتوپاسکال (Z500a)
    for fh in [24, 48, 72]:
        url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=mideast&pkg=z500a&runtime={run_param}&fh={fh}"
        file_name = f"tropical_z500a_fh{fh}.png"
        caption = (
            f"🌀 تراز ۵۰۰ هکتوپاسکال و تاوایی (Z500 & Vorticity)\n"
            f"🌐 مدل: GFS منطقه خاورمیانه\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits"
        )
        try:
            page.goto(url, timeout=60000, wait_until="load")
            page.wait_for_timeout(4000)
            img_elem = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_elem:
                img_elem.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            if os.path.exists(file_name) and os.path.getsize(file_name) > 5000:
                send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"[خطا تروپیکال Z500 ساعت {fh}]: {e}")

# -------------------------------------------------------------
# اسکرین‌شات از Weather-Forecast
# -------------------------------------------------------------
def capture_weather_forecast(page):
    print("\n=== ۳. دریافت اطلاعات از Weather-Forecast ===")
    for item in WF_TARGETS:
        try:
            page.goto(item["url"], timeout=60000, wait_until="load")
            page.wait_for_timeout(6000)
            target_elem = page.query_selector(item["selector"])
            if target_elem:
                target_elem.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            if os.path.exists(item["file"]) and os.path.getsize(item["file"]) > 5000:
                send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"[خطا در Weather-Forecast]: {e}")

# -------------------------------------------------------------
# اسکرین‌شات از Foreca
# -------------------------------------------------------------
def capture_foreca(page):
    print("\n=== ۴. دریافت اطلاعات از Foreca ===")
    for item in FORECA_TARGETS:
        try:
            page.goto(item["url"], timeout=60000, wait_until="load")
            page.wait_for_timeout(6000)
            target_elem = page.query_selector(item["selector"])
            if target_elem:
                target_elem.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            if os.path.exists(item["file"]) and os.path.getsize(item["file"]) > 5000:
                send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"[خطا در Foreca]: {e}")

# -------------------------------------------------------------
# اسکرین‌شات از Yr.no
# -------------------------------------------------------------
def capture_yr(page):
    print("\n=== ۵. دریافت متئوگرام نروژ (Yr.no) ===")
    for item in YR_TARGETS:
        try:
            page.goto(item["url"], timeout=65000, wait_until="load")
            page.wait_for_timeout(7000)
            target_elem = page.query_selector(item["selector"])
            if target_elem:
                target_elem.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            if os.path.exists(item["file"]) and os.path.getsize(item["file"]) > 5000:
                send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"[خطا در Yr.no]: {e}")

# -------------------------------------------------------------
# بررسی و دریافت بولتن اداره کل هواشناسی قم
# -------------------------------------------------------------
def capture_qom_irimo(page):
    print("\n=== ۶. دریافت بولتن پیش‌بینی هواشناسی استان قم ===")
    for item in QOM_IRIMO_URLS:
        try:
            page.goto(item["url"], timeout=50000, wait_until="load")
            page.wait_for_timeout(5000)
            page.screenshot(path=item["file"])
            if os.path.exists(item["file"]) and os.path.getsize(item["file"]) > 5000:
                send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"[خطا در سایت هواشناسی قم]: {e}")

# -------------------------------------------------------------
# فیلتر پیام‌های مهم کانال هواشناسی کشور (iran_met)
# -------------------------------------------------------------
def fetch_iran_met_updates():
    print("\n=== ۷. پایش هشدارهای هواشناسی ایران ===")
    url = "https://t.me/s/iran_met"
    keywords = ["قم", "مرکزی", "هشدار", "سطح نارنجی", "سطح زرد", "سیل", "بارش شدید", "طوفان", "گرد و خاک"]
    try:
        resp = requests.get(url, timeout=REQ_TIMEOUT)
        if not resp.ok:
            return
        html = resp.text
        messages = re.findall(r'<div class="tgme_widget_message_text[^"]*">(.*?)</div>', html, re.DOTALL)
        
        state = load_state()
        sent_hashes = set(state.get("sent_hashes", []))

        for msg in messages[-5:]:
            clean_text = re.sub(r'<[^>]+>', '', msg).strip()
            if any(k in clean_text for k in keywords):
                msg_hash = str(hash(clean_text[:50]))
                if msg_hash not in sent_hashes:
                    forward_caption = f"⚠️ <b>پیام مهم هواشناسی کشور / استان قم:</b>\n\n{clean_text}\n\n📢 منبع: @iran_met"
                    send_text(forward_caption)
                    sent_hashes.add(msg_hash)

        state["sent_hashes"] = list(sent_hashes)[-50:]
        save_state(state)
    except Exception as e:
        print(f"[خطا در دریافت پیام‌های iran_met]: {e}")

# -------------------------------------------------------------
# اجرای اصلی کلیه بخش‌های ربات
# -------------------------------------------------------------
def main():
    print("=" * 60)
    print("شروع اجرای ربات جامع هواشناسی قم (Ali Jazebi)")
    print(f"زمان اجرا (UTC): {datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ۰. متئوگرام چندمدله قم (بدون نیاز به مرورگر، مبتنی بر Open-Meteo)
    capture_and_send_custom_meteogram()

    # اجرای سایر بخش‌ها که نیاز به موتور مرورگر کرومیوم دارند
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ۱. متئوگرام‌های ECMWF
        capture_ecmwf(page)

        # ۲. نقشه‌های تروپیکال تیدبیتس
        capture_tropical_tidbits(page)

        # ۳. وبسایت Weather-Forecast
        capture_weather_forecast(page)

        # ۴. وبسایت Foreca
        capture_foreca(page)

        # ۵. متئوگرام Yr.no
        capture_yr(page)

        # ۶. بولتن اداره کل هواشناسی قم
        capture_qom_irimo(page)

        browser.close()

    # ۷. پایش متن‌های تحلیلی و هشدارهای مهم
    fetch_iran_met_updates()

    print("\n✅ اجرای کلیه مراحل با موفقیت به پایان رسید.")

if __name__ == "__main__":
    main()
