import os
import sys
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # اجرای Matplotlib بدون رابط گرافیکی در GitHub Actions

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

# آستانه‌ها برای حذف نوسان‌های خیلی کوچک و جلوگیری از شلوغی نمودار
# برای دما: قله/دره‌ای با اختلاف حداقل 0.3 درجه
TEMP_PROMINENCE = 0.3

# برای باد: قله/دره‌ای با اختلاف حداقل 1.0 کیلومتر بر ساعت
WIND_PROMINENCE = 1.0

# حداقل فاصله نقاط بر حسب تعداد ساعت
TEMP_MIN_DISTANCE_HOURS = 3
WIND_MIN_DISTANCE_HOURS = 3


# -----------------------------
# تنظیم فونت و متن فارسی
# -----------------------------
available_fonts = {font.name for font in font_manager.fontManager.ttflist}

preferred_fonts = [
    "Noto Naskh Arabic",
    "Noto Sans Arabic",
    "DejaVu Sans",
]

selected_font = next(
    (font for font in preferred_fonts if font in available_fonts),
    "DejaVu Sans",
)

plt.rcParams["font.family"] = selected_font
plt.rcParams["axes.unicode_minus"] = False


def rtl(text):
    """شکل‌دهی و راست‌چین‌سازی متن فارسی برای Matplotlib."""
    return get_display(arabic_reshaper.reshape(str(text)))


# -----------------------------
# اطلاعات دسترسی از GitHub Secrets
# -----------------------------
TELEGRAM_BOT_TOKEN = (
    os.environ.get("BOT_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
)
TELEGRAM_CHAT_ID = (
    os.environ.get("CHANNEL_ID")
    or os.environ.get("TELEGRAM_CHAT_ID")
)

BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = (
    os.environ.get("BALE_CHANNEL_ID")
    or os.environ.get("BALE_CHAT_ID")
)


# -----------------------------
# دریافت اطلاعات هواشناسی با تلاش مجدد
# -----------------------------
def fetch_weather_data(location):
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "forecast_days": 3,
        "timezone": "Asia/Tehran",
        "wind_speed_unit": "kmh",
    }

    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            print(
                f"درخواست داده برای {location['name_fa']} "
                f"(تلاش {attempt}/{REQUEST_ATTEMPTS})..."
            )

            response = requests.get(
                API_URL,
                params=params,
                timeout=(10, 30),  # زمان اتصال، زمان دریافت پاسخ
                headers={"User-Agent": "Qom-Weather-Auto-Capturer/1.0"},
            )
            response.raise_for_status()
            data = response.json()

            if "hourly" not in data:
                raise ValueError(f"پاسخ API فاقد hourly است: {data}")

            required_fields = [
                "time",
                "temperature_2m",
                "precipitation",
                "wind_speed_10m",
            ]
            missing_fields = [
                field for field in required_fields
                if field not in data["hourly"]
            ]
            if missing_fields:
                raise ValueError(
                    f"فیلدهای لازم در پاسخ وجود ندارند: {missing_fields}"
                )

            return data

        except Exception as exc:
            print(
                f"خطا در دریافت داده {location['name_fa']} "
                f"در تلاش {attempt}: {exc}"
            )

            if attempt < REQUEST_ATTEMPTS:
                wait_seconds = 2 * attempt
                print(f"{wait_seconds} ثانیه صبر و تلاش دوباره...")
                time.sleep(wait_seconds)

    return None


def numeric_series(values, field_name):
    """تبدیل مقادیر API به آرایه عددی و پرکردن مقادیر گمشده."""
    result = []

    for value in values:
        if value is None:
            result.append(np.nan)
        else:
            result.append(float(value))

    array = np.asarray(result, dtype=float)
    valid = np.isfinite(array)

    if valid.sum() == 0:
        raise ValueError(f"هیچ مقدار معتبری برای {field_name} دریافت نشد.")

    if not valid.all():
        positions = np.arange(len(array))
        array[~valid] = np.interp(
            positions[~valid],
            positions[valid],
            array[valid],
        )

    return array


