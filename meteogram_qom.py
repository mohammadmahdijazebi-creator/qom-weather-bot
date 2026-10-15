# meteogram_qom.py
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

# پیش‌فرض: قم
DEFAULT_LAT, DEFAULT_LON = 34.64, 50.87
TIMEZONE = "Asia/Tehran"
FORECAST_DAYS = 10

MODELS = [
    {"id": "ecmwf_ifs025", "name": "ECMWF", "color": "#38bdf8", "wind_color": "#e05252"},
    {"id": "gfs_seamless", "name": "GFS", "color": "#f87171", "wind_color": "#38bdf8"},
    {"id": "icon_seamless", "name": "ICON", "color": "#4ade80", "wind_color": "#4ade80"},
    {"id": "gem_seamless", "name": "GEM", "color": "#c084fc", "wind_color": "#c084fc"},
]

VARIABLES = [
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
]


def fetch_live_data(lat=DEFAULT_LAT, lon=DEFAULT_LON, timeout=20, retries=3):
    """دریافت داده‌های زنده از Open-Meteo با قابلیت تلاش مجدد"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(VARIABLES),
        "models": ",".join([m["id"] for m in MODELS]),
        "timezone": TIMEZONE,
        "forecast_days": FORECAST_DAYS,
    }
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "QomWeatherBot/1.0 (Meteorology Operational Meteogram)"},
    )

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data, True
        except Exception as e:
            if attempt == retries:
                print(f"[Warning] API connection failed: {e}")
                return None, False


def generate_qom_meteogram(
    output_path="qom_live_multimodel_meteogram.png",
    lat=DEFAULT_LAT,
    lon=DEFAULT_LON,
    city_en="Qom",
    city_fa="قم"
):
    """تابع اصلی تولید تصویر متئوگرام که در هر بار اجرا خروجی تازه می‌سازد"""
    raw_data, is_live = fetch_live_data(lat=lat, lon=lon)
    if not raw_data or "hourly" not in raw_data:
        raise RuntimeError(f"امکان دریافت داده‌های هواشناسی برای {city_fa} از سرور فراهم نشد.")

    hourly = raw_data["hourly"]
    times = [datetime.fromisoformat(t) for t in hourly["time"]]
    time_nums = mdates.date2num(times)

    model_data = {}
    for m in MODELS:
        m_id = m["id"]
        t_key = f"temperature_2m_{m_id}"
        p_key = f"precipitation_{m_id}"
        ws_key = f"wind_speed_10m_{m_id}"
        wd_key = f"wind_direction_10m_{m_id}"

        model_data[m["name"]] = {
            "name": m["name"],
            "color": m["color"],
            "wind_color": m["wind_color"],
            "temp": np.array(hourly.get(t_key, [np.nan] * len(times)), dtype=float),
            "precip": np.array(hourly.get(p_key, [0.0] * len(times)), dtype=float),
            "wind_spd": np.array(hourly.get(ws_key, [0.0] * len(times)), dtype=float),
            "wind_dir": np.array(hourly.get(wd_key, [0.0] * len(times)), dtype=float),
        }

    # اعمال تم تیره و مدرن
    plt.rcParams.update({
        "text.color": "#e2e8f0",
        "axes.labelcolor": "#94a3b8",
        "xtick.color": "#94a3b8",
        "ytick.color": "#94a3b8",
        "font.family": ["Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
    })

    fig = plt.figure(figsize=(16.5, 14.6), dpi=150, facecolor="#0e1526")
    gs = fig.add_gridspec(
        3, 1,
        height_ratios=[3.4, 2.3, 2.4],
        hspace=0.38,
        left=0.065, right=0.955, top=0.915, bottom=0.080,
    )

    ax_temp = fig.add_subplot(gs[0, 0], facecolor="#131c31")
    ax_rain = fig.add_subplot(gs[1, 0], facecolor="#131c31")
    ax_wind = fig.add_subplot(gs[2, 0], facecolor="#131c31")

    # هدر اصلی متناسب با نام شهر انتخابی
    header_title = f"Iran, {city_en} - Ali Jazebi"
    fig.text(
        0.5, 0.970,
        header_title,
        ha="center", va="center",
        fontsize=21, fontweight="bold",
        color="#ffffff",
    )

    start_str = times[0].strftime("%b %d")
    end_str = times[-1].strftime("%b %d, %Y")
    sub_title = (
        f"Multi-Model Meteogram • 10-Day Hourly Forecast • {start_str} to {end_str} • "
        f"{lat:.2f}°N {lon:.2f}°E • Live Open-Meteo"
    )
    fig.text(
        0.5, 0.945,
        sub_title,
        ha="center", va="center",
        fontsize=10.5,
        color="#94a3b8",
    )

    def style_x_axis(ax):
        ax.set_xlim(time_nums[0] - 0.2, time_nums[-1] + 0.2)
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        ax.grid(True, which="major", color="#2a3b5c", linestyle="--", linewidth=0.7, alpha=0.85)
        ax.grid(True, which="minor", color="#1f2d47", linestyle=":", linewidth=0.5, alpha=0.6)
        ax.tick_params(axis="x", labelsize=9.5, pad=5)
        ax.tick_params(axis="y", labelsize=9.5)

    # ----------------- پنل ۱: دما -----------------
    ax_temp.set_title(
        "Temperature — ensemble lines with model spread and daily max/min (°C)",
        loc="left", fontsize=12.5, fontweight="bold", color="#f1f5f9", pad=10,
    )

    all_temps = np.array([m["temp"] for m in model_data.values()])
    mean_temp = np.nanmean(all_temps, axis=0)
    std_temp = np.nanstd(all_temps, axis=0)

    ax_temp.fill_between(
        time_nums,
        mean_temp - std_temp,
        mean_temp + std_temp,
        color="#38bdf8",
        alpha=0.14,
        label="Model spread (±1σ)",
    )

    for m in model_data.values():
        ax_temp.plot(
            time_nums, m["temp"],
            label=m["name"],
            color=m["color"],
            linewidth=2.0,
            alpha=0.92,
        )

    # برچسب‌های بیشینه و کمینه روزانه
    unique_dates = sorted({t.date() for t in times})
    for d in unique_dates:
        day_indices = [i for i, t in enumerate(times) if t.date() == d]
        if len(day_indices) < 12:
            continue
        day_tnums = [time_nums[i] for i in day_indices]
        day_means = [mean_temp[i] for i in day_indices]

        max_val = max(day_means)
        max_idx = day_means.index(max_val)
        max_x = day_tnums[max_idx]

        min_val = min(day_means)
        min_idx = day_means.index(min_val)
        min_x = day_tnums[min_idx]

        ax_temp.annotate(
            f"{max_val:.0f}°",
            xy=(max_x, max_val),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=8.5, fontweight="bold",
            color="#fdba74",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#9a3412", edgecolor="#ea580c", alpha=0.85, lw=0.6),
        )

        ax_temp.annotate(
            f"{min_val:.0f}°",
            xy=(min_x, min_val),
            xytext=(0, -8),
            textcoords="offset points",
            ha="center", va="top",
            fontsize=8.5, fontweight="bold",
            color="#bae6fd",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#0369a1", edgecolor="#0284c7", alpha=0.85, lw=0.6),
        )

    ax_temp.set_ylabel("Temperature (°C)", fontsize=10.5, fontweight="bold")
    style_x_axis(ax_temp)
    leg = ax_temp.legend(loc="upper right", framealpha=0.45, facecolor="#0e1526", edgecolor="#334155", fontsize=9.5)
    for text in leg.get_texts():
        text.set_color("#e2e8f0")

    # ----------------- پنل ۲: بارش -----------------
    ax_rain.set_title(
        "Precipitation (mm) — grouped per model",
        loc="left", fontsize=12.5, fontweight="bold", color="#f1f5f9", pad=10,
    )

    bar_width = 0.05
    offsets = [-0.075, -0.025, 0.025, 0.075]

    for (m_name, m_info), off in zip(model_data.items(), offsets):
        precip = m_info["precip"]
        ax_rain.bar(
            time_nums + off,
            precip,
            width=bar_width,
            color=m_info["color"],
            alpha=0.85,
            label=m_name,
        )

    # مقادیر بارش تجمعی روزانه
    for d in unique_dates:
        day_indices = [i for i, t in enumerate(times) if t.date() == d]
        if not day_indices:
            continue
        day_center = time_nums[day_indices[len(day_indices) // 2]]
        day_sums = [float(np.sum(m["precip"][day_indices])) for m in model_data.values()]
        max_sum = max(day_sums)
        if max_sum >= 0.2:
            ax_rain.text(
                day_center,
                max_sum + 0.15,
                f"{max_sum:.1f} mm",
                ha="center", va="bottom",
                fontsize=8.5, fontweight="bold",
                color="#67e8f9",
            )

    ax_rain.set_ylabel("Precipitation (mm)", fontsize=10.5, fontweight="bold")
    style_x_axis(ax_rain)
    all_precip = [m["precip"] for m in model_data.values()]
    max_p = float(np.nanmax(all_precip)) if len(all_precip) else 0.0
    ax_rain.set_ylim(bottom=0.0, top=max(1.0, max_p * 1.35))
    leg_r = ax_rain.legend(loc="upper right", framealpha=0.45, facecolor="#0e1526", edgecolor="#334155", fontsize=9.5)
    for text in leg_r.get_texts():
        text.set_color("#e2e8f0")

    # ----------------- پنل ۳: باد -----------------
    ax_wind.set_title(
        "10 m Wind (barbs, kt) — one row per model, 6-hourly",
        loc="left", fontsize=12.5, fontweight="bold", color="#f1f5f9", pad=10,
    )

    models_list = list(model_data.values())
    ax_wind.set_ylim(-0.5, len(models_list) - 0.5)
    ax_wind.set_yticks(range(len(models_list)))
    ax_wind.set_yticklabels(
        [m["name"] for m in reversed(models_list)],
        fontsize=10.0, fontweight="bold",
    )

    sample_mask = [t.hour in (0, 6, 12, 18) for t in times]
    sample_tnums = time_nums[sample_mask]

    for row_idx, m in enumerate(reversed(models_list)):
        ax_wind.axhspan(
            row_idx - 0.45, row_idx + 0.45,
            color=m["wind_color"],
            alpha=0.06,
        )

        speeds = m["wind_spd"][sample_mask] * 0.539957  # km/h to knots
        dirs = m["wind_dir"][sample_mask]

        rads = np.radians(dirs)
        u = -speeds * np.sin(rads)
        v = -speeds * np.cos(rads)

        calm_mask = speeds < 2.5
        active_mask = ~calm_mask

        if np.any(calm_mask):
            ax_wind.plot(
                sample_tnums[calm_mask],
                [row_idx] * np.sum(calm_mask),
                "o",
                color=m["wind_color"],
                markersize=5.5,
                mfc="none",
                mew=1.3,
                alpha=0.75,
            )

        if np.any(active_mask):
            ax_wind.barbs(
                sample_tnums[active_mask],
                [row_idx] * np.sum(active_mask),
                u[active_mask],
                v[active_mask],
                length=6.5,
                pivot="middle",
                barbcolor=m["wind_color"],
                flagcolor=m["wind_color"],
                linewidth=1.2,
                increments=dict(half=5, full=10, flag=50),
            )

    style_x_axis(ax_wind)

    # ----------------- فوتر -----------------
    footer_y = 0.015
    rect = FancyBboxPatch(
        (0.055, footer_y),
        0.89, 0.050,
        boxstyle="round,pad=0.006",
        facecolor="#131c31",
        edgecolor="#22324f",
        transform=fig.transFigure,
        lw=1.0,
    )
    fig.patches.append(rect)

    fig.text(
        0.075, footer_y + 0.025,
        "Model Summary (10-Day):",
        va="center", fontsize=9.5, fontweight="bold", color="#94a3b8",
    )

    col_x = [0.24, 0.40, 0.56, 0.72]
    for (m_name, m_info), cx in zip(model_data.items(), col_x):
        t_min = np.nanmin(m_info["temp"])
        t_max = np.nanmax(m_info["temp"])
        r_sum = np.sum(m_info["precip"])
        w_max = np.nanmax(m_info["wind_spd"])
        summary_txt = f"{m_name}: {t_min:.0f}°/{t_max:.0f}° • {r_sum:.1f}mm • {w_max:.0f}km/h"
        fig.text(
            cx, footer_y + 0.025,
            summary_txt,
            va="center", fontsize=9.0, color=m_info["color"], fontweight="bold",
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    fig.text(
        0.940, footer_y + 0.025,
        f"Generated: {now_str} • Open-Meteo multi-model API",
        ha="right", va="center", fontsize=8.0, color="#64748b",
    )

    plt.savefig(
        output_path,
        facecolor=fig.get_facecolor(),
        edgecolor="none",
        bbox_inches="tight",
        dpi=150,
    )
    plt.close()
    print(f"Meteogram successfully saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_qom_meteogram()
