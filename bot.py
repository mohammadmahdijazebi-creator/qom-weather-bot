import os
import sys
import time
import json
import asyncio
import subprocess
import requests
from playwright.async_api import async_playwright

# --- دریافت متغیرهای محیطی از سکرت‌های گیت‌هاب ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "").strip()
BALE_CHAT_ID = os.environ.get("BALE_CHAT_ID", "").strip()

STATE_FILE = "weather_state.json"

def check_credentials():
    print("--- بررسی وضعیت سکرت‌ها ---")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("[+] تنظیمات تلگرام شناسایی شد.")
    else:
        print("[!] هشدار: TELEGRAM_BOT_TOKEN یا TELEGRAM_CHAT_ID در گیت‌هاب ست نشده است!")

    if BALE_BOT_TOKEN and BALE_CHAT_ID:
        print("[+] تنظیمات بله شناسایی شد.")
    else:
        print("[!] هشدار: BALE_BOT_TOKEN یا BALE_CHAT_ID در گیت‌هاب ست نشده است!")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] خطا در ذخیره وضعیت: {e}")

# --- توابع ارسال تلگرام ---
def send_telegram_photo(photo_path, caption=""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] تلگرام ارسال نشد: سکرت‌ها تعریف نشده‌اند.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            res = requests.post(url, files=files, data=data, timeout=60)
            if res.status_code == 200:
                print(f"[+] عکس به تلگرام ارسال شد: {photo_path}")
                return True
            else:
                print(f"[!] خطای سرور تلگرام: {res.text}")
                return False
    except Exception as e:
        print(f"[!] خطای ارتباطی با تلگرام: {e}")
        return False

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        res = requests.post(url, data=data, timeout=60)
        return res.status_code == 200
    except Exception as e:
        print(f"[!] خطای پیام متنی تلگرام: {e}")
        return False

# --- توابع ارسال پیام‌رسان بله ---
def send_bale_photo(photo_path, caption=""):
    if not BALE_BOT_TOKEN or not BALE_CHAT_ID:
        print("[!] بله ارسال نشد: سکرت‌ها تعریف نشده‌اند.")
        return False
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": BALE_CHAT_ID, "caption": caption}
            res = requests.post(url, files=files, data=data, timeout=60)
            if res.status_code == 200:
                print(f"[+] عکس به بله ارسال شد: {photo_path}")
                return True
            else:
                print(f"[!] خطای سرور بله: {res.text}")
                return False
    except Exception as e:
        print(f"[!] خطای ارتباطی با بله: {e}")
        return False

def send_bale_message(text):
    if not BALE_BOT_TOKEN or not BALE_CHAT_ID:
        return False
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    try:
        data = {"chat_id": BALE_CHAT_ID, "text": text}
        res = requests.post(url, data=data, timeout=60)
        return res.status_code == 200
    except Exception as e:
        print(f"[!] خطای پیام متنی بله: {e}")
        return False

def broadcast_photo(photo_path, caption=""):
    send_telegram_photo(photo_path, caption)
    send_bale_photo(photo_path, caption)

def broadcast_message(text):
    send_telegram_message(text)
    send_bale_message(text)

# --- تصویربرداری با مرورگر ---
async def capture_yr_qom(context):
    print("--- ۱. دریافت پیش‌بینی Yr.no قم ---")
    page = await context.new_page()
    try:
        url = "https://www.yr.no/en/forecast/daily-table/2-117248/Iran/Qom/Qom"
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await asyncio.sleep(4)
        output = "yr_qom.png"
        await page.set_viewport_size({"width": 1280, "height": 1000})
        await page.screenshot(path=output)
        caption = "وضعیت جوی و جدول پیش‌بینی دمایی قم از منبع نروژی (Yr.no)"
        broadcast_photo(output, caption)
    except Exception as e:
        print(f"[!] خطا در دریافت تصویر Yr.no: {e}")
    finally:
        await page.close()

async def capture_tropical_tidbits(context):
    print("--- ۲. دریافت نقشه‌های Tropical Tidbits ---")
    page = await context.new_page()
    try:
        url = "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=mideast&pkg=mslp_pcpn"
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(6)
        output = "tropical_gfs_mslp.png"
        el = await page.query_selector("img.model-image")
        if el:
            await el.screenshot(path=output)
        else:
            await page.screenshot(path=output)
        caption = "مدل GFS - نقشه‌های بارش و فشار سطح دریا خاورمیانه و ایران (Tropical Tidbits)"
        broadcast_photo(output, caption)
    except Exception as e:
        print(f"[!] خطا در ثبت Tropical Tidbits: {e}")
    finally:
        await page.close()

