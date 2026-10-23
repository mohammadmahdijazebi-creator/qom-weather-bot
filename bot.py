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
    print("\n=== ۰. تولید و ارسال متئوگرام چندمدله قم ===")
    out_file = "qom_live_multimodel_meteogram.png"
    caption = (
        "📊 متئوگرام چندمدله ۱۰ روزه قم (ECMWF, GFS, ICON, GEM)\n"
        "📍 ایستگاه: قم (Iran, Qom - Ali Jazebi)\n"
        "🌡 روند دما و خطوط آنسامبل | 🌧 بارش تجمعی | 💨 جهت و شدت باد"
    )
    try:
        print("تولید تازهٔ متئوگرام با داده‌های همین اجرا...")
        generated = generate_qom_meteogram(out_file)
        # Some versions return None; validate the actual output instead.
        if not os.path.isfile(out_file) or os.path.getsize(out_file) < 1000:
            raise RuntimeError(f"متئوگرام تازه تولید نشد: {out_file}")
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
    """Capture all requested GFS packages for every strict 6-hour lead time."""
    print("\n=== ۲. نقشه‌های GFS خاورمیانه و ایران | Tropical Tidbits ===")
    tt_base = "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me"
    packages = [
        ("mslp_pcpn", "🌧 پیش‌بینی بارش تجمیعی و فشار سطح دریا (MSLP)"),
        ("mslp_uv850", "🌐 فشار سطح دریا و باد سطح 850 هکتوپاسکال"),
        ("z500a", "🌀 ارتفاع ژئوپتانسیل و تاوایی تراز 500 هکتوپاسکال"),
    ]
    expected_hours = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]
    if TROPICAL_HOURS != expected_hours:
        raise RuntimeError("TROPICAL_HOURS باید دقیقاً گام ۶ساعتهٔ ۶ تا ۷۲ باشد")
    for package, description in packages:
        print(f"\n--- بستهٔ {package} ---")
        for fh in expected_hours:
            url = f"{tt_base}&pkg={package}&fh={fh}"
            file_name = f"tropical_{package}_fh{fh}.png"
            caption = (f"{description}\n🌐 مدل: GFS خاورمیانه و ایران\n"
                       f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3500)
                clean_tropical_welcome(page)
                page.wait_for_timeout(500)
                image = page.query_selector("#modelImage, .model-image, #analysis-image")
                if image:
                    image.screenshot(path=file_name)
                else:
                    page.screenshot(path=file_name, full_page=True)
                if os.path.getsize(file_name) > 1000:
                    send_media("sendPhoto", "photo", file_name, caption)
                else:
                    print(f"[خطا] تصویر خالی/نامعتبر برای {package} fh={fh}")
            except Exception as exc:
                print(f"خطا در بستهٔ {package}، ساعت {fh}: {exc}")
            time.sleep(1.0)


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



# -----------------------------------------------------------------------------
# پیش‌بینی زندهٔ ۷روزهٔ استان قم، شاخص‌های پایداری و پوستر
# داده‌ها از Open-Meteo گرفته می‌شوند؛ در نبود دادهٔ تراز، شاخص ساختگی نمی‌سازیم.
# -----------------------------------------------------------------------------
import math
import statistics
from datetime import date

DAILY_CITIES = {
    "قم": (34.6401, 50.8764),
    "کهک": (34.3928, 50.8640),
    "سلفچگان": (34.4769, 50.4578),
    "دستجرد": (34.3940, 49.9498),
    "قاهان": (34.7245, 50.2630),
}
FORECAST_CACHE = Path("qom_daily_forecast_cache.json")
POSTER_FILE = Path("qom_7day_weather_poster.png")
FORECAST_DAYS = 7

