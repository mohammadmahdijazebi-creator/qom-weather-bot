import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------
# ۱. کلیدها و توکن‌های تلگرام و بله
# -------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID") or os.environ.get("TELEGRAM_CHAT_ID")

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID") or os.environ.get("BALE_CHAT_ID")

STATE_FILE = Path("weather_state.json")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
REQ_TIMEOUT = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# -------------------------------------------------------------
# ۲. لیست ترتیبی متئوگرام‌های ECMWF
# -------------------------------------------------------------
ECMWF_TARGETS = [
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - قم",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قم",
        "file": "ecmwf_1_qom.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - کهک",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3938&lon=50.8643&station_name=Kahak",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: کهک",
        "file": "ecmwf_2_kahak.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - دستجرد",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: دستجرد",
        "file": "ecmwf_3_dastjerd.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - سلفچگان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.4775&lon=50.4592&station_name=Salafcheg%C4%81n",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: سلفچگان",
        "file": "ecmwf_4_salafchegan.png",
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - قاهان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.7245&lon=50.2632&station_name=Q%C4%81h%C4%81n",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قاهان",
        "file": "ecmwf_5_qahan.png",
    },
]

# -------------------------------------------------------------
# ۳. لیست ترتیبی جداول و نمودارهای Yr.no
# -------------------------------------------------------------
YR_TARGETS = [
    {"name": "جدول روزانه نروژ قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قم", "file": "yr_1_table_qom.png"},
    {"name": "نمودار ساعتی نروژ قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم", "file": "yr_2_graph_qom.png"},
    {"name": "جدول روزانه نروژ دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - دستجرد", "file": "yr_3_table_dastjerd.png"},
    {"name": "نمودار ساعتی نروژ دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد", "file": "yr_4_graph_dastjerd.png"},
    {"name": "جدول روزانه نروژ کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom%20Province/Kahak", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - کهک", "file": "yr_5_table_kahak.png"},
    {"name": "نمودار ساعتی نروژ کهک", "url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom%20Province/Kahak", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک", "file": "yr_6_graph_kahak.png"},
    {"name": "جدول روزانه نروژ سلفچگان", "url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - سلفچگان", "file": "yr_7_table_salaf.png"},
    {"name": "نمودار ساعتی نروژ سلفچگان", "url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان", "file": "yr_8_graph_salaf.png"},
    {"name": "جدول روزانه نروژ قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قاهان", "file": "yr_9_table_qahan.png"},
    {"name": "نمودار ساعتی نروژ قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان", "file": "yr_10_graph_qahan.png"},
]

# -------------------------------------------------------------
# ۴. لیست ترتیبی فورکا (Foreca) ۱۰ و ۱۵ روزه
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
# ۵. بولتن‌های رسمی سازمان هواشناسی
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
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def send_media(method, file_key, file_path, caption):
    """ارسال چندرسانه‌ای به تلگرام و بله"""
    # تلگرام
    if BOT_TOKEN and CHANNEL_ID and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={file_key: f},
                    timeout=REQ_TIMEOUT,
                )
        except Exception as e:
            print(f"[TG Error]: {e}")

    # بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID and os.path.exists(file_path):
        bale_method = "sendDocument" if method == "sendDocument" else "sendPhoto"
        bale_key = "document" if method == "sendDocument" else "photo"
        try:
            with open(file_path, "rb") as f:
                requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{bale_method}",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={bale_key: f},
                    timeout=REQ_TIMEOUT,
                )
        except Exception as e:
            print(f"[Bale Error]: {e}")

    time.sleep(2)


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
    time.sleep(2)


def find_latest_tropical_run():
    """یافتن خودکار آخرین ساعت در دسترس از Tropical Tidbits"""
    now = datetime.now(timezone.utc)
    # بررسی ۴ ران اخیر
    for delta_h in [0, 6, 12, 18, 24]:
        check_time = now - timedelta(hours=delta_h)
        run_h = (check_time.hour // 6) * 6
        run_str = check_time.strftime("%Y%m%d") + f"{run_h:02d}"
        test_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_str}/gfs_mslp_pcpn_me_6.png"
        try:
            r = requests.head(test_url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                print(f"آخرین ران فعال Tropical Tidbits: {run_str}")
                return run_str
        except Exception:
            continue
    # حالت پیش‌فرض
    return now.strftime("%Y%m%d") + "06"


def process_tropical_packages():
    """دانلود تک‌تک فریم‌های Tropical Tidbits و تولید و ارسال انیمیشن متحرک"""
    run_str = find_latest_tropical_run()
    forecast_hours = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]

    packages = [
        {
            "pkg": "mslp_pcpn",
            "title": "بارش تجمیعی و فشار سطح دریا (MSLP & Precipitation)",
            "icon": "🌧",
        },
        {
            "pkg": "z500a",
            "title": "ارتفاع ژئوپتانسیل و تاوایی تراز ۵۰۰ هکتوپاسکال (500hPa Vorticity)",
            "icon": "🌀",
        },
    ]

    for p in packages:
        pkg = p["pkg"]
        pkg_title = p["title"]
        frames = []
        print(f"\nدر حال دریافت فریم‌های Tropical Tidbits برای: {pkg_title}...")

        for fh in forecast_hours:
            img_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_str}/gfs_{pkg}_me_{fh}.png"
            local_name = f"tropical_{pkg}_fh{fh}.png"
            try:
                r = requests.get(img_url, headers=HEADERS, timeout=20)
                if r.status_code == 200 and len(r.content) > 1000:
                    Path(local_name).write_bytes(r.content)
                    frames.append(Image.open(BytesIO(r.content)).convert("RGB"))
                    caption = (
                        f"{p['icon']} نقشه مدل GFS خاورمیانه و ایران\n"
                        f"📊 پارامتر: {pkg_title}\n"
                        f"⏱ پیش‌بینی {fh} ساعت آینده (ران {run_str})\n"
                        f"🌐 منبع: Tropical Tidbits"
                    )
                    send_media("sendPhoto", "photo", local_name, caption)
                else:
                    print(f"فریم {fh} یافت نشد.")
            except Exception as e:
                print(f"خطا در دانلود فریم {fh}: {e}")

        # ساخت فایل گیف متحرک بعد از ارسال همه فریم‌ها
        if len(frames) >= 3:
            gif_name = f"tropical_{pkg}_animated.gif"
            frames[0].save(
                gif_name,
                save_all=True,
                append_images=frames[1:],
                duration=600,
                loop=0,
                optimize=True,
            )
            gif_caption = (
                f"🎬 انیمیشن متحرک پیش‌بینی ۶۰ ساعته مدل GFS\n"
                f"{p['icon']} {pkg_title}\n"
                f"⏱ ران مدل: {run_str}"
            )
            send_media("sendAnimation", "animation", gif_name, gif_caption)
            print(f"انیمیشن {pkg} با موفقیت ارسال شد.")


