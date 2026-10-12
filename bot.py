import os
import time
import requests
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")


def send_to_telegram(photo_path, caption):
    if not os.path.exists(photo_path):
        print(f"File not found: {photo_path}")
        return

    if BOT_TOKEN and CHANNEL_ID:
        is_animation = photo_path.lower().endswith(".gif") or photo_path.lower().endswith(".mp4")
        endpoint = "sendAnimation" if is_animation else "sendPhoto"
        file_key = "animation" if is_animation else "photo"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{endpoint}"
        try:
            with open(photo_path, "rb") as media_file:
                payload = {"chat_id": CHANNEL_ID, "caption": caption}
                files = {file_key: media_file}
                response = requests.post(url, data=payload, files=files, timeout=60)
                if response.status_code == 200:
                    print(f"Telegram sent successfully: {caption[:30]}...")
                else:
                    print(f"Telegram API Error: {response.text}")
        except Exception as e:
            print(f"Failed to send to Telegram: {e}")


def send_to_bale(photo_path, caption):
    if not os.path.exists(photo_path):
        return

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, "rb") as media_file:
                payload = {"chat_id": BALE_CHANNEL_ID, "caption": caption}
                files = {"photo": media_file}
                response = requests.post(url, data=payload, files=files, timeout=60)
                if response.status_code == 200:
                    print(f"Bale sent successfully: {caption[:30]}...")
                else:
                    print(f"Bale API Error: {response.text}")
        except Exception as e:
            print(f"Failed to send to Bale: {e}")


def broadcast(media_path, caption):
    send_to_telegram(media_path, caption)
    send_to_bale(media_path, caption)