# -----------------------------
# پیدا کردن و برچسب‌گذاری قله‌ها و دره‌ها
# -----------------------------
def annotate_extrema(ax, times, values, unit, prominence, min_distance):
    values = np.asarray(values, dtype=float)

    peaks, _ = find_peaks(
        values,
        prominence=prominence,
        distance=min_distance,
        plateau_size=(1, None),
    )
    valleys, _ = find_peaks(
        -values,
        prominence=prominence,
        distance=min_distance,
        plateau_size=(1, None),
    )

    events = {}

    for index in peaks:
        events[int(index)] = "peak"

    for index in valleys:
        events[int(index)] = "valley"

    # بیشینه و کمینه کلی را نیز همیشه وارد می‌کنیم؛
    # حتی اگر در ابتدا یا انتهای بازه باشند.
    max_index = int(np.argmax(values))
    min_index = int(np.argmin(values))

    if max_index == min_index:
        events[max_index] = "both"
    else:
        events[max_index] = "max"
        events[min_index] = "min"

    for order, index in enumerate(sorted(events)):
        kind = events[index]
        value = values[index]

        if kind == "max":
            label = f"MAX {value:.1f} {unit}"
            color = "#b42318"
            marker = "^"
            y_offset = 15

        elif kind == "min":
            label = f"MIN {value:.1f} {unit}"
            color = "#175cd3"
            marker = "v"
            y_offset = -17

        elif kind == "both":
            label = f"MAX/MIN {value:.1f} {unit}"
            color = "#6941c6"
            marker = "o"
            y_offset = 15

        elif kind == "peak":
            label = f"{value:.1f} {unit}"
            color = "#b42318"
            marker = "^"
            y_offset = 14

        else:
            label = f"{value:.1f} {unit}"
            color = "#175cd3"
            marker = "v"
            y_offset = -16

        # جابه‌جایی افقی متناوب برای کم‌شدن برخورد برچسب‌ها
        x_offsets = [-12, 0, 12, 0]
        x_offset = x_offsets[order % len(x_offsets)]

        ax.scatter(
            [times[index]],
            [value],
            color=color,
            marker=marker,
            s=30,
            zorder=5,
        )

        ax.annotate(
            label,
            xy=(times[index], value),
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            ha="center",
            va="bottom" if y_offset > 0 else "top",
            fontsize=7.5,
            fontweight="bold",
            color=color,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": color,
                "alpha": 0.88,
                "linewidth": 0.5,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": color,
                "linewidth": 0.6,
            },
            annotation_clip=False,
        )


# -----------------------------
# رسم نمودار برای یک منطقه
# -----------------------------
def create_meteogram(location, hourly):
    times = [
        datetime.fromisoformat(value)
        for value in hourly["time"]
    ]

    temperatures = numeric_series(
        hourly["temperature_2m"],
        "temperature_2m",
    )
    precipitation = numeric_series(
        hourly["precipitation"],
        "precipitation",
    )
    wind_speed = numeric_series(
        hourly["wind_speed_10m"],
        "wind_speed_10m",
    )

    if not (
        len(times)
        == len(temperatures)
        == len(precipitation)
        == len(wind_speed)
    ):
        raise ValueError("تعداد زمان‌ها و مقادیر پیش‌بینی با هم برابر نیست.")

    if len(times) < 2:
        raise ValueError("تعداد ساعات پیش‌بینی‌شده کافی نیست.")

    min_temp = float(np.min(temperatures))
    max_temp = float(np.max(temperatures))
    min_wind = float(np.min(wind_speed))
    max_wind = float(np.max(wind_speed))
    min_precip = float(np.min(precipitation))
    max_precip = float(np.max(precipitation))
    total_precip = float(np.sum(precipitation))

    fig, (ax_temp, ax_precip, ax_wind) = plt.subplots(
        3,
        1,
        figsize=(15, 11),
        sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1.5, 2.5]},
    )

    fig.patch.set_facecolor("white")

    # نمودار دما
    ax_temp.plot(
        times,
        temperatures,
        color="#d92d20",
        linewidth=2.2,
        label=rtl("دما"),
    )
    ax_temp.fill_between(
        times,
        temperatures,
        min_temp - 1,
        color="#d92d20",
        alpha=0.10,
    )
    ax_temp.set_ylabel(rtl("دما (°C)"), fontsize=11, fontweight="bold")
    ax_temp.set_title(
        rtl(f"پیش‌بینی سطحی ۳ روزه — {location['name_fa']}"),
        fontsize=14,
        fontweight="bold",
        pad=14,
    )
    ax_temp.grid(True, linestyle="--", alpha=0.35)
    ax_temp.legend(loc="upper left", fontsize=9)
    ax_temp.margins(x=0.015)

    temp_span = max(max_temp - min_temp, 1.0)
    ax_temp.set_ylim(
        min_temp - temp_span * 0.28 - 0.5,
        max_temp + temp_span * 0.32 + 0.5,
    )

    annotate_extrema(
        ax=ax_temp,
        times=times,
        values=temperatures,
        unit="°C",
        prominence=TEMP_PROMINENCE,
        min_distance=TEMP_MIN_DISTANCE_HOURS,
    )

    # نمودار بارش
    ax_precip.bar(
        times,
        precipitation,
        width=0.025,
        color="#1570ef",
        alpha=0.82,
    )
    ax_precip.set_ylabel(rtl("بارش (mm)"), fontsize=10, fontweight="bold")
    ax_precip.grid(True, linestyle="--", alpha=0.35)
    ax_precip.set_ylim(bottom=0)

    if max_precip > 0:
        max_precip_index = int(np.argmax(precipitation))
        ax_precip.annotate(
            f"MAX {max_precip:.1f} mm",
            xy=(times[max_precip_index], max_precip),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="#175cd3",
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "#175cd3",
                "alpha": 0.9,
            },
        )
    else:
        ax_precip.text(
            0.99,
            0.82,
            rtl("بارشی در این بازه پیش‌بینی نشده"),
            transform=ax_precip.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="#175cd3",
        )

    # نمودار سرعت باد
    ax_wind.plot(
        times,
        wind_speed,
        color="#7f56d9",
        linewidth=1.8,
        label=rtl("سرعت باد"),
    )
    ax_wind.set_ylabel(
        rtl("سرعت باد (km/h)"),
        fontsize=10,
        fontweight="bold",
    )
    ax_wind.grid(True, linestyle="--", alpha=0.35)
    ax_wind.legend(loc="upper left", fontsize=9)

    wind_span = max(max_wind - min_wind, 1.0)
    ax_wind.set_ylim(
        max(0, min_wind - wind_span * 0.25 - 0.5),
        max_wind + wind_span * 0.35 + 0.5,
    )

    annotate_extrema(
        ax=ax_wind,
        times=times,
        values=wind_speed,
        unit="km/h",
        prominence=WIND_PROMINENCE,
        min_distance=WIND_MIN_DISTANCE_HOURS,
    )

    # محور زمان
    ax_wind.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax_wind.xaxis.set_major_formatter(
        mdates.DateFormatter("%d %b\n%H:%M")
    )
    ax_wind.tick_params(axis="x", labelsize=8)

    for label in ax_wind.get_xticklabels():
        label.set_rotation(0)
        label.set_ha("center")

    plt.tight_layout(pad=2.0)

    filename = f"surface_meteogram_{location['key']}.png"
    fig.savefig(
        filename,
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    caption = (
        f"📊 متئوگرام سطحی ۳ روزه\n"
        f"📍 منطقه: {location['name_fa']}\n"
        f"🌡 دما: کمینه {min_temp:.1f}°C | بیشینه {max_temp:.1f}°C\n"
        f"💨 باد: کمینه {min_wind:.1f} km/h | بیشینه {max_wind:.1f} km/h\n"
        f"🌧 بارش: کمینه {min_precip:.1f} mm | بیشینه {max_precip:.1f} mm\n"
        f"🌧 مجموع بارش سه‌روزه: {total_precip:.1f} mm\n"
        f"⏰ زمان اجرا: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}"
    )

    return filename, caption


# -----------------------------
# ارسال تصویر به پیام‌رسان‌ها
# -----------------------------
def send_photo(platform_name, url, token, chat_id, photo_path, caption):
    if not token or not chat_id:
        print(
            f"خطا: اطلاعات دسترسی {platform_name} تنظیم نشده است. "
            "نام Secrets را بررسی کن."
        )
        return False

    try:
        with open(photo_path, "rb") as photo:
            response = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption,
                },
                files={"photo": photo},
                timeout=(10, 45),
            )

        response.raise_for_status()
        result = response.json()

        if isinstance(result, dict) and result.get("ok") is False:
            print(f"خطای API {platform_name}: {result}")
            return False

        print(f"ارسال به {platform_name} موفق بود: {photo_path}")
        return True

    except Exception as exc:
        print(f"خطا در ارسال به {platform_name}: {exc}")
        return False


