import os
import asyncio
import requests
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

def send_telegram_photo(image_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as f:
        data = {"chat_id": CHANNEL_ID, "caption": caption}
        files = {"photo": f}
        requests.post(url, data=data, files=files, timeout=30)

def download_ecmwf_meteogram():
    """دانلود مستقیم تصویر متئوگرام ۱۰ روزه قم با بالاترین کیفیت بدون نیاز به مرورگر"""
    api_url = "https://charts.ecmwf.int/opencharts-api/v1/products/opencharts_meteogram?lat=34.64&lon=50.86&epsgram=classical_10d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(api_url, headers=headers, timeout=20).json()
        img_url = res["data"]["link"]["href"]
        img_data = requests.get(img_url, headers=headers, timeout=20).content
        output_file = "ecmwf_meteogram.png"
        with open(output_file, "wb") as f:
            f.write(img_data)
        return output_file
    except Exception as e:
        print(f"Error fetching ECMWF meteogram: {e}")
        return None

async def capture_tropical(context):
    """گرفتن اسکرین‌شات از GFS خاورمیانه و بستن تضمینی کادر پاپ‌آپ خوش‌آمدگویی"""
    url = "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg=mslp_pcpn"
    page = await context.new_page()
    await stealth_async(page)
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(4)
        
        # بستن و حذف لایه‌های مزاحم پاپ‌آپ
        await page.evaluate("""() => {
            const overlays = document.querySelectorAll('.introjs-overlay, .introjs-helperLayer, .introjs-tooltipReferenceLayer');
            overlays.forEach(el => el.remove());
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
    """اسکرین‌شات از جدول پیش‌بینی هواشناسی سایت weather-forecast برای شهر قم"""
    url = "https://www.weather-forecast.com/locations/Qom/forecasts/latest"
    page = await context.new_page()
    await stealth_async(page)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)
        
        # اسکرول به محدوده جدول وضعیت هواشناسی
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
    """اسکرین‌شات وضعیت شهر قم از فورکا"""
    url = "https://www.foreca.com/100119853/Qom-Qom-Iran"
    page = await context.new_page()
    await stealth_async(page)
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(4)
        try:
            await page.keyboard.press("Escape")
        except:
            pass
        await page.screenshot(path="foreca_qom.png")
        return "foreca_qom.png"
    except Exception as e:
        print(f"Error on Foreca: {e}")
        return None
    finally:
        await page.close()

async def main():
    print("شروع فرآیند استخراج و ارسال نقشه‌های هواشناسی...")

    # ۱. دریافت مستقیم متئوگرام ۱۰ روزه ECMWF قم
    print("در حال دریافت متئوگرام ECMWF...")
    ecmwf_file = download_ecmwf_meteogram()
    if ecmwf_file:
        send_telegram_photo(ecmwf_file, "📊 متئوگرام ۱۰ روزه گروهی (ENS) مدل اروپایی ECMWF - شهر قم\n🌐 charts.ecmwf.int")
        print("متئوگرام ECMWF ارسال شد.")

    # اجرای مرورگر برای سایر صفحات
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

        # ۲. نقشه مدل GFS بدون پاپ‌آپ
        print("در حال پردازش Tropical Tidbits...")
        trop_file = await capture_tropical(context)
        if trop_file:
            send_telegram_photo(trop_file, "📍 مدل GFS بارش و فشار - خاورمیانه و ایران (Tropical Tidbits)")

        # ۳. سایت weather-forecast.com
        print("در حال پردازش Weather-Forecast...")
        wf_file = await capture_weather_forecast(context)
        if wf_file:
            send_telegram_photo(wf_file, "🌤 پیش‌بینی جدید وضع هوای قم (weather-forecast.com)")

        # ۴. سایت Foreca
        print("در حال پردازش Foreca...")
        foreca_file = await capture_foreca(context)
        if foreca_file:
            send_telegram_photo(foreca_file, "☀️ وضعیت و پیش‌بینی هوای قم (Foreca)")

        await browser.close()
    
    print("تمام فرآیندها با موفقیت به پایان رسید.")

if __name__ == "__main__":
    asyncio.run(main())
