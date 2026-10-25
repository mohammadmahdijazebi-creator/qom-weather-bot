"""Live Qom dashboard. Compatible with the existing bot and workflow."""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

LAT, LON = 34.64, 50.87
TIMEZONE = 'Asia/Tehran'
FORECAST_DAYS = 7
MODELS = [
    {'id': 'ecmwf_ifs025', 'name': 'ECMWF', 'color': '#38bdf8'},
    {'id': 'gfs_seamless', 'name': 'GFS', 'color': '#fb7185'},
    {'id': 'icon_seamless', 'name': 'ICON', 'color': '#4ade80'},
    {'id': 'gem_seamless', 'name': 'GEM', 'color': '#c084fc'},
]
BG, PANEL, TEXT, MUTED = '#031021', '#071b30', '#d5edff', '#83aaca'


def request(params, timeout=30, retries=3):
    url = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'QomWeatherBot/2.0', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.load(response)
            if data.get('error'):
                raise RuntimeError(data.get('reason'))
            return data
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def fetch_live_data(timeout=30, retries=3):
    params = dict(latitude=LAT, longitude=LON, timezone=TIMEZONE,
                  forecast_days=FORECAST_DAYS, wind_speed_unit='kmh', temperature_unit='celsius', precipitation_unit='mm')
    main = request(dict(params,
        current='temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_direction_10m,pressure_msl,weather_code',
        hourly='temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,precipitation_probability,precipitation',
        daily='temperature_2m_max,temperature_2m_min,weather_code'), timeout, retries)
    models = {}
    for model in MODELS:
        try:
            models[model['name']] = request(dict(params, models=model['id'],
                hourly='temperature_2m,wind_speed_10m,wind_direction_10m,precipitation'), timeout, retries)
        except Exception as exc:
            print(f"[Warning] {model['name']} unavailable: {exc}")
    main['model_data'] = models
    return main, True


def series(block, key):
    n = len(block.get('time', []))
    values = block.get(key)
    if not isinstance(values, list) or len(values) != n:
        return np.full(n, np.nan)
    return np.array([float(v) if v is not None else np.nan for v in values])


def fmt(value, unit='', digits=0):
    return f'{value:.{digits}f}{unit}' if value is not None and np.isfinite(value) else 'N/A'


def weather(code):
    if code is None: return 'Unavailable'
    if code == 0: return 'Clear'
    if code in (1, 2): return 'Partly cloudy'
    if code == 3: return 'Overcast'
    if code in (45, 48): return 'Fog'
    if code in (71, 73, 75, 77, 85, 86): return 'Snow'
    if code >= 95: return 'Thunderstorm'
    return 'Rain / drizzle'


def icon(ax, code):
    if code in (0, 1, 2):
        ax.scatter([.30], [.57], s=650, color='#ffc84a', edgecolors='#ffdf80', transform=ax.transAxes)
        for angle in np.linspace(0, 2*np.pi, 12, endpoint=False):
            ax.plot([.30+.13*np.cos(angle), .30+.17*np.cos(angle)],
                    [.57+.15*np.sin(angle), .57+.19*np.sin(angle)], color='#ffc84a', transform=ax.transAxes)
    if code is not None and code != 0:
        ax.scatter([.26,.35,.43], [.55,.59,.54], s=[360,600,350], color='#b2d7f3', transform=ax.transAxes)
        if code >= 51:
            ax.plot([.25,.33,.41], [.35,.32,.35], linestyle='none', marker='|', color='#21a6ff', markersize=10, transform=ax.transAxes)


