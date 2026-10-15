"""
Multi-Model Meteogram Generator for Qom Province Stations
Generates 10-day meteograms using Open-Meteo Ensemble & Deterministic APIs:
- Panel 1: Temperature (ECMWF, GFS, ICON, GEM + ECMWF Ensemble spread shading)
- Panel 2: Total Precipitation with bar labels (mm)
- Panel 3: Horizontal 10m Wind Barbs across 4 Model tracks (knots)
"""

import sys
import os
import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict

# Target Stations Dictionary
STATIONS = {
    "qom": {
        "name_fa": "قم",
        "name_en": "Qom",
        "lat": 34.64,
        "lon": 50.87,
        "output": "meteogram_qom.png"
    },
    "kahak": {
        "name_fa": "کهک",
        "name_en": "Kahak",
        "lat": 34.3938,
        "lon": 50.8643,
        "output": "meteogram_kahak.png"
    },
    "dastjerd": {
        "name_fa": "دستجرد",
        "name_en": "Dastjerd",
        "lat": 34.3949,
        "lon": 49.9502,
        "output": "meteogram_dastjerd.png"
    },
    "salafchegan": {
        "name_fa": "سلفچگان",
        "name_en": "Salafchegan",
        "lat": 34.4775,
        "lon": 50.4592,
        "output": "meteogram_salafchegan.png"
    },
    "qahan": {
        "name_fa": "قهان",
        "name_en": "Qahan",
        "lat": 34.7245,
        "lon": 50.2632,
        "output": "meteogram_qahan.png"
    }
}

MODEL_COLORS = {
    "ECMWF": "#ff4d4d",
    "GFS": "#38bdf8",
    "ICON": "#4ade80",
    "GEM": "#c084fc"
}

def fetch_weather_data(lat, lon):
    """Fetch 10-day forecast and ensemble data from Open-Meteo."""
    try:
        url_det = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&forecast_days=10&timezone=auto"
            f"&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m"
            f"&models=ecmwf_ifs025,gfs_seamless,icon_seamless,gem_seamless"
        )
        r_det = requests.get(url_det, timeout=25)
        r_det.raise_for_status()
        det_data = r_det.json()

        url_ens = (
            f"https://ensemble-api.open-meteo.com/v1/ensemble?"
            f"latitude={lat}&longitude={lon}&forecast_days=10&timezone=auto"
            f"&hourly=temperature_2m&models=ecmwf_ifs025"
        )
        r_ens = requests.get(url_ens, timeout=25)
        r_ens.raise_for_status()
        ens_data = r_ens.json()

        return det_data, ens_data
    except Exception as e:
        print(f"Error fetching data from Open-Meteo: {e}")
        return None, None