def generate_tropical_tidbits_animation():
    """دانلود تمام فریم‌های مدل GFS خاورمیانه و ساخت انیمیشن GIF باکیفیت"""
    print("Generating Tropical Tidbits animation...")
    # دریافت آخرین ساعت‌های پیش‌بینی (تا ۱۲۰ ساعت آینده به فواصل ۶ یا ۱۲ ساعته)
    forecast_hours = [0, 6, 12, 18, 24, 30, 36, 42, 48, 60, 72, 84, 96, 108, 120]
    
    # برای بدست آوردن آخرین ران معتبر، ساعت کنونی را بر مبنای UTC تخمین می‌زنیم
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    # ساعت ران‌های استاندارد GFS: 00, 06, 12, 18
    run_hour = (now_utc.hour // 6) * 6
    run_date_str = now_utc.strftime("%Y%m%d") + f"{run_hour:02d}"

    frames = []
    first_frame_path = "tropical_tidbits_single.png"
    animation_path = "tropical_tidbits_loop.gif"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # در صورت عدم وجود ران جاری، به ران قبلی برمی‌گردد
    base_run_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_date_str}/gfs_mslp_pcpn_me_0.png"
    test_req = requests.get(base_run_url, headers=headers, timeout=10)
    if test_req.status_code != 200:
        # برگشت به ۶ ساعت قبل‌تر
        from datetime import timedelta
        prev_utc = now_utc - timedelta(hours=6)
        run_hour = (prev_utc.hour // 6) * 6
        run_date_str = prev_utc.strftime("%Y%m%d") + f"{run_hour:02d}"

    for fh in forecast_hours:
        img_url = f"https://www.tropicaltidbits.com/analysis/models/gfs/{run_date_str}/gfs_mslp_pcpn_me_{fh}.png"
        try:
            r = requests.get(img_url, headers=headers, timeout=15)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                frames.append(img)
                if len(frames) == 1:
                    img.save(first_frame_path)
            else:
                break
        except Exception as e:
            print(f"Error fetching frame {fh}: {e}")
            break

    if frames:
        frames[0].save(
            animation_path,
            save_all=True,
            append_images=frames[1:],
            duration=400,
            loop=0,
            optimize=True
        )
        print("Tropical Tidbits animation created successfully.")
        return first_frame_path, animation_path
    return None, None


def run_all(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    )

    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # تنظیم کوکی پیش‌فرض Foreca جهت اجبار نمایش دما برحسب سلسیوس
    context.add_cookies([
        {"name": "temp", "value": "c", "domain": ".foreca.com", "path": "/"},
        {"name": "units", "value": "metric", "domain": ".foreca.com", "path": "/"}
    ])

    page = context.new_page()

    # ۱. متئوگرام ۱۰ روزه ECMWF
    try:
        print("1. Capturing ECMWF Meteogram...")
        ecmwf_url = "https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.64&lon=50.86&station_name=Qom"
        page.goto(ecmwf_url, timeout=60000)
        page.wait_for_timeout(8000)
        chart_img = page.query_selector("img[src*='render-worker'], img[src*='opencharts'], .chart-container img")
        if chart_img:
            chart_img.screenshot(path="ecmwf.png")
        else:
            page.screenshot(path="ecmwf.png")
        broadcast("ecmwf.png", "متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF 🌤\n(سایت: charts.ecmwf.int)")
    except Exception as e:
        print(f"Error ECMWF: {e}")

    # ۲. پیش‌بینی وضع هوای قم Weather-Forecast
    try:
        print("2. Capturing Weather-Forecast...")
        page.goto("https://www.weather-forecast.com/locations/Qom/forecasts/latest", timeout=60000)
        page.wait_for_timeout(4000)
        page.evaluate("window.scrollBy(0, 380)")
        page.wait_for_timeout(2000)
        page.screenshot(path="weather_forecast.png")
        broadcast("weather_forecast.png", "پیش‌بینی وضع هوای قم (منبع: Weather-Forecast) 🌦")
    except Exception as e:
        print(f"Error Weather-Forecast: {e}")

    # ۳. صفحات Foreca (قم ۱۵ روزه و ۱۰ روزه شهرهای استان با واحد سلسیوس)
    foreca_targets = [
        {"name": "قم (۱۵ روزه)", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast", "file": "foreca_qom_15d.png"},
        {"name": "قم (۱۰ روزه)", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", "file": "foreca_qom_10d.png"},
        {"name": "کهک (۱۰ روزه)", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast", "file": "foreca_kahak.png"},
        {"name": "سلفچگان (۱۰ روزه)", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast", "file": "foreca_salafchegan.png"},
        {"name": "کهندان (۱۰ روزه)", "url": "https://www.foreca.com/100126883/Kohand%C4%81n-Qom-Province-Iran/10-day-forecast", "file": "foreca_kohandan.png"},
    ]

    for item in foreca_targets:
        try:
            print(f"Capturing Foreca: {item['name']}...")
            page.goto(item["url"], timeout=60000)
            page.wait_for_timeout(5000)
            page.screenshot(path=item["file"])
            broadcast(item["file"], f"پیش‌بینی فورکا (Foreca) - {item['name']} ☀️ (واحد: °C)")
        except Exception as e:
            print(f"Error Foreca {item['name']}: {e}")

    # ۴. سایت Yr.no (جداول متنی)
    yr_locations = [
        {"name": "قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "file": "yr_qom.png"},
        {"name": "قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "file": "yr_qahan.png"},
        {"name": "دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-138402/Iran/Qom%20Province/Dastjerd", "file": "yr_dastjerd.png"},
        {"name": "کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-128338/Iran/Qom%20Province/Kahak", "file": "yr_kahak.png"}
    ]
    for loc in yr_locations:
        try:
            print(f"Capturing Yr.no Table ({loc['name']})...")
            page.goto(loc["url"], timeout=60000)
            page.wait_for_timeout(5000)
            page.screenshot(path=loc["file"])
            broadcast(loc["file"], f"پیش‌بینی وضعیت جوی {loc['name']} (منبع: Yr.no) 🌧")
        except Exception as e:
            print(f"Error Yr.no Table {loc['name']}: {e}")

    # ۵. سایت Yr.no (نمودارهای گرافیکی)
    yr_graphs = [
        {"name": "قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "file": "yr_graph_qom.png"},
        {"name": "قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "file": "yr_graph_qahan.png"},
        {"name": "دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-138402/Iran/Qom%20Province/Dastjerd", "file": "yr_graph_dastjerd.png"},
        {"name": "کهک", "url": "https://www.yr.no/en/forecast/graph/2-128338/Iran/Qom%20Province/Kahak", "file": "yr_graph_kahak.png"}
    ]
    for g in yr_graphs:
        try:
            print(f"Capturing Yr.no Graph ({g['name']})...")
            page.goto(g["url"], timeout=60000)
            page.wait_for_timeout(6000)
            page.screenshot(path=g["file"])
            broadcast(g["file"], f"نمودار پیش‌بینی ساعتی Yr.no ({g['name']}) 📉")
        except Exception as e:
            print(f"Error Yr.no Graph {g['name']}: {e}")

    # ۶. تروپیکال تیدبیتس (اسکرین شات مستقیم صفحه + ساخت انیمیشن کامل)
    try:
        print("Capturing Tropical Tidbits page...")
        page.goto("https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn", timeout=60000)
        page.wait_for_timeout(6000)
        try:
            page.evaluate("""() => {
                const closeBtn = document.querySelector('.modal-close, .introjs-skipbutton, button[aria-label="Close"], .close');
                if (closeBtn) closeBtn.click();
                const modal = document.querySelector('.modal, .introjs-tooltipReferenceLayer, .introjs-helperLayer');
                if (modal) modal.remove();
            }""")
            page.wait_for_timeout(1000)
        except:
            pass
        page.screenshot(path="tropical.png")
        broadcast("tropical.png", "مدل GFS بارش و فشار - خاورمیانه و ایران (Tropical Tidbits) 🌧")
    except Exception as e:
        print(f"Error Tropical Tidbits web capture: {e}")

    browser.close()

    # ۷. ساخت و ارسال انیمیشن تمام فریم‌های Tropical Tidbits
    try:
        single_pic, anim_gif = generate_tropical_tidbits_animation()
        if anim_gif and os.path.exists(anim_gif):
            broadcast(anim_gif, "🎬 انیمیشن کامل پیش‌بینی ۵ روزه مدل عددی GFS (بارش و فشار) خاورمیانه و ایران 🌀")
    except Exception as e:
        print(f"Error processing Tropical Tidbits animation: {e}")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run_all(playwright)
