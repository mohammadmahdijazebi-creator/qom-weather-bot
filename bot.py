import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from meteogram_qom import generate_qom_meteogram

# -------------------------------------------------------------
# تنظیمات محیطی
# -------------------------------------------------------------
BOT_TOKEN = (
    os.environ.get("BOT_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
)
CHANNEL_ID = (
    os.environ.get("CHANNEL_ID")
    or os.environ.get("TELEGRAM_CHAT_ID")
)
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = (
    os.environ.get("BALE_CHANNEL_ID")
    or os.environ.get("BALE_CHAT_ID")
)

STATE_FILE = Path("weather_state.json")
TEXT_FILE = Path("forecast_text.txt")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
REQ_TIMEOUT = 50

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
})

# -------------------------------------------------------------
# اهداف متئوگرام ECMWF
# -------------------------------------------------------------
ECMWF_BASE = (
    "https://charts.ecmwf.int/products/opencharts_meteogram"
    "?epsgram=classical_10d"
)
ECMWF_TARGETS = [
    {
        "name": "قم",
        "web_url": f"{ECMWF_BASE}&lat=34.64&lon=50.86&station_name=Qom",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قم",
        "file": "ecmwf_1_qom.png",
    },
    {
        "name": "کهک",
        "web_url": f"{ECMWF_BASE}&lat=34.3938&lon=50.8643&station_name=Kahak",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: کهک",
        "file": "ecmwf_2_kahak.png",
    },
    {
        "name": "دستجرد",
        "web_url": f"{ECMWF_BASE}&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: دستجرد",
        "file": "ecmwf_3_dastjerd.png",
    },
    {
        "name": "سلفچگان",
        "web_url": f"{ECMWF_BASE}&lat=34.4775&lon=50.4592&station_name=Salafchegan",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: سلفچگان",
        "file": "ecmwf_4_salafchegan.png",
    },
    {
        "name": "قاهان",
        "web_url": f"{ECMWF_BASE}&lat=34.7245&lon=50.2632&station_name=Qahan",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قاهان",
        "file": "ecmwf_5_qahan.png",
    },
]

TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

# -------------------------------------------------------------
# اهداف Yr.no
# -------------------------------------------------------------
YR_BASE = "https://www.yr.no/en/forecast"
YR_TARGETS = [
    {
        "name": "جدول قم",
        "url": f"{YR_BASE}/daily-table/2-119208/Iran/Qom%20Province/Qom",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - قم",
        "file": "yr_1_table_qom.png",
    },
    {
        "name": "نمودار قم",
        "url": f"{YR_BASE}/graph/2-119208/Iran/Qom%20Province/Qom",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم",
        "file": "yr_2_graph_qom.png",
    },
    {
        "name": "جدول کهک",
        "url": f"{YR_BASE}/daily-table/2-122026/Iran/Qom%20Province/Kahak",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - کهک",
        "file": "yr_3_table_kahak.png",
    },
    {
        "name": "نمودار کهک",
        "url": f"{YR_BASE}/graph/2-122026/Iran/Qom%20Province/Kahak",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک",
        "file": "yr_4_graph_kahak.png",
    },
    {
        "name": "جدول سلفچگان",
        "url": f"{YR_BASE}/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - سلفچگان",
        "file": "yr_5_table_salaf.png",
    },
    {
        "name": "نمودار سلفچگان",
        "url": f"{YR_BASE}/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان",
        "file": "yr_6_graph_salaf.png",
    },
    {
        "name": "جدول دستجرد",
        "url": f"{YR_BASE}/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - دستجرد",
        "file": "yr_7_table_dastjerd.png",
    },
    {
        "name": "نمودار دستجرد",
        "url": f"{YR_BASE}/graph/2-137151/Iran/Markazi%20Province/Dastjerd",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد",
        "file": "yr_8_graph_dastjerd.png",
    },
    {
        "name": "جدول قاهان",
        "url": f"{YR_BASE}/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - قاهان",
        "file": "yr_9_table_qahan.png",
    },
    {
        "name": "نمودار قاهان",
        "url": f"{YR_BASE}/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان",
        "file": "yr_10_graph_qahan.png",
    },
]

