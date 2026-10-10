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

def run_all(playwright):
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
        print("1. Capturing ECMWF Meteogram...")
        page.goto("https://charts.ecmwf.int/products/opencharts_meteogram?epsgram=classical_10d&lat=34.6401&lon=50.8764&station_name=Qom", timeout=60000)
        page.wait_for_selector(".chart-image, img.opencharts-image, .chart-container img", timeout=25000)
        page.wait_for_timeout(4000)
        img = page.query_selector(".chart-image, img.opencharts-image, .chart-container img")
        if img:
            img.screenshot(path="ecmwf.png")
        else:
            page.screenshot(path="ecmwf.png")
        send_to_telegram("ecmwf.png", "متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF 🌤\n(سایت: charts.ecmwf.int)")
    except Exception as e:
        print(f"Error ECMWF: {e}")

    # 2. Weather-Forecast (Qom)
    try:
        print("2. Capturing Weather-Forecast...")
        page.goto("https://www.weather-forecast.com/locations/Qom/forecasts/latest", timeout=60000)
        page.wait_for_timeout(5000)
        page.screenshot(path="weather_forecast.png")
        send_to_telegram("weather_forecast.png", "پیش‌بینی وضع هوای قم (منبع: Weather-Forecast) 🌦")
    except Exception as e:
        print(f"Error Weather-Forecast: {e}")

    # 3. Foreca (10-day forecast)
    try:
        print("3. Capturing Foreca...")
        page.goto("https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", timeout=60000)
        page.wait_for_timeout(6000)
        try:
            page.click("button:has-text('Accept')", timeout=3000)
        except:
            pass
        page.screenshot(path="foreca.png")
        send_to_telegram("foreca.png", "پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم ☀️")
    except Exception as e:
        print(f"Error Foreca: {e}")

    # 4. Yr.no (Qom, Qahan, Dastjerd, Kahak)
    yr_locations = [
        {"name": "قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "file": "yr_qom.png"},
        {"name": "قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "file": "yr_qahan.png"},
        {"name": "دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-138402/Iran/Qom%20Province/Dastjerd", "file": "yr_dastjerd.png"},
        {"name": "کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-128338/Iran/Qom%20Province/Kahak", "file": "yr_kahak.png"}
    ]

    for loc in yr_locations:
        try:
            print(f"4. Capturing Yr.no ({loc['name']})...")
            page.goto(loc["url"], timeout=60000)
            page.wait_for_timeout(5000)
            page.screenshot(path=loc["file"])
            send_to_telegram(loc["file"], f"پیش‌بینی وضعیت جوی {loc['name']} (منبع: Yr.no) 🌧")
        except Exception as e:
            print(f"Error Yr.no {loc['name']}: {e}")

    # 5. Tropical Tidbits (GFS Model)
    try:
        print("5. Capturing Tropical Tidbits...")
        page.goto("https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn", timeout=60000)
        page.wait_for_timeout(7000)
        page.screenshot(path="tropical.png")
        send_to_telegram("tropical.png", "مدل GFS بارش و فشار - خاورمیانه و ایران (Tropical Tidbits) 🌧")
    except Exception as e:
        print(f"Error Tropical Tidbits: {e}")

    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run_all(playwright)
