#!/usr/bin/env python3
"""
qom_weather_fixed_bot.py - merged & fixed (bot.py + meteogram_qom.py + new live modules)
- All baseline functions preserved exactly (ECMWF, Yr.no, Foreca, Weather-Forecast,
  iran_met forwarder, Telegram & Bale handlers, atomic JSON state).
- UNCONDITIONAL forced dynamic Qom multi-model meteogram on every run
  (file-existence skip removed).
- Tropical Tidbits GFS Middle East with ALL THREE packages:
  mslp_pcpn, z500a AND mslp_uv850, iterating TROPICAL_HOURS, fh=72 highlighted.
- Fully live 3-day & 7-day regional forecasts (Open-Meteo) for
  Qom, Kahak, Salafchegan, Dastjerd, Qahan + live stability indices
  (CAPE, CIN, LI, K, TT, Showalter) + forced qom_7day_weather_poster.png every run.
"""
#!/usr/bin/env python3
"""
Multi-model meteogram for Qom, Iran (34.64, 50.87) - Ali Jazebi
Style: dark professional meteogram (Image 1) kept intact, with fixes:
  * date labels (Wed 14, Thu 15, ...) beneath EVERY panel (temp / precip / wind)
  * precipitation panel taller with wider bars
  * wind barbs exactly 6-hourly (00/06/12/18), proper u,v conversion (kt),
    calm (<2.5 kt) as open circle, subtle lane strips, model name on left
  * footer: no overlap between model stats and metadata
Data: live Open-Meteo API; cached raw JSON fallback (offline sandbox).
Output: /mnt/data/qom_live_multimodel_meteogram.png
"""
import json, math, os, datetime as dt
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch

LAT, LON = 34.64, 50.87
NDAYS = 10
OUT_PNG = "/mnt/data/qom_live_multimodel_meteogram.png"
MODELS = ["ECMWF", "GFS", "ICON", "GEM"]
API_SUFFIX = {"ECMWF": "ecmwf_ifs025", "GFS": "gfs_seamless",
              "ICON": "icon_seamless", "GEM": "gem_seamless"}
COLORS = {"ECMWF": "#4da3ff", "GFS": "#ff5d5d", "ICON": "#3ddc84", "GEM": "#c77dff"}


def load_data():
    """Try live API, then cached JSON, then deterministic synthetic fallback."""
    URL = ("https://api.open-meteo.com/v1/forecast?latitude=34.64&longitude=50.87"
           "&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m"
           "&models=ecmwf_ifs025,gfs_seamless,icon_seamless,gem_seamless"
           "&forecast_days=10&timezone=auto")
    try:
        from urllib.request import urlopen, Request
        req = Request(URL, headers={"User-Agent": "meteogram/1.0"})
        with urlopen(req, timeout=12) as r:
            print("live fetch OK")
            return json.load(r), True
    except Exception as e:
        print("live fetch failed ->", e)
    for cache in ("/mnt/data/qom_live_mm_raw.json",
                  "/mnt/data/qom_live_multimodel_raw.json"):
        if os.path.exists(cache):
            try:
                with open(cache) as f:
                    print("using cached real API data:", cache)
                    return json.load(f), True
            except Exception as e2:
                print("cache failed:", e2)
    return synthetic_data(), False


def synthetic_data():
    rng = np.random.default_rng(1404)
    t0 = dt.datetime.now().replace(minute=0, second=0, microsecond=0)
    times = [t0 + dt.timedelta(hours=i) for i in range(NDAYS * 24)]
    out = {"hourly": {}}
    temp_f, ps_f, wf = [0.0, -1.2, 0.6, -0.8], [1.0, 1.4, 0.8, 0.9], [1.0, 1.15, 0.95, 1.05]
    for m, cf, ps, wfac in zip(MODELS, temp_f, ps_f, wf):
        T, P, S, D = [], [], [], []
        for i, t in enumerate(times):
            hod = t.hour
            base = 24 + 4 * math.sin(i / 48 * math.pi) + 9 * math.sin((hod - 9) / 24 * 2 * math.pi) + cf
            T.append(round(base + rng.normal(0, 0.3), 2))
            p = round(abs(rng.normal(1.2, 0.6)) * ps, 2) if (120 <= i % 240 < 132 and rng.random() < 0.6) else 0.0
            P.append(p)
            S.append(round(max(1.0, 16 + 8 * math.sin(i / 36) + rng.normal(0, 1.5)) * wfac, 2))
            D.append(int((300 + 20 * math.sin(i / 40) + rng.normal(0, 8)) % 360))
        out["hourly"][f"temperature_2m_{API_SUFFIX[m]}"] = T
        out["hourly"][f"precipitation_{API_SUFFIX[m]}"] = P
        out["hourly"][f"wind_speed_10m_{API_SUFFIX[m]}"] = S
        out["hourly"][f"wind_direction_10m_{API_SUFFIX[m]}"] = D
    out["hourly"]["time"] = [t.isoformat() for t in times]
    return out, False


