import os
import asyncio
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"

def send_telegram_photo(image_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as f:
            data = {"chat_id": CHANNEL_ID, "caption": caption}
            files = {"photo": f}
            res = requests.post(url, data=data, files=files, timeout=60)
        if res.ok:
            print(f"--> ارسال شد: {image_path}")
        else:
            print(f"خطای تلگرام برای {image_path}: {res.text}")
    except Exception as e:
        print(f"خطای ارسال {image_path}: {e}")

def download_ecmwf_meteogram():
    api_url = "https://charts.ecmwf.int/opencharts-api/v1/products/opencharts_meteogram?lat=34.64&lon=50.86&epsgram=classical_10d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(api_url, headers=headers, timeout=30).json()
        img_url = res["data"]["link"]["href"]
        img_data = requests.get(img_url, headers=headers, timeout=30).content
        with open("ecmwf_meteogram.png", "wb") as f:
            f.write(img_data)
        return "ecmwf_meteogram.png"
    except Exception as e:
        print(f"Error fetching ECMWF meteogram: {e}")
        return None

async def capture_tropical(context):
    url = "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn"
    page = await context.new_page()
    await page.add_init_script(STEALTH_JS)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(15)
        await page.evaluate("""() => {
            document.querySelectorAll('.introjs-overlay, .introjs-helperLayer, .introjs-tooltipReferenceLayer')
            .forEach(el => el.remove());
        }""")
        await page.keyboard.press("Escape")
        await asyncio.sleep(2)
        await page.screenshot(path="tropical_gfs.png")
        return "tropical_gfs.png"
    except Exception as e:
        print(f"Error on Tropical Tidbits: {e}")
        return None
    finally:
        await page.close()

async def capture_weather_forecast(context):
    url = "https://www.weather-forecast.com/locations/Qom/forecasts/latest"
    page = await context.new_page()
    await page.add_init_script(STEALTH_JS)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(5)
        await page.evaluate("window.scrollBy(0, 450)")
        await asyncio.sleep(2)
        await page.screenshot(path="weather_forecast_qom.png")
        return "weather_forecast_qom.png"
    except Exception as e:
        print(f"Error on weather-forecast.com: {e}")
        return None
    finally:
        await page.close()

async def capture_foreca(context):
    url = "https://www.foreca.com/100119853/Qom-Qom-Iran"
    page = await context.new_page()
    await page.add_init_script(STEALTH_JS)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(5)
        await page.screenshot(path="foreca_qom.png")
        return "foreca_qom.png"
    except Exception as e:
        print(f"Error on Foreca: {e}")
        return None
    finally:
        await page.close()

async def main():
    print("شروع فرآیند استخراج و ارسال نقشه‌های هواشناسی...")

    print("در حال دریافت متئوگرام ECMWF...")
    ecmwf_file = download_ecmwf_meteogram()
    if ecmwf_file:
        send_telegram_photo(ecmwf_file, "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF - شهر قم\n🌐 charts.ecmwf.int")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        print("در حال پردازش Tropical Tidbits...")
        f1 = await capture_tropical(context)
        if f1:
            send_telegram_photo(f1, "📍 مدل GFS بارش و فشار - خاورمیانه و ایران (Tropical Tidbits)")

        print("در حال پردازش Weather-Forecast...")
        f2 = await capture_weather_forecast(context)
        if f2:
            send_telegram_photo(f2, "🌤 پیش‌بینی وضع هوای قم (weather-forecast.com)")

        print("در حال پردازش Foreca...")
        f3 = await capture_foreca(context)
        if f3:
            send_telegram_photo(f3, "☀️ وضعیت و پیش‌بینی هوای قم (Foreca)")

        await browser.close()

    print("تمام فرآیندها به پایان رسید.")

if __name__ == "__main__":
    asyncio.run(main())
