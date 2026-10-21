# weather.py - current conditions and forecast from api.weather.gov (roadmap 5.4)
#
# Free, no key; it asks for a descriptive User-Agent (net.USER_AGENT).
# Two small requests, both looked up once for Wentzville (2026-09-30) and kept
# in the config so the device never has to search for them:
#   observation  /stations/KSUS/observations/latest  ~4 KB, every 10 min
#                (Spirit of St. Louis airport, the nearest station)
#   forecast     /gridpoints/LSX/72,82/forecast      ~13 KB, every 30 min
# (The hourly forecast is ~160 KB - not used.)
#
# Like the Model 100 project, responses are hand-scanned for the few fields
# needed instead of parsed whole, and capped with max_bytes.

import time
import net
from textutil import ascii_safe

BASE = "https://api.weather.gov"
OBS_MAX_BYTES = 12_000
FC_MAX_BYTES = 30_000
FC_KEEP = 4                  # forecast periods kept (tonight, tomorrow, ...)
STALE_S = 2 * 3600           # an observation older than this is shown as old

COMPASS16 = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def c_to_f(c):
    return None if c is None else c * 9 / 5 + 32


def kmh_to_mph(k):
    return None if k is None else k / 1.609344


def pa_to_inhg(p):
    return None if p is None else p / 3386.389


def compass_name(deg):
    return COMPASS16[int((deg % 360) / 22.5 + 0.5) % 16]


def iso_to_utc(s):
    """'2026-10-01T00:40:00+00:00' -> seconds (UTC). None if it can't be read."""
    try:
        t = time.mktime((int(s[0:4]), int(s[5:7]), int(s[8:10]),
                         int(s[11:13]), int(s[14:16]), int(s[17:19]), 0, 0))
        off = s[19:]
        if off and off[0] in "+-":
            sign = 1 if off[0] == "+" else -1
            t -= sign * (int(off[1:3]) * 3600 + int(off[4:6]) * 60)
        return t
    except (ValueError, IndexError):
        return None


def _qv(body, name):
    """The "value" of a {"unitCode":..,"value":..} field, e.g. "temperature"."""
    i = body.find('"%s":' % name)
    if i == -1:
        return None
    return net.json_num_after(body, '"value":', i)


def parse_observation(body):
    """Dict of readings (US units) from /observations/latest. Missing = None."""
    p = body.find('"properties"')
    if p == -1:
        raise ValueError("no properties")
    body = body[p:]
    wind_dir = _qv(body, "windDirection")
    wind_kmh = _qv(body, "windSpeed")
    feels_c = _qv(body, "heatIndex")
    if feels_c is None:
        feels_c = _qv(body, "windChill")
    return {
        "station": net.json_str_after(body, '"stationId": "') or net.json_str_after(body, '"stationId":"'),
        "time": iso_to_utc(net.json_str_after(body, '"timestamp": "') or
                           net.json_str_after(body, '"timestamp":"')),
        "text": ascii_safe(net.json_str_after(body, '"textDescription": "') or
                           net.json_str_after(body, '"textDescription":"')),
        "temp_f": c_to_f(_qv(body, "temperature")),
        "dewpoint_f": c_to_f(_qv(body, "dewpoint")),
        "feels_f": c_to_f(feels_c),
        "humidity": _qv(body, "relativeHumidity"),
        "wind_dir": wind_dir,
        "wind_mph": kmh_to_mph(wind_kmh),
        "gust_mph": kmh_to_mph(_qv(body, "windGust")),
        "pressure_inhg": pa_to_inhg(_qv(body, "barometricPressure")),
    }


def _str(obj, key):
    return net.json_str_after(obj, '"%s": "' % key) or net.json_str_after(obj, '"%s":"' % key)


