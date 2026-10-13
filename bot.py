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
# کلیدها و توکن‌های تلگرام و بله
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
# ۱. لیست صفحات هدف (ECMWF, Weather.us, Yr.no, Foreca)
# -------------------------------------------------------------
WEB_TARGETS = [
    # --- الف: نقشه‌های اختصاصی Weather.us (بارش تجمعی ایران و اروپا) ---
    {
        "name": "نقشه بارش تجمعی مدل GFS ایران (Weather.us)",
        "url": "https://weather.us/model-charts/standard/iran/accumulated-precipitation.html",
        "alt_url": "https://meteologix.com/ir/model-charts/standard/iran/accumulated-precipitation.html",
        "selector": ".model-chart-img, #chart-img, .chart-container",
        "wait_ms": 7000,
        "caption": "🌧 نقشه پیش‌بینی بارش تجمعی کل کشور ایران (مدل GFS)\n🌐 منبع: Weather.us / Meteologix",
        "file": "weather_us_gfs_iran.png",
        "enabled": True,
    },
    {
        "name": "نقشه بارش تجمعی مدل اروپایی ECMWF ایران (Weather.us)",
        "url": "https://weather.us/model-charts/euro/iran/m0_accumulated-precipitation.html",
        "alt_url": "https://meteologix.com/ir/model-charts/euro/iran/m0_accumulated-precipitation.html",
        "selector": ".model-chart-img, #chart-img, .chart-container",
        "wait_ms": 7000,
        "caption": "🌧 نقشه پیش‌بینی بارش تجمعی ایران (مدل اروپایی ECMWF IFS)\n🌐 منبع: Weather.us / Meteologix",
        "file": "weather_us_ecmwf_iran.png",
        "enabled": True,
    },

    # --- ب: متئوگرام‌های ۱۰ روزه ECMWF (۵ نقطه استان قم) ---
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - قم",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom",
        "selector": "img[src*='render-worker'], img[src*='opencharts'], .chart-container img",
        "wait_ms": 7000,
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قم",
        "file": "ecmwf_qom.png",
        "enabled": True,
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - کهک",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3938&lon=50.8643&station_name=Kahak",
        "selector": "img[src*='render-worker'], img[src*='opencharts'], .chart-container img",
        "wait_ms": 7000,
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: کهک",
        "file": "ecmwf_kahak.png",
        "enabled": True,
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - دستجرد",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "selector": "img[src*='render-worker'], img[src*='opencharts'], .chart-container img",
        "wait_ms": 7000,
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: دستجرد",
        "file": "ecmwf_dastjerd.png",
        "enabled": True,
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - سلفچگان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.4775&lon=50.4592&station_name=Salafchegan",
        "selector": "img[src*='render-worker'], img[src*='opencharts'], .chart-container img",
        "wait_ms": 7000,
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: سلفچگان",
        "file": "ecmwf_salafchegan.png",
        "enabled": True,
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF - قاهان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.7245&lon=50.2632&station_name=Qahan",
        "selector": "img[src*='render-worker'], img[src*='opencharts'], .chart-container img",
        "wait_ms": 7000,
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قاهان",
        "file": "ecmwf_qahan.png",
        "enabled": True,
    },

    # --- ج: فورکا (Foreca) ۱۰ و ۱۵ روزه ---
    {"name": "فورکا ۱۰ روزه قم", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم", "file": "foreca_qom_10d.png", "enabled": True},
    {"name": "فورکا ۱۵ روزه قم", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم", "file": "foreca_qom_15d.png", "enabled": True},
    {"name": "فورکا ۱۰ روزه کهک", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک", "file": "foreca_kahak_10d.png", "enabled": True},
    {"name": "فورکا ۱۵ روزه کهک", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - کهک", "file": "foreca_kahak_15d.png", "enabled": True},
    {"name": "فورکا ۱۰ روزه سلفچگان", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان", "file": "foreca_salaf_10d.png", "enabled": True},
    {"name": "فورکا ۱۵ روزه سلفچگان", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - سلفچگان", "file": "foreca_salaf_15d.png", "enabled": True},
    {"name": "فورکا ۱۰ روزه دستجرد", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - دستجرد", "file": "foreca_dast_10d.png", "enabled": True},
    {"name": "فورکا ۱۵ روزه دستجرد", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - دستجرد", "file": "foreca_dast_15d.png", "enabled": True},
    {"name": "فورکا ۱۰ روزه قاهان", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قاهان", "file": "foreca_qah_10d.png", "enabled": True},
    {"name": "فورکا ۱۵ روزه قاهان", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قاهان", "file": "foreca_qah_15d.png", "enabled": True},

    # --- د: سایت نروژ (Yr.no) جداول و نمودارها ---
    {"name": "جدول روزانه نروژ قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قم", "file": "yr_table_qom.png", "enabled": True},
    {"name": "نمودار ساعتی نروژ قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم", "file": "yr_graph_qom.png", "enabled": True},
    {"name": "جدول روزانه نروژ دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - دستجرد", "file": "yr_table_dastjerd.png", "enabled": True},
    {"name": "نمودار ساعتی نروژ دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد", "file": "yr_graph_dastjerd.png", "enabled": True},
    {"name": "جدول روزانه نروژ کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom%20Province/Kahak", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - کهک", "file": "yr_table_kahak.png", "enabled": True},
    {"name": "نمودار ساعتی نروژ کهک", "url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom%20Province/Kahak", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک", "file": "yr_graph_kahak.png", "enabled": True},
    {"name": "جدول روزانه نروژ سلفچگان", "url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - سلفچگان", "file": "yr_table_salaf.png", "enabled": True},
    {"name": "نمودار ساعتی نروژ سلفچگان", "url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان", "file": "yr_graph_salaf.png", "enabled": True},
    {"name": "جدول روزانه نروژ قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قاهان", "file": "yr_table_qahan.png", "enabled": True},
    {"name": "نمودار ساعتی نروژ قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان", "file": "yr_graph_qahan.png", "enabled": True},
]

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
    """ارسال همزمان به تلگرام و بله"""
    # ۱. تلگرام
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

    # ۲. بله
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


def fetch_tropical_loop(pkg_name, label_fa):
    """تولید حلقه انیمیشن متحرک گیف برای Tropical Tidbits"""
    print(f"\nدر حال پردازش پکیج تروپیکال: {pkg_name}...")
    forecast_hours = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]
    now_utc = datetime.now(timezone.utc)
    run_hour = (now_utc.hour // 6) * 6
    run_str = now_utc.strftime("%Y%m%d") + f"{run_hour:02d}"

    test_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_str}/gfs_{pkg_name}_me_6.png"
    try:
        r = requests.get(test_url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            prev_utc = now_utc - timedelta(hours=6)
            run_hour = (prev_utc.hour // 6) * 6
            run_str = prev_utc.strftime("%Y%m%d") + f"{run_hour:02d}"
    except Exception:
        pass

    frames = []
    gif_file = f"tropical_{pkg_name}_loop.gif"

    for fh in forecast_hours:
        img_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_str}/gfs_{pkg_name}_me_{fh}.png"
        try:
            res = requests.get(img_url, headers=HEADERS, timeout=15)
            if res.status_code == 200:
                frames.append(Image.open(BytesIO(res.content)).convert("RGB"))
            else:
                break
        except Exception:
            break

    if len(frames) >= 3:
        frames[0].save(
            gif_file,
            save_all=True,
            append_images=frames[1:],
            duration=500,
            loop=0,
            optimize=True,
        )
        caption = f"🎬 انیمیشن پیش‌بینی مدل عددی GFS تا ۶۰ ساعت آینده\n🌀 {label_fa}\n⏱ ران مدل: {run_str}"
        send_media("sendAnimation", "animation", gif_file, caption)
        print(f"انیمیشن {pkg_name} با موفقیت ارسال شد.")


def capture_web_targets(playwright):
    """عکسبرداری پیشرفته با تزریق کدهای ضدتشخیص ربات برای Weather.us و سایر سایت‌ها"""
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 920},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )

    # رفع خطای شناسایی ربات برای weather.us / کلودفلر
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
    """)

    context.add_cookies([
        {"name": "temp", "value": "c", "domain": ".foreca.com", "path": "/"},
        {"name": "units", "value": "metric", "domain": ".foreca.com", "path": "/"},
    ])
    page = context.new_page()

    for item in WEB_TARGETS:
        if not item.get("enabled", True):
            continue

        print(f"در حال عکسبرداری: {item['name']}...")
        target_url = item["url"]
        taken = False

        try:
            res = page.goto(target_url, timeout=60000, wait_until="networkidle")
            
            # در صورتی که weather.us بلوکه کرد، از دامنه رزرو meteologix بارگذاری می‌شود
            if ("Access Denied" in page.content() or (res and res.status == 403)) and item.get("alt_url"):
                print(f"استفاده از آدرس بدون محدودیت جایگزین: {item['alt_url']}")
                page.goto(item["alt_url"], timeout=60000, wait_until="networkidle")

            page.wait_for_timeout(item.get("wait_ms", 5000))

            selector = item.get("selector")
            if selector:
                el = page.query_selector(selector)
                if el:
                    el.screenshot(path=item["file"])
                    taken = True

            if not taken:
                page.screenshot(path=item["file"])

            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")

    browser.close()


def check_iran_met(state):
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
        print(f"خطا در دسترسی به @{username}: {e}")
        return

    now_tehran = datetime.now(TEHRAN_TZ)
    today_start = now_tehran.replace(hour=0, minute=0, second=0, microsecond=0)

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

        time_el = msg.find("time")
        if last_id == 0 and time_el and time_el.get("datetime"):
            try:
                p_time = datetime.fromisoformat(time_el.get("datetime")).astimezone(TEHRAN_TZ)
                if p_time < today_start:
                    continue
            except Exception:
                pass

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
                print(f"خطا در ارسال تصویر {p['id']}: {e}")
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
                print(f"بولتن جدید یافت شد: {b['title']}")
                pdf_path = Path(b["filename"])
                pdf_path.write_bytes(r.content)

                today_fa = datetime.now(TEHRAN_TZ).strftime("%Y/%m/%d")
                caption = f"{b['title']}\n📅 تاریخ انتشار: {today_fa}"
                send_media("sendDocument", "document", str(pdf_path), caption)

                b_state[b["id"]] = file_hash
                pdf_path.unlink(missing_ok=True)
            else:
                print(f"بولتن {b['title']} قبلاً ارسال شده است.")
        except Exception as e:
            print(f"خطا در پردازش بولتن {b['title']}: {e}")

    state["bulletins"] = b_state


def main():
    print(f"=== اجرای مانیتور جامع هواشناسی ({datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}) ===")
    state = load_state()

    # ۱. تصویربرداری صفحات وب (شامل نقشه‌های ایران weather.us، متئوگرام‌های اروپایی، فورکا و نروژ)
    with sync_playwright() as playwright:
        capture_web_targets(playwright)

    # ۲. تولید انیمیشن‌های GFS تروپیکال تیدبیتس
    fetch_tropical_loop("mslp_pcpn", "بارش تجمیعی و فشار سطح دریا (MSLP & PCP)")
    fetch_tropical_loop("z500a", "ارتفاع ژئوپتانسیل و تاوایی تراز ۵۰۰ هکتوپاسکال (500hPa)")

    # ۳. دریافت پیام‌های جدید کانال @iran_met
    check_iran_met(state)

    # ۴. دریافت بولتن‌های PDF روزانه بارش و دما
    check_bulletins(state)

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز عملیات ===")


if __name__ == "__main__":
    main()
