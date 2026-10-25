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
    print("\n=== ۰. تولید و ارسال متئوگرام چندمدله قم ===")
    out_file = "qom_live_multimodel_meteogram.png"
    caption = (
        "📊 متئوگرام چندمدله ۱۰ روزه قم (ECMWF, GFS, ICON, GEM)\n"
        "📍 ایستگاه: قم (Iran, Qom - Ali Jazebi)\n"
        "🌡 روند دما و خطوط آنسامبل | 🌧 بارش تجمعی | 💨 جهت و شدت باد"
    )
    try:
        # تولید پویا در هر اجرا (حذف شرط وجود فایل)
        print("تولید فایل متئوگرام چندمدله با generate_qom_meteogram (پویا در هر اجرا)...")
        try:
            from meteogram_qom import generate_qom_meteogram  # ماژول کامل متئوگرام چندمدله
        except ImportError:
            import importlib.util as _ilu
            import sys as _sys
            _cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meteogram_qom-(2).py")
            _spec = _ilu.spec_from_file_location("meteogram_qom_full", _cand)
            _mod = _ilu.module_from_spec(_spec)
            _sys.modules["meteogram_qom_full"] = _mod
            _spec.loader.exec_module(_mod)
            generate_qom_meteogram = _mod.generate_qom_meteogram
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

    print("\n--- دریافت فریم‌های باد تراز ۸۵۰ هکتوپاسکال (UV 850) ---")
    for fh in TROPICAL_HOURS:
        url = f"{tt_base}&pkg=mslp_uv850&fh={fh}"
        file_name = f"tropical_uv850_fh{fh}.png"
        caption = (
            f"💨 باد و رطوبت تراز ۸۵۰ هکتوپاسکال (UV-850)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits"
        )
        print(f"فریم UV-850: {fh} ساعت...")
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
            print(f"خطا در فریم UV850 fh={fh}: {e}")
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
        return ""
    lines = text.split("\n")
    cleaned = []
    bad_tokens = ["t.me/+", "t.me/joinchat", "جهت تبلیغات", "کانال دوم", "عضویت"]
    for line in lines:
        line_strip = line.strip()
        if any(term in line_strip for term in bad_tokens):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def check_iran_met(state):
    print("\n=== ۶. کانال تلگرامی @iran_met ===")
    username = "iran_met"
    chan_state = state.get("channels", {}).get(
        username, {"last_id": 0, "seen_ids": []}
    )
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

    if last_id == 0 and not seen_ids:
        print("[اطلاعیه] ثبت اولیه پیام‌های کانال؛ موردی ارسال نمی‌شود.")
        state.setdefault("channels", {})[username] = {
            "last_id": max(all_current_ids),
            "seen_ids": sorted(all_current_ids)[-200:],
        }
        return

    new_posts = []
    for m_id, msg in parsed_msgs:
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
        caption = (
            f"{p['text']}\n\n📎 منبع: @{username}"
            if p["text"]
            else f"📎 منبع: @{username}"
        )
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        if p["video_url"]:
            tmp_vid = f"tmp_{username}_{p['id']}.mp4"
            try:
                res_v = SESSION.get(p["video_url"], timeout=REQ_TIMEOUT)
                Path(tmp_vid).write_bytes(res_v.content)
                send_media("sendVideo", "video", tmp_vid, caption)
                Path(tmp_vid).unlink(missing_ok=True)
            except Exception:
                pass
        elif p["img_url"]:
            tmp_img = f"tmp_{username}_{p['id']}.jpg"
            try:
                res_i = SESSION.get(p["img_url"], timeout=REQ_TIMEOUT)
                Path(tmp_img).write_bytes(res_i.content)
                send_media("sendPhoto", "photo", tmp_img, caption)
                Path(tmp_img).unlink(missing_ok=True)
            except Exception:
                pass
        else:
            send_text(caption)

        last_id = max(last_id, p["id"])
        seen_ids.add(p["id"])

    state.setdefault("channels", {})[username] = {
        "last_id": last_id,
        "seen_ids": sorted(list(seen_ids))[-200:],
    }


