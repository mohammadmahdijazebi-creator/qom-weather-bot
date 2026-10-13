import os
import time
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------
# اطلاعات اتصال به ربات‌ها (تلگرام و بله)
# -------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID") or os.environ.get("TELEGRAM_CHAT_ID")

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID") or os.environ.get("BALE_CHAT_ID")

# -------------------------------------------------------------
# لیست سایت‌های هدف برای اسکرین‌شات
# (از اینجا می‌توانی سایتی را کم، زیاد یا با enabled: False خاموش کنی)
# -------------------------------------------------------------
TARGETS = [
    # ۱. متئوگرام ۱۰ روزه ECMWF
    {
        "id": "ecmwf_meteogram",
        "name": "متئوگرام ۱۰ روزه ECMWF",
        "enabled": True,
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom",
        "selector": "img[src*='render-worker'], img[src*='opencharts'], .chart-container img",
        "wait_ms": 8000,
        "caption": "متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF 🌤\n(منبع: charts.ecmwf.int)",
        "file": "ecmwf.png",
    },
    # ۲. پیش‌بینی سایت Weather-Forecast برای قم
    {
        "id": "weather_forecast_qom",
        "name": "ودرفورکست قم",
        "enabled": True,
        "url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest",
        "selector": None,
        "scroll_y": 380,
        "wait_ms": 5000,
        "caption": "پیش‌بینی وضع هوای قم (منبع: Weather-Forecast) 🌦",
        "file": "weather_forecast.png",
    },
    # ۳. فورکا (Foreca) - شهرهای استان قم
    {
        "id": "foreca_qom_15d",
        "name": "فورکا - قم (۱۵ روزه)",
        "enabled": True,
        "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast",
        "selector": None,
        "wait_ms": 6000,
        "caption": "پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم ☀️",
        "file": "foreca_qom_15d.png",
    },
    {
        "id": "foreca_qom_10d",
        "name": "فورکا - قم (۱۰ روزه)",
        "enabled": True,
        "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast",
        "selector": None,
        "wait_ms": 5000,
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم ☀️",
        "file": "foreca_qom_10d.png",
    },
    {
        "id": "foreca_kahak",
        "name": "فورکا - کهک (۱۰ روزه)",
        "enabled": True,
        "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast",
        "selector": None,
        "wait_ms": 5000,
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک ☀️",
        "file": "foreca_kahak.png",
    },
    {
        "id": "foreca_salafchegan",
        "name": "فورکا - سلفچگان (۱۰ روزه)",
        "enabled": True,
        "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast",
        "selector": None,
        "wait_ms": 5000,
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان ☀️",
        "file": "foreca_salafchegan.png",
    },
    {
        "id": "foreca_kohandan",
        "name": "فورکا - کهندان (۱۰ روزه)",
        "enabled": True,
        "url": "https://www.foreca.com/100126883/Kohand%C4%81n-Qom-Province-Iran/10-day-forecast",
        "selector": None,
        "wait_ms": 5000,
        "caption": "پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهندان ☀️",
        "file": "foreca_kohandan.png",
    },
    # ۴. سایت Yr.no - نمودارهای گرافیکی (Graph)
    {
        "id": "yr_graph_qom",
        "name": "نمودار ساعتی Yr.no - قم",
        "enabled": True,
        "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom",
        "selector": None,
        "wait_ms": 6000,
        "caption": "نمودار پیش‌بینی ساعتی وضعیت جوی قم (منبع: Yr.no) 📉",
        "file": "yr_graph_qom.png",
    },
    {
        "id": "yr_graph_kahak",
        "name": "نمودار ساعتی Yr.no - کهک",
        "enabled": True,
        "url": "https://www.yr.no/en/forecast/graph/2-128338/Iran/Qom%20Province/Kahak",
        "selector": None,
        "wait_ms": 6000,
        "caption": "نمودار پیش‌بینی ساعتی وضعیت جوی کهک (منبع: Yr.no) 📉",
        "file": "yr_graph_kahak.png",
    },
    {
        "id": "yr_graph_dastjerd",
        "name": "نمودار ساعتی Yr.no - دستجرد",
        "enabled": True,
        "url": "https://www.yr.no/en/forecast/graph/2-138402/Iran/Qom%20Province/Dastjerd",
        "selector": None,
        "wait_ms": 6000,
        "caption": "نمودار پیش‌بینی ساعتی وضعیت جوی دستجرد (منبع: Yr.no) 📉",
        "file": "yr_graph_dastjerd.png",
    },
    {
        "id": "yr_graph_qahan",
        "name": "نمودار ساعتی Yr.no - قاهان",
        "enabled": True,
        "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n",
        "selector": None,
        "wait_ms": 6000,
        "caption": "نمودار پیش‌بینی ساعتی وضعیت جوی قاهان (منبع: Yr.no) 📉",
        "file": "yr_graph_qahan.png",
    },
]


