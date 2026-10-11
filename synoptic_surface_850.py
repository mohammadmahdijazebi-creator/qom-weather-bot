import os
import requests
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import minimum_filter, maximum_filter

# هماهنگ‌سازی کامل با نام متغیرهای موجود در Secrets شما
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHANNEL_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
BALE_CHAT_ID = os.getenv("BALE_CHANNEL_ID") or os.getenv("BALE_CHAT_ID")

lats = np.linspace(32.0, 37.0, 11)
lons = np.linspace(48.5, 54.0, 12)
grid_lons, grid_lats = np.meshgrid(lons, lats)
flat_lats = grid_lats.flatten()
flat_lons = grid_lons.flatten()

CITIES = {
    "Qom": (34.64, 50.88),
    "Tehran": (35.69, 51.39),
    "Arak": (34.09, 49.69),
    "Kashan": (33.98, 51.43),
    "Esfahan": (32.65, 51.67)
}

def fetch_grid_data():
    url = "https://api.open-meteo.com/v1/gfs"
    params = {
        "latitude": ",".join([f"{x:.2f}" for x in flat_lats]),
        "longitude": ",".join([f"{x:.2f}" for x in flat_lons]),
        "hourly": [
            "temperature_2m", "surface_pressure", "wind_speed_10m", "wind_direction_10m",
            "geopotential_height_850hPa", "temperature_850hPa", "wind_speed_850hPa", "wind_direction_850hPa"
        ],
        "wind_speed_unit": "kmh",
        "forecast_days": 1,
        "timezone": "Asia/Tehran"
    }
    resp = requests.get(url, params=params, timeout=35)
    resp.raise_for_status()
    return resp.json()

def find_high_low(data_2d, mode='min', size=3):
    if mode == 'min':
        filtered = minimum_filter(data_2d, size=size, mode='nearest')
        return np.argwhere((data_2d == filtered) & (data_2d != np.max(data_2d)))
    else:
        filtered = maximum_filter(data_2d, size=size, mode='nearest')
        return np.argwhere((data_2d == filtered) & (data_2d != np.min(data_2d)))

def draw_map(level_name, contour_grid, temp_grid, u_grid, v_grid, valid_time):
    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=180)
    fig.patch.set_facecolor('#0b1329')
    ax.set_facecolor('#0f172a')

    # پس‌زمینه رنگی دما
    t_levels = np.arange(np.floor(temp_grid.min()), np.ceil(temp_grid.max()) + 1, 1.5)
    cf = ax.contourf(grid_lons, grid_lats, temp_grid, levels=t_levels, cmap='coolwarm', alpha=0.82)
    cbar = plt.colorbar(cf, ax=ax, orientation='vertical', pad=0.02, shrink=0.82)
    cbar.set_label(f'{level_name} Temperature (°C)', color='#e2e8f0', fontsize=10, fontweight='bold')
    cbar.ax.tick_params(colors='#cbd5e1')

    # کانتورهای فشار سطح یا ارتفاع ۸۵۰
    if level_name == "Surface":
        z_display = contour_grid / 100.0  # هکتوپاسکال
        step = 2.0
        title_str = f"GFS Surface: Pressure (hPa) & 2m Temp (°C)\nValid: {valid_time}"
    else:
        z_display = contour_grid  # gpm
        step = 15.0
        title_str = f"GFS 850 hPa: Height (gpm) & Temp (°C)\nValid: {valid_time}"

    z_levels = np.arange(np.floor(z_display.min()/step)*step, np.ceil(z_display.max()/step)*step + step, step)
    cs = ax.contour(grid_lons, grid_lats, z_display, levels=z_levels, colors='#ffffff', linewidths=1.7)
    ax.clabel(cs, inline=True, fmt='%.1f' if level_name=="Surface" else '%.0f', fontsize=9, colors='#f8fafc', inline_spacing=8)

    # بردار باد
    q = ax.quiver(grid_lons, grid_lats, u_grid, v_grid, color='#fde047', scale=320, width=0.0038, alpha=0.9)
    ax.quiverkey(q, 0.88, 0.05, 50, '50 km/h', labelcolor='#fde047', color='#fde047', coordinates='axes')

    # مراکز H و L
    lows = find_high_low(contour_grid, mode='min', size=3)
    highs = find_high_low(contour_grid, mode='max', size=3)
    for pt in lows:
        ax.text(grid_lons[pt[0], pt[1]], grid_lats[pt[0], pt[1]], 'L', color='#ef4444', fontsize=16, fontweight='heavy',
                ha='center', va='center', bbox=dict(boxstyle='circle,pad=0.2', fc='#1e293b', ec='#ef4444', lw=1.5))
    for pt in highs:
        ax.text(grid_lons[pt[0], pt[1]], grid_lats[pt[0], pt[1]], 'H', color='#3b82f6', fontsize=16, fontweight='heavy',
                ha='center', va='center', bbox=dict(boxstyle='circle,pad=0.2', fc='#1e293b', ec='#3b82f6', lw=1.5))

    # موقعیت شهرها
    for city, (clat, clon) in CITIES.items():
        is_qom = (city == "Qom")
        color = '#f43f5e' if is_qom else '#94a3b8'
        size = 50 if is_qom else 25
        ax.scatter(clon, clat, color=color, s=size, edgecolors='white', lw=1, zorder=6)
        ax.text(clon, clat + 0.12, city, color='#ffffff' if is_qom else '#cbd5e1',
                fontsize=10 if is_qom else 8.5, fontweight='bold' if is_qom else 'normal',
                ha='center', zorder=7, bbox=dict(boxstyle='round,pad=0.15', fc='#0f172a', ec=color, lw=0.8, alpha=0.85))

    ax.set_xlim(grid_lons.min(), grid_lons.max())
    ax.set_ylim(grid_lats.min(), grid_lats.max())
    ax.tick_params(colors='#94a3b8', labelsize=9)
    ax.grid(True, linestyle=':', alpha=0.35, color='#94a3b8')
    ax.set_xlabel('Longitude (°E)', color='#cbd5e1', fontweight='bold', fontsize=10)
    ax.set_ylabel('Latitude (°N)', color='#cbd5e1', fontweight='bold', fontsize=10)
    ax.set_title(title_str, color='#f8fafc', fontsize=12.5, fontweight='bold', pad=12)

    plt.tight_layout()
    filename = f"gfs_{level_name.lower().replace(' ', '_')}_map.png"
    plt.savefig(filename, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    return filename

def broadcast_photo(photo_path, caption):
    # ارسال به تلگرام
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                r = requests.post(url, files={'photo': photo}, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}, timeout=35)
                print(f"[Telegram] Status: {r.status_code}, Response: {r.text[:100]}")
        except Exception as e:
            print(f"[Telegram Error]: {e}")
    else:
        print("[Telegram Warning]: BOT_TOKEN or CHANNEL_ID is not configured!")

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHAT_ID:
        bale_url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                r = requests.post(bale_url, files={'photo': photo}, data={'chat_id': BALE_CHAT_ID, 'caption': caption}, timeout=35)
                print(f"[Bale] Status: {r.status_code}, Response: {r.text[:100]}")
        except Exception as e:
            print(f"[Bale Error]: {e}")
    else:
        print("[Bale Warning]: BALE_BOT_TOKEN or BALE_CHANNEL_ID is not configured!")