def generate_and_send_synoptic_analysis():
    print("\n=== ۷. تدوین و ارسال تحلیل سینوپتیکی و پیش‌بینی شهری ===")
    if not TEXT_FILE.exists():
        print(f"[هشدار] فایل {TEXT_FILE} یافت نشد.")
        return

    content = TEXT_FILE.read_text(encoding="utf-8")
    now = datetime.now(TEHRAN_TZ)
    current_time_str = now.strftime("%Y/%m/%d - ساعت %H:%M")

    persian_days = {
        "Saturday": "شنبه",
        "Sunday": "یکشنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنجشنبه",
        "Friday": "جمعه",
    }
    d1 = persian_days.get(now.strftime("%A"), "امروز")
    d2 = persian_days.get((now + timedelta(days=1)).strftime("%A"), "فردا")
    d3 = persian_days.get((now + timedelta(days=2)).strftime("%A"), "پس‌فردا")

    synoptic_part = ""
    cities_part = ""
    if "[SYNOPTIC]" in content and "[CITIES]" in content:
        parts = content.split("[CITIES]")
        synoptic_part = parts[0].replace("[SYNOPTIC]", "").strip()
        cities_part = parts[1].strip()
    else:
        synoptic_part = content

    if synoptic_part:
        text1 = synoptic_part.format(time=current_time_str)
        send_text(text1)

    if cities_part:
        text2 = cities_part.format(
            time=current_time_str,
            day1=d1,
            day2=d2,
            day3=d3
        )
        send_text(text2)



# =============================================================
# بخش پویا: تحلیل سینوپتیکی-دینامیکی، پیش‌بینی ۳ روزه شهرها،
# شاخص‌های پایداری/ناپایداری و پوستر ۷ روزه (تولید در هر اجرا)
# =============================================================

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = ",".join([
    "temperature_2m", "relative_humidity_2m", "dew_point_2m",
    "apparent_temperature", "precipitation", "rain", "showers",
    "snowfall", "cloud_cover", "pressure_msl", "weather_code",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
    "cape", "convective_inhibition", "lifted_index",
    "k_index", "total_totals_index", "showalter_index",
])

DAILY_VARS = ",".join([
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "apparent_temperature_max", "apparent_temperature_min",
    "precipitation_sum", "rain_sum", "snowfall_sum", "showers_sum",
    "precipitation_hours", "precipitation_probability_max",
    "wind_speed_10m_max", "wind_gusts_10m_max",
    "wind_direction_10m_dominant", "shortwave_radiation_sum",
    "sunshine_duration", "et0_fao_evapotranspiration",
    "uv_index_max", "cape_max", "cape_mean", "lifted_index_min",
    "convective_inhibition_max", "k_index_max",
    "total_totals_index_max", "showalter_index_min",
])

CITIES = [
    {
        "name": "قم", "lat": 34.6416, "lon": 50.8746,
        "province": "قم", "elev": 935,
    },
    {
        "name": "کهک", "lat": 34.3938, "lon": 50.8643,
        "province": "قم", "elev": 1800,
    },
    {
        "name": "سلفچگان", "lat": 34.4775, "lon": 50.4592,
        "province": "قم", "elev": 1382,
    },
    {
        "name": "دستجرد", "lat": 34.3949, "lon": 49.9502,
        "province": "مرکزی", "elev": 2020,
    },
    {
        "name": "قاهان", "lat": 34.7245, "lon": 50.2632,
        "province": "قم", "elev": 1560,
    },
]

PERSIAN_WEEKDAY = {
    0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنجشنبه",
    4: "جمعه", 5: "شنبه", 6: "یکشنبه",
}

WEATHER_CODES = {
    0: "آسمان صاف", 1: "عمدتاً صاف", 2: "نیمه‌ابری", 3: "ابری",
    45: "مه", 48: "مه یخ‌زده", 51: "نم‌نم باران سبک", 53: "نم‌نم باران",
    55: "نم‌نم باران شدید", 56: "نم‌نم باران یخ‌زده", 57: "نم‌نم یخ‌زده شدید",
    61: "باران سبک", 63: "باران متوسط", 65: "باران شدید",
    66: "باران یخ‌زده", 67: "باران یخ‌زده شدید",
    71: "برف سبک", 73: "برف متوسط", 75: "برف شدید", 77: "دانه‌های برف",
    80: "رگبار سبک", 81: "رگبار متوسط", 82: "رگبار شدید",
    85: "رگبار برف سبک", 86: "رگبار برف شدید",
    95: "رعدوبرق", 96: "رعدوبرق با تگرگ سبک", 99: "رعدوبرق با تگرگ شدید",
}

