import os
import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TEHRAN_TZ = ZoneInfo("Asia/Tehran")
LAT = 34.64
LON = 50.87
ELEVATION = 931

MODELS = [
    ("ecmwf_ifs025", "ECMWF", "#d62728"),
    ("gfs_seamless", "GFS", "#1f77b4"),
    ("icon_seamless", "ICON", "#2ca02c"),
    ("gem_seamless", "GEM", "#9467bd"),
]

def fetch_model_data(model_name):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "elevation": ELEVATION,
        "hourly": [
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
        ],
        "models": model_name,
        "timezone": "Asia/Tehran",
        "forecast_days": 10,
    }
    r = requests.get(url, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    hourly = data.get("hourly", {})
    df = pd.DataFrame({
        "time": pd.to_datetime(hourly.get("time")),
        "temp": hourly.get("temperature_2m"),
        "precip": hourly.get("precipitation"),
        "wind_spd": hourly.get("wind_speed_10m"),
        "wind_dir": hourly.get("wind_direction_10m"),
    })
    return df

def generate_qom_meteogram(output_path="qom_live_multimodel_meteogram.png"):
    print("در حال دریافت داده‌های مدل‌ها برای متئوگرام قم...")
    dfs = {}
    for m_code, m_label, _ in MODELS:
        try:
            dfs[m_code] = fetch_model_data(m_code)
            print(f"مدل {m_label} دریافت شد.")
        except Exception as e:
            print(f"خطا در مدل {m_label}: {e}")

    if not dfs:
        raise RuntimeError("هیچ داده‌ای از مدل‌های هواشناسی دریافت نشد.")

    # ادغام و همگام‌سازی زمان‌ها
    base_time = list(dfs.values())[0]["time"]
    temps_df = pd.DataFrame({"time": base_time})
    for m_code, _, _ in MODELS:
        if m_code in dfs:
            temps_df[m_code] = dfs[m_code]["temp"]

    # محاسبه آمار آنسامبل
    model_cols = [c for c in temps_df.columns if c != "time"]
    temps_df["min"] = temps_df[model_cols].min(axis=1)
    temps_df["max"] = temps_df[model_cols].max(axis=1)
    temps_df["mean"] = temps_df[model_cols].mean(axis=1)

    fig, axes = plt.subplots(
        3, 1, figsize=(15, 12), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.3, 1.8], "hspace": 0.22}
    )

    # ------------------ پنل ۱: دما ------------------
    ax1 = axes[0]
    ax1.set_facecolor("#fafbfc")
    ax1.grid(True, linestyle="--", alpha=0.5, color="#ccc")

    # سایه دامنه پراکندگی
    ax1.fill_between(
        temps_df["time"], temps_df["min"], temps_df["max"],
        color="#ffe8cc", alpha=0.55, label="Ensemble spread (Min-Max)"
    )

    for m_code, m_label, color in MODELS:
        if m_code in dfs:
            ax1.plot(
                dfs[m_code]["time"], dfs[m_code]["temp"],
                label=m_label, color=color, linewidth=2.0
            )

    ax1.set_ylabel("Temperature (°C)", fontsize=12, fontweight="bold")
    ax1.set_title("Iran, Qom - Ali Jazebi", fontsize=15, fontweight="bold", pad=12)
    ax1.legend(loc="upper left", ncol=5, frameon=True, facecolor="white", edgecolor="#ddd")

    # درج برچسب‌های دمای بیشینه و کمینه روزانه
    temps_df["date"] = temps_df["time"].dt.date
    for dt, group in temps_df.groupby("date"):
        t_max = group["mean"].max()
        t_min = group["mean"].min()
        t_max_row = group.loc[group["mean"] == t_max].iloc[0]
        t_min_row = group.loc[group["mean"] == t_min].iloc[0]
        ax1.annotate(
            f"{t_max:.0f}°", (t_max_row["time"], t_max),
            textcoords="offset points", xytext=(0, 6),
            ha="center", fontsize=9, fontweight="bold", color="#d62728"
        )
        ax1.annotate(
            f"{t_min:.0f}°", (t_min_row["time"], t_min),
            textcoords="offset points", xytext=(0, -12),
            ha="center", fontsize=9, fontweight="bold", color="#1f77b4"
        )

    # ------------------ پنل ۲: بارش ------------------
    ax2 = axes[1]
    ax2.set_facecolor("#fafbfc")
    ax2.grid(True, linestyle="--", alpha=0.5, color="#ccc")

    # میانگین بارش مدل‌ها
    p_df = pd.DataFrame({"time": base_time})
    for m_code, _, _ in MODELS:
        if m_code in dfs:
            p_df[m_code] = dfs[m_code]["precip"].fillna(0)
    p_cols = [c for c in p_df.columns if c != "time"]
    p_df["mean_p"] = p_df[p_cols].mean(axis=1)

    width = 0.035
    ax2.bar(
        p_df["time"], p_df["mean_p"],
        width=width, color="#2b8cbe", alpha=0.75, label="Precipitation (mm)"
    )
    for _, row in p_df.iterrows():
        if row["mean_p"] >= 0.2:
            ax2.text(
                row["time"], row["mean_p"] + 0.1, f"{row['mean_p']:.1f}",
                ha="center", va="bottom", fontsize=8, color="#084081"
            )

    ax2.set_ylabel("Precip (mm)", fontsize=12, fontweight="bold")
    ax2.set_ylim(0, max(p_df["mean_p"].max() * 1.35, 3.0))
    ax2.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#ddd")

    # ------------------ پنل ۳: بادها (۴ ترک افقی) ------------------
    ax3 = axes[2]
    ax3.set_facecolor("#fafbfc")
    ax3.grid(True, linestyle="--", alpha=0.5, color="#ccc")

    y_positions = [4, 3, 2, 1]
    y_labels = []
    bg_colors = ["#ffebee", "#e3f2fd", "#e8f8f5", "#f3e5f5"]

    for i, ((m_code, m_label, col), y_pos, bg) in enumerate(zip(MODELS, y_positions, bg_colors)):
        y_labels.append(m_label)
        ax3.axhspan(y_pos - 0.45, y_pos + 0.45, color=bg, alpha=0.5, zorder=0)

        if m_code in dfs:
            df_m = dfs[m_code].copy()
            # گام ۶ ساعته بادها: ۰۰, ۰۶, ۱۲, ۱۸
            df_6h = df_m[df_m["time"].dt.hour.isin([0, 6, 12, 18])].copy()

            for _, row in df_6h.iterrows():
                spd_kmh = row["wind_spd"]
                spd_kt = spd_kmh * 0.539957 if pd.notnull(spd_kmh) else 0
                deg = row["wind_dir"] if pd.notnull(row["wind_dir"]) else 0

                rad = np.deg2rad(deg)
                u = -spd_kt * np.sin(rad)
                v = -spd_kt * np.cos(rad)

                t_num = mdates.date2num(row["time"])
                if spd_kt < 2.5:
                    ax3.plot(t_num, y_pos, marker="o", markersize=4, fillstyle="none", color=col, zorder=3)
                else:
                    ax3.barbs(
                        t_num, y_pos, u, v,
                        length=5.5, barbcolor=col, flagcolor=col,
                        linewidth=1.1, zorder=3
                    )

    ax3.set_yticks(y_positions)
    ax3.set_yticklabels(y_labels, fontsize=10, fontweight="bold")
    ax3.set_ylim(0.4, 4.6)
    ax3.set_ylabel("10m Wind", fontsize=12, fontweight="bold")

    # تنظیم قالب تاریخ برای تمامی پنل‌ها
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a\n%d %b"))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        ax.tick_params(axis="x", labelbottom=True, labelsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"متئوگرام اختصاصی با موفقیت در {output_path} ذخیره شد.")
    return output_path

if __name__ == "__main__":
    generate_qom_meteogram()