def generate_qom_meteogram(out_path=None):
    """FORCED dynamic generation: always rebuilds the multi-model meteogram.
    (old file-existence skip removed by design - qom_live_multimodel_meteogram.png
    is freshly regenerated on EVERY single run)"""
    out_file = out_path or OUT_PNG
    raw, live = load_data()
    H = raw["hourly"]
    times = [dt.datetime.fromisoformat(s) for s in H["time"]]
    n = len(times)
    key = lambda m, v: f"{v}_{API_SUFFIX[m]}"

    def series(m, v):
        a = H.get(key(m, v))
        arr = np.array([np.nan if (a is None or i >= len(a) or a[i] is None) else float(a[i])
                        for i in range(n)])
        if np.isnan(arr).all():
            arr[:] = 0.0
        elif np.isnan(arr).any():
            idx = np.arange(n); good = ~np.isnan(arr)
            arr = np.interp(idx, idx[good], arr[good])
        return arr

    T = {m: series(m, "temperature_2m") for m in MODELS}
    P = {m: series(m, "precipitation") for m in MODELS}
    WS = {m: series(m, "wind_speed_10m") for m in MODELS}
    WD = {m: series(m, "wind_direction_10m") for m in MODELS}
    Tstack = np.vstack([T[m] for m in MODELS])
    t_mean, t_spread = Tstack.mean(axis=0), Tstack.std(axis=0)

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "figure.facecolor": "#0e1526", "axes.facecolor": "#131c31",
        "text.color": "#e8eef7", "axes.edgecolor": "#2a3a5c",
        "axes.labelcolor": "#c9d6ea", "xtick.color": "#9fb2cc",
        "ytick.color": "#9fb2cc", "savefig.facecolor": "#0e1526",
    })
    fig = plt.figure(figsize=(16.5, 14.6))
    # taller precipitation panel (request 3) + generous hspace for date labels
    gs = fig.add_gridspec(3, 1, height_ratios=[3.0, 2.3, 3.0],
                          left=0.075, right=0.965, top=0.905, bottom=0.115,
                          hspace=0.55)

    fig.text(0.5, 0.970, "Iran, Qom - Ali Jazebi", ha="center", va="center",
             fontsize=24, fontweight="bold", color="#ffffff")
    days_span = f"{times[0]:%a %d %b %Y}  to  {times[-1]:%a %d %b %Y}"
    fig.text(0.5, 0.944, f"Multi-Model Meteogram · 10-Day Hourly Forecast · {days_span}"
             f" · {LAT:.2f}°N {LON:.2f}°E · {'Live Open-Meteo' if live else 'offline data'}",
             ha="center", va="center", fontsize=11.5, color="#9fb2cc")

    x = mdates.date2num(times)
    xlim = (x[0], x[-1])
    day0 = times[0].replace(hour=0, minute=0)
    day_ticks = [mdates.date2num(day0 + dt.timedelta(days=d)) for d in range(NDAYS)]
    day_lbls = [(day0 + dt.timedelta(days=d)).strftime("%a %d") for d in range(NDAYS)]

    def style_x(ax, labels=True):
        ax.set_xlim(*xlim)
        ax.xaxis.set_major_locator(mdates.DayLocator())
        if labels:
            ax.set_xticks(day_ticks)
            ax.set_xticklabels(day_lbls, fontsize=10.5, color="#dfe9f7")
        ax.tick_params(axis="x", length=0, pad=6)

    # ===================== 1) Temperature =====================
    ax = fig.add_subplot(gs[0])
    ax.fill_between(x, t_mean - t_spread, t_mean + t_spread,
                    color="#4da3ff", alpha=0.16, label="Model spread (±1σ)")
    for m in MODELS:
        ax.plot(x, T[m], color=COLORS[m], lw=2.0, label=m, zorder=3)
    for dx in day_ticks:
        ax.axvline(dx, color="#2a3a5c", lw=0.9, ls="--", alpha=0.55)
    for d in range(NDAYS):
        sl = slice(d * 24, min((d + 1) * 24, n))
        if sl.stop <= sl.start:
            continue
        hi, lo = Tstack[:, sl].max(axis=0), Tstack[:, sl].min(axis=0)
        xi = x[sl]
        ih, il = int(np.argmax(hi)), int(np.argmin(lo))
        ax.annotate(f"{hi[ih]:.0f}°", (xi[ih], hi[ih]), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=10.5, fontweight="bold",
                    color="#ffb3b3",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#3a1c1c", ec="#ff5d5d", lw=0.8))
        ax.annotate(f"{lo[il]:.0f}°", (xi[il], lo[il]), textcoords="offset points",
                    xytext=(0, -16), ha="center", fontsize=10.5, fontweight="bold",
                    color="#b3d9ff",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#16304a", ec="#4da3ff", lw=0.8))
    ax.set_ylim(float(Tstack.min()) - 4, float(Tstack.max()) + 4)
    ax.set_ylabel("Temperature (°C)", fontsize=11)
    ax.grid(axis="y", color="#22304d", lw=0.6, alpha=0.7)
    style_x(ax, labels=True)                       # dates beneath temperature panel
    ax.legend(loc="upper right", ncols=5, fontsize=10, framealpha=0.15,
              facecolor="#0e1526", edgecolor="#2a3a5c")
    ax.set_title("Temperature — ensemble lines with model spread and daily max/min (°C)",
                 fontsize=12.5, pad=10, loc="left", fontweight="bold")

    # ===================== 2) Precipitation (taller, wider bars) =====================
    ax2 = fig.add_subplot(gs[1])
    nb = len(MODELS)
    slot = 1.0                                     # one day-hour column slot
    bw = slot / nb * 0.92                          # wider grouped bars
    maxp = max(float(P[m].max()) for m in MODELS)
    for k, m in enumerate(MODELS):
        off = (k - (nb - 1) / 2) * (slot / nb)
        ax2.bar(x + off, P[m], width=bw, color=COLORS[m], alpha=0.95, label=m,
                edgecolor="white", linewidth=0.35)
    for d in range(NDAYS):
        sl = slice(d * 24, min((d + 1) * 24, n))
        tot = sum(float(P[m][sl].sum()) for m in MODELS) / nb
        if tot > 0.05:
            xc = (x[sl.start] + x[min(sl.stop - 1, n - 1)]) / 2
            ax2.annotate(f"{tot:.1f} mm", (xc, max(maxp * 1.12, 0.25)),
                         ha="center", fontsize=10.5, color="#bcd3f0", fontweight="bold")
    ax2.set_ylim(0, max(maxp * 1.6, 1.2))
    ax2.set_ylabel("Precipitation (mm)", fontsize=11)
    ax2.grid(axis="y", color="#22304d", lw=0.6, alpha=0.7)
    style_x(ax2, labels=True)                      # dates beneath precipitation panel
    ax2.legend(loc="upper right", ncols=4, fontsize=9.5, framealpha=0.15,
               facecolor="#0e1526", edgecolor="#2a3a5c")
    ax2.set_title("Precipitation (mm) — grouped per model", fontsize=12.5, pad=12,
                  loc="left", fontweight="bold")

    # ===================== 3) Wind barbs — 6-hourly, one row per model =====================
    ax3 = fig.add_subplot(gs[2])
    ys = {m: len(MODELS) - 1 - i for i, m in enumerate(MODELS)}
    lane_h = 0.62                                  # wide lanes -> clear, well-spaced barbs
    for m in MODELS:
        # subtle soft background strip per lane (Image 2 style)
        ax3.add_patch(plt.Rectangle((x[0], ys[m] - lane_h / 2), x[-1] - x[0], lane_h,
                                    facecolor=COLORS[m], alpha=0.07,
                                    edgecolor="none", zorder=0))
        ax3.text(x[0] - 0.012 * (x[-1] - x[0]), ys[m], m, ha="right", va="center",
                 fontsize=12, fontweight="bold", color=COLORS[m])
        # 6-hourly sampling: exactly 00, 06, 12, 18 local hours
        idx = [i for i in range(n) if times[i].hour % 6 == 0]
        us, vs, xs, yy = [], [], [], []
        for i in idx:
            spd_kt = WS[m][i] / 1.852
            if spd_kt < 2.5:                       # calm -> small open circle
                ax3.plot(x[i], ys[m], "o", ms=5.5, mfc="none", mec=COLORS[m],
                         mew=1.4, zorder=4)
                continue
            th = math.radians(WD[m][i])            # direction wind comes FROM
            us.append(-spd_kt * math.sin(th))      # proper u,v in knots!
            vs.append(-spd_kt * math.cos(th))
            xs.append(x[i]); yy.append(ys[m])
        if us:
            ax3.barbs(xs, yy, us, vs, length=6.5, pivot="middle",
                      color=COLORS[m], linewidth=1.0, zorder=4,
                      barb_increments=dict(half=5, full=10, flag=50))
    ax3.set_ylim(-0.75, len(MODELS) - 0.25)
    ax3.set_yticks([])
    ax3.set_ylabel("10 m Wind (barbs, kt)", fontsize=11)
    style_x(ax3, labels=True)                      # dates beneath wind panel
    ax3.grid(axis="x", color="#22304d", lw=0.5, alpha=0.5)
    ax3.set_title("Wind barbs (kt) — one row per model, 6-hourly (00/06/12/18), full barb = 10 kt",
                  fontsize=12.5, pad=10, loc="left", fontweight="bold")

    # ===================== footer: no overlap =====================
    stats = {m: (float(T[m].min()), float(T[m].max()),
                 float(P[m].sum()), float(WS[m].max())) for m in MODELS}
    box = FancyBboxPatch((0.055, 0.012), 0.71, 0.085, transform=fig.transFigure,
                         boxstyle="round,pad=0.008", fc="#131c31", ec="#2a3a5c", lw=1.2)
    fig.add_artist(box)
    fig.text(0.075, 0.080, "Model Summary", fontsize=11, fontweight="bold", color="#ffffff")
    for i, m in enumerate(MODELS):
        a, b, c, w_ = stats[m]
        xx = 0.075 + i * 0.170
        fig.text(xx, 0.058, m, fontsize=10.5, fontweight="bold", color=COLORS[m])
        fig.text(xx, 0.032, f"{a:.0f}°/{b:.0f}° · {c:.1f} mm · {w_:.0f} km/h",
                 fontsize=9.5, color="#c9d6ea")
    # metadata block clearly separated on the right (never overlaps stats)
    fig.text(0.960, 0.080, f"Generated {dt.datetime.now():%Y-%m-%d %H:%M}",
             fontsize=9, color="#9fb2cc", ha="right")
    fig.text(0.960, 0.048, "Data: Open-Meteo multi-model API",
             fontsize=9, color="#9fb2cc", ha="right")

    fig.savefig(out_file, dpi=150)
    print("saved:", out_file, os.path.getsize(OUT_PNG), "bytes | live:", live)
    print("stats:", {m: tuple(round(v, 1) for v in s) for m, s in stats.items()})




import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

KEY72 = "\n⭐ فریم کلیدی ۷۲ ساعته - پایان دوره پیش‌بینی"

# (generate_qom_meteogram is defined locally in this merged script)

# -------------------------------------------------------------
# تنظیمات محیطی
# -------------------------------------------------------------
BOT_TOKEN = (
    os.environ.get("BOT_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
)
CHANNEL_ID = (
    os.environ.get("CHANNEL_ID")
    or os.environ.get("TELEGRAM_CHAT_ID")
)
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = (
    os.environ.get("BALE_CHANNEL_ID")
    or os.environ.get("BALE_CHAT_ID")
)

STATE_FILE = Path("weather_state.json")
TEXT_FILE = Path("forecast_text.txt")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
REQ_TIMEOUT = 50

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
})

# -------------------------------------------------------------
# اهداف متئوگرام ECMWF
# -------------------------------------------------------------
ECMWF_BASE = (
    "https://charts.ecmwf.int/products/opencharts_meteogram"
    "?epsgram=classical_10d"
)
ECMWF_TARGETS = [
    {
        "name": "قم",
        "web_url": f"{ECMWF_BASE}&lat=34.64&lon=50.86&station_name=Qom",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قم",
        "file": "ecmwf_1_qom.png",
    },
    {
        "name": "کهک",
        "web_url": f"{ECMWF_BASE}&lat=34.3938&lon=50.8643&station_name=Kahak",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: کهک",
        "file": "ecmwf_2_kahak.png",
    },
    {
        "name": "دستجرد",
        "web_url": f"{ECMWF_BASE}&lat=34.3949&lon=49.9502&station_name=Dastjerd",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: دستجرد",
        "file": "ecmwf_3_dastjerd.png",
    },
    {
        "name": "سلفچگان",
        "web_url": f"{ECMWF_BASE}&lat=34.4775&lon=50.4592&station_name=Salafchegan",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: سلفچگان",
        "file": "ecmwf_4_salafchegan.png",
    },
    {
        "name": "قاهان",
        "web_url": f"{ECMWF_BASE}&lat=34.7245&lon=50.2632&station_name=Qahan",
        "caption": "📊 متئوگرام ۱۰ روزه ENS مدل اروپایی ECMWF\n📍 ایستگاه: قاهان",
        "file": "ecmwf_5_qahan.png",
    },
]

TROPICAL_HOURS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]

