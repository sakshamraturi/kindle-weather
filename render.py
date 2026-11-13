#!/usr/bin/env python3
"""Render a Kindle Paperwhite 3 (1072x1448, 8-bit grayscale) weather screen.

Usage: render.py [out.png]
Data: Open-Meteo (no API key). Location: Karnal, Haryana.
"""
import json
import math
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

PLACE = "Karnal"
REGION = "Haryana"
LAT, LON = 29.6857, 76.9905
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
    f"&timezone={TZ}&forecast_days=5"
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


def fetch():
    with urllib.request.urlopen(URL, timeout=20) as r:
        return json.load(r)


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


def render(data, out):
    img = Image.new("L", (W * S, H * S), 255)
    d = ImageDraw.Draw(img)
    cur, daily = data["current"], data["daily"]
    now = datetime.fromisoformat(cur["time"])

    # header
    text(d, (60, 50), PLACE, font(FONT_BOLD, 64))
    text(d, (60, 128), REGION + ", India", font(FONT_REG, 34))
    text(d, (W - 60, 62), now.strftime("%A"), font(FONT_BOLD, 40), "ra")
    text(d, (W - 60, 112), now.strftime("%-d %B %Y"), font(FONT_REG, 34), "ra")
    hline(d, 190, w=4)

    # current conditions
    label, kind = WMO.get(cur["weather_code"], ("—", "cloud"))
    icon(d, kind, 300, 410, 360)
    text(d, (W - 60, 225), f"{round(cur['temperature_2m'])}°", font(FONT_BOLD, 250), "ra")
    text(d, (W - 60, 500), label, font(FONT_REG, 52), "ra")

    # stats row
    hline(d, 610)
    stats = [
        ("FEELS LIKE", f"{round(cur['apparent_temperature'])}°"),
        ("HUMIDITY", f"{cur['relative_humidity_2m']}%"),
        ("WIND", f"{round(cur['wind_speed_10m'])} km/h"),
    ]
    colw = (W - 120) / 3
    for i, (k, v) in enumerate(stats):
        x = 60 + colw * i + colw / 2
        text(d, (x, 645), k, font(FONT_REG, 28), "ma")
        text(d, (x, 688), v, font(FONT_BOLD, 56), "ma")
    hline(d, 795)

    # 5-day forecast
    top, rowh = 815, 100
    for i in range(5):
        y = top + i * rowh
        day = datetime.fromisoformat(daily["time"][i])
        name = "Today" if i == 0 else day.strftime("%A")
        _, k = WMO.get(daily["weather_code"][i], ("—", "cloud"))
        text(d, (60, y + rowh / 2), name, font(FONT_BOLD if i == 0 else FONT_REG, 42), "lm")
        icon(d, k, 470, y + rowh / 2, 76)
        pp = daily["precipitation_probability_max"][i]
        text(d, (610, y + rowh / 2), f"{pp}%" if pp is not None else "", font(FONT_REG, 34), "lm")
        text(d, (W - 60, y + rowh / 2),
             f"{round(daily['temperature_2m_max'][i])}°  /  {round(daily['temperature_2m_min'][i])}°",
             font(FONT_BOLD, 44), "rm")
        if i < 4:
            hline(d, y + rowh, x0=60, x1=W - 60, w=1)
    hline(d, top + 5 * rowh + 10, w=4)

    # sun times + updated
    y = top + 5 * rowh + 40
    text(d, (60, y), f"Sunrise {hm(daily['sunrise'][0])}", font(FONT_REG, 40))
    text(d, (W - 60, y), f"Sunset {hm(daily['sunset'][0])}", font(FONT_REG, 40), "ra")
    text(d, (W // 2, H - 24), f"Updated {now.strftime('%-I:%M %p').lower()}",
         font(FONT_REG, 26), "ms", fill=90)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(out, optimize=True)  # 8-bit grayscale PNG, no alpha


if __name__ == "__main__":
    render(fetch(), sys.argv[1] if len(sys.argv) > 1 else "weather.png")
