import os
import time
import requests
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
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, "rb") as photo:
                payload = {"chat_id": CHANNEL_ID, "caption": caption}
                files = {"photo": photo}
                response = requests.post(url, data=payload, files=files, timeout=40)
                if response.status_code == 200:
                    print(f"Telegram sent successfully: {caption}")
                else:
                    print(f"Telegram API Error: {response.text}")
        except Exception as e:
            print(f"Failed to send to Telegram {caption}: {e}")


def send_to_bale(photo_path, caption):
    if not os.path.exists(photo_path):
        return

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, "rb") as photo:
                payload = {"chat_id": BALE_CHANNEL_ID, "caption": caption}
                files = {"photo": photo}
                response = requests.post(url, data=payload, files=files, timeout=40)
                if response.status_code == 200:
                    print(f"Bale sent successfully: {caption}")
                else:
                    print(f"Bale API Error: {response.text}")
        except Exception as e:
            print(f"Failed to send to Bale {caption}: {e}")


def broadcast(photo_path, caption):
    send_to_telegram(photo_path, caption)
    send_to_bale(photo_path, caption)


def run_all(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    )

    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    )

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

    # ۳. فورکا ۱۰ روزه (Foreca) - فریز شده
    try:
        print("3. Capturing Foreca...")
        page.goto("https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast", timeout=60000)
        page.wait_for_timeout(5000)
        page.screenshot(path="foreca.png")
        broadcast("foreca.png", "پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم ☀️")
    except Exception as e:
        print(f"Error Foreca: {e}")

    # ۴. سایت Yr.no (جداول متنی)
    yr_locations = [
        {"name": "قم", "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom", "file": "yr_qom.png"},
        {"name": "قاهان", "url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "file": "yr_qahan.png"},
        {"name": "دستجرد", "url": "https://www.yr.no/en/forecast/daily-table/2-138402/Iran/Qom%20Province/Dastjerd", "file": "yr_dastjerd.png"},
        {"name": "کهک", "url": "https://www.yr.no/en/forecast/daily-table/2-128338/Iran/Qom%20Province/Kahak", "file": "yr_kahak.png"}
    ]
    for loc in yr_locations:
        try:
            print(f"4. Capturing Yr.no Table ({loc['name']})...")
            page.goto(loc["url"], timeout=60000)
            page.wait_for_timeout(5000)
            page.screenshot(path=loc["file"])
            broadcast(loc["file"], f"پیش‌بینی وضعیت جوی {loc['name']} (منبع: Yr.no) 🌧")
        except Exception as e:
            print(f"Error Yr.no Table {loc['name']}: {e}")

    # ۵. سایت Yr.no (نمودارهای گرافیکی: قم، قاهان، دستجرد، کهک)
    yr_graphs = [
        {"name": "قم", "url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom%20Province/Qom", "file": "yr_graph_qom.png"},
        {"name": "قاهان", "url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n", "file": "yr_graph_qahan.png"},
        {"name": "دستجرد", "url": "https://www.yr.no/en/forecast/graph/2-138402/Iran/Qom%20Province/Dastjerd", "file": "yr_graph_dastjerd.png"},
        {"name": "کهک", "url": "https://www.yr.no/en/forecast/graph/2-128338/Iran/Qom%20Province/Kahak", "file": "yr_graph_kahak.png"}
    ]
    for g in yr_graphs:
        try:
            print(f"5. Capturing Yr.no Graph ({g['name']})...")
            page.goto(g["url"], timeout=60000)
            page.wait_for_timeout(6000)
            page.screenshot(path=g["file"])
            broadcast(g["file"], f"نمودار پیش‌بینی ساعتی Yr.no ({g['name']}) 📉")
        except Exception as e:
            print(f"Error Yr.no Graph {g['name']}: {e}")

    # ۶. تروپیکال تیدبیتس (Tropical Tidbits)
    try:
        print("6. Capturing Tropical Tidbits...")
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
        print(f"Error Tropical Tidbits: {e}")

    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run_all(playwright)