# -------------------------------------------------------------
# اهداف Yr.no
# -------------------------------------------------------------
YR_BASE = "https://www.yr.no/en/forecast"
YR_TARGETS = [
    {
        "name": "جدول قم",
        "url": f"{YR_BASE}/daily-table/2-119208/Iran/Qom%20Province/Qom",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - قم",
        "file": "yr_1_table_qom.png",
    },
    {
        "name": "نمودار قم",
        "url": f"{YR_BASE}/graph/2-119208/Iran/Qom%20Province/Qom",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قم",
        "file": "yr_2_graph_qom.png",
    },
    {
        "name": "جدول کهک",
        "url": f"{YR_BASE}/daily-table/2-122026/Iran/Qom%20Province/Kahak",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - کهک",
        "file": "yr_3_table_kahak.png",
    },
    {
        "name": "نمودار کهک",
        "url": f"{YR_BASE}/graph/2-122026/Iran/Qom%20Province/Kahak",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - کهک",
        "file": "yr_4_graph_kahak.png",
    },
    {
        "name": "جدول سلفچگان",
        "url": f"{YR_BASE}/daily-table/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - سلفچگان",
        "file": "yr_5_table_salaf.png",
    },
    {
        "name": "نمودار سلفچگان",
        "url": f"{YR_BASE}/graph/2-117287/Iran/Qom%20Province/Salafcheg%C4%81n",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - سلفچگان",
        "file": "yr_6_graph_salaf.png",
    },
    {
        "name": "جدول دستجرد",
        "url": f"{YR_BASE}/daily-table/2-137151/Iran/Markazi%20Province/Dastjerd",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - دستجرد",
        "file": "yr_7_table_dastjerd.png",
    },
    {
        "name": "نمودار دستجرد",
        "url": f"{YR_BASE}/graph/2-137151/Iran/Markazi%20Province/Dastjerd",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - دستجرد",
        "file": "yr_8_graph_dastjerd.png",
    },
    {
        "name": "جدول قاهان",
        "url": f"{YR_BASE}/daily-table/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n",
        "caption": "📋 جدول پیش‌بینی ۱۰ روزه Yr.no - قاهان",
        "file": "yr_9_table_qahan.png",
    },
    {
        "name": "نمودار قاهان",
        "url": f"{YR_BASE}/graph/2-120681/Iran/Qom%20Province/Q%C4%81h%C4%81n",
        "caption": "📉 نمودار پیش‌بینی ساعتی Yr.no - قاهان",
        "file": "yr_10_graph_qahan.png",
    },
]

