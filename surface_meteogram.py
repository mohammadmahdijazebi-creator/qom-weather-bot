import os
import sys
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from scipy.signal import find_peaks

# -----------------------------
# تنظیمات مناطق
# -----------------------------
LOCATIONS = [
    {"key": "qom", "name_fa": "قم", "lat": 34.64, "lon": 50.88},
    {"key": "dastjerd", "name_fa": "دستجرد", "lat": 34.55, "lon": 50.25},
    {"key": "qahan", "name_fa": "قاهان", "lat": 34.70, "lon": 50.26},
    {"key": "kahak", "name_fa": "کهک", "lat": 34.38, "lon": 50.86},
]

API_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_ATTEMPTS = 3

# تنظیم آستانه‌ها متناسب با دوره ۷ روزه برای جلوگیری از شلوغی بیش از حد
TEMP_PROMINENCE = 0.5
WIND_PROMINENCE = 2.0
TEMP_MIN_DISTANCE_HOURS = 8
WIND_MIN_DISTANCE_HOURS = 8

# -----------------------------
# تنظیم فونت و متن فارسی
# -----------------------------
available_fonts = {font.name for font in font_manager.fontManager.ttflist}
preferred_fonts = [
    "Vazirmatn",
    "Noto Sans Arabic",
    "Noto Naskh Arabic",
    "DejaVu Sans",
]

selected_font = next(
    (font for font in preferred_fonts if font in available_fonts),
    "DejaVu Sans",
)

plt.rcParams["font.family"] = selected_font
plt.rcParams["axes.unicode_minus"] = False


def rtl(text):
    return get_display(arabic_reshaper.reshape(str(text)))


# اطلاعات دسترسی
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("CHANNEL_ID") or os.environ.get("TELEGRAM_CHAT_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID") or os.environ.get("BALE_CHAT_ID")


def fetch_weather_data(location):
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "forecast_days": 7,  # تغییر به ۷ روز کامل
        "timezone": "Asia/Tehran",
        "wind_speed_unit": "kmh",
    }

    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=(10, 30),
                headers={"User-Agent": "Qom-Weather-Auto-Capturer/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            if "hourly" not in data:
                raise ValueError("پاسخ فاقد hourly است")

            return data

        except Exception as exc:
            print(f"خطا در دریافت داده {location['name_fa']} (تلاش {attempt}): {exc}")
            if attempt < REQUEST_ATTEMPTS:
                time.sleep(2 * attempt)

    return None


def numeric_series(values, field_name):
    result = [np.nan if v is None else float(v) for v in values]
    array = np.asarray(result, dtype=float)
    valid = np.isfinite(array)

    if valid.sum() == 0:
        raise ValueError(f"هیچ مقدار معتبری برای {field_name} دریافت نشد.")

    if not valid.all():
        positions = np.arange(len(array))
        array[~valid] = np.interp(positions[~valid], positions[valid], array[valid])

    return array


def annotate_extrema(ax, times, values, unit, prominence, min_distance):
    values = np.asarray(values, dtype=float)

    peaks, _ = find_peaks(values, prominence=prominence, distance=min_distance)
    valleys, _ = find_peaks(-values, prominence=prominence, distance=min_distance)

    events = {int(i): "peak" for i in peaks}
    for i in valleys:
        events[int(i)] = "valley"

    max_idx = int(np.argmax(values))
    min_idx = int(np.argmin(values))
    events[max_idx] = "max"
    events[min_idx] = "min"

    for order, index in enumerate(sorted(events)):
        kind = events[index]
        value = values[index]

        if kind in ["max", "peak"]:
            label = f"{'MAX ' if kind=='max' else ''}{value:.1f}{unit}"
            color = "#b42318"
            marker = "^"
            y_offset = 12
        else:
            label = f"{'MIN ' if kind=='min' else ''}{value:.1f}{unit}"
            color = "#175cd3"
            marker = "v"
            y_offset = -14

        ax.scatter([times[index]], [value], color=color, marker=marker, s=28, zorder=5)
        ax.annotate(
            label,
            xy=(times[index], value),
            xytext=(0, y_offset),
            textcoords="offset points",
            ha="center",
            va="bottom" if y_offset > 0 else "top",
            fontsize=7.2,
            fontweight="bold",
            color=color,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=color, alpha=0.9, linewidth=0.5),
        )


