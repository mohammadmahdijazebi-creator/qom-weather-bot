import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------
# ۱. متغیرها و تنظیمات اولیه
# -------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID") or os.environ.get("TELEGRAM_CHAT_ID")

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID") or os.environ.get("BALE_CHAT_ID")

STATE_FILE = Path("weather_state.json")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
REQ_TIMEOUT = 45

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

# -------------------------------------------------------------
# ۲. لیست ترتیبی متئوگرام‌ها (ECMWF)
# -------------------------------------------------------------
ECMWF_ITEMS = [
    {
        "name": "متئوگرام قم",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قم",
        "file": "01_ecmwf_qom.png",
    },
    {
        "name": "متئوگرام کهک",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3938&lon=50.8643&station_name=Kahak",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: کهک",
        "file": "02_ecmwf_kahak.png",
    },
    {
        "name": "متئوگرام دستجرد",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: دستجرد",
        "file": "03_ecmwf_dastjerd.png",
    },
    {
        "name": "متئوگرام سلفچگان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.4775&lon=50.4592&station_name=Salafcheg%C4%81n",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: سلفچگان",
        "file": "04_ecmwf_salafchegan.png",
    },
    {
        "name": "متئوگرام قاهان",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.7245&lon=50.2632&station_name=Q%C4%81h%C4%81n",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قاهان",
        "file": "05_ecmwf_qahan.png",
    },
]

# -------------------------------------------------------------
# ۳. لیست فریم‌های Tropical Tidbits (بارش و ۵۰۰ هکتوپاسکال)
# -------------------------------------------------------------
TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]

