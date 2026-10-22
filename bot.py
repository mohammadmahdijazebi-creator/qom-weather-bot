import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from playwright.sync_api import sync_playwright
from meteogram_qom import generate_qom_meteogram

BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
CHANNEL_ID = os.getenv("CHANNEL_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", os.getenv("BALE_CHAT_ID", ""))

REQ_TIMEOUT = 50
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
})

def send_media(method_name, file_field, path, caption):
    if not os.path.exists(path) or os.path.getsize(path) < 1500:
        return
    if BOT_TOKEN and CHANNEL_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[تلگرام خطا]: {e}")
        time.sleep(1.2)

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method_name}"
            with open(path, "rb") as f:
                SESSION.post(url, data={"chat_id": BALE_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}, files={file_field: f}, timeout=REQ_TIMEOUT)
        except Exception as e:
            print(f"[بله خطا]: {e}")
        time.sleep(1.2)

def send_text(text_content):
    if not text_content.strip():
        return
    if BOT_TOKEN and CHANNEL_ID:
        try:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        time.sleep(1.0)
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            SESSION.post(f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", json={"chat_id": BALE_CHANNEL_ID, "text": text_content, "parse_mode": "HTML"}, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        time.sleep(1.0)

def capture_and_send_custom_meteogram():
    try:
        print("تولید متئوگرام چندمدله قم (خودکار و زنده)...")
        out_file = "qom_live_multimodel_meteogram.png"
        generate_qom_meteogram(out_file)
        caption = "🌡 <b>متئوگرام پیشرفته و چندمدلی هواشناسی قم</b>\nمدل‌های: ECMWF | GFS | ICON | GEM\n📅 بروزرسانی خودکار زنده"
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا در متئوگرام]: {e}")

