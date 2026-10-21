# almanac.py - today's sun and moon for this unit's location (config
# "location"), in local time. The Lantern Time screen and the two gauges
# (daylight left, sun direction) read it. The maths is in sun.py.
#
# All times here are minutes after local midnight (floats); None = that event
# doesn't happen today (only near the poles).

import time
import sun
import timeutil


def hm(minutes):
    """Minutes after midnight -> '18:38' (24-hour, rounded to the minute)."""
    if minutes is None:
        return "--:--"
    m = int(minutes + 0.5) % 1440
    return "%02d:%02d" % (m // 60, m % 60)


def span(minutes):
    """A length of time -> '4 H 46 M' / '46 M'."""
    m = int(minutes + 0.5)
    return "%d H %02d M" % (m // 60, m % 60) if m >= 60 else "%d M" % m


class Almanac:
    hm = staticmethod(hm)

    def __init__(self, cfg):
        self.cfg = cfg
        self.day = None           # (y, m, d) the times below belong to
        self.t = {}               # dawn / rise / noon / set / dusk today
        self.rise_tomorrow = None
        self.length = None        # sunrise to sunset, minutes
        self.change_s = None      # today's length minus yesterday's, seconds
        self.moon = (0, 0, "")    # age (days), lit fraction, name
        self.az = self.el = None
        self.now_min = 0
        self.phase = ""           # "day", "dusk", "night" or "dawn"
        self.calc_ms = 0

    def _local_times(self, utc_noon, lat, lon):
        lt = timeutil.local(self.cfg["tz"], utc_noon)
        off = timeutil.offset_s(utc_noon, self.cfg["tz"]) / 60
        raw = sun.times(lt[0], lt[1], lt[2], lat, lon)
        return {k: (None if v is None else v + off) for k, v in raw.items()}

    def update(self, utc=None):
        """Call about once a second; the day's times are only redone at midnight."""
        if utc is None:
            utc = time.time()
        t0 = time.ticks_ms()
        loc = self.cfg["location"]
        lat, lon = loc["lat"], loc["lon"]
        lt = timeutil.local(self.cfg["tz"], utc)
        day = (lt[0], lt[1], lt[2])
        if day != self.day:
            noon = utc - (lt[3] - 12) * 3600 - lt[4] * 60 - lt[5]      # about local noon
            self.t = self._local_times(noon, lat, lon)
            y = self._local_times(noon - 86400, lat, lon)
            self.rise_tomorrow = self._local_times(noon + 86400, lat, lon)["rise"]
            if self.t["rise"] is not None and self.t["set"] is not None:
                self.length = self.t["set"] - self.t["rise"]
                if y["rise"] is not None and y["set"] is not None:
                    self.change_s = int(round((self.length - (y["set"] - y["rise"])) * 60))
                else:
                    self.change_s = None
            else:
                self.length = self.change_s = None
            self.day = day
        self.now_min = lt[3] * 60 + lt[4] + lt[5] / 60
        g = time.gmtime(utc)
        gmin = g[3] * 60 + g[4] + g[5] / 60
        self.az, self.el = sun.position(g[0], g[1], g[2], gmin, lat, lon)
        self.moon = sun.moon(g[0], g[1], g[2], gmin)
        n, t = self.now_min, self.t
        if t["rise"] is None or t["set"] is None:
            self.phase = "day" if self.el > 0 else "night"
        elif t["rise"] <= n < t["set"]:
            self.phase = "day"
        elif n >= t["set"]:
            self.phase = "dusk" if (t["dusk"] is not None and n < t["dusk"]) else "night"
        else:
            self.phase = "dawn" if (t["dawn"] is not None and n >= t["dawn"]) else "night"
        self.calc_ms = time.ticks_diff(time.ticks_ms(), t0)

    # ---------- what the screen and gauges ask for ----------
    def next_event(self):
        """What the Lantern Time screen counts down to: ('DARK BY', time,
        minutes to go) from sunrise until dark - dark = the end of civil
        twilight, when the lantern gets lit (decided 2026-10-07) - then
        ('SUNRISE', time, minutes to go) through the night."""
        n, t = self.now_min, self.t
        dark = t["dusk"] if t["dusk"] is not None else t["set"]
        if self.phase in ("day", "dusk") and dark is not None:
            return "DARK BY", dark, dark - n
        if t["rise"] is not None and n < t["rise"]:
            return "SUNRISE", t["rise"], t["rise"] - n
        if self.rise_tomorrow is not None:
            return "SUNRISE", self.rise_tomorrow, self.rise_tomorrow + 1440 - n
        return "", None, None

    def readings(self):
        """For the gauges: hours of daylight left, and where the sun is."""
        if self.day is None:
            return {}
        left = 0.0
        if self.phase == "day" and self.t["set"] is not None:
            left = (self.t["set"] - self.now_min) / 60
        return {"daylight_left_h": left,
                "sun_az": self.az if (self.el is not None and self.el > -6) else None}
