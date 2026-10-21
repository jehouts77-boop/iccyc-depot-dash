# screens/weather.py - roadmap 5.4: current conditions + the next few forecast periods
# Data: weather.py (api.weather.gov, KSUS station + LSX 72,82 forecast grid).
# Gauges on this screen (config "gauges" -> "weather"): humidity + barometer.

import timeutil
import weather as WX
import ui as U
from screens.base import Screen

DEG = "\xb0"


def _deg(v):
    return "--" if v is None else "%d%s" % (round(v), DEG)


class WeatherScreen(Screen):
    key = "weather"
    title = "WEATHER"
    short = "WEATHER"

    def __init__(self):
        self.drawn_ok = -1

    def draw(self, app):
        self.frame(app)
        u = app.ui
        w = app.weather
        self.drawn_ok = w.ok
        o = w.obs
        if o is None:
            u.text("WAITING FOR WEATHER", U.W // 2, 188, U.T_HEAD, "amber", "center")
            why = w.last_error or ("WIFI " + app.wifi_state.upper())
            for i, line in enumerate(u.wrap(why, U.T_NOTE, U.W - 40)[:2]):
                u.text(line, U.W // 2, 240 + i * 24, U.T_NOTE, "dim", "center")
            return
        # now: big temperature on the left, conditions on the right
        u.text(_deg(o["temp_f"]), 18, 76, 116, "amber")
        x = 252
        y = 74
        for line in u.wrap(o["text"].upper(), 24, U.W - x - 14)[:2]:
            u.text(line, x, y, 24, "cream")
            y += 24
        y = 126
        if o.get("feels_f") is not None and abs(o["feels_f"] - (o["temp_f"] or 0)) >= 2:
            u.text("FEELS " + _deg(o["feels_f"]), x, y, 24, "text")
        if o.get("humidity") is not None:
            u.text("HUMIDITY %d%%" % round(o["humidity"]), x, y + 24, 24, "text")
        wind = "CALM"
        if o.get("wind_mph") is not None and o["wind_mph"] >= 1:
            wind = "%s %d MPH" % (WX.compass_name(o["wind_dir"] or 0), round(o["wind_mph"]))
            if o.get("gust_mph"):
                wind += " G%d" % round(o["gust_mph"])
        u.text("WIND " + wind, 20, 176, 24, "text")
        if o.get("pressure_inhg") is not None:
            u.text("%.2f IN" % o["pressure_inhg"], U.W - 20, 176, 24, "text", "right")
        if o.get("dewpoint_f") is not None:
            u.text("DEW POINT " + _deg(o["dewpoint_f"]), 20, 200, 24, "dim")
        u.rect(16, 226, U.W - 32, 2, "line")
        # forecast
        y = 238
        for p in (w.forecast or [])[:3]:
            u.text(p["name"], 20, y, 24, "amber", max_w=300)
            hi_lo = ("HIGH " if p["is_day"] else "LOW ") + _deg(p["temp_f"])
            u.text(hi_lo, U.W - 20, y, 24, "cream", "right")
            room = U.W - 40
            if p.get("pop"):                 # chance of rain / snow, at the right
                u.text("%d%%" % p["pop"], U.W - 20, y + 24, U.T_NOTE, "dim", "right")
                room -= 60
            u.text(p["short"], 20, y + 24, U.T_NOTE, "dim", max_w=room)
            y += 54
        # where and when it's from
        t = timeutil.local(app.cfg["tz"], o["time"]) if o.get("time") else None
        note = "%s  %s" % (o.get("station") or "", timeutil.hhmm(t) if t else "")
        stale = w.stale()
        if stale:
            note += "  - OLD"
        u.text(note, U.W // 2, 402, 20, "red" if stale else "dim", "center")

    def tick(self, app, now):
        if app.weather.ok != self.drawn_ok:
            return "full"                    # new data arrived
        return None