PERSIAN_WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
WMO_FA = {
    0: "صاف", 1: "عمدتاً صاف", 2: "نیمه‌ابری", 3: "ابری",
    45: "مه‌آلود", 48: "مه یخ‌زده", 51: "نم‌نم باران خفیف",
    53: "نم‌نم باران", 55: "نم‌نم باران شدید", 56: "باران یخ‌زن خفیف",
    57: "باران یخ‌زن شدید", 61: "باران خفیف", 63: "باران", 65: "باران شدید",
    66: "باران یخ‌زن خفیف", 67: "باران یخ‌زن شدید", 71: "برف خفیف",
    73: "برف", 75: "برف شدید", 77: "دانه‌های برف", 80: "رگبار خفیف",
    81: "رگبار", 82: "رگبار شدید", 85: "رگبار برف خفیف", 86: "رگبار برف شدید",
    95: "رعدوبرق", 96: "رعدوبرق و تگرگ خفیف", 99: "رعدوبرق و تگرگ شدید",
}


def _finite_mean(values):
    """Mean of finite numbers; return None when the source has no usable values."""
    valid = []
    for value in values or []:
        try:
            number = float(value)
            if math.isfinite(number):
                valid.append(number)
        except (TypeError, ValueError):
            continue
    return statistics.mean(valid) if valid else None


def _first_finite(values, index):
    try:
        value = values[index]
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, IndexError):
        return None


def showalter_index(t850_c, td850_c, t500_environment_c):
    """Estimate SI = environmental T500 minus parcel T500 (Celsius).

    Uses Bolton's LCL approximation and a pseudoadiabatic moist lapse rate;
    returns None if required pressure-level data are missing.
    """
    if None in (t850_c, td850_c, t500_environment_c):
        return None
    try:
        t0, td0 = float(t850_c) + 273.15, float(td850_c) + 273.15
        if td0 > t0 + 0.2 or not (150 < t0 < 340):
            return None
        tlcl = 1.0 / (1.0 / (td0 - 56.0) + math.log(t0 / td0) / 800.0) + 56.0
        p = 85000.0 * (tlcl / t0) ** (1004.0 / 287.05)
        temp = tlcl
        # Integrate saturated pseudoadiabatic lapse rate from LCL to 500 hPa.
        while p > 50000.0:
            p_next = max(50000.0, p - 100.0)
            tc = temp - 273.15
            es = 611.2 * math.exp(17.67 * tc / (tc + 243.5))
            rs = 0.622 * es / max(1.0, p - es)
            lv = 2.5e6 - 2.3e3 * tc
            gamma = (9.80665 / 1004.0) * (1 + lv * rs / (287.05 * temp)) / (1 + (lv * lv * rs * 0.622) / (1004.0 * 287.05 * temp * temp))
            dz = -(287.05 * temp / 9.80665) * math.log(p_next / p)
            temp -= gamma * dz
            p = p_next
        return float(t500_environment_c) - (temp - 273.15)
    except (ValueError, OverflowError, ZeroDivisionError):
        return None


