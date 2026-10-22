import os
import asyncio
from datetime import datetime
import pytz
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel_id")

CITIES = [
    {"name": "Qom", "fa": "قم", "ecmwf_url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.64&lon=50.87&station_name=Qom", "wf_url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest"},
    {"name": "Kahak", "fa": "کهک", "ecmwf_url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.39&lon=50.86&station_name=Kahak", "wf_url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest"},
    {"name": "Dastjerd", "fa": "دستجرد", "ecmwf_url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.55&lon=50.25&station_name=Dastjerd", "wf_url": "https://www.weather-forecast.com/locations/Dastjerd/forecasts/latest"},
    {"name": "Salafchegan", "fa": "سلفچگان", "ecmwf_url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.48&lon=50.46&station_name=Salafchegan", "wf_url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest"},
    {"name": "Qahan", "fa": "قاهان", "ecmwf_url": "https://charts.ecmwf.int/products/opencharts_meteogram?base_time=latest&lat=34.72&lon=50.26&station_name=Qahan", "wf_url": "https://www.weather-forecast.com/locations/Qahan/forecasts/latest"}
]

def send_photo_to_telegram(photo_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo:
        payload = {"chat_id": CHANNEL_ID, "caption": caption}
        files = {"photo": photo}
        res = requests.post(url, data=payload, files=files, timeout=40)
        return res.json()

async def capture_ecmwf_full(page, city_info):
    file_name = f"ecmwf_{city_info['name']}.png"
    # تنظیم ابعاد استاندارد و وسیع برای جلوگیری از هرگونه برش سمت راست و پایین
    await page.set_viewport_size({"width": 1650, "height": 1450})
    await page.goto(city_info["ecmwf_url"], wait_until="networkidle", timeout=60000)
    await asyncio.sleep(4)
    
    # گرفتن اسکرین‌شات کامل بدون بریده شدن ستون‌ها و محور زمان پایین
    await page.screenshot(
        path=file_name,
        clip={"x": 0, "y": 0, "width": 1650, "height": 1450}
    )
    return file_name

async def capture_weather_forecast(page, city_info):
    file_name = f"wf_{city_info['name']}.png"
    await page.set_viewport_size({"width": 1280, "height": 780})
    await page.goto(city_info["wf_url"], wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)
    
    # کات دقیق و تمیز: فقط جدول اصلی هواشناسی بدون رفتن به بخش‌های اضافی پایین صفحه
    await page.screenshot(
        path=file_name,
        clip={"x": 40, "y": 140, "width": 1200, "height": 640}
    )
    return file_name

async def main():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz).strftime("%Y/%m/%d - %H:%M")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for city in CITIES:
            # ۱. متئوگرام کامل ECMWF (بدون برش راست و پایین)
            ecmwf_file = await capture_ecmwf_full(page, city)
            caption_ecmwf = f"🌍 مدل ECMWF - ایستگاه {city['name']} ({city['fa']})\n📊 پیش‌بینی ۱۰ روزه انسامبل\n🕒 {now}"
            send_photo_to_telegram(ecmwf_file, caption_ecmwf)
            
            # ۲. جدول استاندارد Weather-Forecast (با کات دقیق)
            wf_file = await capture_weather_forecast(page, city)
            caption_wf = f"🌤 پیش‌بینی تفکیکی آب و هوا - {city['fa']} ({city['name']})\n🕒 {now}"
            send_photo_to_telegram(wf_file, caption_wf)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