# -------------------------------------------------------------
# اهداف Foreca
# -------------------------------------------------------------
FC_BASE = "https://www.foreca.com"
FORECA_TARGETS = [
    {
        "name": "فورکا ۱۰ روزه قم",
        "url": f"{FC_BASE}/100119208/Qom-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم",
        "file": "foreca_1_qom_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه قم",
        "url": f"{FC_BASE}/100119208/Qom-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم",
        "file": "foreca_2_qom_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه کهک",
        "url": f"{FC_BASE}/100122026/Kahak-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک",
        "file": "foreca_3_kahak_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه کهک",
        "url": f"{FC_BASE}/100122026/Kahak-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - کهک",
        "file": "foreca_4_kahak_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه سلفچگان",
        "url": f"{FC_BASE}/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان",
        "file": "foreca_5_salaf_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه سلفچگان",
        "url": f"{FC_BASE}/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - سلفچگان",
        "file": "foreca_6_salaf_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه دستجرد",
        "url": f"{FC_BASE}/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - دستجرد",
        "file": "foreca_7_dast_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه دستجرد",
        "url": f"{FC_BASE}/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - دستجرد",
        "file": "foreca_8_dast_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه قاهان",
        "url": f"{FC_BASE}/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قاهان",
        "file": "foreca_9_qah_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه قاهان",
        "url": f"{FC_BASE}/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قاهان",
        "file": "foreca_10_qah_15d.png",
    },
]

# -------------------------------------------------------------
# اهداف Weather-Forecast
# -------------------------------------------------------------
WF_BASE = "https://www.weather-forecast.com/locations"
WEATHER_FORECAST_TARGETS = [
    {
        "name": "قم",
        "url": f"{WF_BASE}/Qom/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: قم",
        "file": "wf_1_qom.png",
    },
    {
        "name": "کهک",
        "url": f"{WF_BASE}/Kahak/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: کهک",
        "file": "wf_2_kahak.png",
    },
    {
        "name": "سلفچگان",
        "url": f"{WF_BASE}/Salafchegan/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: سلفچگان",
        "file": "wf_3_salafchegan.png",
    },
    {
        "name": "دستجرد",
        "url": f"{WF_BASE}/Dastjerd-11/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: دستجرد",
        "file": "wf_4_dastjerd.png",
    },
]

ADS_PATTERNS = [
    "تبلیغ", "تبلیغات", "رزرو", "تعرفه", "پکیج", "تخفیف", "خرید",
    "فروشگاه", "صرافی", "سیگنال", "بیت کوین", "تتر", "ثبت نام",
    "جوین شو", "عضو شوید", "کانال دوم", "لینک زیر", "فوری/", "پروکسی",
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
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(STATE_FILE)


def send_media(method, file_key, file_path, caption):
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
        print(f"[خطا] فایل {file_path} معتبر نیست.")
        return

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
                    print(f"[تلگرام خطا]: {r.status_code}")
        except Exception as e:
            print(f"[تلگرام Exception]: {e}")

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
                    print(f"[بله خطا]: {r.status_code}")
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


def capture_and_send_custom_meteogram():
    print("\n=== ۸. تولید و ارسال متئوگرام چندمدله قم (گام نهایی) ===")
    out_file = "qom_live_multimodel_meteogram.png"
    caption = (
        "📊 متئوگرام چندمدله ۱۰ روزه قم (ECMWF, GFS, ICON, GEM)\n"
        "📍 ایستگاه: قم (Iran, Qom - Ali Jazebi)\n"
        "🌡 روند دما و خطوط آنسامبل | 🌧 بارش تجمعی | 💨 جهت و شدت باد"
    )
    try:
        generate_qom_meteogram(out_file)
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا در متئوگرام چندمدله]: {e}")


