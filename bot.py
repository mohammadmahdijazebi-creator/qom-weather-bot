import os
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

def send_to_telegram(photo_path, caption):
    if not os.path.exists(photo_path):
        print(f"File not found: {photo_path}")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {'chat_id': CHANNEL_ID, 'caption': caption}
            files = {'photo': photo}
            response = requests.post(url, data=payload, files=files, timeout=40)
            if response.status_code == 200:
                print(f"Sent successfully: {caption}")
            else:
                print(f"Telegram API Error: {response.text}")
    except Exception as e:
        print(f"Failed to send {caption}: {e}")

def capture_charts(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context(
        viewport={'width': 1366, 'height': 900},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )
    page = context.new_page()

    # 1. ECMWF Meteogram (10 Days)
    try:
        print("Capturing ECMWF Meteogram...")
        page.goto("https://charts.ecmwf.int/products/opencharts_meteogram?base_time=202610100000&lat=34.6401&lon=50.8764&station_name=Qom", timeout=60000)
        page.wait_for_timeout(7000)
        img_element = page.query_selector("img[src*='opencharts.ecmwf.int'], .chart-container img, img.opencharts-image")
        if img_element:
            img_element.screenshot(path="meteogram.png")
        else:
            page.screenshot(path="meteogram.png", full_page=False)
        send_to_telegram("meteogram.png", "منمودگاه ۱۰ روزه ENS مدل اروپایی ECMWF 🌤\n(سایت: charts.ecmwf.int)")
    except Exception as e:
        print(f"Error ECMWF: {e}")

    # 2. Foreca 10-day forecast
    try:
        print("Capturing Foreca...")
        page.goto("https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", timeout=60000)
        page.wait_for_timeout(6000)
        # بستن احتمالی پاپ‌آپ کوکی
        try:
            page.click("button:has-text('Accept')", timeout=3000)
        except:
            pass
        page.screenshot(path="foreca.png", full_page=False)
        send_to_telegram("foreca.png", "پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم ☀️")
    except Exception as e:
        print(f"Error Foreca: {e}")

    # 3. Yr.no Forecasts (Qom, Qahan, Dastjerd, Kahak)
    yr_locations = [
        {"name": "قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "file": "yr_qom.png"},
        {"name": "قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "file": "yr_qahan.png"},
        {"name": "دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-138402/Iran/Qom%20Province/Dastjerd", "file": "yr_dastjerd.png"},
        {"name": "کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-129362/Iran/Qom%20Province/Kahak", "file": "yr_kahak.png"}
    ]

    for loc in yr_locations:
        try:
            print(f"Capturing Yr.no ({loc['name']})...")
            page.goto(loc["url"], timeout=60000)
            page.wait_for_timeout(5000)
            page.screenshot(path=loc["file"], full_page=False)
            send_to_telegram(loc["file"], f"پیش‌بینی وضعیت جوی {loc['name']} (منبع: Yr.no) 🌧")
        except Exception as e:
            print(f"Error Yr.no {loc['name']}: {e}")

    browser.close()

# 4. Tropical Tidbits (با استفاده از دانلود مستقیم جهت عبور از مسدودی)
def fetch_tropical_tidbits():
    print("Fetching Tropical Tidbits GFS...")
    url = "https://www.tropicaltidbits.com/analysis/models/gfs/latest/gfs_mslp_pcpn_frzn_mideast_1.png"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.tropicaltidbits.com/"
    }
    try:
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            with open("tropical.png", "wb") as f:
                f.write(res.content)
            send_to_telegram("tropical.png", "مدل GFS بارش و فشار - خاورمیانه و ایران (Tropical Tidbits) 🌧")
        else:
            print(f"Tropical status: {res.status_code}")
    except Exception as e:
        print(f"Error Tropical Tidbits: {e}")

if __name__ == "__main__":
    fetch_tropical_tidbits()
    with sync_playwright() as playwright:
        capture_charts(playwright)