def create_meteogram(location, hourly):
    times = [datetime.fromisoformat(v) for v in hourly["time"]]
    temperatures = numeric_series(hourly["temperature_2m"], "temperature_2m")
    precipitation = numeric_series(hourly["precipitation"], "precipitation")
    wind_speed = numeric_series(hourly["wind_speed_10m"], "wind_speed_10m")

    min_temp = float(np.min(temperatures))
    max_temp = float(np.max(temperatures))
    min_wind = float(np.min(wind_speed))
    max_wind = float(np.max(wind_speed))
    total_precip = float(np.sum(precipitation))

    fig, (ax_temp, ax_precip, ax_wind) = plt.subplots(
        3, 1, figsize=(15, 11), sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1.4, 2.4]}
    )
    fig.patch.set_facecolor("white")

    # ۱. نمودار دما
    ax_temp.plot(times, temperatures, color="#d92d20", linewidth=2.0, label=rtl("دما"))
    ax_temp.fill_between(times, temperatures, min_temp - 1, color="#d92d20", alpha=0.10)
    ax_temp.set_ylabel(rtl("دما (°C)"), fontsize=11, fontweight="bold")
    ax_temp.set_title(
        rtl(f"پیش‌بینی سطحی ۷ روزه — {location['name_fa']}"),
        fontsize=14, fontweight="bold", pad=14
    )
    ax_temp.grid(True, linestyle="--", alpha=0.35)
    ax_temp.legend(loc="upper left", fontsize=9)
    annotate_extrema(ax_temp, times, temperatures, "°", TEMP_PROMINENCE, TEMP_MIN_DISTANCE_HOURS)

    # ۲. نمودار بارش
    ax_precip.bar(times, precipitation, width=0.032, color="#1570ef", alpha=0.82)
    ax_precip.set_ylabel(rtl("بارش (mm)"), fontsize=10, fontweight="bold")
    ax_precip.grid(True, linestyle="--", alpha=0.35)
    ax_precip.set_ylim(bottom=0)

    # ۳. نمودار باد
    ax_wind.plot(times, wind_speed, color="#7f56d9", linewidth=1.8, label=rtl("سرعت باد"))
    ax_wind.set_ylabel(rtl("سرعت باد (km/h)"), fontsize=10, fontweight="bold")
    ax_wind.grid(True, linestyle="--", alpha=0.35)
    ax_wind.legend(loc="upper left", fontsize=9)
    annotate_extrema(ax_wind, times, wind_speed, "k", WIND_PROMINENCE, WIND_MIN_DISTANCE_HOURS)

    # مقیاس زمانی بهینه ۷ روزه
    ax_wind.xaxis.set_major_locator(mdates.DayLocator())
    ax_wind.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%m/%d"))
    ax_wind.xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))
    ax_wind.tick_params(axis="x", labelsize=8.5)

    plt.tight_layout(pad=2.0)
    filename = f"surface_meteogram_{location['key']}.png"
    fig.savefig(filename, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    caption = (
        f"📊 متئوگرام سطحی ۷ روزه\n"
        f"📍 منطقه: {location['name_fa']}\n"
        f"🌡 دما: کمینه {min_temp:.1f}°C | بیشینه {max_temp:.1f}°C\n"
        f"💨 باد: کمینه {min_wind:.1f} km/h | بیشینه {max_wind:.1f} km/h\n"
        f"🌧 مجموع بارش ۷ روزه: {total_precip:.1f} mm\n"
        f"⏰ صدور: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return filename, caption


def send_photo(platform, url, data, photo_path):
    try:
        with open(photo_path, "rb") as f:
            res = requests.post(url, data=data, files={"photo": f}, timeout=(10, 45))
            return res.status_code == 200
    except:
        return False


def broadcast_all(photo_path, caption):
    if BOT_TOKEN and TELEGRAM_CHAT_ID:
        send_photo("Telegram", f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                   {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, photo_path)
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        send_photo("Bale", f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                   {"chat_id": BALE_CHANNEL_ID, "caption": caption}, photo_path)


def main():
    print(f"Font: {selected_font}")
    for loc in LOCATIONS:
        try:
            print(f"Processing {loc['name_fa']}...")
            data = fetch_weather_data(loc)
            if data:
                img, cap = create_meteogram(loc, data["hourly"])
                broadcast_all(img, cap)
        except Exception as e:
            print(f"Error {loc['name_fa']}: {e}")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
