import os
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.ndimage import minimum_filter, maximum_filter
from datetime import datetime

# دریافت توکن و چت‌آیدی از متغیرهای مخزن
TELEGRAM_BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
)
TELEGRAM_CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or os.getenv("CHANNEL_ID")
)

# تعریف شبکه مختصات: استان قم و استان‌های پیرامون (عرض ۳۲ تا ۳۷، طول ۴۸ تا ۵۴)
lats = np.linspace(32.0, 37.0, 11)
lons = np.linspace(48.5, 54.0, 12)
grid_lons, grid_lats = np.meshgrid(lons, lats)
flat_lats = grid_lats.flatten()
flat_lons = grid_lons.flatten()

# مختصات شهرهای شاخص جهت نمایش موقعیت روی نقشه
CITIES = {
    "Qom": (34.64, 50.88),
    "Tehran": (35.69, 51.39),
    "Arak": (34.09, 49.69),
    "Kashan": (33.98, 51.43),
    "Esfahan": (32.65, 51.67)
}

def fetch_grid_data():
    """دریافت داده‌های تراز ۷۰۰ و ۵۰۰ به‌صورت شبکه‌ای از مدل GFS"""
    url = "https://api.open-meteo.com/v1/gfs"
    params = {
        "latitude": ",".join([f"{x:.2f}" for x in flat_lats]),
        "longitude": ",".join([f"{x:.2f}" for x in flat_lons]),
        "hourly": [
            "geopotential_height_700hPa", "relative_humidity_700hPa",
            "wind_speed_700hPa", "wind_direction_700hPa",
            "geopotential_height_500hPa", "temperature_500hPa",
            "wind_speed_500hPa", "wind_direction_500hPa"
        ],
        "wind_speed_unit": "kmh",
        "forecast_days": 1,
        "timezone": "Asia/Tehran"
    }
    resp = requests.get(url, params=params, timeout=35)
    resp.raise_for_status()
    return resp.json()

def find_high_low(data_2d, mode='min', size=3):
    """تشخیص نقاط عطف کم‌ارتفاع (L) و پرارتفاع (H)"""
    if mode == 'min':
        filtered = minimum_filter(data_2d, size=size, mode='nearest')
        return np.argwhere((data_2d == filtered) & (data_2d != np.max(data_2d)))
    else:
        filtered = maximum_filter(data_2d, size=size, mode='nearest')
        return np.argwhere((data_2d == filtered) & (data_2d != np.min(data_2d)))