WIND_SECTORS = [
    (22.5, "شمالی"), (67.5, "شمال شرقی"), (112.5, "شرقی"),
    (157.5, "جنوب شرقی"), (202.5, "جنوبی"), (247.5, "جنوب غربی"),
    (292.5, "غربی"), (337.5, "شمال غربی"), (360.1, "شمالی"),
]


def fetch_city_open_meteo(city, retries=3, timeout=40):
    """دریافت داده زنده و پویای مدل‌های هواشناسی برای یک شهر"""
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "hourly": HOURLY_VARS,
        "daily": DAILY_VARS,
        "timezone": TEHRAN_TZ.key,
        "forecast_days": 7,
        "wind_speed_unit": "kmh",
        "models": "best_match",
    }
    for attempt in range(1, retries + 1):
        try:
            r = SESSION.get(OPEN_METEO_URL, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if "daily" in data and "time" in data["daily"]:
                print(f"[داده زنده] {city['name']}: {len(data['daily']['time'])} روز دریافت شد.")
                return data
            raise ValueError("ساختار داده نامعتبر است")
        except Exception as e:
            if attempt == retries:
                print(f"[هشدار] دریافت داده {city['name']} ناموفق: {e}")
                return None
            time.sleep(3)


def wind_sector(deg):
    if deg is None:
        return "نامشخص"
    for limit, label in WIND_SECTORS:
        if deg < limit:
            return label
    return "شمالی"


def safe(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def stability_class(cape, li, ki, tt, showalter):
    """طبقه‌بندی پویای وضعیت پایداری جو بر پایه شاخص‌های محاسبه‌شده"""
    score = 0
    if cape >= 2500:
        score += 5
    elif cape >= 1500:
        score += 4
    elif cape >= 800:
        score += 3
    elif cape >= 300:
        score += 2
    elif cape >= 50:
        score += 1

    if li <= -6:
        score += 4
    elif li <= -3:
        score += 3
    elif li <= 0:
        score += 2
    elif li <= 2:
        score += 1

    if ki >= 40:
        score += 3
    elif ki >= 35:
        score += 2
    elif ki >= 30:
        score += 1

    if tt >= 55:
        score += 3
    elif tt >= 50:
        score += 2
    elif tt >= 46:
        score += 1

    if showalter <= -3:
        score += 2
    elif showalter <= 0:
        score += 1

    if score >= 12:
        return "بسیار ناپایدار (احتمال توفان تندری شدید)"
    if score >= 9:
        return "ناپایدار (رگبار و رعدوبرق)"
    if score >= 6:
        return "نیمه‌ناپایدار (رگبار پراکنده)"
    if score >= 3:
        return "نسبتاً پایدار (احتمال ابرهای کومه‌ای)"
    return "پایدار"


def synoptic_pattern(pressure, wind_dir, cape, precip, cloud):
    """تشخیص پویای الگوی سینوپتیکی از داده‌های لحظه‌ای"""
    notes = []
    if pressure <= 1000:
        notes.append("کم‌فشار سطحی / تراف کم‌فشار")
    elif pressure >= 1020:
        notes.append("پرفشار سطحی و پایداری نسبی")
    else:
        notes.append("فشار سطحی نرمال فصلی")

    if wind_dir is not None and 180 <= wind_dir <= 315:
        notes.append("جریان مرطوب جنوب‌غربی تا غربی (مناسب ناپایداری)")
    elif wind_dir is not None and (wind_dir <= 45 or wind_dir >= 315):
        notes.append("جریان شمالی خشک")
    elif wind_dir is not None and 45 < wind_dir < 180:
        notes.append("جریان شرقی/جنوب‌شرقی")

    if cloud >= 70:
        notes.append("پوشش ابری گسترده")
    elif cloud >= 30:
        notes.append("ابرهای پراکنده")
    else:
        notes.append("آسمان عمدتاً صاف")

    if cape >= 800:
        notes.append("فرارفت رطوبت و انرژی پتانسیل بالا در ترازهای میانی")
    if precip >= 5:
        notes.append("سامانه بارشی فعال")

    return notes


def day_index_map(daily_times):
    """ساخت نگاشت روز به ایندکس‌های ساعتی همان روز"""
    mapping = {}
    for idx, t in enumerate(daily_times):
        mapping[t] = idx
    return mapping


def build_daily_rows(city, data):
    """تولید ردیف‌های ۳ روزه و ۷ روزه پویا برای یک شهر"""
    daily = data["daily"]
    hourly = data["hourly"]
    times = daily["time"]

    hourly_by_day = {}
    for i, tstr in enumerate(hourly["time"]):
        day = tstr[:10]
        hourly_by_day.setdefault(day, []).append(i)

    rows = []
    for di, day in enumerate(times[:7]):
        hidx = hourly_by_day.get(day, [])
        p_sum = safe(daily.get("precipitation_sum", [0] * 7)[di])
        p_prob = safe(daily.get("precipitation_probability_max", [0] * 7)[di])
        cloud_mean = (
            sum(safe(hourly["cloud_cover"][j]) for j in hidx) / len(hidx)
            if hidx else 0.0
        )
        cape_max = safe(daily.get("cape_max", [0] * 7)[di])
        cape_mean = safe(daily.get("cape_mean", [0] * 7)[di])
        li_min = safe(daily.get("lifted_index_min", [2] * 7)[di], 2.0)
        ki_max = safe(daily.get("k_index_max", [0] * 7)[di])
        tt_max = safe(daily.get("total_totals_index_max", [0] * 7)[di])
        sw_min = safe(daily.get("showalter_index_min", [2] * 7)[di], 2.0)
        cin_max = safe(daily.get("convective_inhibition_max", [0] * 7)[di])
        wind_dom = daily.get("wind_direction_10m_dominant", [None] * 7)[di]
        pressure_mean = (
            sum(safe(hourly["pressure_msl"][j]) for j in hidx) / len(hidx)
            if hidx else 1013.0
        )
        code = int(safe(daily.get("weather_code", [0] * 7)[di]))

        rows.append({
            "date": day,
            "weekday": PERSIAN_WEEKDAY[datetime.fromisoformat(day).weekday()],
            "code": code,
            "cond": WEATHER_CODES.get(code, "وضعیت نامشخص"),
            "tmax": safe(daily.get("temperature_2m_max", [0] * 7)[di]),
            "tmin": safe(daily.get("temperature_2m_min", [0] * 7)[di]),
            "rain": p_sum,
            "prob": p_prob,
            "cloud": cloud_mean,
            "wind_max": safe(daily.get("wind_speed_10m_max", [0] * 7)[di]),
            "gust": safe(daily.get("wind_gusts_10m_max", [0] * 7)[di]),
            "wdir": wind_dom,
            "sector": wind_sector(wind_dom),
            "pressure": pressure_mean,
            "cape_max": cape_max,
            "cape_mean": cape_mean,
            "li_min": li_min,
            "ki_max": ki_max,
            "tt_max": tt_max,
            "sw_min": sw_min,
            "cin_max": cin_max,
            "day_class": stability_class(cape_max, li_min, ki_max, tt_max, sw_min),
        })
    return rows


def fmt_day_header(row, label):
    return (
        f"🗓 {label}: {row['weekday']} {row['date']} | "
        f"{row['cond']}"
    )


def city_three_day_text(city, rows):
    """متن پیش‌بینی ۳ روزه شهر به تفکیک روز"""
    lines = [f"📍 {city['name']} (ارتفاع ~{city['elev']} متر)"]
    labels = ["روز اول", "روز دوم", "روز سوم"]
    for i, row in enumerate(rows[:3]):
        lines.append(fmt_day_header(row, labels[i]))
        lines.append(
            f"   🌡 دما: بیشینه {row['tmax']:.0f}°C / کمینه {row['tmin']:.0f}°C"
        )
        lines.append(
            f"   🌧 بارش: {row['rain']:.1f} میلی‌متر | احتمال {row['prob']:.0f}% | ابر {row['cloud']:.0f}%"
        )
        lines.append(
            f"   💨 باد: {row['sector']} تا {row['wind_max']:.0f} کیلومتر/ساعت (تندباد {row['gust']:.0f})"
        )
        lines.append(
            f"   🧭 فشار سطح دریا: {row['pressure']:.1f} hPa"
        )
    return "\n".join(lines)


def city_stability_text(city, rows):
    """متن شاخص‌های پایداری/ناپایداری ۳ روزه به تفکیک روز"""
    lines = [f"📍 {city['name']}"]
    labels = ["روز اول", "روز دوم", "روز سوم"]
    for i, row in enumerate(rows[:3]):
        lines.append(fmt_day_header(row, labels[i]))
        lines.append(
            f"   🔺 CAPE (بیشینه/میانگین): {row['cape_max']:.0f} / {row['cape_mean']:.0f} J/kg"
        )
        lines.append(f"   🔻 CIN (بیشینه): {row['cin_max']:.0f} J/kg")
        lines.append(f"   🌡 Lifted Index (کمینه): {row['li_min']:.1f}")
        lines.append(f"   📊 K-Index (بیشینه): {row['ki_max']:.0f}")
        lines.append(f"   ⚡ Total Totals (بیشینه): {row['tt_max']:.0f}")
        lines.append(f"   🌀 Showalter Index (کمینه): {row['sw_min']:.1f}")
        lines.append(f"   🚦 وضعیت جو: {row['day_class']}")
    return "\n".join(lines)


def region_seven_day_text(rows):
    """متن خلاصه ۷ روزه منطقه قم بر پایه میانگین شهرها"""
    lines = []
    for i, row in enumerate(rows[:7]):
        lines.append(
            f"🗓 {row['weekday']} {row['date']} | {row['cond']} | "
            f"{row['tmin']:.0f}°…{row['tmax']:.0f}°C | "
            f"بارش {row['rain']:.1f}mm ({row['prob']:.0f}%) | "
            f"باد {row['sector']} {row['wind_max']:.0f}km/h"
        )
    return "\n".join(lines)


def generate_qom_7day_poster(all_city_rows, output_path="qom_7day_weather_poster.png"):
    """تولید پویای پوستر ۷ روزه وضع هوا برای پنج شهر در هر اجرا"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        print(f"[خطا] matplotlib برای پوستر در دسترس نیست: {e}")
        return None

    if not all_city_rows:
        print("[هشدار] داده‌ای برای پوستر ۷ روزه موجود نیست.")
        return None

    qom_rows = all_city_rows.get("قم") or next(iter(all_city_rows.values()))
    days = [r["date"][5:] for r in qom_rows[:7]]
    fig, axes = plt.subplots(
        4, 1, figsize=(14, 11), facecolor="#0e1526",
        gridspec_kw={"height_ratios": [1.1, 1.1, 1.0, 1.0], "hspace": 0.55},
    )
    for ax in axes:
        ax.set_facecolor("#131c31")
        for spine in ax.spines.values():
            spine.set_color("#22324f")
        ax.tick_params(colors="#94a3b8", labelsize=9)
        ax.grid(True, color="#2a3b5c", alpha=0.35, ls=":")

    palette = ["#38bdf8", "#f87171", "#4ade80", "#c084fc", "#fbbf24"]

    ax0 = axes[0]
    for idx, (cname, rows) in enumerate(all_city_rows.items()):
        ax0.plot(days, [r["tmax"] for r in rows[:7]], marker="o",
                 color=palette[idx % len(palette)], lw=2, label=cname)
    ax0.set_title("Qom Region — 7-Day Maximum Temperature (°C)",
                  color="#e2e8f0", fontsize=12, weight="bold", loc="left")
    ax0.legend(frameon=False, ncol=5, fontsize=9, labelcolor="#94a3b8",
               loc="upper center", bbox_to_anchor=(0.5, -0.22))

    ax1 = axes[1]
    for idx, (cname, rows) in enumerate(all_city_rows.items()):
        ax1.plot(days, [r["tmin"] for r in rows[:7]], marker="s",
                 color=palette[idx % len(palette)], lw=2, label=cname)
    ax1.set_title("Qom Region — 7-Day Minimum Temperature (°C)",
                  color="#e2e8f0", fontsize=12, weight="bold", loc="left")
    ax1.legend(frameon=False, ncol=5, fontsize=9, labelcolor="#94a3b8",
               loc="upper center", bbox_to_anchor=(0.5, -0.22))

    ax2 = axes[2]
    width = 0.16
    xs = np.arange(len(days))
    for idx, (cname, rows) in enumerate(all_city_rows.items()):
        ax2.bar(xs + (idx - 2) * width, [r["rain"] for r in rows[:7]],
                width=width, color=palette[idx % len(palette)], alpha=0.9,
                label=cname)
    ax2.set_xticks(xs)
    ax2.set_xticklabels(days, color="#94a3b8", fontsize=9)
    ax2.set_title("Qom Region — 7-Day Precipitation (mm)",
                  color="#e2e8f0", fontsize=12, weight="bold", loc="left")
    ax2.legend(frameon=False, ncol=5, fontsize=9, labelcolor="#94a3b8",
               loc="upper center", bbox_to_anchor=(0.5, -0.22))

    ax3 = axes[3]
    for idx, (cname, rows) in enumerate(all_city_rows.items()):
        ax3.plot(days, [r["cape_max"] for r in rows[:7]], marker="^",
                 color=palette[idx % len(palette)], lw=2, label=cname)
    ax3.set_title("Qom Region — 7-Day Max CAPE (J/kg) — Instability",
                  color="#e2e8f0", fontsize=12, weight="bold", loc="left")
    ax3.legend(frameon=False, ncol=5, fontsize=9, labelcolor="#94a3b8",
               loc="upper center", bbox_to_anchor=(0.5, -0.22))

    fig.suptitle(
        "پوستر ۷ روزه وضع هوای منطقه قم | Qom 7-Day Weather Poster",
        color="#ffffff", fontsize=15, weight="bold", y=0.985,
    )
    fig.text(
        0.5, 0.958,
        "قم • کهک • سلفچگان • دستجرد • قاهان — Dynamic live Open-Meteo data | "
        + datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M"),
        color="#94a3b8", fontsize=9, ha="center",
    )
    fig.subplots_adjust(top=0.93, bottom=0.05, left=0.07, right=0.97)

    try:
        fig.savefig(output_path, facecolor=fig.get_facecolor(),
                    bbox_inches="tight", dpi=140)
        plt.close(fig)
        print(f"[پوستر] فایل ذخیره شد: {output_path}")
        return output_path
    except Exception as e:
        print(f"[خطا در ذخیره پوستر]: {e}")
        plt.close(fig)
        return None


def generate_qom_stability_poster(all_city_rows, output_path="qom_stability_indices_poster.png"):
    """ساخت پوستر تصویری شاخص‌های پایداری سه‌روزه برای شهرهای منطقه قم."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"[خطا] matplotlib برای پوستر شاخص‌ها در دسترس نیست: {e}")
        return None

    if not all_city_rows:
        print("[هشدار] داده‌ای برای پوستر شاخص‌های پایداری موجود نیست.")
        return None

    headers = ["City", "Day", "CAPE max", "CAPE mean", "CIN", "LI min", "KI max", "TT max", "SW min", "Status"]
    table_rows = []
    for city, rows in all_city_rows.items():
        for index, row in enumerate(rows[:3]):
            day = row.get("date", f"Day {index + 1}")
            values = [
                city, day, f"{row['cape_max']:.0f}", f"{row['cape_mean']:.0f}",
                f"{row['cin_max']:.0f}", f"{row['li_min']:.1f}",
                f"{row['ki_max']:.0f}", f"{row['tt_max']:.0f}",
                f"{row['sw_min']:.1f}", str(row.get("day_class", "—")),
            ]
            table_rows.append(values)
    if not table_rows:
        print("[هشدار] ردیف شاخصی برای پوستر موجود نیست.")
        return None

    fig, ax = plt.subplots(figsize=(16, max(5.5, 0.43 * len(table_rows) + 2.5)), facecolor="#0e1526")
    ax.set_facecolor("#0e1526")
    ax.axis("off")
    ax.set_title("Qom Region — 3-Day Atmospheric Stability Indices", color="white",
                 fontsize=17, weight="bold", pad=22)
    table = ax.table(cellText=table_rows, colLabels=headers, cellLoc="center", loc="center",
                     colWidths=[0.12, 0.12, 0.09, 0.09, 0.08, 0.08, 0.08, 0.08, 0.08, 0.18])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.55)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#334155")
        if row == 0:
            cell.set_facecolor("#1e3a5f")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#172238" if row % 2 else "#1b2940")
            cell.set_text_props(color="#e2e8f0")
    fig.text(0.5, 0.025, "CAPE / CIN: J/kg  |  LI / KI / TT / SW: index values  |  Open-Meteo live data",
             ha="center", color="#94a3b8", fontsize=9)
    fig.tight_layout(rect=[0.015, 0.055, 0.985, 0.96])
    try:
        fig.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=160)
        plt.close(fig)
        print(f"[پوستر شاخص‌ها] فایل ذخیره شد: {output_path}")
        return output_path
    except Exception as e:
        print(f"[خطا در ذخیره پوستر شاخص‌ها]: {e}")
        plt.close(fig)
        return None


