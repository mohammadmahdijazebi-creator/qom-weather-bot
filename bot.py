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

# ==========================================
# تنظیمات تلگرام و بله
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID")

BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID") or os.getenv("BALE_CHAT_ID")

STATE_FILE = Path("weather_state.json")
TEXT_FILE = Path("forecast_text.txt")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
REQ_TIMEOUT = 50

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
})

# ==========================================
# اهداف واکشی
# ==========================================
ECMWF_TARGETS = [
    {
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=&epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom",
        "caption": "متئوگرام ۱۰ روزه ECMWF - قم",
        "output": "ecmwf_1_qom.png",
    },
    {
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=&epsgram=classical_10d&lat=34.3938&lon=50.8643&station_name=Kahak",
        "caption": "متئوگرام ۱۰ روزه ECMWF - کهک",
        "output": "ecmwf_2_kahak.png",
    },
    {
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=&epsgram=classical_10d&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "caption": "متئوگرام ۱۰ روزه ECMWF - دستجرد",
        "output": "ecmwf_3_dastjerd.png",
    },
    {
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=&epsgram=classical_10d&lat=34.4775&lon=50.4592&station_name=Salafchegan",
        "caption": "متئوگرام ۱۰ روزه ECMWF - سلفچگان",
        "output": "ecmwf_4_salafchegan.png",
    },
    {
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=&epsgram=classical_10d&lat=34.7245&lon=50.2632&station_name=Qahan",
        "caption": "متئوگرام ۱۰ روزه ECMWF - قاهان",
        "output": "ecmwf_5_qahan.png",
    },
]

TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

YR_TARGETS = [
    {
        "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom/Qom",
        "caption": "جدول پیش‌بینی روزانه Yr.no - قم",
        "output": "yr_1_table_qom.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom/Qom",
        "caption": "نمودار گرافیکی وضعیت جوی Yr.no - قم",
        "output": "yr_2_graph_qom.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom/Kahak",
        "caption": "جدول پیش‌بینی روزانه Yr.no - کهک",
        "output": "yr_3_table_kahak.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom/Kahak",
        "caption": "نمودار گرافیکی وضعیت جوی Yr.no - کهک",
        "output": "yr_4_graph_kahak.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom/Salafchegan",
        "caption": "جدول پیش‌بینی روزانه Yr.no - سلفچگان",
        "output": "yr_5_table_salaf.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom/Salafchegan",
        "caption": "نمودار گرافیکی وضعیت جوی Yr.no - سلفچگان",
        "output": "yr_6_graph_salaf.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi/Dastjerd",
        "caption": "جدول پیش‌بینی روزانه Yr.no - دستجرد",
        "output": "yr_7_table_dastjerd.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi/Dastjerd",
        "caption": "نمودار گرافیکی وضعیت جوی Yr.no - دستجرد",
        "output": "yr_8_graph_dastjerd.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom/Qahan",
        "caption": "جدول پیش‌بینی روزانه Yr.no - قاهان",
        "output": "yr_9_table_qahan.png",
    },
    {
        "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom/Qahan",
        "caption": "نمودار گرافیکی وضعیت جوی Yr.no - قاهان",
        "output": "yr_10_graph_qahan.png",
    },
]

FORECA_TARGETS = [
    {
        "url": "https://www.foreca.com/100119208/Qom-Iran/10-day-forecast",
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم",
        "output": "foreca_1_qom_10d.png",
    },
    {
        "url": "https://www.foreca.com/100119208/Qom-Iran/15-day-forecast",
        "caption": "پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم",
        "output": "foreca_2_qom_15d.png",
    },
    {
        "url": "https://www.foreca.com/100122026/Kahak-Qom-Iran/10-day-forecast",
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک",
        "output": "foreca_3_kahak_10d.png",
    },
    {
        "url": "https://www.foreca.com/100122026/Kahak-Qom-Iran/15-day-forecast",
        "caption": "پیش‌بینی ۱۵ روزه فورکا (Foreca) - کهک",
        "output": "foreca_4_kahak_15d.png",
    },
    {
        "url": "https://www.foreca.com/100117287/Salafchegan-Qom-Iran/10-day-forecast",
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان",
        "output": "foreca_5_salaf_10d.png",
    },
    {
        "url": "https://www.foreca.com/100117287/Salafchegan-Qom-Iran/15-day-forecast",
        "caption": "پیش‌بینی ۱۵ روزه فورکا (Foreca) - سلفچگان",
        "output": "foreca_6_salaf_15d.png",
    },
    {
        "url": "https://www.foreca.com/100137151/Dastjerd-Markazi-Iran/10-day-forecast",
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - دستجرد",
        "output": "foreca_7_dast_10d.png",
    },
    {
        "url": "https://www.foreca.com/100137151/Dastjerd-Markazi-Iran/15-day-forecast",
        "caption": "پیش‌بینی ۱۵ روزه فورکا (Foreca) - دستجرد",
        "output": "foreca_8_dast_15d.png",
    },
    {
        "url": "https://www.foreca.com/100120681/Qahan-Qom-Iran/10-day-forecast",
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - قاهان",
        "output": "foreca_9_qah_10d.png",
    },
    {
        "url": "https://www.foreca.com/100120681/Qahan-Qom-Iran/15-day-forecast",
        "caption": "پیش‌بینی ۱۵ روزه فورکا (Foreca) - قاهان",
        "output": "foreca_10_qah_15d.png",
    },
]

