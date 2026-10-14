import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------
# ۱. متغیرهای محیطی و تنظیمات
# -------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID") or os.environ.get("TELEGRAM_CHAT_ID")

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID") or os.environ.get("BALE_CHAT_ID")

STATE_FILE = Path("weather_state.json")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
REQ_TIMEOUT = 50

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
})

# -------------------------------------------------------------
# ۲. لیست متئوگرام‌های ۱۰ روزه ECMWF (فریز شده)
# -------------------------------------------------------------
ECMWF_TARGETS = [
    {
        "name": "متئوگرام ۱۰ روزه قم",
        "web_url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قم",
        "file": "ecmwf_1_qom.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه کهک",
        "web_url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3938&lon=50.8643&station_name=Kahak",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: کهک",
        "file": "ecmwf_2_kahak.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه دستجرد",
        "web_url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: دستجرد",
        "file": "ecmwf_3_dastjerd.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه سلفچگان",
        "web_url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.4775&lon=50.4592&station_name=Salafcheg%C4%81n",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: سلفچگان",
        "file": "ecmwf_4_salafchegan.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه قاهان",
        "web_url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.7245&lon=50.2632&station_name=Q%C4%81h%C4%81n",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قاهان",
        "file": "ecmwf_5_qahan.png",
    },
]

# -------------------------------------------------------------
# ۳. ساعت‌های فریم Tropical Tidbits
# -------------------------------------------------------------
TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