def send_to_telegram(media_path, caption):
    if not (BOT_TOKEN and CHANNEL_ID):
        return False
    if not os.path.exists(media_path):
        return False

    is_anim = media_path.lower().endswith(".gif") or media_path.lower().endswith(".mp4")
    endpoint = "sendAnimation" if is_anim else "sendPhoto"
    file_field = "animation" if is_anim else "photo"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{endpoint}"

    try:
        with open(media_path, "rb") as f:
            res = requests.post(
                url,
                data={"chat_id": CHANNEL_ID, "caption": caption},
                files={file_field: f},
                timeout=45,
            )
        if res.status_code == 200:
            print(f"[Telegram] با موفقیت ارسال شد: {Path(media_path).name}")
            return True
        else:
            print(f"[Telegram Error] {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Telegram Exception]: {e}")
    return False


def send_to_bale(media_path, caption):
    if not (BALE_BOT_TOKEN and BALE_CHANNEL_ID):
        return False
    if not os.path.exists(media_path):
        return False

    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
    try:
        with open(media_path, "rb") as f:
            res = requests.post(
                url,
                data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                files={"photo": f},
                timeout=45,
            )
        if res.status_code == 200:
            print(f"[Bale] با موفقیت ارسال شد: {Path(media_path).name}")
            return True
        else:
            print(f"[Bale Error] {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Bale Exception]: {e}")
    return False


def broadcast(media_path, caption):
    send_to_telegram(media_path, caption)
    send_to_bale(media_path, caption)
    time.sleep(2)  # وقفه جهت رعایت فاصله پیام‌ها


def generate_tropical_tidbits_animation():
    """دانلود خودکار فریم‌های مدل GFS خاورمیانه و ایجاد گیف متحرک پیش‌بینی ۱۲۰ ساعته"""
    print("\n--- در حال ساخت انیمیشن Tropical Tidbits (مدل GFS) ---")
    forecast_hours = [0, 6, 12, 18, 24, 30, 36, 42, 48, 60, 72, 84, 96, 108, 120]
    now_utc = datetime.now(timezone.utc)
    run_hour = (now_utc.hour // 6) * 6
    run_date_str = now_utc.strftime("%Y%m%d") + f"{run_hour:02d}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # تست در دسترس بودن ران فعلی، در غیر این صورت استفاده از ران ۶ ساعت قبل
    test_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_date_str}/gfs_mslp_pcpn_me_0.png"
    try:
        r_test = requests.get(test_url, headers=headers, timeout=10)
        if r_test.status_code != 200:
            prev_utc = now_utc - timedelta(hours=6)
            run_hour = (prev_utc.hour // 6) * 6
            run_date_str = prev_utc.strftime("%Y%m%d") + f"{run_hour:02d}"
    except Exception:
        pass

    frames = []
    anim_filename = "tropical_tidbits_loop.gif"

    for fh in forecast_hours:
        img_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_date_str}/gfs_mslp_pcpn_me_{fh}.png"
        try:
            r = requests.get(img_url, headers=headers, timeout=15)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                frames.append(img)
            else:
                break
        except Exception as e:
            print(f"خطا در دریافت فریم {fh}: {e}")
            break

    if len(frames) >= 3:
        frames[0].save(
            anim_filename,
            save_all=True,
            append_images=frames[1:],
            duration=450,
            loop=0,
            optimize=True,
        )
        print("انیمیشن Tropical Tidbits با موفقیت ایجاد شد.")
        return anim_filename
    return None


def capture_targets(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )

    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )

    # کوکی‌های لازم برای اینکه فورکا مقادیر را حتماً به سانتیگراد نشان دهد
    context.add_cookies([
        {"name": "temp", "value": "c", "domain": ".foreca.com", "path": "/"},
        {"name": "units", "value": "metric", "domain": ".foreca.com", "path": "/"},
    ])

    page = context.new_page()

    for item in TARGETS:
        if not item.get("enabled", True):
            continue

        print(f"\nدر حال پردازش: {item['name']}...")
        try:
            page.goto(item["url"], timeout=65000, wait_until="networkidle")
            wait_time = item.get("wait_ms", 5000)
            page.wait_for_timeout(wait_time)

            if "scroll_y" in item:
                page.evaluate(f"window.scrollBy(0, {item['scroll_y']})")
                page.wait_for_timeout(1500)

            selector = item.get("selector")
            saved = False
            if selector:
                element = page.query_selector(selector)
                if element:
                    element.screenshot(path=item["file"])
                    saved = True

            if not saved:
                page.screenshot(path=item["file"])

            broadcast(item["file"], item["caption"])

        except Exception as e:
            print(f"خطا در پردازش {item['name']}: {e}")

    browser.close()


def main():
    print(f"=== شروع اجرای فرآیند مانیتورینگ هواشناسی ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    
    # ۱. تصویربرداری از صفحات وب
    with sync_playwright() as playwright:
        capture_targets(playwright)

    # ۲. ساخت و ارسال انیمیشن ۵ روزه Tropical Tidbits
    anim_file = generate_tropical_tidbits_animation()
    if anim_file and os.path.exists(anim_file):
        broadcast(
            anim_file,
            "🎬 انیمیشن کامل پیش‌بینی ۵ روزه مدل عددی GFS (بارش و تراز دریا)\nمنبع: Tropical Tidbits",
        )

    print("\n=== تمام مراحل با موفقیت به پایان رسید ===")


if __name__ == "__main__":
    main()
