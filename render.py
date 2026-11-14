#!/usr/bin/env python3
"""Render a Kindle Paperwhite 3 (1072x1448, 8-bit grayscale) weather screen.

Usage: render.py [out.png]
Data: Open-Meteo (no API key). Location: Gurugram, Haryana.
"""
import json
import math
import sys
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

PLACE = "Gurugram"
REGION = "Haryana"
LAT, LON = 28.4595, 77.0266
TZ = "Asia/Kolkata"
W, H = 1072, 1448
S = 2  # supersample factor for smooth edges

import os


def _pick(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    raise SystemExit("No usable font found: " + ", ".join(paths))


FONT_REG = _pick(
    "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # GitHub runner
)
FONT_BOLD = _pick(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)

URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
    "weather_code,wind_speed_10m"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
    "precipitation_probability_max,sunrise,sunset"
    f"&timezone={TZ}&forecast_days=4"
)

WMO = {
    0: ("Clear", "sun"), 1: ("Mostly clear", "sun"), 2: ("Partly cloudy", "part"),
    3: ("Overcast", "cloud"), 45: ("Fog", "fog"), 48: ("Fog", "fog"),
    51: ("Light drizzle", "rain"), 53: ("Drizzle", "rain"), 55: ("Drizzle", "rain"),
    56: ("Freezing drizzle", "rain"), 57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"), 63: ("Rain", "rain"), 65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"), 67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"), 73: ("Snow", "snow"), 75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"), 80: ("Showers", "rain"), 81: ("Showers", "rain"),
    82: ("Heavy showers", "rain"), 85: ("Snow showers", "snow"),
    86: ("Snow showers", "snow"), 95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm", "storm"), 99: ("Thunderstorm", "storm"),
}


AIR_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={LAT}&longitude={LON}&current=us_aqi,pm2_5,pm10&timezone={TZ}"
)


def get_json(url, tries=5):
    # open-meteo is sometimes slow/throttled for shared CI IPs: retry with backoff
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kindle-weather/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            print(f"attempt {i + 1}/{tries} failed for {url.split('?')[0]}: {e}", file=sys.stderr)
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def fetch():
    data = get_json(URL)
    try:  # air quality is optional: show dashes if it fails
        data["air"] = get_json(AIR_URL, tries=2)
    except Exception as e:
        print("air quality unavailable:", e, file=sys.stderr)
    return data


def font(path, size):
    return ImageFont.truetype(path, size * S)


# ---------- icons (all coordinates in final pixels; drawn at S x) ----------
def cloud(d, cx, cy, size, fill=0, bg=255):
    s = size
    parts = [
        (cx - 0.28 * s, cy + 0.05 * s, 0.22 * s),
        (cx - 0.02 * s, cy - 0.12 * s, 0.30 * s),
        (cx + 0.28 * s, cy + 0.04 * s, 0.24 * s),
    ]
    for x, y, r in parts:
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill)
    d.rectangle([(cx - 0.28 * s) * S, (cy + 0.05 * s) * S,
                 (cx + 0.28 * s) * S, (cy + 0.28 * s) * S], fill=fill)
    d.ellipse([(cx - 0.50 * s) * S, (cy - 0.20 * s) * S,
               (cx - 0.06 * s) * S, (cy + 0.28 * s) * S], fill=fill)
    d.ellipse([(cx + 0.06 * s) * S, (cy - 0.18 * s) * S,
               (cx + 0.52 * s) * S, (cy + 0.28 * s) * S], fill=fill)


def sun(d, cx, cy, size, ray=True):
    r = 0.26 * size
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=0)
    if ray:
        for i in range(8):
            a = i * math.pi / 4
            x1, y1 = cx + math.cos(a) * r * 1.4, cy + math.sin(a) * r * 1.4
            x2, y2 = cx + math.cos(a) * r * 2.0, cy + math.sin(a) * r * 2.0
            d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=0, width=max(2, int(size * 0.045 * S)))


def icon(d, kind, cx, cy, size):
    if kind == "sun":
        sun(d, cx, cy, size)
    elif kind == "part":
        sun(d, cx - size * 0.16, cy - size * 0.16, size * 0.8)
        cloud(d, cx + size * 0.08, cy + size * 0.12, size * 0.8, fill=255)  # knock-out
        cloud(d, cx + size * 0.08, cy + size * 0.12, size * 0.7, fill=0)
    elif kind == "cloud":
        cloud(d, cx, cy, size)
    elif kind == "fog":
        cloud(d, cx, cy - size * 0.12, size * 0.85)
        for i, off in enumerate((0.26, 0.38)):
            y = cy + size * off
            d.line([(cx - size * 0.35) * S, y * S, (cx + size * 0.35) * S, y * S],
                   fill=0, width=max(2, int(size * 0.045 * S)))
    elif kind in ("rain", "storm"):
        cloud(d, cx, cy - size * 0.14, size * 0.85)
        w = max(2, int(size * 0.045 * S))
        if kind == "storm":
            bx, by = cx, cy + size * 0.12
            d.polygon([(bx + 0.04 * size) * S, by * S, (bx - 0.10 * size) * S, (by + 0.20 * size) * S,
                       (bx - 0.01 * size) * S, (by + 0.20 * size) * S, (bx - 0.07 * size) * S, (by + 0.38 * size) * S,
                       (bx + 0.12 * size) * S, (by + 0.12 * size) * S, (bx + 0.02 * size) * S, (by + 0.12 * size) * S],
                      fill=0)
        else:
            for dx in (-0.22, 0.0, 0.22):
                x = cx + dx * size
                y = cy + size * 0.22
                d.line([x * S, y * S, (x - 0.06 * size) * S, (y + 0.18 * size) * S], fill=0, width=w)
    elif kind == "snow":
        cloud(d, cx, cy - size * 0.14, size * 0.85)
        for dx in (-0.22, 0.0, 0.22):
            x, y, r = cx + dx * size, cy + size * 0.30, size * 0.04
            d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=0)