# -------------------------------------------------------------
# اهداف Foreca
# -------------------------------------------------------------
FC_BASE = "https://www.foreca.com"
FORECA_TARGETS = [
    {
        "name": "فورکا ۱۰ روزه قم",
        "url": f"{FC_BASE}/100119208/Qom-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قم",
        "file": "foreca_1_qom_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه قم",
        "url": f"{FC_BASE}/100119208/Qom-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قم",
        "file": "foreca_2_qom_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه کهک",
        "url": f"{FC_BASE}/100122026/Kahak-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - کهک",
        "file": "foreca_3_kahak_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه کهک",
        "url": f"{FC_BASE}/100122026/Kahak-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - کهک",
        "file": "foreca_4_kahak_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه سلفچگان",
        "url": f"{FC_BASE}/100117287/Salafcheg%C4%81n-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - سلفچگان",
        "file": "foreca_5_salaf_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه سلفچگان",
        "url": f"{FC_BASE}/100117287/Salafcheg%C4%81n-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - سلفچگان",
        "file": "foreca_6_salaf_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه دستجرد",
        "url": f"{FC_BASE}/100137165/Dastjerd-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - دستجرد",
        "file": "foreca_7_dast_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه دستجرد",
        "url": f"{FC_BASE}/100137165/Dastjerd-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - دستجرد",
        "file": "foreca_8_dast_15d.png",
    },
    {
        "name": "فورکا ۱۰ روزه قاهان",
        "url": f"{FC_BASE}/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/10-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۰ روزه فورکا (Foreca) - قاهان",
        "file": "foreca_9_qah_10d.png",
    },
    {
        "name": "فورکا ۱۵ روزه قاهان",
        "url": f"{FC_BASE}/100120681/Q%C4%81h%C4%81n-Qom-Province-Iran/15-day-forecast",
        "caption": "☀️ پیش‌بینی ۱۵ روزه فورکا (Foreca) - قاهان",
        "file": "foreca_10_qah_15d.png",
    },
]

# -------------------------------------------------------------
# اهداف Weather-Forecast
# -------------------------------------------------------------
WF_BASE = "https://www.weather-forecast.com/locations"
WEATHER_FORECAST_TARGETS = [
    {
        "name": "قم",
        "url": f"{WF_BASE}/Qom/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: قم",
        "file": "wf_1_qom.png",
    },
    {
        "name": "کهک",
        "url": f"{WF_BASE}/Kahak/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: کهک",
        "file": "wf_2_kahak.png",
    },
    {
        "name": "سلفچگان",
        "url": f"{WF_BASE}/Salafchegan/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: سلفچگان",
        "file": "wf_3_salafchegan.png",
    },
    {
        "name": "دستجرد",
        "url": f"{WF_BASE}/Dastjerd-11/forecasts/latest",
        "caption": "🌐 جدول تفصیلی وضع هوا (Weather-Forecast)\n📍 ایستگاه: دستجرد",
        "file": "wf_4_dastjerd.png",
    },
]

ADS_PATTERNS = [
    "تبلیغ", "تبلیغات", "رزرو", "تعرفه", "پکیج", "تخفیف", "خرید",
    "فروشگاه", "صرافی", "سیگنال", "بیت کوین", "تتر", "ثبت نام",
    "جوین شو", "عضو شوید", "کانال دوم", "لینک زیر", "فوری/", "پروکسی",
]


def load_state():
    if not STATE_FILE.exists():
        return {"channels": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"channels": {}}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(STATE_FILE)


def send_media(method, file_key, file_path, caption):
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
        print(f"[خطا] فایل {file_path} معتبر نیست.")
        return

    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={file_key: f},
                    timeout=REQ_TIMEOUT,
                )
                if r.status_code == 200:
                    print(f"[تلگرام OK]: {file_path}")
                else:
                    print(f"[تلگرام خطا]: {r.status_code}")
        except Exception as e:
            print(f"[تلگرام Exception]: {e}")

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{method}",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={file_key: f},
                    timeout=REQ_TIMEOUT,
                )
                if r.status_code == 200:
                    print(f"[بله OK]: {file_path}")
                else:
                    print(f"[بله خطا]: {r.status_code}")
        except Exception as e:
            print(f"[بله Exception]: {e}")

    time.sleep(2.0)


def send_text(text):
    if BOT_TOKEN and CHANNEL_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": CHANNEL_ID, "text": text},
                timeout=REQ_TIMEOUT,
            )
        except Exception:
            pass

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            requests.post(
                f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage",
                data={"chat_id": BALE_CHANNEL_ID, "text": text},
                timeout=REQ_TIMEOUT,
            )
        except Exception:
            pass
    time.sleep(1.5)


# =============================================================
# بخش پویا و زنده: پیش‌بینی منطقه‌ای ۳ و ۷ روزه (Open-Meteo)
# + شاخص‌های پایداری جوی + پوستر ۷ روزه قم  (تماماً live)
# ==============================================================
REGIONAL_SITES = [
    {"name": "قم",         "lat": 34.6416, "lon": 50.8746, "elev": 928},
    {"name": "کهک",        "lat": 34.3938, "lon": 50.8643, "elev": 1010},
    {"name": "سلفچگان",    "lat": 34.4775, "lon": 50.4592, "elev": 1550},
    {"name": "دستجرد",     "lat": 34.3949, "lon": 49.9502, "elev": 1310},
    {"name": "قاهان",      "lat": 34.7245, "lon": 50.2632, "elev": 1140},
]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
POSTER_PNG = "qom_7day_weather_poster.png"