def parse_forecast(body, keep=FC_KEEP):
    """List of periods: name, temp_f, is_day, pop, wind, short, detail.
    A body cut off by max_bytes just gives fewer periods."""
    i = body.find('"periods"')
    if i == -1:
        raise ValueError("no periods")
    i = body.find("[", i)
    out = []
    while len(out) < keep:
        a = body.find("{", i + 1)
        if a == -1:
            break
        b = net.find_matching_bracket(body, a)
        if b == -1:
            break                          # cut off mid-period: stop here
        obj = body[a:b + 1]
        pop_i = obj.find('"probabilityOfPrecipitation"')
        out.append({
            "name": ascii_safe(_str(obj, "name")).upper(),
            "temp_f": net.json_num_after(obj, '"temperature":'),
            "is_day": obj.find('"isDaytime": true') != -1 or obj.find('"isDaytime":true') != -1,
            "pop": net.json_num_after(obj, '"value":', pop_i) if pop_i != -1 else None,
            "wind": ascii_safe(_str(obj, "windSpeed") + " " + _str(obj, "windDirection")).upper(),
            "short": ascii_safe(_str(obj, "shortForecast")).upper(),
            "detail": ascii_safe(_str(obj, "detailedForecast")),
        })
        i = b
    if not out:
        raise ValueError("no forecast periods")
    return out


class Weather:
    def __init__(self, cfg):
        w = cfg["weather"]
        self.obs_url = "%s/stations/%s/observations/latest" % (BASE, w["station"])
        self.fc_url = "%s/gridpoints/%s/forecast" % (BASE, w["grid"])
        self.obs_every = w["obs_every_s"]
        self.fc_every = w["fc_every_s"]
        self.obs = None
        self.forecast = None
        self.obs_at = None             # time.time() of the last good fetch
        self.fc_at = None
        self.next_obs = 0              # time.time() of the next try
        self.next_fc = 0
        self.ok = 0
        self.fails = 0
        self.last_error = ""
        self.last_ms = 0               # how long the last fetch blocked

    def _get(self, url, max_bytes):
        t0 = time.ticks_ms()
        try:
            code, body = net.http_get(url, timeout_s=10, max_bytes=max_bytes,
                                      headers={"Accept": "application/geo+json"})
        finally:
            self.last_ms = time.ticks_diff(time.ticks_ms(), t0)
        if code != 200:
            raise ValueError("HTTP %s" % code)
        return body

    def due(self, now):
        return now >= self.next_obs or now >= self.next_fc

    def update(self, now=None):
        """Fetch whatever is due (at most one request per call, so the app
        loop is never blocked for two in a row). True if something changed."""
        if now is None:
            now = time.time()
        try:
            if now >= self.next_obs:
                self.next_obs = now + 60           # retry in a minute if this fails
                self.obs = parse_observation(self._get(self.obs_url, OBS_MAX_BYTES))
                self.obs_at = now
                self.next_obs = now + self.obs_every
                self.ok += 1
                return True
            if now >= self.next_fc:
                self.next_fc = now + 120
                self.forecast = parse_forecast(self._get(self.fc_url, FC_MAX_BYTES))
                self.fc_at = now
                self.next_fc = now + self.fc_every
                self.ok += 1
                return True
        except Exception as e:
            self.fails += 1
            self.last_error = ("%s: %s" % (type(e).__name__, e))[:60]
            print("weather:", self.last_error)
        return False

    def stale(self, now=None):
        if self.obs is None or self.obs.get("time") is None:
            return True
        if now is None:
            now = time.time()
        return now - self.obs["time"] > STALE_S

    def readings(self):
        """Values for app.data (the gauges). Empty when there's nothing usable."""
        o = self.obs
        if o is None or self.stale():
            return {}
        out = {}
        for k in ("temp_f", "humidity", "pressure_inhg", "wind_mph", "dewpoint_f"):
            if o.get(k) is not None:
                out[k] = o[k]
        if o.get("wind_dir") is not None:
            out["wind_dir"] = o["wind_dir"]
        elif o.get("wind_mph") == 0:
            out["wind_dir"] = 0            # calm: no direction reported
        return out