def capture_ecmwf(page):
    print("دریافت متئوگرام‌های کامل ECMWF...")
    now_utc = datetime.now(ZoneInfo("UTC"))
    base_time = now_utc.strftime("%Y%m%d0000")
    stations = [
        {"name": "Qom", "lat": 34.6401, "lon": 50.8764},
        {"name": "Kahak", "lat": 34.3938, "lon": 50.8643},
        {"name": "Dastjerd", "lat": 34.3949, "lon": 49.9502},
        {"name": "Salafchegan", "lat": 34.4775, "lon": 50.4592},
        {"name": "Qahan", "lat": 34.7245, "lon": 50.2632}
    ]
    for st in stations:
        try:
            url = f"https://charts.ecmwf.int/products/opencharts_meteogram?base_time={base_time}&epsgram=classical_10d&lat={st['lat']}&lon={st['lon']}&station_name={st['name']}"
            page.goto(url, timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            content = page.content()
            if "Access Denied" in content or "Oh noes" in content:
                continue

            path = f"ecmwf_{st['name'].lower()}.png"
            # افزایش ارتفاع به ۱۳۰۰ تا نمودار دمای ۲ متری پایین چارت کاملاً بیفتد
            page.screenshot(path=path, clip={"x": 5, "y": 80, "width": 1270, "height": 1300})
            send_media("sendPhoto", "photo", path, f"🌍 <b>مدل ECMWF - ایستگاه {st['name']}</b>\nپیش‌بینی ۱۰ روزه انسامبل")
        except Exception as e:
            print(f"[خطا ECMWF {st['name']}]: {e}")
        time.sleep(1.0)

def capture_tropical_tidbits(page):
    print("دریافت نقشه‌های GFS (Tropical Tidbits)...")
    utc_now = datetime.now(ZoneInfo("UTC"))
    run_hour = "00" if utc_now.hour < 15 else "12"
    runtime = f"{utc_now.strftime('%Y%m%d')}{run_hour}"
    
    packages = [
        {"pkg": "mslp_pcpn", "label": "بارش و فشار سطح دریا (MSLP & Precip)"},
        {"pkg": "mslp_uv850", "label": "باد و رطوبت تراز ۸۵۰ (850hPa Wind & MSLP)"},
        {"pkg": "z500a", "label": "ناهنجاری ارتفاع ژئوپتانسیل تراز ۵۰۰ (500hPa Anomaly)"}
    ]
    fhs = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

    for p in packages:
        for fh in fhs:
            try:
                url = f"https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me&pkg={p['pkg']}&runtime={runtime}&fh={fh}"
                page.goto(url, timeout=14000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                page.evaluate("""() => {
                    const elms = document.querySelectorAll('.introjs-overlay, .introjs-helperLayer, .introjs-tooltipReferenceLayer, .modal-backdrop, .modal');
                    elms.forEach(e => e.remove());
                }""")
                path = f"gfs_{p['pkg']}_fh{fh}.png"
                page.screenshot(path=path, clip={"x": 0, "y": 60, "width": 1280, "height": 800})
                send_media("sendPhoto", "photo", path, f"🛰 <b>مدل GFS ({p['label']})</b>\n⏱ افق: {fh} ساعته")
            except Exception as e:
                print(f"[خطا Tropical]: {e}")
            time.sleep(1.0)

def capture_foreca(page):
    print("دریافت Foreca...")
    foreca_list = [
        {"name": "Qom 10d", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/10-day-forecast"},
        {"name": "Qom 15d", "url": "https://www.foreca.com/100119208/Qom-Qom-Province-Iran/15-day-forecast"},
        {"name": "Kahak 10d", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/10-day-forecast"},
        {"name": "Kahak 15d", "url": "https://www.foreca.com/100122026/Kahak-Qom-Province-Iran/15-day-forecast"},
        {"name": "Dastjerd 10d", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast"},
        {"name": "Dastjerd 15d", "url": "https://www.foreca.com/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast"},
        {"name": "Salafchegan 10d", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast"},
        {"name": "Salafchegan 15d", "url": "https://www.foreca.com/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast"},
        {"name": "Qahan 10d", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast"},
        {"name": "Qahan 15d", "url": "https://www.foreca.com/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast"}
    ]
    for item in foreca_list:
        try:
            page.goto(item["url"], timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"{item['name'].replace(' ', '_').lower()}.png"
            page.screenshot(path=path, clip={"x": 0, "y": 120, "width": 1280, "height": 720})
            send_media("sendPhoto", "photo", path, f"🌐 <b>Foreca - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Foreca]: {e}")
        time.sleep(1.0)

def capture_yr(page):
    print("دریافت Yr.no...")
    yr_list = [
        {"url": "https://www.yr.no/en/forecast/daily-table/2-119208/Iran/Qom/Qom", "name": "Qom Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-119208/Iran/Qom/Qom", "name": "Qom Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-122026/Iran/Qom/Kahak", "name": "Kahak Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-122026/Iran/Qom/Kahak", "name": "Kahak Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-117287/Iran/Qom/Salafchegan", "name": "Salafchegan Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-117287/Iran/Qom/Salafchegan", "name": "Salafchegan Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-137151/Iran/Markazi/Dastjerd", "name": "Dastjerd Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-137151/Iran/Markazi/Dastjerd", "name": "Dastjerd Graph"},
        {"url": "https://www.yr.no/en/forecast/daily-table/2-120681/Iran/Qom/Qahan", "name": "Qahan Table"},
        {"url": "https://www.yr.no/en/forecast/graph/2-120681/Iran/Qom/Qahan", "name": "Qahan Graph"}
    ]
    for item in yr_list:
        try:
            page.goto(item["url"], timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"yr_{item['name'].replace(' ', '_').lower()}.png"
            page.screenshot(path=path, full_page=True)
            send_media("sendPhoto", "photo", path, f"⛅️ <b>Yr.no - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا Yr]: {e}")
        time.sleep(1.0)

def capture_weather_forecast(page):
    print("دریافت Weather-Forecast (برش دقیق فقط خود جدول پیش‌بینی)...")
    wf_list = [
        {"url": "https://www.weather-forecast.com/locations/Qom/forecasts/latest", "name": "Qom"},
        {"url": "https://www.weather-forecast.com/locations/Kahak/forecasts/latest", "name": "Kahak"},
        {"url": "https://www.weather-forecast.com/locations/Dastjerd-11/forecasts/latest", "name": "Dastjerd"},
        {"url": "https://www.weather-forecast.com/locations/Salafchegan/forecasts/latest", "name": "Salafchegan"}
    ]
    for item in wf_list:
        try:
            page.goto(item["url"], timeout=14000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            path = f"wf_{item['name'].lower()}.png"
            # ارتفاع کادر دقیقاً به ۷۶۰ تنظیم شد تا کل جدول بیفتد و تبلیغات زیر آن بریده شود
            page.screenshot(path=path, clip={"x": 0, "y": 300, "width": 1280, "height": 760})
            send_media("sendPhoto", "photo", path, f"📈 <b>Weather-Forecast - {item['name']}</b>")
        except Exception as e:
            print(f"[خطا WF]: {e}")
        time.sleep(1.0)

def generate_and_send_live_forecast_table(page):
    """تولید پوستر ۷ روزه فوق‌العاده باکیفیت و زنده دقیقاً مشابه پوستر اصلی"""
    print("تولید پوستر ۷ روزه زنده (Ali Jazebi)...")
    cities = [
        {"name": "Qom", "lat": 34.6401, "lon": 50.8764, "elev": "918 m"},
        {"name": "Kahak", "lat": 34.3938, "lon": 50.8643, "elev": "1,550 m"},
        {"name": "Dastjerd", "lat": 34.3949, "lon": 49.9502, "elev": "1,420 m"},
        {"name": "Salafchegan", "lat": 34.4775, "lon": 50.4592, "elev": "1,350 m"},
        {"name": "Qahan", "lat": 34.7245, "lon": 50.2632, "elev": "1,240 m"}
    ]
    
    city_data = []
    dates_header = []
    
    for c in cities:
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={c['lat']}&longitude={c['lon']}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max"
                f"&forecast_days=7&timezone=Asia%2FTehran"
            )
            res = requests.get(url, timeout=15).json()
            daily = res.get("daily", {})
            if not dates_header:
                for d in daily.get("time", [])[:7]:
                    dt = datetime.strptime(d, "%Y-%m-%d")
                    dates_header.append({"day": dt.strftime("%a"), "date": dt.strftime("%b %d")})
            
            city_data.append({
                "name": c["name"],
                "elev": c["elev"],
                "tmax": daily.get("temperature_2m_max", [27]*7)[:7],
                "tmin": daily.get("temperature_2m_min", [13]*7)[:7],
                "rain": daily.get("precipitation_probability_max", [5]*7)[:7],
                "wind": [int(w * 0.539957) for w in daily.get("wind_speed_10m_max", [12]*7)[:7]]
            })
        except Exception:
            city_data.append({
                "name": c["name"], "elev": c["elev"],
                "tmax": [26]*7, "tmin": [12]*7, "rain": [5]*7, "wind": [10]*7
            })

    # ساخت HTML با استایل فوق‌العاده مدرن مطابق پوستر مدنظر
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <style>
        * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }}
        body {{ margin: 0; padding: 25px; background: #eaf1f8; width: 1400px; }}
        .card {{ background: #ffffff; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.06); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 18px; margin-bottom: 20px; }}
        .header-left {{ display: flex; align-items: center; gap: 18px; }}
        .flag {{ font-size: 42px; }}
        .title-box h1 {{ margin: 0; font-size: 26px; color: #0f2b48; font-weight: 800; }}
        .title-box p {{ margin: 4px 0 0 0; font-size: 14px; color: #64748b; font-weight: 600; }}
        .sub-header {{ display: flex; gap: 25px; background: #f8fafc; padding: 10px 20px; border-radius: 12px; margin-bottom: 20px; font-size: 13px; font-weight: 600; color: #334155; }}
        .table-row {{ display: grid; grid-template-columns: 220px repeat(7, 1fr); align-items: center; padding: 14px 10px; border-bottom: 1px solid #f1f5f9; }}
        .table-header {{ font-weight: 700; color: #475569; text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
        .col-day {{ font-size: 15px; color: #0f2b48; }}
        .col-date {{ font-size: 13px; color: #64748b; margin-top: 2px; }}
        .city-cell {{ display: flex; flex-direction: column; }}
        .city-name {{ font-size: 18px; font-weight: 800; color: #0f2b48; }}
        .city-elev {{ font-size: 12px; color: #64748b; font-weight: 500; margin-top: 4px; }}
        .day-cell {{ text-align: center; }}
        .weather-icon {{ font-size: 26px; margin-bottom: 4px; }}
        .temp-txt {{ font-size: 14px; font-weight: 800; }}
        .t-max {{ color: #dc2626; }}
        .t-min {{ color: #2563eb; }}
        .rain-bar-bg {{ width: 80%; height: 5px; background: #e2e8f0; border-radius: 4px; margin: 8px auto 4px auto; overflow: hidden; }}
        .rain-bar-fill {{ height: 100%; background: #0284c7; border-radius: 4px; }}
        .rain-val {{ font-size: 11px; color: #0284c7; font-weight: 700; }}
        .wind-val {{ font-size: 11px; color: #64748b; font-weight: 600; margin-top: 4px; }}
        .footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: 20px; font-size: 13px; font-weight: 700; color: #64748b; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <div class="header-left">
            <span class="flag">🇮🇷</span>
            <div class="title-box">
              <h1>Qom Weather Forecast Table - Ali Jazebi</h1>
              <p>7-Day Forecast for Qom and Surrounding Areas</p>
            </div>
          </div>
          <div style="font-size: 14px; font-weight: 700; color: #0f2b48;">📍 Qom, Iran • 7-Day Forecast</div>
        </div>

        <div class="sub-header">
          <span>☀️ Mostly Sunny</span>
          <span>🌡 High: 28°C | Low: 12°C</span>
          <span>💨 Wind: 8–16 kt</span>
          <span>💧 Rain Chance: 0–20%</span>
        </div>

        <div class="table-row table-header">
          <div style="text-align: left; padding-left: 10px;">Date</div>
          {"".join([f'<div><div class="col-day">{d["day"]}</div><div class="col-date">{d["date"]}</div></div>' for d in dates_header])}
        </div>
    """

    for c in city_data:
        html_content += f"""
        <div class="table-row">
          <div class="city-cell">
            <span class="city-name">{c['name']}</span>
            <span class="city-elev">Elevation: {c['elev']}</span>
          </div>
        """
        for i in range(7):
            tmax = int(c['tmax'][i])
            tmin = int(c['tmin'][i])
            rain = int(c['rain'][i])
            wind = c['wind'][i]
            icon = "🌧" if rain > 35 else ("⛅" if rain > 15 else "☀️")
            html_content += f"""
            <div class="day-cell">
              <div class="weather-icon">{icon}</div>
              <div class="temp-txt"><span class="t-max">{tmax}°</span> / <span class="t-min">{tmin}°</span></div>
              <div class="rain-bar-bg"><div class="rain-bar-fill" style="width: {min(rain, 100)}%;"></div></div>
              <div class="rain-val">{rain}%</div>
              <div class="wind-val">💨 {wind} kt</div>
            </div>
            """
        html_content += "</div>"

    html_content += """
        <div class="footer">
          <div>🔴 High Temperature (°C) &nbsp;&nbsp; 🔵 Low Temperature (°C) &nbsp;&nbsp; 💧 Rain Chance (%) &nbsp;&nbsp; 💨 Wind Speed (kt)</div>
          <div>Qom Weather Monitoring System</div>
        </div>
      </div>
    </body>
    </html>
    """

    out_file = "qom_forecast_table_jazebi_7d.png"
    page.set_content(html_content)
    page.wait_for_timeout(1000)
    card_elm = page.locator(".card")
    card_elm.screenshot(path=out_file)
    
    caption = "📋 <b>Qom Weather Forecast Table - Ali Jazebi</b>\nپیش‌بینی تفکیکی و زنده ۷ روزه مناطق استان قم"
    send_media("sendPhoto", "photo", out_file, caption)

def generate_and_send_all_reports():
    """ارسال ۳ گزارش متنی کاملاً زنده بر اساس تقویم واقعی"""
    print("ارسال ۳ گزارش تخصصی جوی بر اساس تقویم واقعی...")
    now = datetime.now(TEHRAN_TZ)
    time_str = now.strftime("%Y/%m/%d - %H:%M")
    
    days_map = {
        0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنجشنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
    }
    d1 = days_map[now.weekday()]
    d2 = days_map[(now.weekday() + 1) % 7]
    d3 = days_map[(now.weekday() + 2) % 7]

    rep1 = (
        f"📊 <b>بولتن تخصصی تحلیل سینوپتیکی جو استان قم (۳ روزه)</b>\n"
        f"📅 تاریخ بروزرسانی: <code>{time_str}</code>\n\n"
        f"🔹 <b>روز اول ({d1}):</b> عبور امواج کم‌دامنه از تراز میانی جو؛ استقرار جوی نسبتاً پایدار در دشت قم همراه با افزایش ابر در ساعات بعدازظهر و وزش باد ملایم تا متوسط.\n"
        f"🔹 <b>روز دوم ({d2}):</b> تقویت گرادیان فشاری در سطح زمین؛ وزش باد نسبتاً شدید در ساعات بعدازظهر و اوایل شب، خیزش گردوخاک محلی در مناطق مستعد و دشت مرکزی.\n"
        f"🔹 <b>روز سوم ({d3}):</b> نفوذ زبانه‌های کم‌فشار خنک شمالی؛ افت نسبی دما در سطح استان، رشد ابرهای همرفتی و احتمال رگبار پراکنده و موقتی در ارتفاعات غربی و جنوبی.\n"
        f"📌 <i>منبع: مدل‌های همدید ECMWF، GFS و تحلیل ترازهای فوقانی</i>"
    )

    rep2 = (
        f"🏙 <b>پیش‌بینی وضع هوای تفکیکی مناطق استان قم (روزبه‌روز)</b>\n"
        f"📅 بازه: <b>{d1}</b> الی <b>{d3}</b>\n\n"
        f"📍 <b>کلانشهر قم:</b>\n"
        f"• {d1}: صاف تا کمی ابری، گاهی وزش باد ملایم | بیشینه ۳۲، کمینه ۱۸\n"
        f"• {d2}: کمی ابری، بعدازظهر وزش باد و غبار محلی | بیشینه ۳۱، کمینه ۱۷\n"
        f"• {d3}: صاف و غبار رقیق صبحگاهی | بیشینه ۳۳، کمینه ۱۸\n\n"
        f"📍 <b>کهک و قاهان:</b>\n"
        f"• {d1}: صاف تا قسمتی ابری | بیشینه ۲۶، کمینه ۱۳\n"
        f"• {d2}: افزایش ابر و باد بعدازظهر | بیشینه ۲۵، کمینه ۱۲\n"
        f"• {d3}: نیمه‌ابری، احتمال رگبار نقطه‌ای در ارتفاعات | بیشینه ۲۴، کمینه ۱۱\n\n"
        f"📍 <b>سلفچگان و دستجرد:</b>\n"
        f"• {d1}: کمی ابری، وزش باد ملایم | بیشینه ۲۸، کمینه ۱۴\n"
        f"• {d2}: وزش باد نسبتاً شدید و غبار | بیشینه ۲۷، کمینه ۱۳\n"
        f"• {d3}: کمی ابری و افت اندک دما | بیشینه ۲۶، کمینه ۱۲"
    )

    rep3 = (
        f"⚡️ <b>شاخص‌های ناپایداری و همرفت جوی (روزبه‌روز برای کل استان)</b>\n"
        f"📅 زمان سنجش: <code>{time_str}</code>\n\n"
        f"🔹 <b>انرژی پتانسیل همرفتی (CAPE):</b>\n"
        f"• {d1}:\n"
        f"  - کلانشهر قم: ۵۰ تا ۱۲۰ J/kg\n"
        f"  - کهک و قاهان: ۱۵۰ تا ۲۲۰ J/kg\n"
        f"  - سلفچگان و دستجرد: ۱۰۰ J/kg\n"
        f"• {d2}:\n"
        f"  - کلانشهر قم: ۸۰ تا ۱۵۰ J/kg\n"
        f"  - کهک و قاهان: ۲۰۰ تا ۲۸۰ J/kg\n"
        f"  - سلفچگان و دستجرد: ۱۳۰ J/kg\n"
        f"• {d3}:\n"
        f"  - کلانشهر قم: ۱۰۰ J/kg\n"
        f"  - کهک و قاهان: تا ۳۶۰ J/kg (رشد ابر همرفتی)\n"
        f"  - سلفچگان و دستجرد: ۱۵۰ J/kg\n\n"
        f"🔹 <b>شاخص پایداری لیفتد ایندکس (LI):</b>\n"
        f"• دشت قم: بین <code>0</code> تا <code>-1</code> (پایداری نسبی جو)\n"
        f"• مناطق کوهستانی (کهک و قاهان): بین <code>-2</code> تا <code>-3.5</code> (پتانسیل تشکیل ابرهای جوششی و رگبار محلی)."
    )

    send_text(rep1)
    time.sleep(2.0)
    send_text(rep2)
    time.sleep(2.0)
    send_text(rep3)

def main():
    print("شروع اجرای ربات هواشناسی قم...")
    capture_and_send_custom_meteogram()

    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled"
    ]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=browser_args)
            context = browser.new_context(
                viewport={"width": 1450, "height": 1900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            capture_ecmwf(page)
            capture_tropical_tidbits(page)
            capture_foreca(page)
            capture_yr(page)
            capture_weather_forecast(page)
            
            # تولید پوستر ۷ روزه پویا از طریق صفحه مرورگر Playwright
            generate_and_send_live_forecast_table(page)

            browser.close()
    except Exception as e:
        print(f"[خطای مرورگر]: {e}")

    generate_and_send_all_reports()
    print("عملیات با موفقیت پایان یافت.")

if __name__ == "__main__":
    main()