def fetch_city_forecast(city, lat, lon):
    """Fetch a fresh 7-day forecast and hourly thermodynamic fields for a city."""
    hourly = ("temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,"
              "wind_speed_10m,wind_direction_10m,cape,convective_inhibition,"
              "lifted_index,temperature_850hPa,temperature_700hPa,temperature_500hPa,"
              "dew_point_850hPa,dew_point_700hPa")
    daily = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
    params = {"latitude": lat, "longitude": lon, "hourly": hourly, "daily": daily,
              "forecast_days": FORECAST_DAYS, "timezone": "Asia/Tehran", "wind_speed_unit": "kmh"}
    response = SESSION.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
    response.raise_for_status()
    raw = response.json()
    days = raw.get("daily", {})
    hours = raw.get("hourly", {})
    dates = days.get("time", [])
    if len(dates) < FORECAST_DAYS:
        raise ValueError(f"پاسخ ناقص پیش‌بینی برای {city}")
    result = []
    for i, iso_date in enumerate(dates[:FORECAST_DAYS]):
        day_iso = iso_date
        hourly_ids = [j for j, stamp in enumerate(hours.get("time", [])) if str(stamp).startswith(day_iso)]
        indexes = {}
        for key in ("cape", "convective_inhibition", "lifted_index", "temperature_850hPa",
                    "temperature_700hPa", "temperature_500hPa", "dew_point_850hPa", "dew_point_700hPa"):
            indexes[key] = _finite_mean([_first_finite(hours.get(key, []), j) for j in hourly_ids])
        t850, t700, t500 = (indexes[k] for k in ("temperature_850hPa", "temperature_700hPa", "temperature_500hPa"))
        td850, td700 = indexes["dew_point_850hPa"], indexes["dew_point_700hPa"]
        # Conventional K and Total Totals definitions, when all required levels exist.
        indexes["k_index"] = (t850 - t500 + td850 - (t700 - td700)) if None not in (t850, t500, td850, t700, td700) else None
        indexes["total_totals"] = (t850 + td850 - 2 * t500) if None not in (t850, td850, t500) else None
        # Approximate Showalter parcel ascent from 850 hPa to 500 hPa using
        # Bolton LCL temperature followed by numerical moist-adiabatic ascent.
        indexes["showalter_index"] = showalter_index(t850, td850, t500)
        result.append({
            "date": day_iso,
            "weekday": PERSIAN_WEEKDAYS[date.fromisoformat(day_iso).weekday()],
            "code": int(_first_finite(days.get("weather_code", []), i) or 0),
            "tmin": _first_finite(days.get("temperature_2m_min", []), i),
            "tmax": _first_finite(days.get("temperature_2m_max", []), i),
            "precip": _first_finite(days.get("precipitation_sum", []), i),
            "wind": _first_finite(days.get("wind_speed_10m_max", []), i),
            "cape": indexes["cape"], "cin": indexes["convective_inhibition"],
            "li": indexes["lifted_index"], "k": indexes["k_index"],
            "tt": indexes["total_totals"], "showalter": indexes["showalter_index"],
        })
    return {"city": city, "latitude": lat, "longitude": lon, "days": result,
            "fetched_at": datetime.now(TEHRAN_TZ).isoformat(), "source": "Open-Meteo live"}


def fetch_all_forecasts():
    forecasts, errors = {}, []
    for city, (lat, lon) in DAILY_CITIES.items():
        try:
            forecasts[city] = fetch_city_forecast(city, lat, lon)
            print(f"[پیش‌بینی زنده] {city}: دریافت شد")
        except Exception as exc:
            errors.append(f"{city}: {exc}")
            print(f"[هشدار پیش‌بینی] {city}: {exc}")
    if forecasts:
        payload = {"fetched_at": datetime.now(TEHRAN_TZ).isoformat(), "cities": forecasts}
        tmp = FORECAST_CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(FORECAST_CACHE)
        return forecasts, True, errors
    # A cache is a resilience fallback only; its timestamp is explicitly displayed.
    if FORECAST_CACHE.exists():
        try:
            cached = json.loads(FORECAST_CACHE.read_text(encoding="utf-8"))
            print("[هشدار] دادهٔ زنده در دسترس نیست؛ استفاده از کش قبلی")
            return cached.get("cities", {}), False, errors
        except Exception as exc:
            errors.append(f"cache: {exc}")
    return {}, False, errors


def stability_label(key, value):
    if value is None:
        return "ناموجود"
    if key == "cape": return "ناپایداری شدید" if value >= 1000 else "ناپایداری" if value >= 300 else "همرفت ضعیف/پایدار"
    if key == "cin": return "مهار ضعیف" if value > -25 else "مهار متوسط" if value > -100 else "مهار قوی"
    if key in ("li", "showalter"): return "ناپایدار" if value < -2 else "مرزی" if value < 2 else "پایدار"
    if key == "k": return "احتمال رشد همرفتی" if value >= 30 else "شرایط مرزی" if value >= 20 else "پایداری نسبی"
    if key == "tt": return "ناپایدار" if value >= 50 else "شرایط مرزی" if value >= 44 else "پایدارتر"
    return "ناموجود"


