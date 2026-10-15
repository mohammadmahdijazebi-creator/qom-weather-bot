"""
Multi-Model Ensemble Meteogram for Qom, Iran
Header: Iran, Qom - Ali Jazebi
Design: Premium Dark Theme, 3 subplots (Temp + Spread, Grouped Precip, 4-Row Wind Barbs), Model Summary Footer.
Models: ECMWF IFS, GFS, ICON, GEM
"""
import os
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TEHRAN_TZ = ZoneInfo("Asia/Tehran")
LAT, LON = 34.64, 50.87
STATION_LABEL = "Iran, Qom - Ali Jazebi"

# پالت رنگی اختصاصی مدل‌ها در تم دارک
PALETTE = {
    "bg": "#0c1222",
    "card_bg": "#121b2d",
    "text": "#e2e8f0",
    "text_muted": "#8da2fb",
    "grid": "#1e293b",
    "ecmwf": "#ff4d4f",
    "gfs": "#38bdf8",
    "icon": "#34d399",
    "gem": "#c084fc",
    "spread": "#1e3a5f",
}

def fetch_openmeteo_data():
    """دریافت داده‌های همزمان ۴ مدل اصلی از Open-Meteo"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": [
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
        ],
        "models": ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "gem_seamless"],
        "forecast_days": 10,
        "timezone": "Asia/Tehran",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def generate_qom_meteogram(output_path="qom_live_multimodel_meteogram.png"):
    data = fetch_openmeteo_data()
    hourly = data["hourly"]
    times = pd.to_datetime(hourly["time"])

    # متغیرهای دما
    t_ecmwf = hourly.get("temperature_2m_ecmwf_ifs025", [None]*len(times))
    t_gfs = hourly.get("temperature_2m_gfs_seamless", [None]*len(times))
    t_icon = hourly.get("temperature_2m_icon_seamless", [None]*len(times))
    t_gem = hourly.get("temperature_2m_gem_seamless", [None]*len(times))

    # بارش
    p_ecmwf = hourly.get("precipitation_ecmwf_ifs025", [0]*len(times))
    p_gfs = hourly.get("precipitation_gfs_seamless", [0]*len(times))
    p_icon = hourly.get("precipitation_icon_seamless", [0]*len(times))
    p_gem = hourly.get("precipitation_gem_seamless", [0]*len(times))

    # باد
    ws_ecmwf = hourly.get("wind_speed_10m_ecmwf_ifs025", [0]*len(times))
    wd_ecmwf = hourly.get("wind_direction_10m_ecmwf_ifs025", [0]*len(times))
    ws_gfs = hourly.get("wind_speed_10m_gfs_seamless", [0]*len(times))
    wd_gfs = hourly.get("wind_direction_10m_gfs_seamless", [0]*len(times))
    ws_icon = hourly.get("wind_speed_10m_icon_seamless", [0]*len(times))
    wd_icon = hourly.get("wind_direction_10m_icon_seamless", [0]*len(times))
    ws_gem = hourly.get("wind_speed_10m_gem_seamless", [0]*len(times))
    wd_gem = hourly.get("wind_direction_10m_gem_seamless", [0]*len(times))

    df = pd.DataFrame({
        "time": times,
        "t_ec": t_ecmwf, "t_gfs": t_gfs, "t_icon": t_icon, "t_gem": t_gem,
        "p_ec": p_ecmwf, "p_gfs": p_gfs, "p_icon": p_icon, "p_gem": p_gem,
        "ws_ec": ws_ecmwf, "wd_ec": wd_ecmwf,
        "ws_gfs": ws_gfs, "wd_gfs": wd_gfs,
        "ws_icon": ws_icon, "wd_icon": wd_icon,
        "ws_gem": ws_gem, "wd_gem": wd_gem,
    })

    # محاسبه انحراف معیار و میانگین دما برای هاله آنسامبل
    temp_cols = ["t_ec", "t_gfs", "t_icon", "t_gem"]
    df["t_mean"] = df[temp_cols].mean(axis=1)
    df["t_std"] = df[temp_cols].std(axis=1)
    df["t_upper"] = df["t_mean"] + df["t_std"]
    df["t_lower"] = df["t_mean"] - df["t_std"]

    # تنظیمات شکل و فونت در پس‌زمینه دارک
    plt.rcParams.update({
        "figure.facecolor": PALETTE["bg"],
        "axes.facecolor": PALETTE["card_bg"],
        "axes.edgecolor": "#1e293b",
        "axes.labelcolor": PALETTE["text"],
        "xtick.color": PALETTE["text_muted"],
        "ytick.color": PALETTE["text_muted"],
        "text.color": PALETTE["text"],
        "grid.color": PALETTE["grid"],
        "grid.alpha": 0.4,
        "grid.linestyle": "--",
    })

    fig, axes = plt.subplots(3, 1, figsize=(16, 17), gridspec_kw={"height_ratios": [4, 2.5, 3.2]})
    fig.subplots_adjust(top=0.91, bottom=0.08, hspace=0.35, left=0.07, right=0.96)

    # سربرگ اختصاصی
    fig.suptitle(STATION_LABEL, fontsize=20, weight="bold", color="#ffffff", y=0.97)
    sub_title = (
        f"Multi-Model Meteogram • 10-Day Hourly Forecast • "
        f"{times.iloc[0].strftime('%a %d %b %Y')} to {times.iloc[-1].strftime('%a %d %b %Y')} • "
        f"{LAT}°N {LON}°E • Live Open-Meteo"
    )
    fig.text(0.5, 0.945, sub_title, ha="center", fontsize=11, color="#94a3b8")

    # -------------------------------------------------------------
    # پنل ۱: دما با هاله آنسامبل و برچسب‌های واضح بیشینه/کمینه
    # -------------------------------------------------------------
    ax1 = axes[0]
    ax1.fill_between(df["time"], df["t_lower"], df["t_upper"], color=PALETTE["spread"], alpha=0.55, label="Model spread (±1σ)")
    ax1.plot(df["time"], df["t_ec"], color=PALETTE["ecmwf"], linewidth=2.2, label="ECMWF")
    ax1.plot(df["time"], df["t_gfs"], color=PALETTE["gfs"], linewidth=2.0, label="GFS")
    ax1.plot(df["time"], df["t_icon"], color=PALETTE["icon"], linewidth=2.0, label="ICON")
    ax1.plot(df["time"], df["t_gem"], color=PALETTE["gem"], linewidth=2.0, label="GEM")

    ax1.set_title("Temperature — ensemble lines with model spread and daily max/min (°C)", loc="left", fontsize=12, pad=10, weight="bold")
    ax1.set_ylabel("Temperature (°C)", fontsize=11)
    ax1.grid(True)
    ax1.legend(loc="upper right", ncol=5, frameon=True, facecolor="#0f172a", edgecolor="#334155", fontsize=9.5)

    # برچسب‌گذاری بیشینه و کمینه‌های روزانه در باکس‌های اختصاصی
    df["date"] = df["time"].dt.date
    for date, group in df.groupby("date"):
        # بیشینه
        max_idx = group["t_mean"].idxmax()
        max_row = group.loc[max_idx]
        max_val = int(round(max_row[temp_cols].max()))
        ax1.annotate(
            f"{max_val}°",
            xy=(max_row["time"], max_val),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9.5,
            weight="bold",
            color="#ffffff",
            bbox=dict(boxstyle="round,pad=0.25", fc="#d97706", ec="none", alpha=0.9),
        )

        # کمینه
        min_idx = group["t_mean"].idxmin()
        min_row = group.loc[min_idx]
        min_val = int(round(min_row[temp_cols].min()))
        ax1.annotate(
            f"{min_val}°",
            xy=(min_row["time"], min_val),
            xytext=(0, -11),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=9.5,
            weight="bold",
            color="#ffffff",
            bbox=dict(boxstyle="round,pad=0.25", fc="#0284c7", ec="none", alpha=0.9),
        )

    # -------------------------------------------------------------
    # پنل ۲: بارش تفکیک‌شده و دسته‌بندی‌شده بر اساس مدل (Grouped)
    # -------------------------------------------------------------
    ax2 = axes[1]
    w = 0.045  # پهنای میله‌ها در محور زمان
    t_num = mdates.date2num(df["time"])
    ax2.bar(t_num - 1.5*w, df["p_ec"], width=w, color=PALETTE["ecmwf"], label="ECMWF", alpha=0.9)
    ax2.bar(t_num - 0.5*w, df["p_gfs"], width=w, color=PALETTE["gfs"], label="GFS", alpha=0.9)
    ax2.bar(t_num + 0.5*w, df["p_icon"], width=w, color=PALETTE["icon"], label="ICON", alpha=0.9)
    ax2.bar(t_num + 1.5*w, df["p_gem"], width=w, color=PALETTE["gem"], label="GEM", alpha=0.9)

    ax2.set_title("Precipitation (mm) — grouped per model", loc="left", fontsize=12, pad=10, weight="bold")
    ax2.set_ylabel("Precipitation (mm)", fontsize=11)
    ax2.grid(True)
    ax2.legend(loc="upper right", ncol=4, frameon=True, facecolor="#0f172a", edgecolor="#334155", fontsize=9.5)

    # درج مجموع بارش روی رویدادهای بارشی
    for date, group in df.groupby("date"):
        tot_day = group[["p_ec", "p_gfs", "p_icon", "p_gem"]].sum().max()
        if tot_day > 0.4:
            mid_time = group["time"].iloc[len(group)//2]
            ax2.text(mid_time, tot_day + 0.15, f"{tot_day:.1f} mm", ha="center", va="bottom", fontsize=9, color="#ffffff", weight="bold")

    # -------------------------------------------------------------
    # پنل ۳: بارب‌های باد ۴ مدل در ۴ تراک با نوارهای رنگی ملایم
    # -------------------------------------------------------------
    ax3 = axes[2]
    # نمونه‌برداری هر ۶ ساعت برای تمیزی و خوانایی
    sub_df = df.iloc[::6].copy()
    sub_t = mdates.date2num(sub_df["time"])

    # نوارهای پس‌زمینه برای تفکیک مدل‌ها
    ax3.axhspan(3.5, 4.5, color=PALETTE["ecmwf"], alpha=0.08)
    ax3.axhspan(2.5, 3.5, color=PALETTE["gfs"], alpha=0.08)
    ax3.axhspan(1.5, 2.5, color=PALETTE["icon"], alpha=0.08)
    ax3.axhspan(0.5, 1.5, color=PALETTE["gem"], alpha=0.08)

    models_wind = [
        ("ECMWF", 4, sub_df["ws_ec"], sub_df["wd_ec"], PALETTE["ecmwf"]),
        ("GFS", 3, sub_df["ws_gfs"], sub_df["wd_gfs"], PALETTE["gfs"]),
        ("ICON", 2, sub_df["ws_icon"], sub_df["wd_icon"], PALETTE["icon"]),
        ("GEM", 1, sub_df["ws_gem"], sub_df["wd_gem"], PALETTE["gem"]),
    ]

    for name, y_pos, spd, direct, col in models_wind:
        # تبدیل سرعت کیلومتر بر ساعت به نات (knot)
        spd_kt = (spd * 0.539957).fillna(0).values
        dir_rad = np.radians(direct.fillna(0).values)

        u = -spd_kt * np.sin(dir_rad)
        v = -spd_kt * np.cos(dir_rad)

        for i in range(len(sub_t)):
            # اگر باد کمتر از ۲ نات باشد، دایره آرام (Calm) می‌کشیم
            if spd_kt[i] < 2.0:
                ax3.plot(sub_t[i], y_pos, "o", mfc="none", mec=col, ms=5.5, mew=1.5)
            else:
                ax3.barbs(
                    sub_t[i], y_pos, u[i], v[i],
                    length=5.6, barbcolor=col, flagcolor=col,
                    linewidth=1.2, pivot="middle"
                )

    ax3.set_ylim(0.4, 4.6)
    ax3.set_yticks([4, 3, 2, 1])
    ax3.set_yticklabels(["ECMWF", "GFS", "ICON", "GEM"], weight="bold", fontsize=10.5)
    ax3.get_yticklabels()[0].set_color(PALETTE["ecmwf"])
    ax3.get_yticklabels()[1].set_color(PALETTE["gfs"])
    ax3.get_yticklabels()[2].set_color(PALETTE["icon"])
    ax3.get_yticklabels()[3].set_color(PALETTE["gem"])

    ax3.set_title("10 m Wind (barbs, kt) — one row per model, 6-hourly", loc="left", fontsize=12, pad=10, weight="bold")
    ax3.grid(True, axis="x")

    # فرمت تاریخ و محور افقی برای هر ۳ پنل
    for ax in axes:
        ax.set_xlim(df["time"].iloc[0], df["time"].iloc[-1])
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))
        ax.tick_params(axis="x", labelsize=9.5)

    # -------------------------------------------------------------
    # نوار وضعیت زیرین (Model Summary Footer)
    # -------------------------------------------------------------
    summary_text = (
        f"Model Summary (10-Day):     "
        f"ECMWF: {df['t_ec'].min():.0f}°/{df['t_ec'].max():.0f}° • {df['p_ec'].sum():.1f}mm • {df['ws_ec'].max():.0f}km/h     "
        f"GFS: {df['t_gfs'].min():.0f}°/{df['t_gfs'].max():.0f}° • {df['p_gfs'].sum():.1f}mm • {df['ws_gfs'].max():.0f}km/h     "
        f"ICON: {df['t_icon'].min():.0f}°/{df['t_icon'].max():.0f}° • {df['p_icon'].sum():.1f}mm • {df['ws_icon'].max():.0f}km/h     "
        f"GEM: {df['t_gem'].min():.0f}°/{df['t_gem'].max():.0f}° • {df['p_gem'].sum():.1f}mm • {df['ws_gem'].max():.0f}km/h"
    )
    fig.text(0.07, 0.035, summary_text, fontsize=9.2, color="#94a3b8", weight="bold")
    gen_time_str = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")
    fig.text(0.96, 0.02, f"Generated: {gen_time_str} • Open-Meteo multi-model API", ha="right", fontsize=8, color="#64748b")

    plt.savefig(output_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"متئوگرام تاریک قم با موفقیت ذخیره شد: {output_path}")

if __name__ == "__main__":
    generate_qom_meteogram()