def capture_ecmwf(page):
    print("\n=== ۱. دریافت متئوگرام‌های ۱۰ روزه ECMWF ===")
    for item in ECMWF_TARGETS:
        print(f"در حال باز کردن: {item['name']}...")
        try:
            page.goto(item["web_url"], timeout=70000, wait_until="load")
            page.wait_for_timeout(12000)

            selector = "img[src*='render-worker'], img[src*='opencharts'], .chart-container img"
            img_el = page.query_selector(selector)
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


def clean_tropical_welcome(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        page.evaluate("""() => {
            const btns = document.querySelectorAll('.modal .close, button.close, [data-dismiss="modal"]');
            btns.forEach(b => b.click());
            const modals = document.querySelectorAll('.modal, .modal-backdrop, .fade.in, [class*="backdrop"]');
            modals.forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.filter = "none";
            document.body.style.opacity = "1";
            document.documentElement.style.filter = "none";
            const mapEl = document.querySelector('#modelImage, .model-image, #analysis-image');
            if (mapEl) {
                mapEl.style.filter = "none";
                mapEl.style.opacity = "1";
            }
        }""")
    except Exception:
        pass


def capture_tropical_tidbits(page):
    print("\n=== ۲. عکسبرداری Tropical Tidbits ===")
    tt_base = "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me"

    print("\n--- دریافت فریم‌های بارش و فشار سطح دریا ---")
    for fh in TROPICAL_HOURS:
        url = f"{tt_base}&pkg=mslp_pcpn&fh={fh}"
        file_name = f"tropical_pcpn_fh{fh}.png"
        caption = (
            f"🌧 پیش‌بینی بارش تجمیعی و فشار سطح دریا (MSLP)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits"
        )
        print(f"فریم بارش: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(600)

            img_el = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_el:
                img_el.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم بارش fh={fh}: {e}")
        time.sleep(1.5)

    print("\n--- دریافت فریم‌های تراز ۵۰۰ هکتوپاسکال ---")
    for fh in TROPICAL_HOURS:
        url = f"{tt_base}&pkg=z500a&fh={fh}"
        file_name = f"tropical_z500a_fh{fh}.png"
        caption = (
            f"🌀 تاوایی و ارتفاع ژئوپتانسیل تراز ۵۰۰ هکتوپاسکال\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits"
        )
        print(f"فریم ۵۰۰ هکتوپاسکال: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(600)

            img_el = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_el:
                img_el.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم ۵۰۰ fh={fh}: {e}")
        time.sleep(1.5)


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


def capture_weather_forecast(page):
    print("\n=== ۵. دریافت پیش‌بینی‌های افقی Weather-Forecast ===")
    page.set_viewport_size({"width": 1920, "height": 1080})

    for item in WEATHER_FORECAST_TARGETS:
        print(f"عکسبرداری جدول افقی: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            page.evaluate("""() => {
                const ads = document.querySelectorAll('.fc-dialog-container, #onetrust-banner-sdk, .banner-close, .advert, .advertisement, [id*="google_ads"]');
                ads.forEach(e => e.remove());
                const tableCont = document.querySelector('.forecast-table, .forecast-cont');
                if (tableCont) {
                    tableCont.scrollIntoView({ behavior: 'instant', block: 'center' });
                }
            }""")
            page.wait_for_timeout(1500)

            selector = ".forecast-table, .forecast-cont, .location-summary-forecast"
            table_el = page.query_selector(selector)
            if table_el:
                table_el.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در Weather-Forecast {item['name']}: {e}")
        time.sleep(1.5)

    page.set_viewport_size({"width": 1366, "height": 900})


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
        weather_terms = [
            "بارش", "باران", "برف", "دما", "باد", "هواشناسی",
            "سیل", "رگبار", "توفان", "ابری", "سامانه", "هشدار",
        ]
        if not any(term in text for term in weather_terms):
            return True
    return False


def clean_text_advertisements(text):
    if not text:
        return "