def main():
    print(f"Telegram configured: {bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)}")
    print(f"Bale configured: {bool(BALE_BOT_TOKEN and BALE_CHAT_ID)}")

    res = fetch_grid_data()
    items = res if isinstance(res, list) else [res]
    target_idx = 12
    valid_time = items[0]["hourly"]["time"][target_idx]

    surf_press = np.zeros(grid_lats.shape)
    t2m = np.zeros(grid_lats.shape)
    u_surf = np.zeros(grid_lats.shape)
    v_surf = np.zeros(grid_lats.shape)

    z850 = np.zeros(grid_lats.shape)
    t850 = np.zeros(grid_lats.shape)
    u850 = np.zeros(grid_lats.shape)
    v850 = np.zeros(grid_lats.shape)

    idx = 0
    for r in range(grid_lats.shape[0]):
        for c in range(grid_lats.shape[1]):
            h = items[idx]["hourly"]
            
            surf_press[r, c] = h["surface_pressure"][target_idx]
            t2m[r, c] = h["temperature_2m"][target_idx]
            wspd_s = h["wind_speed_10m"][target_idx]
            wdir_s = h["wind_direction_10m"][target_idx]
            u_surf[r, c] = -wspd_s * np.sin(np.radians(wdir_s))
            v_surf[r, c] = -wspd_s * np.cos(np.radians(wdir_s))

            z850[r, c] = h["geopotential_height_850hPa"][target_idx]
            t850[r, c] = h["temperature_850hPa"][target_idx]
            wspd_8 = h["wind_speed_850hPa"][target_idx]
            wdir_8 = h["wind_direction_850hPa"][target_idx]
            u850[r, c] = -wspd_8 * np.sin(np.radians(wdir_8))
            v850[r, c] = -wspd_8 * np.cos(np.radians(wdir_8))

            idx += 1

    # ۱. نقشه سطح زمین
    print("Generating Surface map...")
    img_surf = draw_map("Surface", surf_press, t2m, u_surf, v_surf, valid_time)
    broadcast_photo(img_surf, f"🗺 نقشه سینوپتیک سطح زمین (GFS)\n📍 قم و مرکز ایران | موعد: {valid_time}")

    # ۲. نقشه ۸۵۰
    print("Generating 850 hPa map...")
    img_850 = draw_map("850 hPa", z850, t850, u850, v850, valid_time)
    broadcast_photo(img_850, f"🗺 نقشه سینوپتیک تراز ۸۵۰ هکتوپاسکال (GFS)\n📍 قم و مرکز ایران | موعد: {valid_time}")
    print("All tasks completed.")

if __name__ == "__main__":
    main()