# ---------- layout ----------
def text(d, xy, s, f, anchor="la", fill=0):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)


def hline(d, y, x0=60, x1=W - 60, w=2):
    d.line([x0 * S, y * S, x1 * S, y * S], fill=0, width=w * S)


def hm(iso):
    return datetime.fromisoformat(iso).strftime("%-I:%M %p").lower()


def aqi_info(v):
    if v is None:
        return "—", 0
    for hi, name in ((50, "Good"), (100, "Moderate"), (150, "Unhealthy for sensitive"),
                     (200, "Unhealthy"), (300, "Very unhealthy"), (10**9, "Hazardous")):
        if v <= hi:
            return name, v


def render(data, out):
    img = Image.new("L", (W * S, H * S), 255)
    d = ImageDraw.Draw(img)
    cur, daily = data["current"], data["daily"]
    air = (data.get("air") or {}).get("current") or {}
    now = datetime.now(ZoneInfo(TZ))

    # header: date + place
    text(d, (60, 40), now.strftime("%A"), font(FONT_BOLD, 96))
    text(d, (60, 150), now.strftime("%-d %B %Y"), font(FONT_REG, 44))
    text(d, (W - 60, 50), PLACE, font(FONT_BOLD, 58), "ra")
    text(d, (W - 60, 120), REGION, font(FONT_REG, 34), "ra")
    hline(d, 235, w=4)

    # current conditions
    label, kind = WMO.get(cur["weather_code"], ("—", "cloud"))
    icon(d, kind, 250, 395, 270)
    text(d, (W - 60, 245), f"{round(cur['temperature_2m'])}°", font(FONT_BOLD, 190), "ra")
    text(d, (W - 60, 440), label, font(FONT_REG, 46), "ra")
    text(d, (W - 60, 498), f"Feels like {round(cur['apparent_temperature'])}°", font(FONT_REG, 36), "ra")
    hline(d, 570)

    # air quality
    v = air.get("us_aqi")
    cat, _ = aqi_info(v)
    text(d, (60, 600), "AIR QUALITY (US AQI)", font(FONT_REG, 28))
    text(d, (60, 638), "—" if v is None else str(round(v)), font(FONT_BOLD, 110))
    vw = d.textlength("—" if v is None else str(round(v)), font=font(FONT_BOLD, 110)) / S
    text(d, (60 + vw + 28, 678), cat, font(FONT_BOLD, 44))
    pm25, pm10 = air.get("pm2_5"), air.get("pm10")
    text(d, (W - 60, 610), "PM2.5 " + ("—" if pm25 is None else f"{round(pm25)}"), font(FONT_REG, 34), "ra")
    text(d, (W - 60, 656), "PM10 " + ("—" if pm10 is None else f"{round(pm10)}"), font(FONT_REG, 34), "ra")
    # gauge 0..300 with category ticks
    gx0, gx1, gy = 60, W - 60, 790
    gw = gx1 - gx0
    d.rectangle([gx0 * S, gy * S, gx1 * S, (gy + 18) * S], outline=0, width=2 * S)
    for t in (50, 100, 150, 200):
        x = gx0 + gw * t / 300
        d.line([x * S, gy * S, x * S, (gy + 18) * S], fill=0, width=1 * S)
    if v is not None:
        x = gx0 + gw * min(v, 300) / 300
        d.rectangle([gx0 * S, gy * S, x * S, (gy + 18) * S], fill=0)
    hline(d, 850)

    # stats row
    stats = [
        ("HUMIDITY", f"{cur['relative_humidity_2m']}%"),
        ("WIND", f"{round(cur['wind_speed_10m'])} km/h"),
        ("SUNRISE", hm(daily['sunrise'][0])),
        ("SUNSET", hm(daily['sunset'][0])),
    ]
    colw = (W - 120) / 4
    for i, (k, val) in enumerate(stats):
        x = 60 + colw * i + colw / 2
        text(d, (x, 875), k, font(FONT_REG, 24), "ma")
        text(d, (x, 910), val, font(FONT_BOLD, 38), "ma")
    hline(d, 985)

    # 5-day forecast
    top, rowh = 990, 94
    for i in range(4):
        y = top + i * rowh
        day = datetime.fromisoformat(daily["time"][i])
        name = "Today" if i == 0 else day.strftime("%A")
        _, k = WMO.get(daily["weather_code"][i], ("—", "cloud"))
        text(d, (60, y + rowh / 2), name, font(FONT_BOLD if i == 0 else FONT_REG, 38), "lm")
        icon(d, k, 470, y + rowh / 2, 74)
        pp = daily["precipitation_probability_max"][i]
        text(d, (600, y + rowh / 2), f"{pp}%" if pp is not None else "", font(FONT_REG, 32), "lm")
        text(d, (W - 60, y + rowh / 2),
             f"{round(daily['temperature_2m_max'][i])}°  /  {round(daily['temperature_2m_min'][i])}°",
             font(FONT_BOLD, 40), "rm")
        if i < 3:
            hline(d, y + rowh, w=1)
    hline(d, top + 4 * rowh + 8, w=4)
    text(d, (W // 2, H - 30), f"Updated {now.strftime('%-I:%M %p').lower()} · refreshes every 15 min",
         font(FONT_REG, 24), "ms", fill=90)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(out, optimize=True)  # 8-bit grayscale PNG, no alpha


if __name__ == "__main__":
    render(fetch(), sys.argv[1] if len(sys.argv) > 1 else "weather.png")