def draw_synoptic_map(target_level, z_grid, scalar_grid, u_grid, v_grid, scalar_type, valid_time):
    """رسم نقشه حرفه‌ای سینوپتیک با کانتورهای ارتفاع، برچسب‌ها، مراکز H/L و فلش‌های باد"""
    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=180)
    fig.patch.set_facecolor('#0b1329')
    ax.set_facecolor('#0f172a')

    # ۱. کانتور طیف رنگی پس‌زمینه
    if scalar_type == 'humidity':
        # تراز ۷۰۰: رطوبت نسبی
        cf = ax.contourf(grid_lons, grid_lats, scalar_grid, levels=np.arange(10, 105, 10), cmap='YlGnBu', alpha=0.85)
        cbar = plt.colorbar(cf, ax=ax, orientation='vertical', pad=0.02, shrink=0.82)
        cbar.set_label('700 hPa Relative Humidity (%)', color='#e2e8f0', fontsize=10, fontweight='bold')
        cbar.ax.tick_params(colors='#cbd5e1')
        title_text = f"GFS 700 hPa: Geopotential Height (gpm), Wind & RH (%)\nValid: {valid_time}"
    else:
        # تراز ۵۰۰: دما
        t_levels = np.arange(np.floor(scalar_grid.min()), np.ceil(scalar_grid.max()) + 1, 1.5)
        cf = ax.contourf(grid_lons, grid_lats, scalar_grid, levels=t_levels, cmap='coolwarm', alpha=0.82)
        cbar = plt.colorbar(cf, ax=ax, orientation='vertical', pad=0.02, shrink=0.82)
        cbar.set_label('500 hPa Temperature (°C)', color='#e2e8f0', fontsize=10, fontweight='bold')
        cbar.ax.tick_params(colors='#cbd5e1')
        title_text = f"GFS 500 hPa: Geopotential Height (dam), Wind & Temp (°C)\nValid: {valid_time}"

    # ۲. خطوط کانتور ارتفاع ژئوپتانسیل (ایزوهیپس‌ها)
    if target_level == 500:
        z_display = z_grid / 10.0  # تبدیل به دکامتر (dam)
        step = 2.0
    else:
        z_display = z_grid  # بر حسب متر (gpm)
        step = 15.0

    z_levels = np.arange(np.floor(z_display.min()/step)*step, np.ceil(z_display.max()/step)*step + step, step)
    cs = ax.contour(grid_lons, grid_lats, z_display, levels=z_levels, colors='#ffffff', linewidths=1.7)
    # نوشتن اعداد ارتفاع دقیقاً روی خطوط
    ax.clabel(cs, inline=True, fmt='%.0f', fontsize=9, colors='#f8fafc', inline_spacing=8)

    # ۳. فلش‌های جهت و سرعت باد (Wind Quiver)
    q = ax.quiver(
        grid_lons, grid_lats, u_grid, v_grid,
        color='#fde047', scale=320, width=0.0038, headwidth=4, headlength=5, alpha=0.9
    )
    ax.quiverkey(q, 0.88, 0.05, 50, '50 km/h', labelcolor='#fde047', color='#fde047', coordinates='axes')

    # ۴. تعیین و علامت‌گذاری مراکز کم‌ارتفاع (L) و پرارتفاع (H)
    lows = find_high_low(z_grid, mode='min', size=3)
    highs = find_high_low(z_grid, mode='max', size=3)

    for pt in lows:
        lon_pt, lat_pt = grid_lons[pt[0], pt[1]], grid_lats[pt[0], pt[1]]
        ax.text(lon_pt, lat_pt, 'L', color='#ef4444', fontsize=16, fontweight='heavy',
                ha='center', va='center', bbox=dict(boxstyle='circle,pad=0.2', fc='#1e293b', ec='#ef4444', lw=1.5))

    for pt in highs:
        lon_pt, lat_pt = grid_lons[pt[0], pt[1]], grid_lats[pt[0], pt[1]]
        ax.text(lon_pt, lat_pt, 'H', color='#3b82f6', fontsize=16, fontweight='heavy',
                ha='center', va='center', bbox=dict(boxstyle='circle,pad=0.2', fc='#1e293b', ec='#3b82f6', lw=1.5))

    # ۵. نشانه‌گذاری شهرهای مهم (موقعیت قم به رنگ متمایز)
    for city, (clat, clon) in CITIES.items():
        is_qom = (city == "Qom")
        color = '#f43f5e' if is_qom else '#94a3b8'
        size = 50 if is_qom else 25
        ax.scatter(clon, clat, color=color, s=size, edgecolors='white', lw=1, zorder=6)
        ax.text(clon, clat + 0.12, city, color='#ffffff' if is_qom else '#cbd5e1',
                fontsize=10 if is_qom else 8.5, fontweight='bold' if is_qom else 'normal',
                ha='center', zorder=7, bbox=dict(boxstyle='round,pad=0.15', fc='#0f172a', ec=color, lw=0.8, alpha=0.85))

    # ۶. جزئیات محورها و تیتر
    ax.set_xlim(grid_lons.min(), grid_lons.max())
    ax.set_ylim(grid_lats.min(), grid_lats.max())
    ax.tick_params(colors='#94a3b8', labelsize=9)
    ax.grid(True, linestyle=':', alpha=0.35, color='#94a3b8')
    ax.set_xlabel('Longitude (°E)', color='#cbd5e1', fontweight='bold', fontsize=10)
    ax.set_ylabel('Latitude (°N)', color='#cbd5e1', fontweight='bold', fontsize=10)
    ax.set_title(title_text, color='#f8fafc', fontsize=12.5, fontweight='bold', pad=12)

    plt.tight_layout()
    file_name = f"gfs_{target_level}_synoptic.png"
    plt.savefig(file_name, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return file_name

def send_telegram_photo(photo_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Warning] Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        resp = requests.post(url, files=files, data=data, timeout=35)
        if resp.status_code == 200:
            print(f"Sent {photo_path} to Telegram")
        else:
            print(f"Failed to send: {resp.text}")

def main():
    print("Fetching synoptic data for 700 & 500 hPa...")
    res = fetch_grid_data()
    # اگر چند نقطه برگشت داده شده باشد، پاسخ لیستی از دیکشنری‌هاست
    items = res if isinstance(res, list) else [res]
    
    # ساعت پیش‌بینی (ساعت ۱۲ محلی بعدازظهر یا نزدیک‌ترین ساعت)
    target_idx = 12

    # استخراج مقادیر شبکه‌ای
    z700 = np.zeros(grid_lats.shape)
    rh700 = np.zeros(grid_lats.shape)
    u700 = np.zeros(grid_lats.shape)
    v700 = np.zeros(grid_lats.shape)

    z500 = np.zeros(grid_lats.shape)
    t500 = np.zeros(grid_lats.shape)
    u500 = np.zeros(grid_lats.shape)
    v500 = np.zeros(grid_lats.shape)

    valid_time_str = items[0]["hourly"]["time"][target_idx]

    idx = 0
    for r in range(grid_lats.shape[0]):
        for c in range(grid_lats.shape[1]):
            h = items[idx]["hourly"]
            
            # 700 hPa
            z700[r, c] = h["geopotential_height_700hPa"][target_idx]
            rh700[r, c] = h["relative_humidity_700hPa"][target_idx]
            wspd700 = h["wind_speed_700hPa"][target_idx]
            wdir700 = h["wind_direction_700hPa"][target_idx]
            u700[r, c] = -wspd700 * np.sin(np.radians(wdir700))
            v700[r, c] = -wspd700 * np.cos(np.radians(wdir700))

            # 500 hPa
            z500[r, c] = h["geopotential_height_500hPa"][target_idx]
            t500[r, c] = h["temperature_500hPa"][target_idx]
            wspd500 = h["wind_speed_500hPa"][target_idx]
            wdir500 = h["wind_direction_500hPa"][target_idx]
            u500[r, c] = -wspd500 * np.sin(np.radians(wdir500))
            v500[r, c] = -wspd500 * np.cos(np.radians(wdir500))

            idx += 1

    # رسم و ارسال نقشه تراز ۷۰۰
    img_700 = draw_synoptic_map(700, z700, rh700, u700, v700, 'humidity', valid_time_str)
    send_telegram_photo(
        img_700,
        f"🗺 نقشه سینوپتیک تراز ۷۰۰ هکتوپاسکال (مدل GFS)\n"
        f"🔹 کانتورهای ارتفاع (gpm) + رطوبت نسبی (%) + بردار باد\n"
        f"📍 پهنه قم و مرکز ایران | موعد: {valid_time_str}"
    )

    # رسم و ارسال نقشه تراز ۵۰۰
    img_500 = draw_synoptic_map(500, z500, t500, u500, v500, 'temperature', valid_time_str)
    send_telegram_photo(
        img_500,
        f"🗺 نقشه سینوپتیک تراز ۵۰۰ هکتوپاسکال (مدل GFS)\n"
        f"🔹 کانتورهای ضخامت/ارتفاع (dam) + دمای تراز ۵۰۰ + بردار باد + مراکز H و L\n"
        f"📍 پهنه قم و مرکز ایران | موعد: {valid_time_str}"
    )

if __name__ == "__main__":
    main()