def capture_all_web(playwright):
    """عکسبرداری از ECMWF، Yr.no و Foreca به ترتیب مشخص شده"""
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 920},
        user_agent=HEADERS["User-Agent"],
    )
    context.add_cookies([
        {"name": "temp", "value": "c", "domain": ".foreca.com", "path": "/"},
        {"name": "units", "value": "metric", "domain": ".foreca.com", "path": "/"},
    ])
    page = context.new_page()

    # ۱. متئوگرام‌های ECMWF (۵ ایستگاه)
    print("\n--- دریافت متئوگرام‌های ۱۰ روزه ECMWF ---")
    for item in ECMWF_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=65000, wait_until="networkidle")
            page.wait_for_timeout(8000)
            img_el = page.query_selector("img[src*='render-worker'], img[src*='opencharts'], .chart-container img")
            if img_el:
                img_el.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")

    # ۲. سایت Yr.no نروژ (۱۰ آیتم)
    print("\n--- دریافت پیش‌بینی‌های Yr.no نروژ ---")
    for item in YR_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(6000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")

    # ۳. سایت فورکا (۱۰ آیتم)
    print("\n--- دریافت پیش‌بینی‌های فورکا (Foreca) ---")
    for item in FORECA_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(6000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")

    browser.close()


def check_iran_met(state):
    """بررسی کانال تلگرام بدون تکرار"""
    username = "iran_met"
    print(f"\nدر حال بررسی کانال تلگرامی @{username}...")
    chan_state = state.get("channels", {}).get(username, {"last_id": 0, "seen_ids": []})
    last_id = int(chan_state.get("last_id", 0))
    seen_ids = list(chan_state.get("seen_ids", []))

    try:
        url = f"https://t.me/s/{username}"
        r = requests.get(url, headers=HEADERS, timeout=REQ_TIMEOUT)
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
                res_img = requests.get(p["img_url"], headers=HEADERS, timeout=REQ_TIMEOUT)
                Path(tmp_img).write_bytes(res_img.content)
                send_media("sendPhoto", "photo", tmp_img, caption)
                Path(tmp_img).unlink(missing_ok=True)
            except Exception as e:
                print(f"خطا در ارسال تصویر: {e}")
        else:
            send_text(caption)

        last_id = max(last_id, p["id"])
        if p["id"] not in seen_ids:
            seen_ids.append(p["id"])

    state.setdefault("channels", {})[username] = {
        "last_id": last_id,
        "seen_ids": seen_ids[-100:],
    }


def check_bulletins(state):
    """بررسی و دانلود روزانه فایل‌های PDF بدون تکرار"""
    print("\nدر حال بررسی بولتن‌های PDF سازمان هواشناسی...")
    b_state = state.get("bulletins", {})

    for b in BULLETINS:
        try:
            r = requests.get(b["url"], headers=HEADERS, timeout=REQ_TIMEOUT)
            if r.status_code != 200 or len(r.content) < 5000:
                continue

            file_hash = hashlib.sha256(r.content).hexdigest()
            saved_hash = b_state.get(b["id"])

            if file_hash != saved_hash:
                print(f"بولتن جدید دریافت شد: {b['title']}")
                pdf_path = Path(b["filename"])
                pdf_path.write_bytes(r.content)

                today_fa = datetime.now(TEHRAN_TZ).strftime("%Y/%m/%d")
                caption = f"{b['title']}\n📅 تاریخ انتشار: {today_fa}"
                send_media("sendDocument", "document", str(pdf_path), caption)

                b_state[b["id"]] = file_hash
                pdf_path.unlink(missing_ok=True)
            else:
                print(f"بولتن {b['title']} تغییر نکرده است.")
        except Exception as e:
            print(f"خطا در بولتن {b['title']}: {e}")

    state["bulletins"] = b_state


def main():
    print(f"=== شروع اجرای کامل سیستم پایش جوی ({datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}) ===")
    state = load_state()

    # ۱. تصویربرداری ۵ متئوگرام ECMWF
    with sync_playwright() as playwright:
        capture_all_web(playwright)

    # ۲. دانلود تک‌تک فریم‌ها و متحرک‌های Tropical Tidbits (بارش و تراز ۵۰۰)
    process_tropical_packages()

    # ۳. پست‌های کانال تلگرامی
    check_iran_met(state)

    # ۴. بولتن‌های بارش و دمای کشور
    check_bulletins(state)

    save_state(state)
    print("\n=== پایان اجرای موفق کلیه مراحل ===")


if __name__ == "__main__":
    main()