def _fmt(value, suffix="", digits=0):
    if value is None: return "ناموجود"
    return f"{value:.{digits}f}{suffix}"


def format_regional_forecast(forecasts, live):
    now = datetime.now(TEHRAN_TZ)
    lines = ["🌦 پیش‌بینی پویا و تفکیکی وضع هوای استان قم | ۷ روز آینده",
             f"⏱ بروزرسانی: {now.strftime('%Y/%m/%d - ساعت %H:%M')}" + (" (دادهٔ زنده)" if live else " (کش ذخیره‌شده؛ احتمال کهنگی)"),
             "━━━━━━━━━━━━━━━━━━"]
    for day_i in range(FORECAST_DAYS):
        sample = next((f["days"][day_i] for f in forecasts.values() if len(f.get("days", [])) > day_i), None)
        if not sample: continue
        lines.append(f"\n🗓 {sample['weekday']} ({'روز ' + str(day_i + 1)} | {sample['date']}):")
        for city in DAILY_CITIES:
            if city not in forecasts or len(forecasts[city]["days"]) <= day_i: continue
            d = forecasts[city]["days"][day_i]
            desc = WMO_FA.get(d["code"], "وضعیت متغیر")
            t_range = f"{_fmt(d['tmin'], '°')} تا {_fmt(d['tmax'], '°')}" if d["tmin"] is not None and d["tmax"] is not None else "دما ناموجود"
            lines.append(f"▫️ {city}: {desc}، دما {t_range}، بارش {_fmt(d['precip'], ' mm', 1)}، بیشینه باد {_fmt(d['wind'], ' km/h')}")
            vals = [("CAPE", d["cape"], " J/kg"), ("CIN", d["cin"], " J/kg"), ("LI", d["li"], "°C"),
                    ("K", d["k"], "°C"), ("TT", d["tt"], "°C"), ("Showalter", d["showalter"], "°C")]
            available = [f"{key} {_fmt(value, unit)} ({stability_label(key.lower() if key != 'Showalter' else 'showalter_index', value)})"
                         for key, value, unit in vals if value is not None]
            lines.append("   └ پایداری: " + ("؛ ".join(available) if available else "شاخص‌های تراز جو در منبع امروز موجود نیستند"))
    lines.append("\nℹ️ شاخص‌ها بر پایهٔ فیلدهای پیش‌بینی‌شدهٔ منبع‌اند؛ مقدار ناموجود حدس زده نشده است.")
    return "\n".join(lines)


