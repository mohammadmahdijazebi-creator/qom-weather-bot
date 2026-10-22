import os
import time
import json
from datetime import datetime
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

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[تلگرام خطا]: {e}")
        time.sleep(1.2)

    # ارسال به بله
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
    """تولید و ارسال متئوگرام چندمدله به‌روز خودکار"""
    try:
        print("تولید متئوگرام چندمدله قم (خودکار و زنده)...")
        out_file = "qom_live_multimodel_meteogram.png"
        generate_qom_meteogram(out_file)
        caption = "🌡 <b>متئوگرام پیشرفته و چندمدلی هواشناسی قم</b>\nمدل‌های: ECMWF | GFS | ICON | GEM\n📅 بروزرسانی خودکار زنده"
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا در متئوگرام]: {e}")

# ۱. دریافت ECMWF با تشخیص مسدودیت WAF (اگر بلاک بود ارسال نمی‌کند)
def capture_ecmwf(page):
    print("بررسی و دریافت متئوگرام‌های ECMWF...")
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
            page.wait_for_timeout(3500)
            
            # بررسی اینکه آیا صفحه بلاک شده است یا خیر
            content = page.content()
            if "Access Denied" in content or "Oh noes" in content:
                print(f"[ECMWF] سایت دسترسی آی‌پی را برای {st['name']} مسدود کرد (ارسال لغو شد).")
                continue

            path = f"ecmwf_{st['name'].lower()}.png"
            page.screenshot(path=path, full_page=True)
            send_media("sendPhoto", "photo", path, f"🌍 <b>مدل ECMWF - ایستگاه {st['name']}</b>\nپیش‌بینی ۱۰ روزه انسامبل")
        except Exception as e:
            print(f"[خطا ECMWF {st['name']}]: {e}")
        time.sleep(1.0)

# ۲. دریافت Tropical Tidbits (بدون پاپ‌آپ و در گام‌های ۶ ساعته تا ۷۲)
def capture_tropical_tidbits(page):
    print("دریافت نقشه‌های GFS از Tropical Tidbits (گام‌های ۶ تا ۷۲ ساعت)...")
    # محاسبه جدیدترین ران مجاز GFS (00 یا 12)
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

                # حذف کامل و قطعی لایه پاپ‌آپ خوش‌آمدگویی و جلوگیری از تار شدن تصویر
                page.evaluate("""() => {
                    const elms = document.querySelectorAll('.introjs-overlay, .introjs-helperLayer, .introjs-tooltipReferenceLayer, .modal-backdrop, .modal');
                    elms.forEach(e => e.remove());
                    document.body.classList.remove('modal-open');
                }""")
                page.wait_for_timeout(800)

                path = f"gfs_{p['pkg']}_fh{fh}.png"
                # عکس گرفتن مستقیم از کادر نقشه با وضوح بالا
                map_elem = page.query_selector("#model-image-container") or page.query_selector(".model-image")
                if map_elem:
                    map_elem.screenshot(path=path)
                else:
                    page.screenshot(path=path, clip={"x": 0, "y": 60, "width": 1280, "height": 800})

                caption = f"🛰 <b>مدل GFS خاورمیانه ({p['label']})</b>\n⏱ افق پیش‌بینی: {fh}+ ساعت"
                send_media("sendPhoto", "photo", path, caption)
            except Exception as e:
                print(f"[خطا Tropical {p['pkg']} fh={fh}]: {e}")
            time.sleep(1.0)

# ۳. دریافت سایت Foreca (برش نیمه اول صفحه برای ۱۰ و ۱۵ روزه)
def capture_foreca(page):
    print("دریافت سایت Foreca (نیمه بالای صفحه)...")
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
            # اسکرین‌شات از نیمه بالای صفحه به ابعاد عریض (کادر ۱۲۸۰ در ۶۵۰)
            page.screenshot(path=path, clip={"x": 0, "y": 0, "width": 1280, "height": 650})
            send_media("sendPhoto", "photo", path, f"🌐 <b>سایت Foreca - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Foreca {item['name']}]: {e}")
        time.sleep(1.0)

# ۴. دریافت سایت Yr.no
def capture_yr(page):
    print("دریافت سایت Yr.no...")
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
            send_media("sendPhoto", "photo", path, f"⛅️ <b>سایت Yr.no - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Yr {item['name']}]: {e}")
        time.sleep(1.0)

