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

LAT, LON = 34.64, 50.87
TIMEZONE = "Asia/Tehran"
FORECAST_DAYS = 10

MODELS = [
    {
        "id": "ecmwf_ifs025",
        "name": "ECMWF",
        "color": "#38bdf8",
        "wind_color": "#e05252",
    },
    {"id": "gfs_seamless", "name": "GFS", "color": "#f87171", "wind_color": "#38bdf8"},
    {
        "id": "icon_seamless",
        "name": "ICON",
        "color": "#4ade80",
        "wind_color": "#4ade80",
    },
    {"id": "gem_seamless", "name": "GEM", "color": "#c084fc", "wind_color": "#c084fc"},
]


def fetch_live_data(timeout=20, retries=3):
    """دریافت داده‌های زنده و لحظه‌ای هواشناسی با مکانیزم تلاش مجدد"""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m",
        "models": ",".join(m["id"] for m in MODELS),
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
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data, True
        except Exception as e:
            if attempt == retries:
                print(f"[Warning] API connection failed: {e}")
                return None, False


def generate_qom_meteogram(output_path="qom_live_multimodel_meteogram.png"):
    """تابع اصلی تولید تصویر متئوگرام که در هر بار اجرا خروجی تازه می‌سازد"""
    data, is_live = fetch_live_data()
    if not data or "hourly" not in data:
        raise RuntimeError("امکان دریافت داده‌های هواشناسی از سرور فراهم نشد.")

    hourly = data["hourly"]
    time_strs = hourly["time"]
    time_dts = [datetime.fromisoformat(t) for t in time_strs]
    x_num = mdates.date2num(time_dts)

    # استخراج سری‌های زمانی مدل‌ها
    model_data = {}
    for m in MODELS:
        mid = m["id"]
        t_key = f"temperature_2m_{mid}"
        p_key = f"precipitation_{mid}"
        ws_key = f"wind_speed_10m_{mid}"
        wd_key = f"wind_direction_10m_{mid}"

        temps = hourly.get(t_key, [])
        precips = hourly.get(p_key, [0.0] * len(time_dts))
        winds = hourly.get(ws_key, [0.0] * len(time_dts))
        dirs = hourly.get(wd_key, [0.0] * len(time_dts))

        model_data[m["name"]] = {
            "temp": np.array(temps, dtype=float),
            "precip": np.array(precips, dtype=float),
            "wind_speed": np.array(winds, dtype=float),
            "wind_dir": np.array(dirs, dtype=float),
            "color": m["color"],
            "wind_color": m["wind_color"],
        }

    # تنظیمات ظاهری دارک
    plt.rcParams.update(
        {
            "text.color": "#e2e8f0",
            "axes.labelcolor": "#94a3b8",
            "xtick.color": "#94a3b8",
            "ytick.color": "#94a3b8",
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        }
    )

    fig = plt.figure(figsize=(16.5, 14.6), dpi=150, facecolor="#0e1526")
    gs = fig.add_gridspec(
        3,
        1,
        height_ratios=[3.4, 2.3, 2.4],
        hspace=0.38,
        left=0.07,
        right=0.96,
        top=0.91,
        bottom=0.09,
    )

    ax_temp = fig.add_subplot(gs[0, 0], facecolor="#131c31")
    ax_precip = fig.add_subplot(gs[1, 0], facecolor="#131c31")
    ax_wind = fig.add_subplot(gs[2, 0], facecolor="#131c31")

    # هدر و تیتر
    fig.text(
        0.5,
        0.965,
        "Iran, Qom - Ali Jazebi",
        fontsize=21,
        weight="bold",
        ha="center",
        color="#ffffff",
    )
    start_str = time_dts[0].strftime("%a %d %b %Y")
    end_str = time_dts[-1].strftime("%a %d %b %Y")
    fig.text(
        0.5,
        0.938,
        f"Multi-Model Meteogram • 10-Day Hourly Forecast • {start_str} to {end_str} • 34.64°N 50.87°E • Live Open-Meteo",
        fontsize=10.5,
        ha="center",
        color="#94a3b8",
    )

    def style_x_axis(ax):
        ax.set_xlim(x_num[0] - 0.2, x_num[-1] + 0.2)
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        ax.grid(True, which="major", axis="x", color="#2a3b5c", alpha=0.45, ls="--")
        ax.grid(True, which="major", axis="y", color="#2a3b5c", alpha=0.35, ls=":")
        ax.tick_params(labelsize=10, pad=5)
        for spine in ax.spines.values():
            spine.set_color("#22324f")

    # ================= 1. پنل دما (کاملاً فریز و دست‌نخورده) =================
    ax_temp.set_title(
        "Temperature — ensemble lines with model spread and daily max/min (°C)",
        fontsize=12,
        weight="bold",
        loc="left",
        pad=10,
    )
    all_temps = np.array([m["temp"] for m in model_data.values()])
    mean_temp = np.nanmean(all_temps, axis=0)
    std_temp = np.nanstd(all_temps, axis=0)
    ax_temp.fill_between(
        x_num,
        mean_temp - std_temp,
        mean_temp + std_temp,
        color="#38bdf8",
        alpha=0.14,
        label="Model spread (±1σ)",
    )

    for name, m in model_data.items():
        ax_temp.plot(
            x_num, m["temp"], color=m["color"], lw=2.0, label=name, alpha=0.92
        )

    # برچسب بیشینه و کمینه روزانه
    days = {}
    for dt, t in zip(time_dts, mean_temp):
        d_str = dt.strftime("%Y-%m-%d")
        days.setdefault(d_str, []).append((dt, t))

    for d_str, entries in days.items():
        if len(entries) < 12:
            continue
        max_dt, max_val = max(entries, key=lambda x: x[1])
        min_dt, min_val = min(entries, key=lambda x: x[1])
        ax_temp.text(
            mdates.date2num(max_dt),
            max_val + 1.2,
            f"{int(round(max_val))}°",
            ha="center",
            va="bottom",
            fontsize=9.5,
            weight="bold",
            color="#ffedd5",
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="#9a3412",
                edgecolor="#ea580c",
                alpha=0.75,
            ),
        )
        ax_temp.text(
            mdates.date2num(min_dt),
            min_val - 1.2,
            f"{int(round(min_val))}°",
            ha="center",
            va="top",
            fontsize=9.5,
            weight="bold",
            color="#e0f2fe",
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="#0369a1",
                edgecolor="#0284c7",
                alpha=0.75,
            ),
        )

    ax_temp.set_ylabel("Temperature (°C)", fontsize=11)
    ax_temp.legend(loc="upper right", frameon=False, ncol=5, fontsize=9.5)
    style_x_axis(ax_temp)

    # ================= 2. پنل بارش (عریض، مرتفع و واضح) =================
    ax_precip.set_title(
        "Precipitation (mm) — grouped per model",
        fontsize=12,
        weight="bold",
        loc="left",
        pad=10,
    )
    bar_width = 0.05
    offsets = [-0.075, -0.025, 0.025, 0.075]

    for idx, (name, m) in enumerate(model_data.items()):
        ax_precip.bar(
            x_num + offsets[idx],
            m["precip"],
            width=bar_width,
            color=m["color"],
            alpha=0.85,
            label=name,
        )

    # برچسب بارش‌های قابل توجه
    for d_str, entries in days.items():
        day_dts = [e[0] for e in entries]
        day_indices = [
            i for i, t in enumerate(time_dts) if t.strftime("%Y-%m-%d") == d_str
        ]
        day_precip_max = max(
            np.sum(m["precip"][day_indices]) for m in model_data.values()
        )
        if day_precip_max >= 0.2:
            mid_time = mdates.date2num(day_dts[len(day_dts) // 2])
            ax_precip.text(
                mid_time,
                day_precip_max + 0.1,
                f"{day_precip_max:.1f} mm",
                ha="center",
                va="bottom",
                fontsize=9.5,
                weight="bold",
                color="#e2e8f0",
            )

    ax_precip.set_ylabel("Precipitation (mm)", fontsize=11)
    ax_precip.set_ylim(
        0,
        max(
            1.0,
            max(np.max(m["precip"]) for m in model_data.values()) * 1.35
            if any(np.max(m["precip"]) > 0 for m in model_data.values())
            else 1.0,
        ),
    )
    ax_precip.legend(loc="upper right", frameon=False, ncol=4, fontsize=9.5)
    style_x_axis(ax_precip)

    # ================= 3. پنل باد (بارب استاندارد ۶ ساعته طبق شکل ۲) =================
    ax_wind.set_title(
        "10 m Wind (barbs, kt) — one row per model, 6-hourly",
        fontsize=12,
        weight="bold",
        loc="left",
        pad=10,
    )
    ax_wind.set_ylim(-0.5, 3.5)
    ax_wind.set_yticks([])

    # نمونه‌برداری دقیقاً ۶ ساعته (00, 06, 12, 18)
    six_indices = [i for i, dt in enumerate(time_dts) if dt.hour in [0, 6, 12, 18]]
    x_wind = [x_num[i] for i in six_indices]

    for r_idx, (name, m) in enumerate(model_data.items()):
        y_pos = 3 - r_idx  # چیدمان از بالا به پایین: ECMWF, GFS, ICON, GEM

        # نوار پس‌زمینه افقی مجزا برای هر مدل
        ax_wind.axhspan(
            y_pos - 0.35, y_pos + 0.35, color=m["wind_color"], alpha=0.06, lw=0
        )
        ax_wind.text(
            x_num[0] - 0.18,
            y_pos,
            name,
            ha="right",
            va="center",
            fontsize=11,
            weight="bold",
            color=m["wind_color"],
        )

        speeds_kt = m["wind_speed"][six_indices] * 0.539957  # تبدیل km/h به knots
        directions_deg = m["wind_dir"][six_indices]

        # مؤلفه‌های استاندارد جهت باد هواشناسی (سمت وزش باد به مرکز)
        rads = np.radians(directions_deg)
        u_arr = -speeds_kt * np.sin(rads)
        v_arr = -speeds_kt * np.cos(rads)

        calm_x, calm_y = [], []
        barb_x, barb_y, barb_u, barb_v = [], [], [], []

        for x_val, spd, u, v in zip(x_wind, speeds_kt, u_arr, v_arr):
            if spd < 2.5:  # باد آرام به‌صورت دایره توخالی
                calm_x.append(x_val)
                calm_y.append(y_pos)
            else:
                barb_x.append(x_val)
                barb_y.append(y_pos)
                barb_u.append(u)
                barb_v.append(v)

        if calm_x:
            ax_wind.plot(
                calm_x,
                calm_y,
                "o",
                mfc="none",
                mec=m["wind_color"],
                mew=1.6,
                ms=5.5,
            )

        if barb_x:
            ax_wind.barbs(
                barb_x,
                barb_y,
                barb_u,
                barb_v,
                length=6.5,
                pivot="middle",
                barbcolor=m["wind_color"],
                flagcolor=m["wind_color"],
                linewidth=1.2,
                barb_increments=dict(half=5, full=10, flag=50),
            )

    style_x_axis(ax_wind)

    # ================= فوتر (کارت خلاصه بدون تداخل متن) =================
    footer_y = 0.015
    rect = FancyBboxPatch(
        (0.07, footer_y),
        0.89,
        0.05,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        facecolor="#131c31",
        edgecolor="#22324f",
        transform=fig.transFigure,
        clip_on=False,
    )
    fig.patches.append(rect)

    fig.text(
        0.085,
        footer_y + 0.033,
        "Model Summary (10-Day):",
        fontsize=10,
        weight="bold",
        color="#e2e8f0",
        va="center",
    )
    col_x = [0.24, 0.40, 0.56, 0.72]
    for idx, (name, m) in enumerate(model_data.items()):
        t_min = np.min(m["temp"])
        t_max = np.max(m["temp"])
        tot_rain = np.sum(m["precip"])
        max_wind = np.max(m["wind_speed"])
        stat_text = (
            f"{name}: {t_min:.0f}°/{t_max:.0f}° • {tot_rain:.1f}mm • {max_wind:.0f}km/h"
        )
        fig.text(
            col_x[idx],
            footer_y + 0.033,
            stat_text,
            fontsize=8.8,
            color=m["color"],
            va="center",
        )

    fig.text(
        0.95,
        footer_y + 0.013,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} • Open-Meteo multi-model API",
        fontsize=8,
        color="#64748b",
        ha="right",
        va="center",
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