def send_to_telegram(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    return send_photo(
        platform_name="Telegram",
        url=url,
        token=TELEGRAM_BOT_TOKEN,
        chat_id=TELEGRAM_CHAT_ID,
        photo_path=photo_path,
        caption=caption,
    )


def send_to_bale(photo_path, caption):
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
    return send_photo(
        platform_name="Bale",
        url=url,
        token=BALE_BOT_TOKEN,
        chat_id=BALE_CHANNEL_ID,
        photo_path=photo_path,
        caption=caption,
    )


# -----------------------------
# اجرای کل مناطق
# -----------------------------
def main():
    print(f"فونت انتخاب‌شده: {selected_font}")
    failures = []

    for location in LOCATIONS:
        name = location["name_fa"]
        print(f"\n===== شروع پردازش {name} =====")

        try:
            data = fetch_weather_data(location)

            if data is None:
                failures.append(f"{name}: دریافت داده ناموفق بود")
                print(f"پس از تلاش مجدد، داده {name} دریافت نشد.")
                continue

            filename, caption = create_meteogram(
                location,
                data["hourly"],
            )
            print(f"نمودار ساخته شد: {filename}")

            telegram_ok = send_to_telegram(filename, caption)
            bale_ok = send_to_bale(filename, caption)

            if not telegram_ok:
                failures.append(f"{name}: ارسال Telegram ناموفق بود")

            if not bale_ok:
                failures.append(f"{name}: ارسال Bale ناموفق بود")

        except Exception as exc:
            failures.append(f"{name}: {exc}")
            print(f"خطا در پردازش {name}: {exc}")

        # فاصله کوتاه بین درخواست‌های شهرها
        time.sleep(2)

    if failures:
        print("\n===== خلاصه خطاها =====")
        for failure in failures:
            print(f"- {failure}")

        # باعث می‌شود اگر شهری ارسال نشده باشد، اجرای Actions سبزِ کاذب نشود.
        sys.exit(1)

    print("\nتمام مناطق با موفقیت پردازش و ارسال شدند.")


if __name__ == "__main__":
    main()