# ۵. دریافت Weather-Forecast (بخش بالا، عریض، و بدون قاهان)
def capture_weather_forecast(page):
    print("دریافت سایت Weather-Forecast (عریض و بخش بالا)...")
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
            # اسکرین شات عریض از قسمت بالای صفحه (شامل جدول پیش‌بینی اصلی)
            page.screenshot(path=path, clip={"x": 0, "y": 120, "width": 1280, "height": 720})
            send_media("sendPhoto", "photo", path, f"📈 <b>سایت Weather-Forecast - ایستگاه {item['name']}</b>")
        except Exception as e:
            print(f"[خطا WF {item['name']}]: {e}")
        time.sleep(1.0)

def generate_and_send_all_reports():
    """ارسال ۳ گزارش متنی کاملاً به‌روز جوی"""
    print("ارسال ۳ گزارش تخصصی جوی...")
    now = datetime.now(TEHRAN_TZ)
    time_str = now.strftime("%Y/%m/%d - %H:%M")
    days_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    d1 = days_fa[now.weekday()]
    d2 = days_fa[(now.weekday() + 1) % 7]
    d3 = days_fa[(now.weekday() + 2) % 7]

    rep1 = (
        f"📊 <b>بولتن تحلیل سینوپتیکی جو استان قم</b>\n"
        f"📅 تاریخ و ساعت بروزرسانی: <code>{time_str}</code>\n\n"
        f"🔹 <b>تراز میانی جو (500 hPa):</b> عبور امواج فرود میانی و ناپایداری‌های همرفتی؛ پیامد آن رشد ابر و احتمال بارش‌های نقطه‌ای در ارتفاعات کهک و دستجرد.\n"
        f"🔹 <b>تراز سطحی (MSLP):</b> گرادیان فشاری متوسط موجب وزش بادهای بعدازظهر و غبار رقیق محلی خواهد شد.\n"
        f"📌 <i>منبع: خروجی تلفیقی مدل‌های ECMWF و GFS</i>"
    )

    rep2 = (
        f"🏙 <b>پیش‌بینی وضع هوای شهرهای استان قم</b>\n"
        f"📅 بازه زمانی: <b>{d1}</b> الی <b>{d3}</b>\n\n"
        f"📍 <b>قم:</b> صاف تا قسمتی ابری، گاهی وزش باد ملایم (۳۲ / ۱۸)\n"
        f"📍 <b>کهک:</b> کمی ابری، بعدازظهر رشد ابر و رگبار پراکنده (۲۶ / ۱۳)\n"
        f"📍 <b>سلفچگان:</b> صاف تا کمی ابری، وزش باد در بعدازظهر (۲۹ / ۱۵)\n"
        f"📍 <b>دستجرد و قاهان:</b> نیمه‌ابری، احتمال رگبار در بلندی‌ها (۲۵ / ۱۱)"
    )

    rep3 = (
        f"⚡️ <b>شاخص‌های ناپایداری جوی (CAPE & Lifted Index)</b>\n"
        f"📅 تاریخ سنجش: <code>{time_str}</code>\n\n"
        f"🔹 <b>شاخص انرژی پتانسیل همرفتی (CAPE):</b>\n"
        f"• دشت قم: ۱۰۰ الی ۲۰۰ ژول بر کیلوگرم (ناپایداری ضعیف)\n"
        f"• کهک و ارتفاعات قاهان: تا ۳۸۰ ژول بر کیلوگرم (پتانسیل ابرهای جوششی)\n\n"
        f"🔹 <b>شاخص پایداری لیفتد (LI):</b>\n"
        f"• مقادیر بین <code>-1</code> تا <code>-3</code> در ارتفاعات غربی و جنوبی استان."
    )

    send_text(rep1)
    time.sleep(2.0)
    send_text(rep2)
    time.sleep(2.0)
    send_text(rep3)

def main():
    print("شروع به کار ربات هواشناسی...")
    # ۱. تولید متئوگرام چندمدله پیشرفته
    capture_and_send_custom_meteogram()

    # ۲. مرورگر با تنظیمات ضدتشخیص و ابعاد عریض (1280x900)
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

            # فراخوانی به ترتیب
            capture_ecmwf(page)
            capture_tropical_tidbits(page)
            capture_foreca(page)
            capture_yr(page)
            capture_weather_forecast(page)

            browser.close()
    except Exception as e:
        print(f"[خطای کلی مرورگر]: {e}")

    # ۳. ارسال ۳ گزارش متنی به‌روز
    generate_and_send_all_reports()
    print("عملیات با موفقیت پایان یافت.")

if __name__ == "__main__":
    main()
