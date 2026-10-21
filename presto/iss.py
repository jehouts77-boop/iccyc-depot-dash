# iss.py - where the International Space Station is right now (roadmap 5.7a,
# stage 2; the ISS page of the Overhead screen)
#
# Data: wheretheiss.at (free, no key, "roughly one request per second" allowed)
#   https://api.wheretheiss.at/v1/satellites/25544
# answers with the point on the Earth the ISS is straight above (latitude,
# longitude), its height (km), speed (km/h) and whether it is in sunlight
# ("daylight") or in the Earth's shadow ("eclipsed"). About 300 bytes.
#
# Worked out here from that and the unit's own location:
#   - how far away that point on the ground is, and which way (great circle)
#   - elevation: how many degrees above the horizon the ISS would be seen
#     from here (below 0 = under the horizon). Simple sphere geometry, good to
#     about a degree, which is plenty for a needle.
#   - which way it is heading, from the last two positions
#
# Like planes.py: one request per call to update(), and the app only fetches
# while the ISS page is showing.

import json
import math
import time
import net
from aprs import miles_and_bearing

URL = "https://api.wheretheiss.at/v1/satellites/25544"
EARTH_KM = 6371.0
KM_TO_MI = 0.621371
MAX_BYTES = 2000


def elevation(ground_mi, alt_km):
    """Degrees above the horizon of something alt_km up, straight above a point
    ground_mi away along the Earth's surface."""
    g = ground_mi / KM_TO_MI / EARTH_KM            # angle at the Earth's centre
    r = EARTH_KM / (EARTH_KM + alt_km)
    return math.degrees(math.atan2(math.cos(g) - r, math.sin(g)))


def horizon_mi(alt_km):
    """Ground distance at which something alt_km up sits right on the horizon."""
    return math.acos(EARTH_KM / (EARTH_KM + alt_km)) * EARTH_KM * KM_TO_MI


def parse(body, home):
    doc = json.loads(body)
    if not isinstance(doc, dict):
        raise ValueError("not an object")
    lat, lon, alt = doc.get("latitude"), doc.get("longitude"), doc.get("altitude")
    for v in (lat, lon, alt):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ValueError("no position")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 150 < alt < 1000):
        raise ValueError("position out of range")
    mi, brg = miles_and_bearing(home[0], home[1], lat, lon)
    kmh = doc.get("velocity")
    vis = doc.get("visibility")
    ts = doc.get("timestamp")
    return {
        "lat": lat, "lon": lon, "alt_mi": alt * KM_TO_MI, "alt_km": alt,
        "mph": kmh * KM_TO_MI if isinstance(kmh, (int, float)) else None,
        "sunlit": None if vis not in ("daylight", "eclipsed") else vis == "daylight",
        "mi": mi, "brg": brg, "elev": elevation(mi, alt),
        "horizon_mi": horizon_mi(alt),
        "ts": ts if isinstance(ts, int) else None,
    }


class ISS:
    def __init__(self, cfg):
        self.cfg = cfg
        self.c = cfg["iss"]
        self.now = None               # the latest position (dict from parse)
        self.track = None             # compass direction it is moving, or None
        self.prev = None
        self.next_at = 0
        self.updated = None
        self.ok = 0
        self.fails = 0
        self.rounds = 0
        self.last_error = ""
        self.last_ms = 0

    def due(self, now):
        return now >= self.next_at

    def wake(self, now=None):
        if now is None:
            now = time.time()
        if self.updated is None or now - self.updated > self.c["every_s"]:
            self.next_at = 0

    def update(self, now=None):
        if now is None:
            now = time.time()
        self.next_at = now + self.c["every_s"]
        t0 = time.ticks_ms()
        try:
            try:
                code, body = net.http_get(URL, timeout_s=10, max_bytes=MAX_BYTES)
            finally:
                self.last_ms = time.ticks_diff(time.ticks_ms(), t0)
            if code != 200:
                raise ValueError("HTTP %s" % code)
            loc = self.cfg["location"]
            pos = parse(body, (loc["lat"], loc["lon"]))
        except Exception as e:
            self.fails += 1
            self.last_error = ("%s: %s" % (type(e).__name__, e))[:60]
            print("iss:", self.last_error)
            self.next_at = now + max(self.c["every_s"], 30)
            return False
        old = self.now
        if old is not None and self.updated is not None and now - self.updated < 120:
            _, self.track = miles_and_bearing(old["lat"], old["lon"], pos["lat"], pos["lon"])
        else:
            self.track = None
        self.prev, self.now = old, pos
        self.updated = now
        self.ok += 1
        self.rounds += 1
        return True

    def stale(self, now=None):
        if now is None:
            now = time.time()
        # it moves about 5 miles a second: a position a minute old is 300 miles out
        return self.updated is None or now - self.updated > max(4 * self.c["every_s"], 60)

    def readings(self):
        """For the gauges: how high above the horizon, and which way to look."""
        p = self.now
        if p is None or self.stale():
            return {}
        return {"iss_elev": p["elev"], "iss_bearing": p["brg"], "iss_mi": p["mi"]}