def send_long_text(text, limit=3500):
    """ارسال متن بلند به صورت قطعه‌قطعه بدون کم شدن هیچ خطی"""
    if not text:
        return
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > limit:
            send_text(chunk)
            time.sleep(1.0)
            chunk = line
        else:
            chunk = f"{chunk}\n{line}" if chunk else line
    if chunk:
        send_text(chunk)


def dynamic_synoptic_and_city_forecast():
    """بخش پویا: تحلیل سینوپتیکی، پیش‌بینی ۳ روزه شهرها، شاخص‌های پایداری و پوستر"""
    print("\n=== ۸. تحلیل سینوپتیکی و دینامیکی پویا + پیش‌بینی ۳ روزه شهرها ===")
    now = datetime.now(TEHRAN_TZ)
    stamp = now.strftime("%Y/%m/%d - ساعت %H:%M")

    all_city_rows = {}
    failed = []
    for city in CITIES:
        data = fetch_city_open_meteo(city)
        if not data:
            failed.append(city["name"])
            continue
        rows = build_daily_rows(city, data)
        all_city_rows[city["name"]] = rows

    if not all_city_rows:
        print("[هشدار] هیچ داده پویایی برای شهرها دریافت نشد؛ بخش تحلیل پویا اجرا نشد.")
        return

    # ---------- ۱. تحلیل سینوپتیکی و دینامیکی ----------
    try:
        sync_lines = [
            "🌐 تحلیل سینوپتیکی و دینامیکی پویا",
            f"🕒 زمان تحلیل: {stamp}",
            "داده مبنا: Open-Meteo (مدل best_match) — به‌روزرسانی خودکار در هر اجرا",
            "",
        ]
        for cname, rows in all_city_rows.items():
            r0 = rows[0]
            notes = synoptic_pattern(
                r0["pressure"], r0["wdir"], r0["cape_max"], r0["rain"], r0["cloud"]
            )
            sync_lines.append(f"📍 {cname}:")
            sync_lines.append(
                f"   سطح دریا: {r0['pressure']:.1f} hPa | جریان: {r0['sector']} "
                f"{r0['wind_max']:.0f} km/h | CAPE بیشینه: {r0['cape_max']:.0f} J/kg"
            )
            for n in notes:
                sync_lines.append(f"   • {n}")
            sync_lines.append("")

        regional = all_city_rows["قم"] if "قم" in all_city_rows else next(
            iter(all_city_rows.values())
        )
        sync_lines.append("🌀 تحلیل دینامیکی تراز میانی و منطقه‌ای (۳ روز آینده):")
        for i, row in enumerate(regional[:3]):
            sync_lines.append(
                f"   روز {i + 1} ({row['weekday']} {row['date']}): "
                f"{row['day_class']} | LI={row['li_min']:.1f} | KI={row['ki_max']:.0f} | "
                f"TT={row['tt_max']:.0f} | SW={row['sw_min']:.1f}"
            )
        if failed:
            sync_lines.append("")
            sync_lines.append(
                "⚠️ عدم دریافت داده زنده برای: " + "، ".join(failed)
            )
        send_long_text("\n".join(sync_lines))
    except Exception as e:
        print(f"[خطا] بخش تحلیل سینوپتیکی و دینامیکی ناموفق بود: {e!r}")

    # ---------- ۲. پیش‌بینی ۳ روزه شهرها به تفکیک روز ----------
    try:
        for cname, rows in all_city_rows.items():
            try:
                header = f"📅 پیش‌بینی پویا ۳ روزه — {cname}\n🕒 {stamp}\n"
                send_long_text(header + city_three_day_text(next(
                    c for c in CITIES if c["name"] == cname), rows))
            except Exception as e:
                print(f"[خطا] پیش‌بینی ۳ روزه شهر {cname} ناموفق بود: {e!r}")
    except Exception as e:
        print(f"[خطا] بخش پیش‌بینی ۳ روزه شهرها ناموفق بود: {e!r}")

    # ---------- ۳. پوستر تصویری شاخص‌های پایداری/ناپایداری ۳ روزه ----------
    try:
        stability_poster = generate_qom_stability_poster(all_city_rows)
        if stability_poster:
            send_media(
                "sendPhoto", "photo", stability_poster,
                "📈 پوستر شاخص‌های پایداری و ناپایداری سه‌روزه منطقه قم\n"
                "📍 شامل CAPE، CIN، LI، KI، TT و Showalter\n"
                f"🕒 تولید در: {stamp}"
            )
    except Exception as e:
        print(f"[خطا] تولید/ارسال پوستر شاخص‌های پایداری ناموفق بود: {e!r}")

    # ---------- ۴. خلاصه ۷ روزه منطقه ----------
    try:
        for cname, rows in all_city_rows.items():
            try:
                header = f"🗓 پیش‌بینی پویا ۷ روزه — {cname} (قم و حومه)\n🕒 {stamp}\n"
                send_long_text(header + region_seven_day_text(rows))
            except Exception as e:
                print(f"[خطا] خلاصه ۷ روزه {cname} ناموفق بود: {e!r}")
    except Exception as e:
        print(f"[خطا] بخش خلاصه ۷ روزه منطقه ناموفق بود: {e!r}")

    # ---------- ۵. پوستر ۷ روزه ----------
    try:
        poster = generate_qom_7day_poster(all_city_rows)
        if poster:
            send_media(
                "sendPhoto", "photo", poster,
                "🖼 پوستر پویا ۷ روزه هوای منطقه قم\n"
                "📍 قم • کهک • سلفچگان • دستجرد • قاهان\n"
                f"🕒 تولید در: {stamp}"
            )
    except Exception as e:
        print(f"[خطا] تولید/ارسال پوستر ۷ روزه ناموفق بود: {e!r}")