def generate_meteogram_for_station(city_key, info):
    lat = info["lat"]
    lon = info["lon"]
    city_en = info["name_en"]
    output_filename = info["output"]

    print(f"Generating meteogram for {city_en} ({lat}, {lon})...")
    det_data, ens_data = fetch_weather_data(lat, lon)
    if not det_data:
        print(f"Skipping {city_en} due to data fetching failure.")
        return False

    hourly_det = det_data.get("hourly", {})
    raw_times = hourly_det.get("time", [])
    if not raw_times:
        print(f"No timeline found for {city_en}.")
        return False

    times = [datetime.fromisoformat(t) for t in raw_times]
    n_pts = len(times)

    # Extract deterministic data
    t_ecmwf = np.array(hourly_det.get("temperature_2m_ecmwf_ifs025", [np.nan] * n_pts), dtype=float)
    t_gfs = np.array(hourly_det.get("temperature_2m_gfs_seamless", [np.nan] * n_pts), dtype=float)
    t_icon = np.array(hourly_det.get("temperature_2m_icon_seamless", [np.nan] * n_pts), dtype=float)
    t_gem = np.array(hourly_det.get("temperature_2m_gem_seamless", [np.nan] * n_pts), dtype=float)

    p_ecmwf = np.array(hourly_det.get("precipitation_ecmwf_ifs025", [0.0] * n_pts), dtype=float)
    p_gfs = np.array(hourly_det.get("precipitation_gfs_seamless", [0.0] * n_pts), dtype=float)
    p_icon = np.array(hourly_det.get("precipitation_icon_seamless", [0.0] * n_pts), dtype=float)
    p_gem = np.array(hourly_det.get("precipitation_gem_seamless", [0.0] * n_pts), dtype=float)

    wspd_ecmwf = np.array(hourly_det.get("wind_speed_10m_ecmwf_ifs025", [0.0] * n_pts), dtype=float)
    wdir_ecmwf = np.array(hourly_det.get("wind_direction_10m_ecmwf_ifs025", [0.0] * n_pts), dtype=float)
    wspd_gfs = np.array(hourly_det.get("wind_speed_10m_gfs_seamless", [0.0] * n_pts), dtype=float)
    wdir_gfs = np.array(hourly_det.get("wind_direction_10m_gfs_seamless", [0.0] * n_pts), dtype=float)
    wspd_icon = np.array(hourly_det.get("wind_speed_10m_icon_seamless", [0.0] * n_pts), dtype=float)
    wdir_icon = np.array(hourly_det.get("wind_direction_10m_icon_seamless", [0.0] * n_pts), dtype=float)
    wspd_gem = np.array(hourly_det.get("wind_speed_10m_gem_seamless", [0.0] * n_pts), dtype=float)
    wdir_gem = np.array(hourly_det.get("wind_direction_10m_gem_seamless", [0.0] * n_pts), dtype=float)

    # Ensemble quantiles (10% - 90%)
    ens_q10 = None
    ens_q90 = None
    if ens_data and "hourly" in ens_data:
        hourly_ens = ens_data["hourly"]
        ens_members = [
            v for k, v in hourly_ens.items()
            if k.startswith("temperature_2m_member") and len(v) == n_pts
        ]
        if ens_members:
            ens_arr = np.array(ens_members, dtype=float)
            ens_q10 = np.nanpercentile(ens_arr, 10, axis=0)
            ens_q90 = np.nanpercentile(ens_arr, 90, axis=0)

    # Plot styling
    plt.style.use('dark_background')
    fig, (ax_temp, ax_precip, ax_wind) = plt.subplots(
        nrows=3, ncols=1, figsize=(14, 11),
        sharex=True,
        gridspec_kw={'height_ratios': [2.2, 1.2, 1.6], 'hspace': 0.18}
    )
    fig.patch.set_facecolor('#0c1222')

    for ax in (ax_temp, ax_precip, ax_wind):
        ax.set_facecolor('#0e1526')
        ax.grid(True, color='#1e293b', linestyle='--', linewidth=0.6, alpha=0.7)
        ax.tick_params(colors='#94a3b8', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#1e293b')

    # Title
    fig.suptitle(
        f"Iran, {city_en} - Ali Jazebi",
        color='#f8fafc', fontsize=16, fontweight='bold', y=0.96
    )

    # PANEL 1: TEMPERATURE
    if ens_q10 is not None and ens_q90 is not None:
        ax_temp.fill_between(
            times, ens_q10, ens_q90,
            color='#ef4444', alpha=0.15, label='ECMWF ENS (10-90%)'
        )

    ax_temp.plot(times, t_ecmwf, color=MODEL_COLORS["ECMWF"], linewidth=2.0, label='ECMWF IFS')
    ax_temp.plot(times, t_gfs, color=MODEL_COLORS["GFS"], linewidth=1.5, label='GFS')
    ax_temp.plot(times, t_icon, color=MODEL_COLORS["ICON"], linewidth=1.5, label='ICON')
    ax_temp.plot(times, t_gem, color=MODEL_COLORS["GEM"], linewidth=1.5, label='GEM')

    ax_temp.set_ylabel("2m Temp (°C)", color='#f8fafc', fontsize=10, fontweight='bold')
    ax_temp.legend(loc='upper right', frameon=True, facecolor='#1e293b', edgecolor='#334155', fontsize=8, labelcolor='#e2e8f0')

    # Daily Max / Min annotations based on ECMWF
    day_indices = defaultdict(list)
    for idx, dt_val in enumerate(times):
        day_indices[dt_val.date()].append(idx)

    for day, indices in day_indices.items():
        day_temps = t_ecmwf[indices]
        valid_mask = ~np.isnan(day_temps)
        if np.any(valid_mask):
            max_pos = indices[np.nanargmax(day_temps)]
            min_pos = indices[np.nanargmin(day_temps)]

            ax_temp.annotate(
                f"{int(round(t_ecmwf[max_pos]))}°",
                xy=(times[max_pos], t_ecmwf[max_pos]),
                xytext=(0, 7), textcoords='offset points',
                ha='center', fontsize=8, fontweight='bold', color='#f87171'
            )
            ax_temp.annotate(
                f"{int(round(t_ecmwf[min_pos]))}°",
                xy=(times[min_pos], t_ecmwf[min_pos]),
                xytext=(0, -12), textcoords='offset points',
                ha='center', fontsize=8, fontweight='bold', color='#60a5fa'
            )

    # PANEL 2: PRECIPITATION
    precip_mean = np.nanmean([p_ecmwf, p_gfs, p_icon, p_gem], axis=0)
    width = 0.038
    bar_rects = ax_precip.bar(times, precip_mean, width=width, color='#38bdf8', alpha=0.85, label='Mean Precip')

    for rect in bar_rects:
        h = rect.get_height()
        if h >= 0.5:
            ax_precip.annotate(
                f"{h:.1f}",
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 2), textcoords="offset points",
                ha='center', va='bottom', fontsize=7, color='#e0f2fe', fontweight='bold'
            )

    ax_precip.set_ylabel("Precip (mm)", color='#f8fafc', fontsize=10, fontweight='bold')
    max_p = np.nanmax(precip_mean) if len(precip_mean) > 0 and not np.isnan(np.nanmax(precip_mean)) else 0.0
    ax_precip.set_ylim(bottom=0, top=max(4.0, max_p * 1.35))

    # PANEL 3: WIND BARBS
    # 4 distinct horizontal rows: ECMWF (3), GFS (2), ICON (1), GEM (0)
    models_wind = [
        ("ECMWF", MODEL_COLORS["ECMWF"], wspd_ecmwf, wdir_ecmwf, 3),
        ("GFS", MODEL_COLORS["GFS"], wspd_gfs, wdir_gfs, 2),
        ("ICON", MODEL_COLORS["ICON"], wspd_icon, wdir_icon, 1),
        ("GEM", MODEL_COLORS["GEM"], wspd_gem, wdir_gem, 0)
    ]

    # Shaded horizontal track backgrounds
    ax_wind.axhspan(2.5, 3.5, color='#ff4d4d', alpha=0.08)
    ax_wind.axhspan(1.5, 2.5, color='#38bdf8', alpha=0.08)
    ax_wind.axhspan(0.5, 1.5, color='#4ade80', alpha=0.08)
    ax_wind.axhspan(-0.5, 0.5, color='#c084fc', alpha=0.08)

    # Sample wind every 6 hours
    mask_6h = np.array([t.hour % 6 == 0 for t in times])
    times_6h = [times[i] for i in range(len(times)) if mask_6h[i]]
    x_num = mdates.date2num(times_6h)

    for name, col, wspd_full, wdir_full, y_pos in models_wind:
        wspd_sub = wspd_full[mask_6h] * 0.539957  # km/h to knots
        wdir_sub = wdir_full[mask_6h]

        rad = np.deg2rad(wdir_sub)
        u = -wspd_sub * np.sin(rad)
        v = -wspd_sub * np.cos(rad)
        y = np.full_like(x_num, y_pos)

        # Plot calm winds as open circle
        calm = wspd_sub < 2.0
        if np.any(calm):
            ax_wind.plot(
                np.array(times_6h)[calm], y[calm],
                'o', markersize=4, markerfacecolor='none',
                markeredgecolor=col, markeredgewidth=1.2
            )

        active = ~calm
        if np.any(active):
            ax_wind.barbs(
                x_num[active], y[active],
                u[active], v[active],
                length=5.5,
                barbcolor=col,
                flagcolor=col,
                linewidth=1.0,
                pivot='middle'
            )

    ax_wind.set_yticks([0, 1, 2, 3])
    ax_wind.set_yticklabels(['GEM', 'ICON', 'GFS', 'ECMWF'], color='#e2e8f0', fontweight='bold', fontsize=9)
    ax_wind.set_ylim(-0.7, 3.7)

    # Date format on X axis
    ax_wind.xaxis.set_major_locator(mdates.DayLocator())
    ax_wind.xaxis.set_major_formatter(mdates.DateFormatter('%a\n%d %b'))

    plt.setp(ax_wind.get_xticklabels(), color='#cbd5e1', fontsize=9, fontweight='bold')
    ax_wind.set_xlim(times[0], times[-1])

    plt.tight_layout()
    plt.subplots_adjust(top=0.92, hspace=0.18)

    fig.savefig(output_filename, dpi=180, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"Meteogram saved successfully: {output_filename}")
    return True

def generate_qom_meteogram():
    """Default runner for all stations."""
    for key, station_info in STATIONS.items():
        try:
            generate_meteogram_for_station(key, station_info)
        except Exception as err:
            print(f"Error processing {key}: {err}")

if __name__ == "__main__":
    generate_qom_meteogram()
