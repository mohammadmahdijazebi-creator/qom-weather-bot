import os
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = "@qom_weather_forecast"

URLS = [
    {
        "name": "GFS - خاورمیانه و ایران (Tropical Tidbits)",
        "url": "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn"
    },
    {
        "name": "بارش تجمعی مدل اروپایی (Meteologix/ECMWF)",
        "url": "https://www.meteologix.com/ir/model-charts/euro/iran/accumulated-precipitation.html"
    },
    {
        "name": "پیش‌بینی روزانه قم (Yr.no)",
        "url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom%20Province/Qom"
    },
    {
        "name": "پیش‌بینی روزانه دستجرد (Yr.no)",
        "url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd"
    },
    {
        "name": "وزش باد و تندباد قم (Meteologix)",
        "url": "https://www.meteologix.com/ir/model-charts/euro/qom/gusts-3h.html"
    },
    {
        "name": "پیش‌بینی ۱۰ روزه قم (Foreca)",
        "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast"
    }
]

def send_photo_to_telegram(image_path, caption):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        payload = {"chat_id": CHANNEL_ID, "caption": caption}
        files = {"photo": photo}
        res = requests.post(api_url, data=payload, files=files, timeout=60)
        return res.json()

def main():
    os.makedirs("screenshots", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        )
        # مخفی کردن علامت ربات بودن مرورگر
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = context.new_page()

        for idx, item in enumerate(URLS):
            img_path = f"screenshots/shot_{idx+1}.png"
            print(f"در حال دریافت: {item['name']}")
            try:
                page.goto(item["url"], timeout=60000, wait_until="networkidle")
                time.sleep(5)  # مکث برای بارگذاری کامل نقشه‌ها
                page.screenshot(path=img_path, full_page=False)
                caption = f"📍 {item['name']}\n🔗 {item['url']}"
                send_photo_to_telegram(img_path, caption)
                print(f"با موفقیت ارسال شد: {item['name']}")
            except Exception as e:
                print(f"خطا در دریافت {item['name']}: {e}")

        browser.close()

if __name__ == "__main__":
    main()