def _shape_fa(text):
    """Shape Persian/Arabic script for Matplotlib when optional packages exist."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(str(text)))
    except ImportError:
        # Keep generation functional on minimal installs; install arabic-reshaper
        # and python-bidi for correctly connected/right-to-left poster labels.
        return str(text)


def generate_forecast_poster(forecasts, live):
    """Render a fresh 7-day infographic using forecast values (never sample values)."""
    if not forecasts:
        print("[پوستر] داده‌ای برای ترسیم نیست؛ پوستر ساختگی تولید نمی‌شود.")
        return False
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cities = list(forecasts)
    fig, axes = plt.subplots(len(cities), 1, figsize=(15, 3.2 * len(cities)), squeeze=False)
    fig.patch.set_facecolor("#101827")
    fig.suptitle(_shape_fa("پیش‌بینی ۷ روزهٔ استان قم | دما، بارش و پایداری جو"), color="white", fontsize=20, y=0.995)
    for row, city in enumerate(cities):
        ax = axes[row, 0]
        ax.set_facecolor("#172337")
        ds = forecasts[city]["days"][:FORECAST_DAYS]
        x = list(range(len(ds)))
        hi = [d["tmax"] if d["tmax"] is not None else float("nan") for d in ds]
        lo = [d["tmin"] if d["tmin"] is not None else float("nan") for d in ds]
        rain = [d["precip"] if d["precip"] is not None else 0 for d in ds]
        ax.plot(x, hi, color="#ff755b", marker="o", linewidth=2, label="بیشینه °C")
        ax.plot(x, lo, color="#70c1ff", marker="o", linewidth=2, label="کمینه °C")
        ax.fill_between(x, lo, hi, color="#9bbde0", alpha=.13)
        ax.set_xticks(x, [_shape_fa(f"{d['weekday']}\n{d['date'][5:]}") for d in ds], color="white")
        ax.tick_params(axis="y", colors="white")
        ax.grid(alpha=.2, color="white")
        ax.set_ylabel(_shape_fa(city), color="white", rotation=0, labelpad=35, fontsize=13)
        ax2 = ax.twinx()
        ax2.bar(x, rain, color="#45c4d8", alpha=.35, width=.42, label="بارش mm")
        ax2.tick_params(axis="y", colors="#8ee8f0")
        ax2.set_ylabel(_shape_fa("بارش mm"), color="#8ee8f0")
        ax2.set_ylim(bottom=0)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, [_shape_fa(label) for label in labels], loc="upper left", ncol=2, fontsize=8, facecolor="#172337", labelcolor="white")
        stability = [d["cape"] for d in ds]
        if any(v is not None for v in stability):
            text = "CAPE: " + " | ".join(_fmt(v, " J/kg") for v in stability)
        else:
            text = "CAPE: دادهٔ تراز در دسترس نیست"
        ax.text(.99, .95, text, transform=ax.transAxes, ha="right", va="top", color="#ffd166", fontsize=8)
        for spine in ax.spines.values(): spine.set_color("#52647c")
    stamp = datetime.now(TEHRAN_TZ).strftime("تازه‌سازی: %Y/%m/%d %H:%M") if live else "کش قبلی؛ دادهٔ زنده در دسترس نبود"
    fig.text(.5, .005, _shape_fa(stamp), ha="center", color="#c5d2e3", fontsize=10)
    fig.tight_layout(rect=(0.02, 0.025, .98, .97))
    fig.savefig(POSTER_FILE, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    if not POSTER_FILE.exists() or POSTER_FILE.stat().st_size < 1000:
        raise RuntimeError("پوستر ۷روزه به‌درستی ذخیره نشد")
    print(f"[پوستر] تولید شد: {POSTER_FILE}")
    return True


def generate_and_send_dynamic_forecast():
    """Refresh forecast & infographic on every bot run, then notify Telegram/Bale."""
    forecasts, live, errors = fetch_all_forecasts()
    if not forecasts:
        print("[هشدار] هیچ پیش‌بینی شهری دریافت نشد؛ ارسال متن/پوستر انجام نشد.")
        return
    forecast_text = format_regional_forecast(forecasts, live)
    TEXT_FILE.write_text(forecast_text, encoding="utf-8")
    send_text(forecast_text)
    try:
        if generate_forecast_poster(forecasts, live):
            send_media("sendPhoto", "photo", str(POSTER_FILE),
                       "🗓 پوستر پویا و تازهٔ پیش‌بینی ۷روزهٔ استان قم | دما، بارش و شاخص‌های پایداری")
    except Exception as exc:
        print(f"[خطای تولید پوستر] {exc}")
    if errors:
        print("برخی منابع/شهرها ناموفق بودند: " + " | ".join(errors))

def main():
    now_str = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")
    print(f"=== Run start: {now_str} ===")
    state = load_state()

    # ۰. متئوگرام چندمدله قم: تولید مجدد در هر اجرا
    capture_and_send_custom_meteogram()

    # پیش‌بینی شهری و پوستر هفت‌روزه نیز در هر اجرا تازه‌سازی می‌شوند.
    generate_and_send_dynamic_forecast()

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

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز چرخه پایش و ارسال تحلیل ===")


if __name__ == "__main__":
    main()
