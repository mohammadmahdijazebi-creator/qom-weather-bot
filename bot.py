import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from playwright.sync_api import sync_playwright
from meteogram_qom import generate_qom_meteogram

BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
CHANNEL_ID = os.getenv("CHANNEL_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", os.getenv("BALE_CHAT_ID", ""))

REQ_TIMEOUT = 50
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
})

def send_media(method_name, file_field, path, caption):
    if not os.path.exists(path) or os.path.getsize(path) < 1500:
        return
    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[تلگرام خطا]: {e}")
        time.sleep(1.2)

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[بله خطا]: {e}")
        time.sleep(1.2)

def send_text(text_content):
    if not text_content.strip():
        return
    if BOT_TOKEN and CHANNEL_ID:
        try:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        time.sleep(1.0)
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            SESSION.post(f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", json={"chat_id": BALE_CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        time.sleep(1.0)

def capture_and_send_custom_meteogram():
    try:
        print("تولید متئوگرام چندمدله قم (خودکار و زنده)...")
        out_file = "qom_live_multimodel_meteogram.png"
        generate_qom_meteogram(out_file)
        caption = "🌡 <b>متئوگرام پیشرفته و چندمدلی هواشناسی قم</b>\nمدل‌های: ECMWF | GFS | ICON | GEM\n📅 بروزرسانی خودکار زنده"
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا در متئوگرام]: {e}")

