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
# ۱. کلیدها و توکن‌ها
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
})

# -------------------------------------------------------------
# ۲. لیست ترتیبی متئوگرام‌ها (ECMWF) - [کاملاً فریز شده]
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
TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]

# -------------------------------------------------------------
# ۴. لیست جداول و نمودارهای نروژ (Yr.no) - [کاملاً فریز شده]
# -------------------------------------------------------------
YR_TARGETS = [
    {"name": "جدول روزانه قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قم", "file": "yr_1_table_qom.png"},
    {"name": "نمودار ساعتی قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم", "file": "yr_2_graph_qom.png"},
    {"name": "جدول روزانه دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - دستجرد", "file": "yr_3_table_dastjerd.png"},
    {"name": "نمودار ساعتی دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد", "file": "yr_4_graph_dastjerd.png"},
    {"name": "جدول روزانه کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom%20Province/Kahak", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - کهک", "file": "yr_5_table_kahak.png"},
    {"name": "نمودار ساعتی کهک", "url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom%20Province/Kahak", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک", "file": "yr_6_graph_kahak.png"},
    {"name": "جدول روزانه سلفچگان", "url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - سلفچگان", "file": "yr_7_table_salaf.png"},
    {"name": "نمودار ساعتی سلفچگان", "url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان", "file": "yr_8_graph_salaf.png"},
    {"name": "جدول روزانه قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قاهان", "file": "yr_9_table_qahan.png"},
    {"name": "نمودار ساعتی قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان", "file": "yr_10_graph_qahan.png"},
]

# -------------------------------------------------------------
# ۵. لیست پیش‌بینی‌های فورکا (Foreca) - [کاملاً فریز شده]
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
# ۶. بولتن‌های رسمی سازمان هواشناسی
# -------------------------------------------------------------
BULLETINS = [
    {
        "id": "irimo_rain",
        "title": "🌧 بولتن روزانه بارش کشور (سازمان هواشناسی)",
        "url": "https://ndc.irimo.ir/far/services/file_manager/1182801/download/1/%D8%A8%D9%88%D9%84%D8%AA%D9%86-%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87-%D8%A8%D8%A7%D8%B1%D8%B4-050721.html?t=%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87",
        "filename": "bulletin_rain.pdf",
    },
    {
        "id": "irimo_temp",
        "title": "🌡 بولتن روزانه دمای کشور (سازمان هواشناسی)",
        "url": "https://ndc.irimo.ir/far/services/file_manager/1182799/download/1/%D8%A8%D9%88%D9%84%D8%AA%D9%86-%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87-%D8%AF%D9%85%D8%A7-050721.html?t=%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87",
        "filename": "bulletin_temp.pdf",
    },
]


def load_state():
    if not STATE_FILE.exists():
        return {"channels": {}, "bulletins": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"channels": {}, "bulletins": {}}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def send_media(method, file_key, file_path, caption):
    """ارسال امن مدیا به تلگرام و بله با بررسی حجم واقعی فایل"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 2000:
        print(f"[خطا] فایل {file_path} معتبر نیست یا ایجاد نشده است.")
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
        b_method = "sendDocument" if method == "sendDocument" else "sendPhoto"
        b_key = "document" if file_key == "document" else "photo"
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{b_method}",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={b_key: f},
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
# ۱. دریافت متئوگرام‌های ECMWF (کاملاً فریز شده و پایدار)
# -------------------------------------------------------------
def capture_ecmwf(page):
    print("\n=== ۱. دریافت متئوگرام‌های ۱۰ روزه ECMWF ===")
    for item in ECMWF_TARGETS:
        print(f"در حال باز کردن: {item['name']}...")
        try:
            page.goto(item["web_url"], timeout=65000, wait_until="load")
            page.wait_for_timeout(9000)

            img_selector = "img[src*='render-worker'], img[src*='opencharts'], .chart-container img"
            img_el = page.query_selector(img_selector)

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
# ۲. دریافت دقیق Tropical Tidbits با Playwright (رفع مشکل مسدودی CDN)
# -------------------------------------------------------------
def capture_tropical_tidbits(page):
    print("\n=== ۲. عکسبرداری فریم‌های Tropical Tidbits (بارش و ۵۰۰ هکتوپاسکال) ===")

    # الف) ۱۰ فریم بارش تجمیعی و فشار (mslp_pcpn)
    print("\n--- دریافت ۱۰ فریم بارش و فشار (mslp_pcpn) ---")
    for fh in TROPICAL_HOURS:
        # لینک دقیق درخواستی (با باز کردن خودکار جدیدترین ران پایدار)
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
            # صبر کردن تا تصویر نقشه داخل وبسایت بارگذاری شود
            page.wait_for_timeout(4500)

            # اسکرین‌شات از خود نقشه یا کل کانتینر
            img_element = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_element:
                img_element.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در دریافت فریم بارش fh={fh}: {e}")
        time.sleep(1.5)

    # ب) ۱۰ فریم تاوایی و ارتفاع تراز ۵۰۰ هکتوپاسکال (z500a)
    print("\n--- دریافت ۱۰ فریم تاوایی و تراز ۵۰۰ هکتوپاسکال (z500a) ---")
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
            page.wait_for_timeout(4500)

            img_element = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_element:
                img_element.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در دریافت فریم ۵۰۰ fh={fh}: {e}")
        time.sleep(1.5)


# -------------------------------------------------------------
# ۳. جداول و نمودارهای Yr.no - [کاملاً فریز شده]
# -------------------------------------------------------------
def capture_yr(page):
    print("\n=== ۳. جداول و نمودارهای سایت Yr.no ===")
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
# ۴. پیش‌بینی‌های فورکا (Foreca) - [کاملاً فریز شده]
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
# ۵. کانال تلگرامی @iran_met - [کاملاً فریز شده]
# -------------------------------------------------------------
def check_iran_met(state):
    print("\n=== ۵. کانال تلگرامی @iran_met ===")
    username = "iran_met"
    chan_state = state.get("channels", {}).get(username, {"last_id": 0, "seen_ids": []})
    last_id = int(chan_state.get("last_id", 0))
    seen_ids = list(chan_state.get("seen_ids", []))

    try:
        url = f"https://t.me/s/{username}"
        r = SESSION.get(url, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        messages = soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))
    except Exception as e:
        print(f"خطا در کانال @{username}: {e}")
        return

    new_posts = []
    for msg in messages:
        dp = msg.get("data-post", "")
        if "/" not in dp:
            continue
        try:
            m_id = int(dp.rsplit("/", 1)[-1])
        except ValueError:
            continue

        if m_id in seen_ids or (last_id > 0 and m_id <= last_id):
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

        if not text and not img_url:
            continue

        new_posts.append({"id": m_id, "text": text, "img_url": img_url})

    for p in sorted(new_posts, key=lambda x: x["id"]):
        caption = f"{p['text']}\n\n📎 منبع: @{username}" if p["text"] else f"📎 منبع: @{username}"
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        if p["img_url"]:
            tmp_img = f"tmp_{username}_{p['id']}.jpg"
            try:
                res_img = SESSION.get(p["img_url"], timeout=REQ_TIMEOUT)
                Path(tmp_img).write_bytes(res_img.content)
                send_media("sendPhoto", "photo", tmp_img, caption)
                Path(tmp_img).unlink(missing_ok=True)
            except Exception as e:
                print(f"خطا در تصویر تلگرام: {e}")
        else:
            send_text(caption)

        last_id = max(last_id, p["id"])
        if p["id"] not in seen_ids:
            seen_ids.append(p["id"])

    state.setdefault("channels", {})[username] = {
        "last_id": last_id,
        "seen_ids": seen_ids[-100:],
    }


# -------------------------------------------------------------
# ۶. بولتن‌های رسمی سازمان هواشناسی - [کاملاً فریز شده]
# -------------------------------------------------------------
def check_bulletins(state):
    print("\n=== ۶. بولتن‌های روزانه PDF سازمان هواشناسی ===")
    b_state = state.get("bulletins", {})

    for b in BULLETINS:
        try:
            r = SESSION.get(b["url"], timeout=REQ_TIMEOUT)
            if r.status_code != 200 or len(r.content) < 10000:
                print(f"پاسخ بولتن {b['title']} نامعتبر است.")
                continue

            file_hash = hashlib.sha256(r.content).hexdigest()
            saved_hash = b_state.get(b["id"])

            if file_hash != saved_hash:
                print(f"بولتن جدید بارگذاری می‌شود: {b['title']}")
                pdf_path = Path(b["filename"])
                pdf_path.write_bytes(r.content)

                today_fa = datetime.now(TEHRAN_TZ).strftime("%Y/%m/%d")
                caption = f"{b['title']}\n📅 تاریخ انتشار: {today_fa}\n🏛 مرکز ملی اقلیم و مدیریت بحران خشکسالی"
                send_media("sendDocument", "document", str(pdf_path), caption)

                b_state[b["id"]] = file_hash
                pdf_path.unlink(missing_ok=True)
            else:
                print(f"بولتن {b['title']} تغییر نکرده است.")
        except Exception as e:
            print(f"خطا در بولتن {b['title']}: {e}")

    state["bulletins"] = b_state


# -------------------------------------------------------------
# اجرای برنامه به ترتیب دقیق
# -------------------------------------------------------------
def main():
    print(f"=== شروع ارسال منظم پایش جوی ({datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}) ===")
    state = load_state()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        # ۱. متئوگرام‌های ۵ ایستگاه ECMWF (فریز شده)
        capture_ecmwf(page)

        # ۲. عکسبرداری مستقیم از صفحات وب Tropical Tidbits (اصلاح شده و تضمینی)
        capture_tropical_tidbits(page)

        # ۳. جداول و نمودارهای Yr.no (فریز شده)
        capture_yr(page)

        # ۴. پیش‌بینی‌های Foreca (فریز شده)
        capture_foreca(page)

        browser.close()

    # ۵. پست‌های کانال تلگرام iran_met (فریز شده)
    check_iran_met(state)

    # ۶. بولتن‌های بارش و دمای کشور (فریز شده)
    check_bulletins(state)

    save_state(state)
    print("\n=== اتمام موفقیت‌آمیز چرخه پایش ===")


if __name__ == "__main__":
    main()
