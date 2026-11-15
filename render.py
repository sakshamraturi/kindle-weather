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
            print(f"attempt {i + 1}/{tries} failed for {url.split('/')[2]}: {e}", file=sys.stderr)
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def fetch():
    data = get_json(URL)
    try:  # air quality is optional: show dashes if it fails
        data["air"] = get_json(AIR_URL, tries=2)
    except Exception as e:
        print("air quality unavailable:", e, file=sys.stderr)
    sched = os.environ.get("SCHEDULE_URL", "").strip()
    if sched:
        try:  # events + tasks come from the Google Apps Script feed
            data["sched"] = get_json(sched, tries=3)
            if data["sched"].get("error"):
                raise RuntimeError(data["sched"]["error"])
            for e in data["sched"].get("errors") or []:
                print("schedule warning:", e, file=sys.stderr)
        except Exception as e:
            print("schedule unavailable:", e, file=sys.stderr)
            data.pop("sched", None)
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


class Off:
    """Draw helper that shifts everything down/up by oy final pixels."""
    def __init__(self, d, oy):
        self.d, self.oy = d, oy * S

    def _y(self, pts):
        if isinstance(pts[0], (tuple, list)):
            return [(p[0], p[1] + self.oy) for p in pts]
        return [v + (self.oy if i % 2 else 0) for i, v in enumerate(pts)]

    def text(self, xy, *a, **k): return self.d.text((xy[0], xy[1] + self.oy), *a, **k)
    def line(self, pts, **k): return self.d.line(self._y(pts), **k)
    def rectangle(self, pts, **k): return self.d.rectangle(self._y(pts), **k)
    def ellipse(self, pts, **k): return self.d.ellipse(self._y(pts), **k)
    def polygon(self, pts, **k): return self.d.polygon(self._y(pts), **k)
    def textlength(self, *a, **k): return self.d.textlength(*a, **k)


def fit(d, s, path, size, maxw):
    """Shrink the font a little, then truncate with an ellipsis, to fit maxw px."""
    while size > 22 and d.textlength(s, font=font(path, size)) / S > maxw:
        size -= 2
    f = font(path, size)
    if d.textlength(s, font=f) / S > maxw:
        while len(s) > 1 and d.textlength(s + "…", font=f) / S > maxw:
            s = s[:-1]
        s = s.rstrip() + "…"
    return s, f


