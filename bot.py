# -*- coding: utf-8 -*-
"""
Qom Weather Bot - نسخه ماژولار
برای اضافه کردن سایت/شهر جدید: فقط در بخش CONFIG یک خط کپی کن.
"""
import os, time, json, re
from urllib.parse import quote
from playwright.sync_api import sync_playwright
import requests

# ==============================================================
# ⚙️⚙️⚙️  تنظیمات - فقط اینجا را دست بزن  ⚙️⚙️⚙️
# هر سایت = یک بلوک. برای اضافه کردن، یک بلوک را کپی و تغییر بده.
# ==============================================================
CONFIG = [
    # ---------- نسخه ۱۰ روزه فورکا (اصلاح شد) ----------
    dict(name="Foreca - پیش‌بینی ۱۰ روزه قم",
         url="https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast",
         wait=8),

    # ---------- yr.no (۴ شهر) ----------
    dict(name="Yr.no - پیش‌بینی روزانه قم",
         url="https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom",
         wait=8),
    dict(name="Yr.no - پیش‌بینی روزانه قاهان",
         url="https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n",
         wait=8),
    dict(name="Yr.no - پیش‌بینی روزانه دستجرد",
         url="https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd",
         wait=8),
    dict(name="Yr.no - پیش‌بینی روزانه کهک",
         url="https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom%20Province/Kahak",
         wait=8),

    # ---------- weather.us (روند بلندمدت Euro مدل) ----------
    dict(name="weather.us - روند دمای قم",
         url="https://weather.us/forecast/119208-qom/xltrend/euro/temperature",
         wait=10),
    dict(name="weather.us - روند بارش قم",
         url="https://weather.us/forecast/119208-qom/xltrend/euro/precipitation",
         wait=10),
    dict(name="weather.us - روند سرعت باد قم",
         url="https://weather.us/forecast/119208-qom/xltrend/euro/mean-wind-speed",
         wait=10),
    dict(name="weather.us - نقشه تندبادها (Gusts)",
         url="https://weather.us/model-charts/euro/qom/gusts-3h/20261010-1800z.html",
         wait=10),
]
# ==============================================================
# ⚠️ توجه: سه پیام ثابت (ECMWF، Tropical Tidbits، weather.com)
#    پایین‌تر به شکل ثابت ارسال می‌شوند تا چیزی به هم نخورد.
# ==============================================================

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en','fa']});
const orig = navigator.permissions.query;
navigator.permissions.query = (p) => p.name === 'notifications'
  ? Promise.resolve({state: Notification.permission}) : orig(p);
"""

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# ---------- پیام‌های ثابت (بدون تغییر) ----------
FIXED_MESSAGES = [
    dict(
        caption="منعودگاه ۱۰ روزه ENS مدل اروپایی ECMWF ⛅\n(سایت: charts.ecmwf.int)",
        url="https://charts.ecmwf.int/opencharts-api/v1/products/opencharts_meteogram/ten_days_even_ensemble_forecasts_meteogram?lon=50.9&lat=34.7&station_id=111208",
    ),
    dict(
        caption="مدل GFS بارش و فشار - خاورمیانه و ایران (Tropical Tidbits) 🌧️",
        url="https://www.tropicaltidbits.com/analysis/models/gfs.png",
    ),
    dict(
        caption="پیش‌بینی ۱۴ روز هوای قم (weather.com) ☀️",
        url="https://weather.com/weather/tenday/l/Qom%2C+Qom+Province%2C+Iran",
    ),
]


def send_photo(photo_path: str, caption: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as f:
        r = requests.post(url, data={"chat_id": CHANNEL_ID, "caption": caption[:1024]},
                          files={"photo": f}, timeout=120)
    try:
        res = r.json()
    except Exception:
        res = {"ok": False, "description": r.text[:300]}
    if not res.get("ok"):
        print(f"--> خطا در ارسال: {res}")
    else:
        print(f"--> ارسال شد: {caption.splitlines()[0][:50]}")


def shoot(page, out_name: str, wait_s: int) -> str:
    page.wait_for_load_state("domcontentloaded", timeout=90000)
    time.sleep(wait_s)  # فرصت برای لود کردن نمودارها
    page.screenshot(path=out_name, full_page=False)
    return out_name


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("!! BOT_TOKEN یا CHANNEL_ID تعریف نشده است.")
        return
    ts = str(int(time.time()))
    os.makedirs("shots", exist_ok=True)

    # ۱) ارسال پیام‌های ثابت (مثل قبل)
    for m in FIXED_MESSAGES:
        out = f"shots/{ts}_fixed_{m['url'][:20].replace('/', '_')}.png"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                      user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
            page = ctx.new_page()
            page.add_init_script(STEALTH_JS)
            try:
                page.goto(m["url"], timeout=90000, wait_until="domcontentloaded")
                time.sleep(8)
                page.screenshot(path=out)
            except Exception as e:
                print(f"!! تصویر ثابت نشد: {m['url']} -> {e}")
            finally:
                browser.close()
        if os.path.exists(out):
            send_photo(out, m["caption"])

    # ۲) ارسال سایت‌های CONFIG (بخش قابل ویرایش)
    for item in CONFIG:
        out = f"shots/{ts}_{re.sub(r'[^0-9a-zA-Z]', '_', item['name'])[:40]}.png"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = browser.new_context(viewport={"width": 1280, "height": 1000},
                                      user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
            page = ctx.new_page()
            page.add_init_script(STEALTH_JS)
            try:
                page.goto(item["url"], timeout=90000, wait_until="domcontentloaded")
                shoot(page, out, item["wait"])
                print(f"OK: {item['name']}")
            except Exception as e:
                print(f"!! نشد: {item['name']} -> {e}")
            finally:
                browser.close()
        if os.path.exists(out):
            send_photo(out, item["name"])

    print("پایان اجرا ✅")


if __name__ == "__main__":
    main()