def fetch_regional_forecast():
    """دریافت کاملاً زنده داده‌های Open-Meteo برای هر ۵ ایستگاه منطقه."""
    results = {}
    for site in REGIONAL_SITES:
        params = {
            "latitude": site["lat"],
            "longitude": site["lon"],
            "hourly": (
                "temperature_2m,dew_point_2m,relative_humidity_2m,"
                "precipitation,precipitation_probability,weather_code,"
                "wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
                "cloud_cover,pressure_msl,cape,cin,lifted_index,"
                "k_index,total_totals,showalter_index"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,"
                "wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,"
                "sunrise,sunset"
            ),
            "timezone": "auto",
            "forecast_days": 8,
        }
        try:
            r = SESSION.get(OPEN_METEO_URL, params=params, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            results[site["name"]] = {"site": site, "data": data, "live": True}
            print(f"[OK زنده] {site['name']}: {len(data.get('daily', {}).get('time', []))} روز")
        except Exception as e:
            print(f"[خطا در {site['name']}]: {e}")
            results[site["name"]] = {"site": site, "data": None, "live": False}
        time.sleep(1.0)
    return results


def stability_report(hourly):
    """محاسبه/استخراج زنده شاخص‌های پایداری جوی از داده‌های ساعتی."""
    def get(k):
        return hourly.get(k) or []

    def max_nonneg(a):
        return max([v for v in a if v is not None] or [0.0])

    def min_or_none(a):
        vals = [v for v in a if v is not None]
        return min(vals) if vals else None

    return {
        "CAPE (J/kg)": max_nonneg(get("cape")),
        "CIN (J/kg)": min_or_none(get("cin")),
        "Lifted Index": min_or_none(get("lifted_index")),
        "K-Index": max_nonneg(get("k_index")),
        "Total Totals": max_nonneg(get("total_totals")),
        "Showalter": min_or_none(get("showalter_index")),
    }


def interpret_stability(s):
    """تفسیر خودکار شاخص‌های پایداری برای متن گزارش."""
    notes = []
    cape = s["CAPE (J/kg)"]
    li = s["Lifted Index"]
    ki = s["K-Index"]
    if cape is not None:
        if cape >= 2500:
            notes.append("CAPE بسیار بالا (>=۲۵۰۰): ناپایداری شدید و خطر رگبار/تندباد ⛈")
        elif cape >= 1000:
            notes.append("CAPE بالا (>=۱۰۰۰): ناپایداری متوسط و احتمال رگبار ⚡")
        elif cape >= 300:
            notes.append("CAPE ملایم: ناپایداری خفیف")
        else:
            notes.append("CAPE پایین: جو نسبتاً پایدار")
    if li is not None:
        if li <= -2:
            notes.append("LI منفی: جو ناپایدار")
        elif li <= 2:
            notes.append("LI مرزی")
        else:
            notes.append("LI مثبت: جو پایدار در تراز پایین")
    if ki is not None:
        if ki >= 30:
            notes.append("K-Index بالا: پتانسیل توزان هوای مرطوب")
        elif ki >= 20:
            notes.append("K-Index متوسط")
        else:
            notes.append("K-Index پایین: هوای خشک")
    if not notes:
        notes.append("شاخص‌ها برای این دوره در دسترس نیستند.")
    return notes


def format_regional_forecast_text(regional, horizon_days):
    """متن کاملاً پویای پیش‌بینی ۳ یا ۷ روزه از داده‌های زنده."""
    now = datetime.now(TEHRAN_TZ)
    header = (
        f"🌦 پیش‌بینی {'۳' if horizon_days == 3 else '۷'} روزه منطقه‌ای (کاملاً زنده - Open-Meteo)\n"
        f"🕒 تهیه: {now:%Y/%m/%d - %H:%M}\n"
        + "=" * 34 + "\n"
    )
    blocks = []
    for name, bundle in regional.items():
        d = bundle["data"]
        if not d or "daily" not in d:
            blocks.append(f"📍 {name}: داده زنده دریافت نشد ⚠")
            continue
        daily = d["daily"]
        n = min(horizon_days, len(daily["time"]))
        lines = [f"📍 {name}:"]
        for i in range(n):
            date = daily["time"][i]
            try:
                day_lbl = datetime.fromisoformat(date).strftime("%a")
            except Exception:
                day_lbl = date
            tmax = daily["temperature_2m_max"][i]
            tmin = daily["temperature_2m_min"][i]
            prec = daily["precipitation_sum"][i] or 0
            pprob = daily["precipitation_probability_max"][i]
            if pprob is None:
                pprob = daily.get("precipitation_probability_max", [None] * n)[i]
            wind = daily["wind_speed_10m_max"][i]
            gust = daily["wind_gusts_10m_max"][i]
            lines.append(
                f"  • {date} ({day_lbl}): {tmin:.0f}..{tmax:.0f}°C | "
                f"بارش {prec:.1f} mm (احتمال {pprob if pprob is not None else '-'}٪) | "
                f"باد {wind:.0f} km/h (تندباد {gust:.0f})"
            )
        # شاخص‌های پایداری روی کل دوره
        s = stability_report(d.get("hourly", {}) or {})
        lines.append("  🧪 شاخص‌های پایداری (بیشینه دوره):")
        for k, v in s.items():
            lines.append(f"     - {k}: {'-' if v is None else f'{v:.1f}'}")
        for note in interpret_stability(s):
            lines.append(f"     ⚠ {note}")
        blocks.append("\n".join(lines))
    return header + ("\n" + ("-" * 34) + "\n").join(blocks)


WMO_FA = {
    0: "صاف", 1: "عمدتاً صاف", 2: "نیمه‌ابری", 3: "ابری",
    45: "مه", 48: "مه یخ‌زده", 51: "نم‌نم خفیف", 53: "نم‌نم", 55: "نم‌نم شدید",
    61: "باران خفیف", 63: "باران", 65: "باران شدید",
    71: "برف خفیف", 73: "برف", 75: "برف شدید",
    80: "رگبار خفیف", 81: "رگبار", 82: "رگبار شدید",
    95: "رعدوبرق", 96: "رعدوبرق با تگرگ", 99: "رعدوبرق شدید با تگرگ",
}


def wmo_text(code):
    return WMO_FA.get(int(code) if code is not None else -1, "نامشخص")


def generate_7day_poster(regional):
    """تولید اجباری پوستر ۷ روزه قم از داده زنده (همیشه تولید می‌شود)."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "figure.facecolor": "#0e1526", "axes.facecolor": "#131c31",
        "text.color": "#e8eef7", "axes.edgecolor": "#2a3a5c",
        "savefig.facecolor": "#0e1526",
    })
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 11), height_ratios=[2.1, 1.5])
    fig.suptitle("Qom - 7-Day Regional Weather Poster (Live Open-Meteo)",
                 fontsize=18, fontweight="bold", color="#ffffff", y=0.975)
    fig.text(0.5, 0.947,
             f"Generated {datetime.now(TEHRAN_TZ):%Y-%m-%d %H:%M} (Tehran)",
             ha="center", fontsize=10, color="#9fb2cc")

    ax1 = axes[0]
    plotted = False
    for bundle in regional.values():
        d = bundle["data"]
        if not d or "daily" not in d:
            continue
        daily = d["daily"]
        n = min(7, len(daily["time"]))
        days = list(range(n))
        tmax = [daily["temperature_2m_max"][i] for i in range(n)]
        tmin = [daily["temperature_2m_min"][i] for i in range(n)]
        label = bundle["site"]["name"]
        ax1.plot(days, tmax, "o-", lw=2, markersize=5)
        ax1.plot(days, tmin, "s--", lw=1.6, markersize=4, alpha=0.85)
        ax1.annotate(label, (days[-1], tmax[-1]), textcoords="offset points",
                     xytext=(8, 4), fontsize=10, fontweight="bold")
        plotted = True
    if plotted:
        ax1.set_xlim(-0.4, 6.9)
        ax1.set_xticks(range(7))
        ax1.set_xticklabels(
            [str(regional["قم"]["data"]["daily"]["time"][i])
             for i in range(min(7, len(regional["قم"]["data"]["daily"]["time"])))] if regional.get("قم", {}).get("data") else [f"D{i+1}" for i in range(7)],
            fontsize=8.5)
        ax1.set_ylabel("Temperature (°C)", fontsize=11)
        ax1.grid(color="#22304d", alpha=0.6)
        ax1.set_title("Daily max / min temperature - all 5 regional stations",
                      fontsize=12.5, loc="left", fontweight="bold")
    else:
        ax1.text(0.5, 0.5, "داده زنده در دسترس نبود", ha="center", va="center",
                 transform=ax1.transAxes)

    ax2 = axes[1]
    plotted2 = False
    for bundle in regional.values():
        d = bundle["data"]
        if not d or "daily" not in d:
            continue
        daily = d["daily"]
        n = min(7, len(daily["time"]))
        days = list(range(n))
        prec = [(daily["precipitation_sum"][i] or 0) for i in range(n)]
        ax2.bar([x + 0.0 for x in days], prec, width=0.55, alpha=0.9,
                label=bundle["site"]["name"])
        plotted2 = True
    if plotted2:
        ax2.set_xlim(-0.6, 6.9)
        ax2.set_xticks(range(7))
        ax2.set_xticklabels(
            [str(regional["قم"]["data"]["daily"]["time"][i])
             for i in range(min(7, len(regional["قم"]["data"]["daily"]["time"])))] if regional.get("قم", {}).get("data") else [f"D{i+1}" for i in range(7)],
            fontsize=8.5)
        ax2.set_ylabel("Precipitation (mm)", fontsize=11)
        ax2.grid(axis="y", color="#22304d", alpha=0.6)
        ax2.legend(fontsize=8.5, ncol=3, framealpha=0.15)
        ax2.set_title("Daily precipitation totals - all 5 regional stations",
                      fontsize=12.5, loc="left", fontweight="bold")
    else:
        ax2.text(0.5, 0.5, "داده زنده در دسترس نبود", ha="center", va="center",
                 transform=ax2.transAxes)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(POSTER_PNG, dpi=150)
    plt.close(fig)
    print("saved:", POSTER_PNG, os.path.getsize(POSTER_PNG), "bytes")
    return POSTER_PNG


def capture_regional_forecasts():
    """پیش‌بینی زنده ۳ و ۷ روزه + پوستر ۷ روزه - همیشه تولید و ارسال می‌شود."""
    print("\n=== ۰-ب. پیش‌بینی زنده منطقه‌ای ۳ و ۷ روزه + شاخص‌های پایداری ===")
    regional = fetch_regional_forecast()

    if not any(b["live"] for b in regional.values()):
        print("[هشدار] هیچ داده زنده‌ای دریافت نشد؛ متن/پوستر ارسال نمی‌شود.")
        return regional

    # ۳ روزه
    txt3 = format_regional_forecast_text(regional, horizon_days=3)
    print(txt3[:400])
    send_text(txt3)

    # ۷ روزه
    txt7 = format_regional_forecast_text(regional, horizon_days=7)
    send_text(txt7)

    # پوستر ۷ روزه - تولید اجباری در هر اجرا
    try:
        poster = generate_7day_poster(regional)
        caption = (
            "🖼 پوستر ۷ روزه هواشناسی منطقه قم (زنده - Open-Meteo)\n"
            "🌡 بیشینه/کمینه دمای ۵ ایستگاه | 🌧 بارش روزانه\n"
            "📍 قم، کهک، سلفچگان، دستجرد، قاهان"
        )
        send_media("sendPhoto", "photo", poster, caption)
    except Exception as e:
        print(f"[خطا در تولید پوستر ۷ روزه]: {e}")

    return regional

def capture_and_send_custom_meteogram():
    print("\n=== ۰. تولید و ارسال متئوگرام چندمدله قم ===")
    out_file = "qom_live_multimodel_meteogram.png"
    caption = (
        "📊 متئوگرام چندمدله ۱۰ روزه قم (ECMWF, GFS, ICON, GEM)\n"
        "📍 ایستگاه: قم (Iran, Qom - Ali Jazebi)\n"
        "🌡 روند دما و خطوط آنسامبل | 🌧 بارش تجمعی | 💨 جهت و شدت باد"
    )
    try:
        # FORCED DYNAMIC GENERATION - the old file-existence skip was removed.
        print("تولید اجباری و پویای متئوگرام چندمدله (بدون skip)...")
        generate_qom_meteogram(out_file)
        if not os.path.exists(out_file) or os.path.getsize(out_file) < 1000:
            raise RuntimeError("متئوگرام تولید نشد")
        send_media("sendPhoto", "photo", out_file, caption)
    except Exception as e:
        print(f"[خطا در متئوگرام چندمدله]: {e}")


def capture_ecmwf(page):
    print("\n=== ۱. دریافت متئوگرام‌های ۱۰ روزه ECMWF ===")
    for item in ECMWF_TARGETS:
        print(f"در حال باز کردن: {item['name']}...")
        try:
            page.goto(item["web_url"], timeout=70000, wait_until="load")
            page.wait_for_timeout(12000)

            selector = "img[src*='render-worker'], img[src*='opencharts'], .chart-container img"
            img_el = page.query_selector(selector)
            if img_el:
                img_src = img_el.get_attribute("src")
                if img_src and img_src.startswith("http"):
                    res = SESSION.get(img_src, timeout=30)
                    if res.status_code == 200 and len(res.content) > 3000:
                        Path(item["file"]).write_bytes(res.content)
                    else:
                        img_el.screenshot(path=item["file"])
                else:
                    img_el.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        time.sleep(2)


def clean_tropical_welcome(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        page.evaluate("""() => {
            const btns = document.querySelectorAll('.modal .close, button.close, [data-dismiss="modal"]');
            btns.forEach(b => b.click());
            const modals = document.querySelectorAll('.modal, .modal-backdrop, .fade.in, [class*="backdrop"]');
            modals.forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.filter = "none";
            document.body.style.opacity = "1";
            document.documentElement.style.filter = "none";
            const mapEl = document.querySelector('#modelImage, .model-image, #analysis-image');
            if (mapEl) {
                mapEl.style.filter = "none";
                mapEl.style.opacity = "1";
            }
        }""")
    except Exception:
        pass


def capture_tropical_tidbits(page):
    print("\n=== ۲. عکسبرداری Tropical Tidbits ===")
    tt_base = "https://www.tropicaltidbits.com/analysis/models/?model=gfs&region=me"

    print("\n--- دریافت فریم‌های بارش و فشار سطح دریا ---")
    for fh in TROPICAL_HOURS:
        url = f"{tt_base}&pkg=mslp_pcpn&fh={fh}"
        file_name = f"tropical_pcpn_fh{fh}.png"
        caption = (
            f"🌧 پیش‌بینی بارش تجمیعی و فشار سطح دریا (MSLP)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits{KEY72 if fh == 72 else ''}"
        )
        print(f"فریم بارش: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(600)

            img_el = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_el:
                img_el.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم بارش fh={fh}: {e}")
        time.sleep(1.5)

    print("\n--- دریافت فریم‌های تراز ۵۰۰ هکتوپاسکال ---")
    for fh in TROPICAL_HOURS:
        url = f"{tt_base}&pkg=z500a&fh={fh}"
        file_name = f"tropical_z500a_fh{fh}.png"
        caption = (
            f"🌀 تاوایی و ارتفاع ژئوپتانسیل تراز ۵۰۰ هکتوپاسکال\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits{KEY72 if fh == 72 else ''}"
        )
        print(f"فریم ۵۰۰ هکتوپاسکال: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(600)

            img_el = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_el:
                img_el.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)

            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم ۵۰۰ fh={fh}: {e}")
        time.sleep(1.5)

    print("\n--- دریافت فریم‌های باد تراز ۸۵۰ هکتوپاسکال (mslp_uv850) ---")
    for fh in TROPICAL_HOURS:
        url = f"{tt_base}&pkg=mslp_uv850&fh={fh}"
        file_name = f"tropical_uv850_fh{fh}.png"
        hl = "\n⭐ فریم کلیدی ۷۲ ساعته - پایان دوره پیش‌بینی" if fh == 72 else ""
        caption = (
            f"💨 باد سطح ۸۵۰ هکتوپاسکال و فشار سطح دریا (MSLP)\n"
            f"🌐 مدل: GFS خاورمیانه و ایران\n"
            f"⏱ پیش‌بینی {fh} ساعت آینده | Tropical Tidbits{hl}"
        )
        print(f"فریم باد ۸۵۰: {fh} ساعت...")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            clean_tropical_welcome(page)
            page.wait_for_timeout(600)
            img_el = page.query_selector("#modelImage, .model-image, #analysis-image")
            if img_el:
                img_el.screenshot(path=file_name)
            else:
                page.screenshot(path=file_name)
            send_media("sendPhoto", "photo", file_name, caption)
        except Exception as e:
            print(f"خطا در فریم ۸۵۰ fh={fh}: {e}")
        time.sleep(1.5)


def capture_yr(page):
    print("\n=== ۳. جداول و نمودارهای Yr.no ===")
    for item in YR_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        time.sleep(1.5)


def capture_foreca(page):
    print("\n=== ۴. پیش‌بینی‌های فورکا (Foreca) ===")
    for item in FORECA_TARGETS:
        print(f"عکسبرداری: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            page.screenshot(path=item["file"])
            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در {item['name']}: {e}")
        time.sleep(1.5)


def capture_weather_forecast(page):
    print("\n=== ۵. دریافت پیش‌بینی‌های افقی Weather-Forecast ===")
    page.set_viewport_size({"width": 1920, "height": 1080})

    for item in WEATHER_FORECAST_TARGETS:
        print(f"عکسبرداری جدول افقی: {item['name']}...")
        try:
            page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            page.evaluate("""() => {
                const ads = document.querySelectorAll('.fc-dialog-container, #onetrust-banner-sdk, .banner-close, .advert, .advertisement, [id*="google_ads"]');
                ads.forEach(e => e.remove());
                const tableCont = document.querySelector('.forecast-table, .forecast-cont');
                if (tableCont) {
                    tableCont.scrollIntoView({ behavior: 'instant', block: 'center' });
                }
            }""")
            page.wait_for_timeout(1500)

            selector = ".forecast-table, .forecast-cont, .location-summary-forecast"
            table_el = page.query_selector(selector)
            if table_el:
                table_el.screenshot(path=item["file"])
            else:
                page.screenshot(path=item["file"])

            send_media("sendPhoto", "photo", item["file"], item["caption"])
        except Exception as e:
            print(f"خطا در Weather-Forecast {item['name']}: {e}")
        time.sleep(1.5)

    page.set_viewport_size({"width": 1366, "height": 900})


def is_advertisement(text, has_media):
    if not text and not has_media:
        return True
    text_lower = text.lower() if text else ""
    if "t.me/+" in text_lower or "joinchat" in text_lower:
        return True
    for kw in ADS_PATTERNS:
        if kw in text_lower:
            return True
    if not has_media:
        weather_terms = [
            "بارش", "باران", "برف", "دما", "باد", "هواشناسی",
            "سیل", "رگبار", "توفان", "ابری", "سامانه", "هشدار",
        ]
        if not any(term in text for term in weather_terms):
            return True
    return False


def clean_text_advertisements(text):
    if not text:
        return ""
    lines = text.split("\n")
    cleaned = []
    bad_tokens = ["t.me/+", "t.me/joinchat", "جهت تبلیغات", "کانال دوم", "عضویت"]
    for line in lines:
        line_strip = line.strip()
        if any(term in line_strip for term in bad_tokens):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def check_iran_met(state):
    print("\n=== ۶. کانال تلگرامی @iran_met ===")
    username = "iran_met"
    chan_state = state.get("channels", {}).get(
        username, {"last_id": 0, "seen_ids": []}
    )
    last_id = int(chan_state.get("last_id", 0))
    seen_ids = set(chan_state.get("seen_ids", []))

    try:
        url = f"https://t.me/s/{username}"
        r = SESSION.get(url, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        messages = soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))
    except Exception as e:
        print(f"خطا در بررسی تلگرام: {e}")
        return

    all_current_ids = []
    parsed_msgs = []
    for msg in messages:
        dp = msg.get("data-post", "")
        if "/" not in dp:
            continue
        try:
            m_id = int(dp.rsplit("/", 1)[-1])
            all_current_ids.append(m_id)
            parsed_msgs.append((m_id, msg))
        except ValueError:
            continue

    if not all_current_ids:
        return

    if last_id == 0 and not seen_ids:
        print("[اطلاعیه] ثبت اولیه پیام‌های کانال؛ موردی ارسال نمی‌شود.")
        state.setdefault("channels", {})[username] = {
            "last_id": max(all_current_ids),
            "seen_ids": sorted(all_current_ids)[-200:],
        }
        return

    new_posts = []
    for m_id, msg in parsed_msgs:
        if m_id in seen_ids or m_id <= last_id:
            continue

        text_el = msg.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text("\n", strip=True) if text_el else ""

        photo_el = msg.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
        img_url = None
        if photo_el:
            style = photo_el.get("style", "")
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
            if m:
                img_url = m.group(1)

        video_el = msg.find("video")
        video_url = video_el.get("src") if video_el else None
        has_media = bool(img_url or video_url)

        if is_advertisement(text, has_media):
            seen_ids.add(m_id)
            last_id = max(last_id, m_id)
            continue

        cleaned_text = clean_text_advertisements(text)
        new_posts.append({
            "id": m_id,
            "text": cleaned_text,
            "img_url": img_url,
            "video_url": video_url,
        })

    for p in sorted(new_posts, key=lambda x: x["id"]):
        caption = (
            f"{p['text']}\n\n📎 منبع: @{username}"
            if p["text"]
            else f"📎 منبع: @{username}"
        )
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        if p["video_url"]:
            tmp_vid = f"tmp_{username}_{p['id']}.mp4"
            try:
                res_v = SESSION.get(p["video_url"], timeout=REQ_TIMEOUT)
                Path(tmp_vid).write_bytes(res_v.content)
                send_media("sendVideo", "video", tmp_vid, caption)
                Path(tmp_vid).unlink(missing_ok=True)
            except Exception:
                pass
        elif p["img_url"]:
            tmp_img = f"tmp_{username}_{p['id']}.jpg"
            try:
                res_i = SESSION.get(p["img_url"], timeout=REQ_TIMEOUT)
                Path(tmp_img).write_bytes(res_i.content)
                send_media("sendPhoto", "photo", tmp_img, caption)
                Path(tmp_img).unlink(missing_ok=True)
            except Exception:
                pass
        else:
            send_text(caption)

        last_id = max(last_id, p["id"])
        seen_ids.add(p["id"])

    state.setdefault("channels", {})[username] = {
        "last_id": last_id,
        "seen_ids": sorted(list(seen_ids))[-200:],
    }


def generate_and_send_synoptic_analysis():
    print("\n=== ۷. تدوین و ارسال تحلیل سینوپتیکی و پیش‌بینی شهری ===")
    if not TEXT_FILE.exists():
        print(f"[هشدار] فایل {TEXT_FILE} یافت نشد.")
        return

    content = TEXT_FILE.read_text(encoding="utf-8")
    now = datetime.now(TEHRAN_TZ)
    current_time_str = now.strftime("%Y/%m/%d - ساعت %H:%M")

    persian_days = {
        "Saturday": "شنبه",
        "Sunday": "یکشنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنجشنبه",
        "Friday": "جمعه",
    }
    d1 = persian_days.get(now.strftime("%A"), "امروز")
    d2 = persian_days.get((now + timedelta(days=1)).strftime("%A"), "فردا")
    d3 = persian_days.get((now + timedelta(days=2)).strftime("%A"), "پس‌فردا")

    synoptic_part = ""
    cities_part = ""
    if "[SYNOPTIC]" in content and "[CITIES]" in content:
        parts = content.split("[CITIES]")
        synoptic_part = parts[0].replace("[SYNOPTIC]", "").strip()
        cities_part = parts[1].strip()
    else:
        synoptic_part = content

    if synoptic_part:
        text1 = synoptic_part.format(time=current_time_str)
        send_text(text1)

    if cities_part:
        text2 = cities_part.format(
            time=current_time_str,
            day1=d1,
            day2=d2,
            day3=d3
        )
        send_text(text2)


def main():
    now_str = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M")
    print(f"=== Run start: {now_str} ===")
    state = load_state()

    # ۰. متئوگرام چندمدله قم
    capture_and_send_custom_meteogram()

    # ۰-ب. پیش‌بینی زنده ۳/۷ روزه + شاخص‌ها + پوستر ۷ روزه
    capture_regional_forecasts()

    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=browser_args,
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = context.new_page()

        # ۱. متئوگرام‌های ۱۰ روزه ECMWF
        capture_ecmwf(page)

        # ۲. نقشه Tropical Tidbits
        capture_tropical_tidbits(page)

        # ۳. جداول و نمودارهای Yr.no
        capture_yr(page)

        # ۴. پیش‌بینی‌های فورکا (Foreca)
        capture_foreca(page)

        # ۵. پیش‌بینی‌های افقی Weather-Forecast
        capture_weather_forecast(page)

        browser.close()

    # ۶. بررسی کانال تلگرامی iran_met
    check_iran_met(state)

    # ۷. تحلیل تخصصی دینامیکی-سینوپتیکی و پیش‌بینی شهری
    generate_and_send_synoptic_analysis()

    save_state(state)
    print("\n=== پایان موفقیت‌آمیز چرخه پایش و ارسال تحلیل ===")


if __name__ == "__main__":
    main()