def render(data, out):
    img = Image.new("L", (W * S, H * S), 255)
    d0 = ImageDraw.Draw(img)
    d = d0
    X0, X1 = 60, W - 60
    cur, daily = data["current"], data["daily"]
    air = (data.get("air") or {}).get("current") or {}
    sched = data.get("sched")
    now = datetime.now(ZoneInfo(TZ))
    today = now.date()

    def F(sz, bold=False): return font(FONT_BOLD if bold else FONT_REG, sz)
    def label(x, y, s): text(d, (x, y), s, F(22, True), fill=90)
    def box(x0, y0, x1, y1, fill=None, outline=None, w=2):
        d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill, outline=outline, width=w * S)

    # ---- header: date (left), place + sun times (right)
    text(d, (X0, 34), now.strftime("%A"), F(86, True))
    text(d, (X0, 138), now.strftime("%-d %B %Y"), F(40))
    text(d, (X1, 52), PLACE, F(44, True), "ra")
    text(d, (X1, 108), REGION, F(30), "ra", fill=70)
    text(d, (X1, 160), f"Sunrise {hm(daily['sunrise'][0])}   Sunset {hm(daily['sunset'][0])}",
         F(26), "ra", fill=70)
    hline(d, 232)

    # ---- coming up: next 5 holidays / birthdays
    label(X0, 246, "COMING UP")
    if sched is None:
        text(d, (X0, 290), "Calendar unavailable", F(32), fill=110)
        events = []
    else:
        events = [e for e in sched.get("events", []) if e["date"] >= today.isoformat()][:5]
        if not events:
            text(d, (X0, 290), "Nothing coming up", F(32), fill=110)
    y = 278
    for ev in events:
        dt = datetime.fromisoformat(ev["date"]).date()
        sub = dt.strftime("%b").upper() if (dt.month != today.month or dt.year != today.year) else dt.strftime("%a").upper()
        kind = "HOLIDAY" if ev.get("type") == "holiday" else "BIRTHDAY"
        kf = F(20, True)
        tw = d.textlength(kind, font=kf) / S
        bx0 = X1 - tw - 26
        text(d, (X0, y + 22), str(dt.day), F(34, True), "lm")
        text(d, (X0 + 62, y + 24), sub, F(20), "lm", fill=100)
        name, nf = fit(d, ev["title"], FONT_REG, 34, bx0 - (X0 + 185) - 20)
        text(d, (X0 + 185, y + 22), name, nf, "lm")
        if kind == "HOLIDAY":
            box(bx0, y + 8, X1, y + 38, fill=0)
            text(d, ((bx0 + X1) / 2, y + 23), kind, kf, "mm", fill=255)
        else:
            box(bx0, y + 8, X1, y + 38, outline=0)
            text(d, ((bx0 + X1) / 2, y + 23), kind, kf, "mm")
        y += 52
    hline(d, 556, w=1)

    # everything below is laid out in a fixed block, shifted up by 100px
    d = Off(d0, -100)

    # ---- weather + air quality
    label_, kind_ = WMO.get(cur["weather_code"], ("—", "cloud"))
    icon(d, kind_, 150, 770, 190)
    text(d, (290, 690), f"{round(cur['temperature_2m'])}°", F(150, True))
    cond_s, cond_f = fit(d, f"{label_} · Feels like {round(cur['apparent_temperature'])}°", FONT_REG, 32, 360)
    text(d, (296, 848), cond_s, cond_f)
    v = air.get("us_aqi")
    cat, _ = aqi_info(v)
    vs = "—" if v is None else str(round(v))
    label(680, 690, "AIR QUALITY (US AQI)")
    text(d, (680, 716), vs, F(80, True))
    vw = d.textlength(vs, font=F(80, True)) / S
    cat_s, cat_f = fit(d, cat, FONT_BOLD, 30, X1 - (680 + vw + 22))
    text(d, (680 + vw + 22, 786), cat_s, cat_f, "ls")
    pm25, pm10 = air.get("pm2_5"), air.get("pm10")
    text(d, (680, 812), "PM2.5 " + ("—" if pm25 is None else str(round(pm25))) +
         "  ·  PM10 " + ("—" if pm10 is None else str(round(pm10))), F(24))
    text(d, (680, 846), f"Humidity {cur['relative_humidity_2m']}%  ·  Wind {round(cur['wind_speed_10m'])} km/h", F(24))
    hline(d, 890)

    # ---- forecast: next 4 days
    label(X0, 902, "FORECAST")
    colw = (X1 - X0) / 4
    for i in range(4):
        j = i + 1
        cx = X0 + colw * i + colw / 2
        day = datetime.fromisoformat(daily["time"][j])
        _, k = WMO.get(daily["weather_code"][j], ("—", "cloud"))
        pp = daily["precipitation_probability_max"][j]
        text(d, (cx, 932), day.strftime("%a"), F(28, True), "ma")
        icon(d, k, cx, 1018, 80)
        text(d, (cx, 1062), f"{round(daily['temperature_2m_max'][j])}° / {round(daily['temperature_2m_min'][j])}°",
             F(28, True), "ma")
        text(d, (cx, 1098), f"rain {pp}%" if pp is not None else "", F(22), "ma", fill=90)
        if i:
            d.line([(X0 + colw * i) * S, 930 * S, (X0 + colw * i) * S, 1128 * S], fill=170, width=S)
    hline(d, 1150)

    # ---- to do (Google Tasks)
    label(X0, 1164, "TO DO")
    if sched is None:
        text(d, (X0, 1200), "Tasks unavailable", F(32), fill=110)
        tasks = []
    else:
        tasks = sched.get("tasks", [])[:6]
        if not tasks:
            text(d, (X0, 1200), "All done", F(32), fill=110)
    y = 1194
    for t in tasks:
        due, over = "", False
        if t.get("due"):
            dd = datetime.fromisoformat(t["due"]).date()
            if dd < today: due, over = "Overdue", True
            elif dd == today: due = "Today"
            elif (dd - today).days == 1: due = "Tomorrow"
            else: due = dd.strftime("%a %-d")
        box(X0, y + 7, X0 + 26, y + 33, outline=0, w=3)
        dw = d.textlength(due, font=F(26, over)) / S if due else 0
        title, tf = fit(d, t["title"], FONT_BOLD if over else FONT_REG, 32, X1 - (X0 + 48) - dw - 24)
        text(d, (X0 + 48, y + 20), title, tf, "lm")
        if due:
            text(d, (X1, y + 20), due, F(26, over), "rm", fill=0 if over else 90)
        y += 42
        d.line([X0 * S, (y - 2) * S, X1 * S, (y - 2) * S], fill=200, width=S)

    # footer
    cal_t = ""
    if sched and sched.get("generated"):
        try:
            g = datetime.fromisoformat(sched["generated"].replace("Z", "+00:00")).astimezone(ZoneInfo(TZ))
            cal_t = f" · Calendar & tasks {g.strftime('%-I:%M %p').lower()}"
        except Exception:
            pass
    text(d, (W // 2, 1478), f"Weather {now.strftime('%-I:%M %p').lower()}{cal_t}", F(22), "ma", fill=110)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(out, optimize=True)  # 8-bit grayscale PNG, no alpha


if __name__ == "__main__":
    render(fetch(), sys.argv[1] if len(sys.argv) > 1 else "weather.png")