async def capture_weather_forecast_qom(context):
    print("--- ۳. دریافت اطلاعات weather-forecast.com ---")
    page = await context.new_page()
    try:
        url = "https://www.weather-forecast.com/locations/Qom/forecasts/latest"
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)
        output = "weather_forecast_qom.png"
        await page.set_viewport_size({"width": 1300, "height": 900})
        await page.screenshot(path=output)
        caption = "جدول جامع پیش‌بینی وضع هوا و پارامترهای جوی قم (Weather-Forecast)"
        broadcast_photo(output, caption)
    except Exception as e:
        print(f"[!] خطا در دریافت Weather-Forecast: {e}")
    finally:
        await page.close()

def check_iran_met_channel():
    print("--- ۴. بررسی و فیلتر کانال تلگرام @iran_met ---")
    try:
        url = "https://t.me/s/iran_met"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200 and ("قم" in res.text or "مرکزی" in res.text):
            print("[+] نام استان قم یا مناطق همجوار در کانال @iran_met رصد شد.")
    except Exception as e:
        print(f"[!] خطا در بررسی کانال: {e}")

def get_bulletin_text():
    lines = [
        "🔹 **بولتن تحلیلی و وضعیت سینوپتیکی استان قم** 🔹",
        "",
        "📍 **وضعیت مناطق استان (قم، کهک، سلفچگان، دستجرد، کهندان):**",
        "• آسمان غالباً صاف تا کمی ابری، در ساعات بعدازظهر گاهی وزش باد محلی.",
        "• روند تدریجی نوسانات دما متناسب با الگوی پاییزه.",
        "• مناطق مرتفع و کوهستانی (کهندان و دستجرد): شب‌های سردتر و هوای مه‌آلود یا پاییزی مطبوع.",
        "• دشت قم و سلفچگان: جوی پایدار، تداوم هوای خنک شبانه و اعتدال روزانه.",
        "",
        "⚠️ کلیه تغییرات سامانه‌های مدیترانه‌ای و الگوهای تراز ۵۰۰ هکتوپاسکال به دقت رصد و اطلاع‌رسانی می‌شود.",
        "🆔 هواشناسی قم - علی جزبی"
    ]
    return "\n".join(lines)

def send_synoptic_analysis():
    print("--- ۵. ارسال بولتن تحلیلی و سینوپتیکی ---")
    msg = get_bulletin_text()
    broadcast_message(msg)

# --- اجرای نهایی متئوگرام چندمدله ---
def run_custom_meteogram():
    print("=== ۸. تولید و ارسال متئوگرام چندمدله قم (گام نهایی) ===")
    meteogram_script = "meteogram_qom.py"
    if os.path.exists(meteogram_script):
        try:
            print(f"[*] اجرای اسکریپت {meteogram_script}...")
            result = subprocess.run([sys.executable, meteogram_script], capture_output=True, text=True, check=True)
            print(result.stdout)
            print("[+] اسکریپت متئوگرام با موفقیت اجرا شد.")
        except subprocess.CalledProcessError as e:
            print(f"[!] خطا در اجرای {meteogram_script}: {e.stderr}")
    else:
        print(f"[!] فایل {meteogram_script} یافت نشد.")

    meteogram_img = "qom_live_multimodel_meteogram.png"
    if not os.path.exists(meteogram_img):
        meteogram_img = "qom_10day_multimodel_meteogram.png"

    if os.path.exists(meteogram_img):
        caption = "متئوگرام چندمدله ۱۰ روزه استان قم (ECMWF, GFS, ICON, GEM)\nIran, Qom - Ali Jazebi"
        broadcast_photo(meteogram_img, caption)
    else:
        print("[!] هیچ فایل تصویری از متئوگرام یافت نشد.")

async def main():
    print("==========================================")
    print("شروع فرآیند مانیتورینگ خودکار هواشناسی قم")
    print("==========================================")

    # گام ۰: چک کردن وجود سکرت‌ها
    check_credentials()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        await capture_yr_qom(context)
        await capture_tropical_tidbits(context)
        await capture_weather_forecast_qom(context)

        await browser.close()

    check_iran_met_channel()
    send_synoptic_analysis()

    # گام نهایی
    run_custom_meteogram()

    print("==========================================")
    print("کلیه مراحل ربات با موفقیت به پایان رسید.")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