# -------------------------------------------------------------
# ۴. جداول و نمودارهای Yr.no (فریز شده)
# -------------------------------------------------------------
YR_TARGETS = [
    {"name": "جدول روزانه قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - قم", "file": "yr_1_table_qom.png"},
    {"name": "نمودار ساعتی قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم", "file": "yr_2_graph_qom.png"},
    {"name": "جدول روزانه کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom%20Province/Kahak", "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - کهک", "file": "yr_3_table_kahak.png"},
    {"name": "نمودار ساعتی کهک", "url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom%20Province/Kahak", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک", "file": "yr_4_graph_kahak.png"},
    {"name": "جدول روزانه سلفچگان", "url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - سلفچگان", "file": "yr_5_table_salaf.png"},
    {"name": "نمودار ساعتی سلفچگان", "url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان", "file": "yr_6_graph_salaf.png"},
    {"name": "جدول روزانه دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - دستجرد", "file": "yr_7_table_dastjerd.png"},
    {"name": "نمودار ساعتی دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد", "file": "yr_8_graph_dastjerd.png"},
    {"name": "جدول روزانه قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - قاهان", "file": "yr_9_table_qahan.png"},
    {"name": "نمودار ساعتی قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان", "file": "yr_10_graph_qahan.png"},
]

# -------------------------------------------------------------
# ۵. پیش‌بینی‌های فورکا (Foreca) (فریز شده)
# -------------------------------------------------------------
FORECA_TARGETS = [
    {"name": "فورکا ۱۰ روزه قم", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم", "file": "foreca_1_qom_10d.png"},
    {"name": "فورکا ۱۵ روزه قم", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم", "file": "foreca_2_qom_15d.png"},
    {"name": "فورکا ۱۰ روزه کهک", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک", "file": "foreca_3_kahak_10d.png"},
    {"name": "فورکا ۱۵ روزه کهک", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - کهک", "file": "foreca_4_kahak_15d.png"},
    {"name": "فورکا ۱۰ روزه سلفچگان", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان", "file": "foreca_5_salaf_10d.png"},
    {"name": "فورکا ۱۵ روزه سلفچگان", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - سلفچگان", "file": "foreca_6_salaf_15d.png"},
    {"name": "فورکا ۱۰ روزه دستجرد", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - دستجرد", "file": "foreca_7_dast_10d.png"},
    {"name": "فورکا ۱۵ روزه دستجرد", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - دستجرد", "file": "foreca_8_dast_15d.png"},
    {"name": "فورکا ۱۰ روزه قاهان", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قاهان", "file": "foreca_9_qah_10d.png"},
    {"name": "فورکا ۱۵ روزه قاهان", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قاهان", "file": "foreca_10_qah_15d.png"},
]

# -------------------------------------------------------------
# ۶. لینک‌های درخواستی Weather-Forecast (با ترتیب دقیق)
# -------------------------------------------------------------
WEATHER_FORECAST_TARGETS = [
    {
        "name": "پیش‌بینی آب‌وهوا قم",
        "url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest",
        "caption": "🌐 پیش‌بینی دقیق وضع هوا (Weather-Forecast)\n📍 ایستگاه: قم",
        "file": "wf_1_qom.png",
    },
    {
        "name": "پیش‌بینی آب‌وهوا کهک",
        "url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest",
        "caption": "🌐 پیش‌بینی دقیق وضع هوا (Weather-Forecast)\n📍 ایستگاه: کهک",
        "file": "wf_2_kahak.png",
    },
    {
        "name": "پیش‌بینی آب‌وهوا سلفچگان",
        "url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest",
        "caption": "🌐 پیش‌بینی دقیق وضع هوا (Weather-Forecast)\n📍 ایستگاه: سلفچگان",
        "file": "wf_3_salafchegan.png",
    },
    {
        "name": "پیش‌بینی آب‌وهوا دستجرد",
        "url": "https://www.weather-forecast.com/locations/Dastjerd-11/forecasts/latest",
        "caption": "🌐 پیش‌بینی دقیق وضع هوا (Weather-Forecast)\n📍 ایستگاه: دستجرد",
        "file": "wf_4_dastjerd.png",
    },
]

ADS_PATTERNS = [
    "تبلیغ", "تبلیغات", "رزرو", "تعرفه", "پکیج", "تخفیف", "خرید", "فروشگاه", "قیمت روز",
    "صرافی", "سیگنال", "ارز دیجیتال", "بیت کوین", "تتر", "کسب درآمد", "ثبت نام",
    "جوین شو", "عضو شوید", "کانال دوم", "لینک زیر", "فوری /", "فوری/", "پروکسی",
]


def load_state():
    if not STATE_FILE.exists():
        return {"channels": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"channels": {}}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def send_media(method, file_key, file_path, caption):
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
        print(f"[خطا] فایل {file_path} معتبر نیست.")
        return

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={file_key: f},
                    timeout=REQ_TIMEOUT,
                )
                if r.status_code == 200:
                    print(f"[تلگرام OK]: {file_path}")
                else:
                    print(f"[تلگرام خطا]: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"[تلگرام Exception]: {e}")

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method}",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={file_key: f},
                    timeout=REQ_TIMEOUT,
                )
                if r.status_code == 200:
                    print(f"[بله OK]: {file_path}")
                else:
                    print(f"[بله خطا]: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"[بله Exception]: {e}")

    time.sleep(2.0)


def send_text(text):
    if BOT_TOKEN and CHANNEL_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": CHANNEL_ID, "text": text},
                timeout=REQ_TIMEOUT,
            )
        except Exception:
            pass

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            requests.post(
                f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage",
                data={"chat_id": BALE_CHANNEL_ID, "text": text},
                timeout=REQ_TIMEOUT,
            )
        except Exception:
            pass
    time.sleep(1.5)


# -------------------------------------------------------------
# ۱. متئوگرام‌های ۱۰ روزه ECMWF
# -------------------------------------------------------------
def capture_ecmwf(page):
    print("\n=== ۱. دریافت متئوگرام‌های ۱۰ روزه ECMWF ===")
    for item in ECMWF_TARGETS:
        print(f"در حال باز کردن: {item['name']}...")
        try:
            page.goto(item["web_url"], timeout=70000, wait_until="load")
            page.wait_for_timeout(12000)

            img_el = page.query_selector("img[src*='render-worker'], img[src*='opencharts'], .chart-container img")

            if img_el:
                img_src = img_el.get_attribute("src")
                if img_src and img_src.startswith("http"):
                    res = SESSION.get(img_src, timeout=30)
                    if res.status_code == 200 and len(res.content) > 3000:
                        Path(item["file"]).write_bytes(res.content)
                    else:
                        img_el.screenshot(path=item["file"])
                else:
                    img_el.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        time.sleep(2)


# -------------------------------------------------------------
# ۲. Tropical Tidbits (حذف پاپ‌آپ خوش‌آمدگویی و رفع قطعی تاری)
# -------------------------------------------------------------
def clean_tropical_welcome(page):
    """بستن طبیعی پاپ‌آپ و لغو هرگونه استایل blur یا backdrop"""
    try:
        # شبیه‌سازی کلید بستن مودال
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # اجرای اسکریپت حذف قطعی پاپ‌آپ، بلک‌دراپ و فیلتر تاری
        page.evaluate("""() => {
            // ۱. بستن کلیک روی هر دکمه close موجود در مودال
            document.querySelectorAll('.modal .close, button.close, [data-dismiss="modal"]').forEach(b => b.click());

            // ۲. حذف هر عنصر مودال و لایه‌های پس‌زمینه تیره
            document.querySelectorAll('.modal, .modal-backdrop, .fade.in, [class*="backdrop"]').forEach(el => el.remove());

            // ۳. بازگرداندن استایل شفاف و واضح صفحه
            document.body.classList.remove('modal-open');
            document.body.style.filter = "none";
            document.body.style.opacity = "1";
            document.documentElement.style.filter = "none";

            // ۴. شفاف‌سازی نقشه اصلی
            const mapEl = document.querySelector('#modelImage, .model-image, #analysis-image');
            if (mapEl) {
                mapEl.style.filter = "none";
                mapEl.style.opacity = "1";
            }
        }""")
    except Exception:
        pass


def capture_tropical_tidbits(page):
    print("\n=== ۲. عکسبرداری Tropical Tidbits (بدون پاپ‌آپ و کاملاً شارپ) ===")

    # الف) بارش و فشار سطح دریا
    print("\n--- دریافت فریم‌های بارش و فشار ---")
    for fh in TROPICAL_HOURS:
        url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn&fh={fh}"
        file_name = f"tropical_pcpn_fh{fh}.png"
        caption = (
            f"🌧 پیش‌بینی بارش تجمیعی و فشار سطح دریا (MSLP)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده\n"
            f"🔗 منبع: Tropical Tidbits"
        )
        print(f"در حال دریافت فریم بارش: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(800)

            img_element = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_element:
                img_element.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم بارش fh={fh}: {e}")
        time.sleep(1.5)

    # ب) تراز ۵۰۰ هکتوپاسکال
    print("\n--- دریافت فریم‌های تراز ۵۰۰ هکتوپاسکال ---")
    for fh in TROPICAL_HOURS:
        url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=z500a&fh={fh}"
        file_name = f"tropical_z500a_fh{fh}.png"
        caption = (
            f"🌀 تاوایی و ارتفاع ژئوپتانسیل تراز ۵۰۰ هکتوپاسکال\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده\n"
            f"🔗 منبع: Tropical Tidbits"
        )
        print(f"در حال دریافت فریم ۵۰۰ هکتوپاسکال: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(800)

            img_element = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_element:
                img_element.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم ۵۰۰ fh={fh}: {e}")
        time.sleep(1.5)


# -------------------------------------------------------------
# ۳. جداول و نمودارهای Yr.no (فریز شده)
# -------------------------------------------------------------
def capture_yr(page):
    print("\n=== ۳. جداول و نمودارهای Yr.no ===")
    for item in YR_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        time.sleep(1.5)


# -------------------------------------------------------------
# ۴. پیش‌بینی‌های فورکا (Foreca) (فریز شده)
# -------------------------------------------------------------
def capture_foreca(page):
    print("\n=== ۴. پیش‌بینی‌های فورکا (Foreca) ===")
    for item in FORECA_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        time.sleep(1.5)


# -------------------------------------------------------------
# ۵. سایت Weather-Forecast (طبق ترتیب دقیق خواسته شده)
# -------------------------------------------------------------
def capture_weather_forecast(page):
    print("\n=== ۵. دریافت پیش‌بینی‌های Weather-Forecast ===")
    for item in WEATHER_FORECAST_TARGETS:
        print(f"در حال عکسبرداری از: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            # بستن احتمالی بنرهای کوکی و مزاحم
            try:
                page.evaluate("""() => {
                    document.querySelectorAll('.fc-dialog-container, #onetrust-banner-sdk, .banner-close').forEach(e => e.remove());
                }""")
            except Exception:
                pass

            # گرفتن اسکرین‌شات از جدول اصلی پیش‌بینی یا کل کادر کاربردی
            forecast_block = page.query_selector(".forecast-cont, .location-page, main")
            if forecast_block:
                forecast_block.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در Weather-Forecast {item['name']}: {e}")
        time.sleep(1.5)


# -------------------------------------------------------------
# ۶. کانال تلگرامی @iran_met (جلوگیری ۱۰۰٪ قطعی از پیام تکراری)
# -------------------------------------------------------------
def is_advertisement(text, has_media):
    if not text and not has_media:
        return True
    text_lower = text.lower() if text else ""
    if "t.me/+" in text_lower or "joinchat" in text_lower:
        return True
    for kw in ADS_PATTERNS:
        if kw in text_lower:
            return True
    if not has_media:
        weather_terms = ["بارش", "باران", "برف", "دما", "باد", "هواشناسی", "سیل", "رگبار", "توفان", "ابری", "سامانه", "هشدار"]
        if not any(term in text for term in weather_terms):
            return True
    return False


def clean_text_advertisements(text):
    if not text:
        return ""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line_strip = line.strip()
        if any(term in line_strip for term in ["t.me/+", "t.me/joinchat", "جهت تبلیغات", "کانال دوم", "عضویت"]):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def check_iran_met(state):
    print("\n=== ۶. کانال تلگرامی @iran_met (بررسی پیام‌های کاملاً جدید) ===")
    username = "iran_met"
    chan_state = state.get("channels", {}).get(username, {"last_id": 0, "seen_ids": []})
    last_id = int(chan_state.get("last_id", 0))
    seen_ids = set(chan_state.get("seen_ids", []))

    try:
        url = f"https://t.me/s/{username}"
        r = SESSION.get(url, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        messages = soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))
    except Exception as e:
        print(f"خطا در بررسی تلگرام: {e}")
        return

    # استخراج تمام شناسه‌های موجود در صفحه فعلی
    all_current_ids = []
    parsed_msgs = []
    for msg in messages:
        dp = msg.get("data-post", "")
        if "/" not in dp:
            continue
        try:
            m_id = int(dp.rsplit("/", 1)[-1])
            all_current_ids.append(m_id)
            parsed_msgs.append((m_id, msg))
        except ValueError:
            continue

    if not all_current_ids:
        return

    # گارد تضمینی: اگر ربات تازه اجرا شده و وضعیت قبلی ذخیره نبوده، پیام‌های قدیمی را نریز!
    if last_id == 0 and not seen_ids:
        print("[اطلاعیه] اولین بار است که کانال بررسی می‌شود یا وضعیت خالی است. پیام‌های فعلی فقط مارک شدند و چیزی ارسال نمی‌شود.")
        state.setdefault("channels", {})[username] = {
            "last_id": max(all_current_ids),
            "seen_ids": sorted(all_current_ids)[-200:],
        }
        return

    new_posts = []
    for m_id, msg in parsed_msgs:
        # اگر قبلاً دیده شده یا کوچک‌تر/مساوی آخرین پیام دیده شده است، قطعا رد شود
        if m_id in seen_ids or m_id <= last_id:
            continue

        text_el = msg.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text("\n", strip=True) if text_el else ""

        photo_el = msg.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
        img_url = None
        if photo_el:
            style = photo_el.get("style", "")
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
            if m:
                img_url = m.group(1)

        video_el = msg.find("video")
        video_url = video_el.get("src") if video_el else None

        has_media = bool(img_url or video_url)

        if is_advertisement(text, has_media):
            seen_ids.add(m_id)
            last_id = max(last_id, m_id)
            continue

        cleaned_text = clean_text_advertisements(text)
        new_posts.append({
            "id": m_id,
            "text": cleaned_text,
            "img_url": img_url,
            "video_url": video_url,
        })

    for p in sorted(new_posts, key=lambda x: x["id"]):
        caption = f"{p['text']}\n\n📎 منبع: @{username}" if p["text"] else f"📎 منبع: @{username}"
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        if p["video_url"]:
            tmp_vid = f"tmp_{username}_{p['id']}.mp4"
            try:
                print(f"دانلود و ارسال فیلم پست {p['id']}...")
                res_v = SESSION.get(p["video_url"], timeout=REQ_TIMEOUT)
                Path(tmp_vid).write_bytes(res_v.content)
                send_media("sendVideo", "video", tmp_vid, caption)
                Path(tmp_vid).unlink(missing_ok=True)
            except Exception as e:
                print(f"خطا در ارسال فیلم: {e}")
        elif p["img_url"]:
            tmp_img = f"tmp_{username}_{p['id']}.jpg"
            try:
                res_i = SESSION.get(p["img_url"], timeout=REQ_TIMEOUT)
                Path(tmp_img).write_bytes(res_i.content)
                send_media("sendPhoto", "photo", tmp_img, caption)
                Path(tmp_img).unlink(missing_ok=True)
            except Exception as e:
                print(f"خطا در ارسال عکس: {e}")
        else:
            send_text(caption)

        last_id = max(last_id, p["id"])
        seen_ids.add(p["id"])

    # ذخیره در فایل وضعیت
    state.setdefault("channels", {})[username] = {
        "last_id": last_id,
        "seen_ids": sorted(list(seen_ids))[-200:],
    }


# -------------------------------------------------------------
# اجرای برنامه اصلی
# -------------------------------------------------------------
def main():
    print(f"=== آغاز اجرای ربات هواشناسی ({datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}) ===")
    state = load_state()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        # ۱. متئوگرام‌های ۱۰ روزه ECMWF (فریز شده)
        capture_ecmwf(page)

        # ۲. نقشه Tropical Tidbits (بدون پاپ‌آپ و کاملاً شارپ)
        capture_tropical_tidbits(page)

        # ۳. جداول و نمودارهای Yr.no (فریز شده)
        capture_yr(page)

        # ۴. پیش‌بینی‌های فورکا (فریز شده)
        capture_foreca(page)

        # ۵. پیش‌بینی‌های Weather-Forecast (ترتیب جدید: قم، کهک، سلفچگان، دستجرد)
        capture_weather_forecast(page)

        browser.close()

    # ۶. بررسی کانال تلگرامی iran_met (جلوگیری قطعی از تکرار)
    check_iran_met(state)

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز چرخه پایش ===")


if __name__ == "__main__":
    main()