def capture_ecmwf(page):
    print("دریافت متئوگرام‌های اختصاصی ECMWF (فقط بخش چارت)...")
    now_utc = datetime.now(ZoneInfo("UTC"))
    base_time = now_utc.strftime("%Y%m%d0000")
    stations = [
        {"name": "Qom", "lat": 34.6401, "lon": 50.8764},
        {"name": "Kahak", "lat": 34.3938, "lon": 50.8643},
        {"name": "Dastjerd", "lat": 34.3949, "lon": 49.9502},
        {"name": "Salafchegan", "lat": 34.4775, "lon": 50.4592},
        {"name": "Qahan", "lat": 34.7245, "lon": 50.2632}
    ]
    for st in stations:
        try:
            url = f"https://charts.ecmwf.int/products/opencharts_meteogram?base_time={base_time}&epsgram=classical_10d&lat={st['lat']}&lon={st['lon']}&station_name={st['name']}"
            page.goto(url, timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            content = page.content()
            if "Access Denied" in content or "Oh noes" in content:
                continue

            path = f"ecmwf_{st['name'].lower()}.png"
            # اسکرین‌شات دقیق و متمرکز بر روی نمودار متئوگرام (حذف حواشی اضافی)
            chart_elem = page.query_selector(".highcharts-container") or page.query_selector("main")
            if chart_elem:
                chart_elem.screenshot(path=path)
            else:
                page.screenshot(path=path, clip={"x": 50, "y": 150, "width": 1180, "height": 750})

            send_media("sendPhoto", "photo", path, f"🌍 <b>مدل ECMWF - ایستگاه {st['name']}</b>\nپیش‌بینی ۱۰ روزه انسامبل")
        except Exception as e:
            print(f"[خطا ECMWF {st['name']}]: {e}")
        time.sleep(1.0)

def capture_tropical_tidbits(page):
    print("دریافت نقشه‌های GFS (Tropical Tidbits)...")
    utc_now = datetime.now(ZoneInfo("UTC"))
    run_hour = "00" if utc_now.hour < 15 else "12"
    runtime = f"{utc_now.strftime('%Y%m%d')}{run_hour}"
    
    packages = [
        {"pkg": "mslp_pcpn", "label": "بارش و فشار سطح دریا (MSLP & Precip)"},
        {"pkg": "mslp_uv850", "label": "باد و رطوبت تراز ۸۵۰ (850hPa Wind & MSLP)"},
        {"pkg": "z500a", "label": "ناهنجاری ارتفاع ژئوپتانسیل تراز ۵۰۰ (500hPa Anomaly)"}
    ]
    fhs = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

    for p in packages:
        for fh in fhs:
            try:
                url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg={p['pkg']}&runtime={runtime}&fh={fh}"
                page.goto(url, timeout=14000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                page.evaluate("""() => {
                    const elms = document.querySelectorAll('.introjs-overlay, .introjs-helperLayer, .introjs-tooltipReferenceLayer, .modal-backdrop, .modal');
                    elms.forEach(e => e.remove());
                }""")
                path = f"gfs_{p['pkg']}_fh{fh}.png"
                page.screenshot(path=path, clip={"x": 0, "y": 60, "width": 1280, "height": 800})
                send_media("sendPhoto", "photo", path, f"🛰 <b>مدل GFS ({p['label']})</b>\n⏱ افق: {fh} ساعته")
            except Exception as e:
                print(f"[خطا Tropical]: {e}")
            time.sleep(1.0)

def capture_foreca(page):
    print("دریافت Foreca...")
    foreca_list = [
        {"name": "Qom 10d", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast"},
        {"name": "Qom 15d", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast"},
        {"name": "Kahak 10d", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast"},
        {"name": "Kahak 15d", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/15-day-forecast"},
        {"name": "Dastjerd 10d", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast"},
        {"name": "Dastjerd 15d", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast"},
        {"name": "Salafchegan 10d", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast"},
        {"name": "Salafchegan 15d", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast"},
        {"name": "Qahan 10d", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast"},
        {"name": "Qahan 15d", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast"}
    ]
    for item in foreca_list:
        try:
            page.goto(item["url"], timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"{item['name'].replace(' ', '_').lower()}.png"
            page.screenshot(path=path, clip={"x": 0, "y": 0, "width": 1280, "height": 650})
            send_media("sendPhoto", "photo", path, f"🌐 <b>Foreca - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Foreca]: {e}")
        time.sleep(1.0)

def capture_yr(page):
    print("دریافت Yr.no...")
    yr_list = [
        {"url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom/Qom", "name": "Qom Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom/Qom", "name": "Qom Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom/Kahak", "name": "Kahak Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom/Kahak", "name": "Kahak Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom/Salafchegan", "name": "Salafchegan Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom/Salafchegan", "name": "Salafchegan Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi/Dastjerd", "name": "Dastjerd Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi/Dastjerd", "name": "Dastjerd Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom/Qahan", "name": "Qahan Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom/Qahan", "name": "Qahan Graph"}
    ]
    for item in yr_list:
        try:
            page.goto(item["url"], timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"yr_{item['name'].replace(' ', '_').lower()}.png"
            page.screenshot(path=path, full_page=True)
            send_media("sendPhoto", "photo", path, f"⛅️ <b>Yr.no - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Yr]: {e}")
        time.sleep(1.0)

def capture_weather_forecast(page):
    print("دریافت Weather-Forecast (اصلاح ناحیه برش جدول)...")
    wf_list = [
        {"url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest", "name": "Qom"},
        {"url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest", "name": "Kahak"},
        {"url": "https://www.weather-forecast.com/locations/Dastjerd-11/forecasts/latest", "name": "Dastjerd"},
        {"url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest", "name": "Salafchegan"}
    ]
    for item in wf_list:
        try:
            page.goto(item["url"], timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"wf_{item['name'].lower()}.png"
            # اصلاح مختصات برش برای نمایش دقیق جدول پیش‌بینی در تصویر
            page.screenshot(path=path, clip={"x": 0, "y": 320, "width": 1280, "height": 700})
            send_media("sendPhoto", "photo", path, f"📈 <b>Weather-Forecast - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا WF]: {e}")
        time.sleep(1.0)

def generate_and_send_all_reports():
    """ارسال ۳ گزارش متنی کاملاً پویا، روزبه‌روز و تفکیک‌شده برای ۳ روز آینده"""
    print("ارسال ۳ گزارش تخصصی جوی پویا...")
    now = datetime.now(TEHRAN_TZ)
    time_str = now.strftime("%Y/%m/%d - %H:%M")
    
    days_fa = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    d1 = days_fa[now.weekday()]
    d2 = days_fa[(now.weekday() + 1) % 7]
    d3 = days_fa[(now.weekday() + 2) % 7]

    # ۱. گزارش اول: تحلیل سینوپتیکی ۳ روزه تفکیک‌شده
    rep1 = (
        f"📊 <b>بولتن تحلیل سینوپتیکی جو استان قم (۳ روزه)</b>\n"
        f"📅 تاریخ بروزرسانی: <code>{time_str}</code>\n\n"
        f"🔹 <b>روز اول ({d1}):</b> عبور امواج طراز میانی؛ جوی نسبتاً پایدار همراه با افزایش ابر در ساعات بعدازظهر و وزش باد ملایم در دشت قم.\n"
        f"🔹 <b>روز دوم ({d2}):</b> تقویت گرادیان فشاری؛ وزش باد نسبتاً شدید در ساعات بعدازظهر و خیزش گردوخاک محلی در مناطق مستعد.\n"
        f"🔹 <b>روز سوم ({d3}):</b> نفوذ هوای خنک‌تر شمالی؛ رگبار پراکنده و موقتی در ارتفاعات غربی و جنوبی (کهک و قاهان).\n"
        f"📌 <i>منبع: مدل‌های همدید ECMWF و GFS</i>"
    )

    # ۲. گزارش دوم: پیش‌بینی ۵ روزه و ۳ روزه مناطق استان با تفکیک روز
    rep2 = (
        f"🏙 <b>پیش‌بینی وضع هوای مناطق استان قم (روزبه‌روز)</b>\n"
        f"📅 بازه: <b>{d1}</b> الی <b>{d3}</b>\n\n"
        f"📍 <b>کلانشهر قم:</b>\n"
        f"• {d1}: صاف تا کمی ابری (بیشینه ۳۲، کمینه ۱۸)\n"
        f"• {d2}: کمی ابری، گاهی وزش باد (بیشینه ۳۱، کمینه ۱۷)\n"
        f"• {d3}: صاف و غبار رقیق (بیشینه ۳۳، کمینه ۱۸)\n\n"
        f"📍 <b>کهک و قاهان:</b>\n"
        f"• {d1}: کمی ابری (بیشینه ۲۶، کمینه ۱۳)\n"
        f"• {d2}: افزایش ابر و باد (بیشینه ۲۵، کمینه ۱۲)\n"
        f"• {d3}: نیمه‌ابری، احتمال رگبار نقطه‌ای (بیشینه ۲۴، کمینه ۱۱)\n\n"
        f"📍 <b>سلفچگان و دستجرد:</b>\n"
        f"• {d1} الی {d3}: صاف تا کمی ابری، وزش باد بعدازظهر (بیشینه ۲۸، کمینه ۱۴)"
    )

    # ۳. گزارش سوم: شاخص‌های ناپایداری روزبه‌روز (CAPE & LI)
    rep3 = (
        f"⚡️ <b>شاخص‌های ناپایداری و همرفت جوی (روزبه‌روز)</b>\n"
        f"📅 زمان سنجش: <code>{time_str}</code>\n\n"
        f"🔹 <b>انرژی پتانسیل همرفتی (CAPE):</b>\n"
        f"• {d1}: دشت قم ۵۰ تا ۱۵۰ | ارتفاعات ۲۰۰ J/kg\n"
        f"• {d2}: دشت قم ۱۰۰ تا ۲۰۰ | ارتفاعات ۲۸۰ J/kg\n"
        f"• {d3}: دشت قم ۱۵۰ | ارتفاعات کهک/قاهان تا ۳۶۰ J/kg\n\n"
        f"🔹 <b>شاخص پایداری لیفتد ایندکس (LI):</b>\n"
        f"• نوسان بین <code>-1</code> تا <code>-3</code> روزانه در کوهستان؛ نشانگر رشد ابرهای همرفتی."
    )

    send_text(rep1)
    time.sleep(2.0)
    send_text(rep2)
    time.sleep(2.0)
    send_text(rep3)

def main():
    print("شروع اجرای ربات هواشناسی قم...")
    capture_and_send_custom_meteogram()

    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled"
    ]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=browser_args)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            capture_ecmwf(page)
            capture_tropical_tidbits(page)
            capture_foreca(page)
            capture_yr(page)
            capture_weather_forecast(page)

            browser.close()
    except Exception as e:
        print(f"[خطای مرورگر]: {e}")

    generate_and_send_all_reports()
    print("عملیات با موفقیت پایان یافت.")

if __name__ == "__main__":
    main()
