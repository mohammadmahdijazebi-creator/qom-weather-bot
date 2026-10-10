import os
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = "@qom_weather_forecast"

# لیست سایت‌ها و نام نمایشی
URLS = [
    {
        "name": "GFS - خاورمیانه و ایران (Tropical Tidbits)",
        "url": "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn&runtime=2026101006&fh=6"
    },
    {
        "name": "بارش تجمعی مدل اروپایی (Weather.us)",
        "url": "https://weather.us/model-charts/euro/iran/accumulated-precipitation/20261010-1400z.html"
    },
    {
        "name": "روند ۱۴ روزه قم (Weather.us)",
        "url": "https://weather.us/forecast/9078841-ky-e-sadgn/14-day-trend"
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
        "name": "وزش باد و تندباد قم (Weather.us)",
        "url": "https://weather.us/model-charts/euro/qom/gusts-3h/20261010-1800z.html"
    },
    {
        "name": "متئوگرام ۱۰ روزه ECMWF قم",
        "url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=202610100000&epsgram=classical_10d&lat=34.64&lon=50.86"
    },
    {
        "name": "پیش‌بینی ۱۰ روزه فورکا قم (Foreca)",
        "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast"
    }
]

def send_photo_to_telegram(image_path, caption):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        payload = {"chat_id": CHANNEL_ID, "caption": caption}
        files = {"photo": photo}
        res = requests.post(api_url, data=payload, files=files, timeout=30)
        return res.json()

def main():
    os.makedirs("screenshots", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # ابعاد مرورگر برای گرفتن اسکرین‌شات دسکتاپ باکیفیت
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        for idx, item in enumerate(URLS):
            img_path = f"screenshots/shot_{idx+1}.png"
            print(f"در حال دریافت: {item['name']}")
            try:
                page.goto(item["url"], timeout=60000, wait_until="networkidle")
                time.sleep(3)  # چند ثانیه مکث برای رندر شدن نمودارها
                page.screenshot(path=img_path, full_page=False)
                
                caption = f"📍 {item['name']}\n🔗 {item['url']}"
                send_photo_to_telegram(img_path, caption)
                print(f"با موفقیت به کانال ارسال شد: {item['name']}")
            except Exception as e:
                print(f"خطا در دریافت {item['name']}: {e}")

        browser.close()

if __name__ == "__main__":
    main()