def generate_qom_meteogram(output_path='qom_live_multimodel_meteogram.png'):
    data, _ = fetch_live_data()
    h, d, c = data['hourly'], data['daily'], data['current']
    dates = [datetime.fromisoformat(t) for t in h['time']]
    if not dates:
        raise RuntimeError('Empty hourly forecast; refusing to generate a stale chart.')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': TEXT,
        'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED, 'font.size': 10})
    fig = plt.figure(figsize=(18, 12), dpi=140, facecolor=BG)

    def box(rect):
        ax = fig.add_axes(rect, facecolor=PANEL)
        for spine in ax.spines.values(): spine.set_color('#12324b')
        return ax

    header = box([.025,.865,.95,.115]); header.set_axis_off()
    header.text(.015,.72,'Qom - Ali Jazebi',fontsize=25,weight='bold')
    header.text(.015,.40,'7-Day Weather Forecast & Multi-Model Meteogram',color=MUTED,fontsize=12)
    header.text(.015,.13,'34.64°N  50.87°E  |  Local time: Asia/Tehran',color=MUTED)
    header.text(.48,.65,fmt(c.get('temperature_2m'),'°C'),fontsize=30,weight='bold')
    header.text(.48,.26,weather(c.get('weather_code')),fontsize=13)
    header.text(.64,.72,'Feels like  '+fmt(c.get('apparent_temperature'),'°C'))
    header.text(.64,.46,'Humidity  '+fmt(c.get('relative_humidity_2m'),'%'))
    header.text(.64,.20,'Wind  '+fmt(c.get('wind_speed_10m'),' km/h'))
    header.text(.98,.72,datetime.now(ZoneInfo(TIMEZONE)).strftime('%a %d %b %Y'),ha='right')
    header.text(.98,.46,'MSL pressure  '+fmt(c.get('pressure_msl'),' hPa'),ha='right')
    header.text(.98,.20,'Current data: '+c.get('time','N/A').replace('T',' '),ha='right',fontsize=9,color=MUTED)

    for i, day in enumerate(d['time'][:7]):
        ax = box([.025+i*.137,.699,.128,.145]); ax.set_xticks([]); ax.set_yticks([])
        ax.text(.5,.88,datetime.fromisoformat(day).strftime('%a  %d %b'),ha='center',transform=ax.transAxes,fontsize=12)
        code = d['weather_code'][i]; icon(ax,code)
        ax.text(.68,.58,fmt(d['temperature_2m_max'][i],'°'),ha='center',fontsize=23,transform=ax.transAxes)
        ax.text(.68,.35,fmt(d['temperature_2m_min'][i],'°'),ha='center',fontsize=16,color='#38bdf8',transform=ax.transAxes)
        ax.text(.5,.10,weather(code),ha='center',fontsize=10,transform=ax.transAxes)

    def chart(rect,title):
        ax=box(rect); ax.set_title(title,loc='left',pad=12,fontsize=12)
        ax.grid(alpha=.25,color='#23425e'); ax.set_axisbelow(True)
        ax.set_xlim(dates[0],dates[-1]); ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%a %d'))
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6,12,18]))
        return ax

    temp=chart([.045,.453,.81,.195],'Temperature (°C) — hourly forecast and model comparison')
    temp.plot(dates,series(h,'temperature_2m'),color='#ff626d',lw=2.6,label='Best match')
    temp.plot(dates,series(h,'apparent_temperature'),color='#f2bc60',lw=1.4,ls='--',label='Feels like')
    wind=chart([.045,.267,.81,.13],'10 m Wind (km/h) — speed and direction')
    wind.plot(dates,series(h,'wind_speed_10m'),color='#2196ff',lw=2.4,label='Best match')
    wind.fill_between(dates,0,series(h,'wind_speed_10m'),color='#1685fb',alpha=.13)
    for model in MODELS:
        mh=data['model_data'].get(model['name'],{}).get('hourly',{})
        if not mh: continue
        mt=[datetime.fromisoformat(t) for t in mh['time']]
        for ax,key in ((temp,'temperature_2m'),(wind,'wind_speed_10m')):
            ax.plot(mt,series(mh,key),color=model['color'],lw=1,alpha=.8,label=model['name'])
    temp.legend(loc='upper left',ncol=6,fontsize=8,frameon=False)
    wind.legend(loc='upper left',ncol=5,fontsize=8,frameon=False)
    speed=series(h,'wind_speed_10m'); direction=series(h,'wind_direction_10m')
    inds=np.arange(0,len(dates),6)
    valid=np.isfinite(speed[inds]) & np.isfinite(direction[inds])
    ix=inds[valid]; rad=np.radians(direction[ix])
    wind.quiver(mdates.date2num([dates[i] for i in ix]),speed[ix]+3,-np.sin(rad),-np.cos(rad),
                color='#46d6d1',angles='uv',scale=65,width=.002,pivot='middle')
    wind.set_ylim(bottom=0)
    rain=chart([.045,.085,.81,.125],'Precipitation probability (%) — best-match forecast')
    prob=series(h,'precipitation_probability')
    rain.bar(dates,prob,width=.033,color='#267bff',alpha=.9); rain.set_ylim(0,105)
    if not np.isfinite(prob).any(): rain.text(.5,.5,'Probability unavailable',ha='center',transform=rain.transAxes)

    def stats(rect,title,lines):
        ax=box(rect); ax.set_xticks([]); ax.set_yticks([])
        ax.text(.10,.88,title,fontsize=11,weight='bold',transform=ax.transAxes)
        for i,line in enumerate(lines): ax.text(.10,.66-i*.20,line,fontsize=11,color=MUTED,transform=ax.transAxes)
    t=series(h,'temperature_2m'); p=series(h,'precipitation')
    def extreme(a,fn): return fn(a[np.isfinite(a)]) if np.isfinite(a).any() else None
    stats([.875,.453,.10,.195],'Temperature',[
        'Max '+fmt(extreme(t,np.max),'°C'),'Min '+fmt(extreme(t,np.min),'°C')])
    stats([.875,.267,.10,.13],'Wind',[
        fmt(c.get('wind_speed_10m'),' km/h'),'From '+fmt(c.get('wind_direction_10m'),'°')])
    total=float(p.sum()) if len(p) and np.isfinite(p).all() else None
    stats([.875,.085,.10,.125],'Rain (7 days)',[
        'Total '+fmt(total,' mm',1),'Peak '+fmt(extreme(prob,np.max),'%')])
    stamp=datetime.now(ZoneInfo(TIMEZONE)).strftime('%Y-%m-%d %H:%M %Z')
    fig.text(.025,.027,'Qom - Ali Jazebi  |  Open-Meteo  |  Missing values remain unavailable.',fontsize=9,color=MUTED)
    fig.text(.975,.027,'Retrieved: '+stamp,ha='right',fontsize=9,color=MUTED)
    fig.text(.025,.010,'Best match: API default forecast. Model availability and forecast horizons vary. Retrieval time is not model initialization time.',fontsize=8,color=MUTED)
    tmp=str(output_path)+'.tmp.png'
    try:
        fig.savefig(tmp,facecolor=BG,dpi=140)
        import os
        os.replace(tmp,output_path)
    finally:
        plt.close(fig)
    print('Meteogram saved: '+str(output_path))
    return output_path


if __name__ == '__main__':
    generate_qom_meteogram()