WEATHER_FORECAST_TARGETS = [
    {
        "url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest",
        "caption": "جدول تفصیلی وضعیت جوی - قم (Weather-Forecast)",
        "output": "wf_1_qom.png",
    },
    {
        "url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest",
        "caption": "جدول تفصیلی وضعیت جوی - کهک (Weather-Forecast)",
        "output": "wf_2_kahak.png",
    },
    {
        "url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest",
        "caption": "جدول تفصیلی وضعیت جوی - سلفچگان (Weather-Forecast)",
        "output": "wf_3_salafchegan.png",
    },
    {
        "url": "https://www.weather-forecast.com/locations/Dastjerd/forecasts/latest",
        "caption": "جدول تفصیلی وضعیت جوی - دستجرد (Weather-Forecast)",
        "output": "wf_4_dastjerd.png",
    },
]

ADS_PATTERNS = [
    "تبلیغ", "رزرو تبلیغات", "تعرفه", "پذیرش تبلیغات", "ادمین تبلیغات",
    "سیگنال", "ارز دیجیتال", "بیت کوین", "تتر", "صرافی", "سود تضمینی",
    "فروش فیلترشکن", "vpn", "وی پی ان", "کانفیگ", "خرید سرور",
    "همکاری در فروش",
]

# ==========================================
# مدیریت وضعیت و پایگاه داده
# ==========================================
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"channels": {}}