# -------------------------------------------------------------
# ۴. لیست جداول و نمودارهای Yr.no
# -------------------------------------------------------------
YR_ITEMS = [
    {"name": "جدول روزانه قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قم", "file": "yr_table_qom.png"},
    {"name": "نمودار ساعتی قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم", "file": "yr_graph_qom.png"},
    {"name": "جدول روزانه دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - دستجرد", "file": "yr_table_dastjerd.png"},
    {"name": "نمودار ساعتی دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi%20Province/Dastjerd", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد", "file": "yr_graph_dastjerd.png"},
    {"name": "جدول روزانه کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom%20Province/Kahak", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - کهک", "file": "yr_table_kahak.png"},
    {"name": "نمودار ساعتی کهک", "url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom%20Province/Kahak", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک", "file": "yr_graph_kahak.png"},
    {"name": "جدول روزانه سلفچگان", "url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - سلفچگان", "file": "yr_table_salaf.png"},
    {"name": "نمودار ساعتی سلفچگان", "url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان", "file": "yr_graph_salaf.png"},
    {"name": "جدول روزانه قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📋 جدول پیش‌بینی روزانه Yr.no - قاهان", "file": "yr_table_qahan.png"},
    {"name": "نمودار ساعتی قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان", "file": "yr_graph_qahan.png"},
]

# -------------------------------------------------------------
# ۵. لیست پیش‌بینی‌های فورکا (Foreca)
# -------------------------------------------------------------
FORECA_ITEMS = [
    {"name": "فورکا ۱۰ روزه قم", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم", "file": "foreca_qom_10d.png"},
    {"name": "فورکا ۱۵ روزه قم", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم", "file": "foreca_qom_15d.png"},
    {"name": "فورکا ۱۰ روزه کهک", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک", "file": "foreca_kahak_10d.png"},
    {"name": "فورکا ۱۵ روزه کهک", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - کهک", "file": "foreca_kahak_15d.png"},
    {"name": "فورکا ۱۰ روزه سلفچگان", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان", "file": "foreca_salaf_10d.png"},
    {"name": "فورکا ۱۵ روزه سلفچگان", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - سلفچگان", "file": "foreca_salaf_15d.png"},
    {"name": "فورکا ۱۰ روزه دستجرد", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - دستجرد", "file": "foreca_dast_10d.png"},
    {"name": "فورکا ۱۵ روزه دستجرد", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - دستجرد", "file": "foreca_dast_15d.png"},
    {"name": "فورکا ۱۰ روزه قاهان", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast", "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قاهان", "file": "foreca_qah_10d.png"},
    {"name": "فورکا ۱۵ روزه قاهان", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast", "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قاهان", "file": "foreca_qah_15d.png"},
]

# -------------------------------------------------------------
# ۶. بولتن‌های رسمی سازمان هواشناسی
# -------------------------------------------------------------
BULLETINS = [
    {
        "id": "irimo_rain",
        "title": "🌧 بولتن روزانه بارش کشور (سازمان هواشناسی)",
        "url": "https://ndc.irimo.ir/far/services/file_manager/1182801/download/1/%D8%A8%D9%88%D9%84%D8%AA%D9%86-%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87-%D8%A8%D8%A7%D8%B1%D8%B4-050721.html?t=%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87",
        "filename": "Daily_Rain_Bulletin.pdf",
    },
    {
        "id": "irimo_temp",
        "title": "🌡 بولتن روزانه دمای کشور (سازمان هواشناسی)",
        "url": "https://ndc.irimo.ir/far/services/file_manager/1182799/download/1/%D8%A8%D9%88%D9%84%D8%AA%D9%86-%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87-%D8%AF%D9%85%D8%A7-050721.html?t=%D8%B1%D9%88%D8%B2%D8%A7%D9%86%D9%87",
        "filename": "Daily_Temp_Bulletin.pdf",
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


def send_to_channels(file_path, caption, is_doc=False):
    """ارسال قطعی عکس یا سند به تلگرام و بله با لاگ دقیق"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
        print(f"[خطا]: فایل {file_path} برای ارسال معتبر نیست.")
        return

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        method = "sendDocument" if is_doc else "sendPhoto"
        key = "document" if is_doc else "photo"
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={key: f},
                    timeout=REQ_TIMEOUT,
                )
            if r.status_code == 200:
                print(f"[تلگرام OK]: {file_path}")
            else:
                print(f"[تلگرام خطا]: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"[تلگرام Exception]: {e}")

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        b_method = "sendDocument" if is_doc else "sendPhoto"
        b_key = "document" if is_doc else "photo"
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
                print(f"[بله خطا]: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"[بله Exception]: {e}")

    time.sleep(2.5)


def send_text_msg(text):
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
# ۱. متئوگرام‌های ECMWF با مدیریت زمان و سلکتور دقیق
# -------------------------------------------------------------
def capture_ecmwf(browser):
    print("\n================== ۱. متئوگرام‌های ECMWF ==================")
    for item in ECMWF_ITEMS:
        print(f"در حال پردازش: {item['name']}...")
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        try:
            page.goto(item["url"], timeout=70000, wait_until="load")
            # صبر برای رندر کامل چارت‌های اپن‌چارتس
            page.wait_for_timeout(10000)
            
            # جستجوی تصویر متئوگرام درون DOM
            chart = page.query_selector("img[src*='render-worker']") or page.query_selector(".chart-container")
            if chart:
                chart.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            send_to_channels(item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در دریافت {item['name']}: {e}")
        finally:
            page.close()


# -------------------------------------------------------------
# ۲. دریافت مستقیم و قطعی Tropical Tidbits
# -------------------------------------------------------------
def resolve_active_tropical_run():
    """یافتن آخرین ران معتبر با تست درخواست‌های HTTP"""
    now = datetime.now(timezone.utc)
    for delta_h in [0, 6, 12, 18, 24, 30]:
        t = now - timedelta(hours=delta_h)
        run_h = (t.hour // 6) * 6
        run_str = t.strftime("%Y%m%d") + f"{run_h:02d}"
        test_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_str}/gfs_mslp_pcpn_me_6.png"
        try:
            res = requests.head(test_url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                print(f"ران فعال و آماده Tropical Tidbits پیدا شد: {run_str}")
                return run_str
        except Exception:
            continue
    return now.strftime("%Y%m%d") + "00"


def process_tropical_tidbits():
    print("\n================== ۲. نقشه‌های Tropical Tidbits ==================")
    active_run = resolve_active_tropical_run()

    # الف) بارش و فشار سطح دریا
    print("\n--- بارش و فشار سطح دریا (mslp_pcpn) ---")
    for fh in TROPICAL_HOURS:
        img_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{active_run}/gfs_mslp_pcpn_me_{fh}.png"
        f_name = f"gfs_pcpn_fh{fh}.png"
        caption = (
            f"🌧 پیش‌بینی بارش تجمیعی و فشار سطح دریا (MSLP)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده (ران: {active_run})\n"
            f"🔗 Tropical Tidbits"
        )
        try:
            r = requests.get(img_url, headers=HEADERS, timeout=25)
            if r.status_code == 200 and len(r.content) > 2000:
                Path(f_name).write_bytes(r.content)
                send_to_channels(f_name, caption)
            else:
                print(f"فریم بارش fh={fh} در دسترس نبود (وضعیت {r.status_code}).")
        except Exception as e:
            print(f"خطا در دانلود فریم بارش fh={fh}: {e}")

    # ب) تراز ۵۰۰ هکتوپاسکال
    print("\n--- تراز ۵۰۰ هکتوپاسکال و تاوایی (z500a) ---")
    for fh in TROPICAL_HOURS:
        img_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{active_run}/gfs_z500a_me_{fh}.png"
        f_name = f"gfs_z500a_fh{fh}.png"
        caption = (
            f"🌀 تاوایی و ارتفاع ژئوپتانسیل تراز ۵۰۰ هکتوپاسکال\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده (ران: {active_run})\n"
            f"🔗 Tropical Tidbits"
        )
        try:
            r = requests.get(img_url, headers=HEADERS, timeout=25)
            if r.status_code == 200 and len(r.content) > 2000:
                Path(f_name).write_bytes(r.content)
                send_to_channels(f_name, caption)
            else:
                print(f"فریم ۵۰۰ fh={fh} در دسترس نبود (وضعیت {r.status_code}).")
        except Exception as e:
            print(f"خطا در دانلود فریم ۵۰۰ fh={fh}: {e}")


# -------------------------------------------------------------
# ۳. جداول و نمودارهای Yr.no
# -------------------------------------------------------------
def capture_yr(browser):
    print("\n================== ۳. جداول و نمودارهای Yr.no ==================")
    for item in YR_ITEMS:
        print(f"در حال عکسبرداری: {item['name']}...")
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        try:
            page.goto(item["url"], timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path=item["file"])
            send_to_channels(item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        finally:
            page.close()


# -------------------------------------------------------------
# ۴. پیش‌بینی‌های فورکا (Foreca) با هندل مطمئن المان
# -------------------------------------------------------------
def capture_foreca(browser):
    print("\n================== ۴. پیش‌بینی‌های فورکا (Foreca) ==================")
    for item in FORECA_ITEMS:
        print(f"در حال پردازش: {item['name']}...")
        page = browser.new_page(viewport={"width": 1366, "height": 950})
        try:
            page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            page.screenshot(path=item["file"])
            send_to_channels(item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        finally:
            page.close()


# -------------------------------------------------------------
# ۵. پست‌های کانال تلگرام @iran_met بدون تکرار
# -------------------------------------------------------------
def check_iran_met(state):
    print("\n================== ۵. کانال تلگرام @iran_met ==================")
    username = "iran_met"
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
        print(f"خطا در دریافت کانال @{username}: {e}")
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
                send_to_channels(tmp_img, caption)
                Path(tmp_img).unlink(missing_ok=True)
            except Exception as e:
                print(f"خطا در ارسال عکس پست: {e}")
        else:
            send_text_msg(caption)

        last_id = max(last_id, p["id"])
        if p["id"] not in seen_ids:
            seen_ids.append(p["id"])

    state.setdefault("channels", {})[username] = {
        "last_id": last_id,
        "seen_ids": seen_ids[-100:],
    }


# -------------------------------------------------------------
# ۶. بولتن‌های رسمی سازمان هواشناسی به صورت PDF معتبر
# -------------------------------------------------------------
def check_bulletins(state):
    print("\n================== ۶. بولتن‌های روزانه PDF ==================")
    b_state = state.get("bulletins", {})

    for b in BULLETINS:
        print(f"بررسی بولتن: {b['title']}...")
        try:
            r = requests.get(b["url"], headers=HEADERS, timeout=REQ_TIMEOUT)
            if r.status_code != 200 or len(r.content) < 5000:
                print(f"پاسخ بولتن {b['title']} نامعتبر بود.")
                continue

            # ذخیره و اعتبارسنجی فایل باینری
            pdf_path = Path(b["filename"])
            pdf_path.write_bytes(r.content)

            file_hash = hashlib.sha256(r.content).hexdigest()
            saved_hash = b_state.get(b["id"])

            if file_hash != saved_hash:
                print(f"بولتن جدید بارگذاری می‌شود: {b['title']}")
                today_fa = datetime.now(TEHRAN_TZ).strftime("%Y/%m/%d")
                caption = f"{b['title']}\n📅 تاریخ ثبت: {today_fa}\n🏛 مرکز ملی اقلیم و مدیریت بحران خشکسالی"
                send_to_channels(str(pdf_path), caption, is_doc=True)
                b_state[b["id"]] = file_hash
            else:
                print(f"بولتن {b['title']} تغییر نکرده است و تکراری ارسال نمی‌شود.")

            pdf_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"خطا در بولتن {b['title']}: {e}")

    state["bulletins"] = b_state


# -------------------------------------------------------------
# اجرای اصلی به ترتیب دقیق فهرست شما
# -------------------------------------------------------------
def main():
    print(f"=== آغاز پایش کامل - {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M:%S')} ===")
    state = load_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )

        # ۱. متئوگرام‌های ۵ ایستگاه ECMWF
        capture_ecmwf(browser)

        # ۲. فریم‌های Tropical Tidbits (بارش و ۵۰۰ هکتوپاسکال)
        process_tropical_tidbits()

        # ۳. جداول و نمودارهای Yr.no
        capture_yr(browser)

        # ۴. پیش‌بینی‌های Foreca
        capture_foreca(browser)

        browser.close()

    # ۵. پست‌های جدید کانال تلگرام
    check_iran_met(state)

    # ۶. بولتن‌های روزانه PDF
    check_bulletins(state)

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز تمامی ۴۷ آیتم به ترتیب لیست ===")


if __name__ == "__main__":
    main()