def main():
    now_str = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")
    print(f"=== Run start: {now_str} ===")
    state = load_state()

    # ۰. متئوگرام چندمدله قم
    capture_and_send_custom_meteogram()

    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=browser_args,
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()

        # ۱. متئوگرام‌های ۱۰ روزه ECMWF
        capture_ecmwf(page)

        # ۲. نقشه Tropical Tidbits
        capture_tropical_tidbits(page)

        # ۳. جداول و نمودارهای Yr.no
        capture_yr(page)

        # ۴. پیش‌بینی‌های فورکا (Foreca)
        capture_foreca(page)

        # ۵. پیش‌بینی‌های افقی Weather-Forecast
        capture_weather_forecast(page)

        browser.close()

    # ۶. بررسی کانال تلگرامی iran_met
    check_iran_met(state)

    # ۷. تحلیل تخصصی دینامیکی-سینوپتیکی و پیش‌بینی شهری
    generate_and_send_synoptic_analysis()

    # ۸. تحلیل پویا: سینوپتیک، پیش‌بینی ۳ روزه، پوستر شاخص‌های پایداری و ۷ روزه
    dynamic_synoptic_and_city_forecast()

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز چرخه پایش و ارسال تحلیل ===")


if __name__ == "__main__":
    main()
# ==========================================================================
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# ==========================================================================