def save_state(state: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ==========================================
# ارسال به شبکه‌های اجتماعی
# ==========================================
def send_media(method: str, file_key: str, file_path: str, caption: str = ""):
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
        print(f"[رد شد]: فایل {file_path} وجود ندارد یا معتبر نیست.")
        return

    # ۱. ارسال به تلگرام
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
                print(f"[تلگرام]: {file_path} با موفقیت ارسال شد.")
            else:
                print(f"[خطای تلگرام]: {r.text}")
        except Exception as e:
            print(f"[خطا در ارتباط تلگرام]: {e}")

    # ۲. ارسال به بله
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
                print(f"[بله]: {file_path} با موفقیت ارسال شد.")
            else:
                print(f"[خطای بله]: {r.text}")
        except Exception as e:
            print(f"[خطا در ارتباط بله]: {e}")

    time.sleep(2.0)


def send_text(text: str):
    if not text.strip():
        return

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


# ==========================================
# تولید و ارسال متئوگرام چندمدله برای ۵ منطقه
# ==========================================
def capture_and_send_custom_meteogram():
    """تولید و ارسال متئوگرام چندمدله ۱۰ روزه برای قم، کهک، سلفچگان، دستجرد و قاهان"""
    print("\n=== ۰. تولید و ارسال متئوگرام‌های چندمدله استان قم ===")

    stations = [
        {"fa": "قم", "en": "Qom", "lat": 34.64, "lon": 50.87, "file": "qom_live_multimodel_meteogram.png"},
        {"fa": "کهک", "en": "Kahak", "lat": 34.3938, "lon": 50.8643, "file": "kahak_live_multimodel_meteogram.png"},
        {"fa": "سلفچگان", "en": "Salafchegan", "lat": 34.4775, "lon": 50.4592, "file": "salafchegan_live_multimodel_meteogram.png"},
        {"fa": "دستجرد", "en": "Dastjerd", "lat": 34.3949, "lon": 49.9502, "file": "dastjerd_live_multimodel_meteogram.png"},
        {"fa": "قاهان", "en": "Qahan", "lat": 34.7245, "lon": 50.2632, "file": "qahan_live_multimodel_meteogram.png"},
    ]

    for st in stations:
        out_file = st["file"]
        caption = (
            f"📊 متئوگرام چندمدله ۱۰ روزه {st['fa']} (ECMWF, GFS, ICON, GEM)\n"
            f"🔹 دما، بارش تجمعی و سمت و سرعت باد\n"
            f"📍 ایستگاه: Iran, {st['en']} - Ali Jazebi"
        )
        try:
            print(f"تولید فایل متئوگرام برای {st['fa']} با generate_qom_meteogram...")
            generate_qom_meteogram(
                output_path=out_file,
                lat=st["lat"],
                lon=st["lon"],
                city_en=st["en"],
                city_fa=st["fa"]
            )
            if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
                send_media("sendPhoto", "photo", out_file, caption=caption)
                time.sleep(1.5)
            else:
                print(f"[هشدار]: فایل متئوگرام {st['fa']} ایجاد نشد یا حجم آن کمتر از ۱۰۰۰ بایت است.")
        except Exception as e:
            print(f"[خطا در متئوگرام چندمدله {st['fa']}]: {e}")


# ==========================================
# تصویربرداری تخصصی با Playwright
# ==========================================
def capture_ecmwf(page, target):
    print(f"دریافت ECMWF: {target['caption']}...")
    try:
        page.goto(target["url"], timeout=70000)
        time.sleep(12)

        chart_elem = page.query_selector("img[src*='render-worker'], img[src*='opencharts'], .chart-container img")
        if chart_elem:
            src = chart_elem.get_attribute("src")
            if src and src.startswith("http"):
                res = SESSION.get(src, timeout=REQ_TIMEOUT)
                if res.status_code == 200 and len(res.content) > 3000:
                    with open(target["output"], "wb") as f:
                        f.write(res.content)
                    send_media("sendPhoto", "photo", target["output"], caption=target["caption"])
                    return

            chart_elem.screenshot(path=target["output"])
            send_media("sendPhoto", "photo", target["output"], caption=target["caption"])
            return

        page.screenshot(path=target["output"])
        send_media("sendPhoto", "photo", target["output"], caption=target["caption"])
    except Exception as e:
        print(f"[خطای ECMWF]: {e}")


def clean_tropical_welcome(page):
    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
        page.evaluate("""
            () => {
                const selectors = [
                    '.modal', '.fade', '.modal-backdrop', '#welcomeModal',
                    '.ui-dialog', '.ui-widget-overlay', '[id*="modal"]', '[class*="modal"]'
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                document.body.classList.remove('modal-open');
                document.body.style.overflow = 'auto';
                document.body.style.filter = 'none';
            }
        """)
        time.sleep(0.5)
    except Exception:
        pass


def capture_tropical_tidbits(page):
    print("\n=== ۲. دریافت نقشه‌های Tropical Tidbits ===")
    clean_tropical_welcome(page)

    # ۱. بارش و فشار
    for h in TROPICAL_HOURS:
        url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn&fh={h}"
        out = f"tropical_mslp_{h}h.png"
        caption = f"پیش‌بینی بارش و فشار تراز دریا GFS خاورمیانه (+{h} ساعت)"
        try:
            page.goto(url, timeout=40000)
            time.sleep(2.5)
            clean_tropical_welcome(page)
            elem = page.query_selector("#modelImage, .model-image, #analysis-image")
            if elem:
                elem.screenshot(path=out)
            else:
                page.screenshot(path=out)
            send_media("sendPhoto", "photo", out, caption=caption)
        except Exception as e:
            print(f"[خطای نقشه بارش +{h}]: {e}")

    # ۲. تاوایی و ارتفاع تراز ۵۰۰
    for h in TROPICAL_HOURS:
        url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=z500a&fh={h}"
        out = f"tropical_z500_{h}h.png"
        caption = f"ناهنجاری تراز ۵۰۰ هکتوپاسکال GFS (+{h} ساعت)"
        try:
            page.goto(url, timeout=40000)
            time.sleep(2.5)
            clean_tropical_welcome(page)
            elem = page.query_selector("#modelImage, .model-image, #analysis-image")
            if elem:
                elem.screenshot(path=out)
            else:
                page.screenshot(path=out)
            send_media("sendPhoto", "photo", out, caption=caption)
        except Exception as e:
            print(f"[خطای نقشه تراز ۵۰۰ +{h}]: {e}")


def capture_yr(page, target):
    print(f"دریافت Yr.no: {target['caption']}...")
    try:
        page.goto(target["url"], wait_until="networkidle", timeout=60000)
        time.sleep(5)
        page.screenshot(path=target["output"], full_page=True)
        send_media("sendPhoto", "photo", target["output"]
