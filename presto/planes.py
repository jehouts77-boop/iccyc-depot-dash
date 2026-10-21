# planes.py - what is flying near the unit (roadmap 5.7, the Overhead screen)
#
# Data: two free volunteer feeds that answer in the same layout ({"ac": [...]},
# the ADS-B Exchange v2 format), tried in this order (FEEDS below):
#   1. adsb.fi   https://opendata.adsb.fi/api/v3/lat/<lat>/lon/<lon>/dist/<nm>
#      (from 2026-10-17). Personal, non-commercial use; 1 request/s; their terms
#      ask for a credit and a link to https://adsb.fi (it is in the README).
#   2. adsb.lol  https://api.adsb.lol/v2/point/<lat>/<lon>/<nm>  (the feed from
#      2026-10-07; kept as the backup). Desk test 2026-10-17, from the Presto:
#      adsb.fi 3 of 3 in 0.84-0.93 s; adsb.lol 2 of 3 in 12.6-25.5 s (its
#      servers were slow to set up the secure connection and to answer);
#      airplanes.live answered 403 (they now want to be contacted first).
# If the feed in use fails, the next refresh tries the other one; after any
# request the next one starts again with adsb.fi.
# Each answer is every aircraft the volunteers' receivers hear inside the
# circle: about 600 bytes a plane, 12-14 KB for 20-odd planes within 30-40 nm
# of Wentzville. adsb.lol adds each plane's distance ("dst", nautical miles)
# and direction ("dir", degrees) from the point asked; when a feed leaves
# them out, parse() works them out from the plane's position.
#
# One request per call to update(), like weather.py and trains.py. The app
# only fetches while the Overhead screen is showing: it is a free hobby
# service, and each request holds up the screen for a moment.
#
# Shown: planes in the air only (a parked or taxiing plane reports its
# altitude as the word "ground"), with a position less than fresh_s old.
# Units on the screen: miles, feet, MPH (the feed gives nautical miles, feet, knots).

import json
import time
import net
from textutil import ascii_safe
from trains import miles_and_bearing

FEEDS = (                     # (short name for Diagnostics, URL pattern: lat, lon, radius nm)
    ("FI", "https://opendata.adsb.fi/api/v3/lat/%.4f/lon/%.4f/dist/%d"),
    ("LOL", "https://api.adsb.lol/v2/point/%.4f/%.4f/%d"),
)
MAX_BYTES = 60_000            # about 100 planes; a longer answer is thrown away whole
MI_PER_NM = 1.15078

# Airline radio callsign prefixes -> names: "SWA4322" is shown as "SOUTHWEST 4322".
# Only used when the callsign is three letters and then a flight number.
AIRLINES = {
    "AAL": "AMERICAN", "AAY": "ALLEGIANT", "ABX": "ABX AIR", "ACA": "AIR CANADA",
    "AMF": "AMERIFLIGHT", "ASA": "ALASKA", "ASH": "MESA", "ATN": "AIR TRANSPORT",
    "BAW": "BRITISH AIRWAYS", "DAL": "DELTA", "DLH": "LUFTHANSA", "EDV": "ENDEAVOR",
    "EJA": "NETJETS", "ENY": "ENVOY", "FDX": "FEDEX", "FFT": "FRONTIER", "GJS": "GOJET",
    "GTI": "ATLAS AIR", "JBU": "JETBLUE", "JIA": "PSA", "JZA": "JAZZ", "KAP": "CAPE AIR",
    "LXJ": "FLEXJET", "MXY": "BREEZE", "NKS": "SPIRIT", "PDT": "PIEDMONT", "RCH": "REACH",
    "RPA": "REPUBLIC", "SCX": "SUN COUNTRY", "SKW": "SKYWEST", "SWA": "SOUTHWEST",
    "UAL": "UNITED", "UPS": "UPS", "WJA": "WESTJET",
}

# Aircraft type codes -> names. Anything not listed shows its code.
TYPES = {
    "A319": "AIRBUS A319", "A320": "AIRBUS A320", "A321": "AIRBUS A321",
    "A20N": "AIRBUS A320NEO", "A21N": "AIRBUS A321NEO", "A332": "AIRBUS A330-200",
    "A333": "AIRBUS A330-300", "A359": "AIRBUS A350-900", "BCS1": "AIRBUS A220-100",
    "BCS3": "AIRBUS A220-300",
    "B712": "BOEING 717", "B737": "BOEING 737-700", "B738": "BOEING 737-800",
    "B739": "BOEING 737-900", "B38M": "BOEING 737 MAX 8", "B39M": "BOEING 737 MAX 9",
    "B744": "BOEING 747-400", "B748": "BOEING 747-8", "B752": "BOEING 757-200",
    "B753": "BOEING 757-300", "B762": "BOEING 767-200", "B763": "BOEING 767-300",
    "B772": "BOEING 777-200", "B77L": "BOEING 777-200LR", "B77W": "BOEING 777-300ER",
    "B788": "BOEING 787-8", "B789": "BOEING 787-9", "MD11": "MD-11",
    "CRJ2": "BOMBARDIER CRJ-200", "CRJ7": "BOMBARDIER CRJ-700", "CRJ9": "BOMBARDIER CRJ-900",
    "E135": "EMBRAER 135", "E145": "EMBRAER 145", "E170": "EMBRAER 170",
    "E75L": "EMBRAER 175", "E75S": "EMBRAER 175", "E190": "EMBRAER 190",
    "AT72": "ATR 72", "AT76": "ATR 72", "DH8D": "DASH 8 Q400",
    "C150": "CESSNA 150", "C152": "CESSNA 152", "C172": "CESSNA 172", "C177": "CESSNA CARDINAL",
    "C182": "CESSNA 182", "C206": "CESSNA 206", "C208": "CESSNA CARAVAN",
    "C210": "CESSNA 210", "C310": "CESSNA 310", "C340": "CESSNA 340", "C402": "CESSNA 402",
    "C414": "CESSNA 414", "C421": "CESSNA 421",
    "C510": "CESSNA CITATION MUSTANG", "C525": "CESSNA CITATIONJET", "C25A": "CESSNA CITATION CJ2",
    "C25B": "CESSNA CITATION CJ3", "C25C": "CESSNA CITATION CJ4", "C550": "CESSNA CITATION II",
    "C560": "CESSNA CITATION V", "C56X": "CESSNA CITATION EXCEL",
    "C680": "CESSNA CITATION SOVEREIGN", "C68A": "CESSNA CITATION LATITUDE",
    "C700": "CESSNA CITATION LONGITUDE", "C750": "CESSNA CITATION X",
    "P28A": "PIPER CHEROKEE", "P28B": "PIPER CHEROKEE", "P28R": "PIPER ARROW",
    "PA32": "PIPER CHEROKEE SIX", "P32R": "PIPER SARATOGA", "PA34": "PIPER SENECA",
    "PA44": "PIPER SEMINOLE", "PA46": "PIPER MALIBU", "P46T": "PIPER MERIDIAN",
    "M600": "PIPER M600", "M700": "PIPER M700",
    "SR20": "CIRRUS SR20", "SR22": "CIRRUS SR22", "S22T": "CIRRUS SR22T", "SF50": "CIRRUS VISION JET",
    "BE33": "BEECH BONANZA", "BE35": "BEECH BONANZA", "BE36": "BEECH BONANZA",
    "BE55": "BEECH BARON", "BE58": "BEECH BARON", "BE9L": "BEECH KING AIR 90",
    "BE20": "BEECH KING AIR 200", "B350": "BEECH KING AIR 350", "BE40": "BEECHJET 400",
    "M20P": "MOONEY M20", "M20T": "MOONEY M20", "DV20": "DIAMOND DA20", "DA40": "DIAMOND DA40",
    "DA42": "DIAMOND DA42", "EV97": "EVEKTOR EUROSTAR", "RV12": "VAN'S RV-12",
    "PC12": "PILATUS PC-12", "PC24": "PILATUS PC-24", "TBM7": "TBM 700", "TBM8": "TBM 850",
    "TBM9": "TBM 900",
    "E50P": "EMBRAER PHENOM 100", "E55P": "EMBRAER PHENOM 300", "E545": "EMBRAER LEGACY 450",
    "E550": "EMBRAER PRAETOR 600", "LJ35": "LEARJET 35", "LJ45": "LEARJET 45",
    "LJ60": "LEARJET 60", "LJ75": "LEARJET 75", "H25B": "HAWKER 800",
    "CL30": "CHALLENGER 300", "CL35": "CHALLENGER 350", "CL60": "CHALLENGER 600",
    "GLF4": "GULFSTREAM IV", "GLF5": "GULFSTREAM V", "GLF6": "GULFSTREAM G650",
    "GLEX": "GLOBAL EXPRESS", "GL5T": "GLOBAL 5000", "F2TH": "FALCON 2000", "FA50": "FALCON 50",
    "F900": "FALCON 900",
    "B06": "BELL 206 HELICOPTER", "B407": "BELL 407 HELICOPTER", "B429": "BELL 429 HELICOPTER",
    "EC30": "EC130 HELICOPTER", "EC35": "EC135 HELICOPTER", "EC45": "EC145 HELICOPTER",
    "AS50": "AS350 HELICOPTER", "R22": "ROBINSON R22 HELICOPTER",
    "R44": "ROBINSON R44 HELICOPTER", "R66": "ROBINSON R66 HELICOPTER",
    "H60": "BLACK HAWK HELICOPTER",
    "C130": "C-130 HERCULES", "C30J": "C-130J HERCULES", "C17": "C-17 GLOBEMASTER",
    "K35R": "KC-135 TANKER", "F15": "F-15 EAGLE",
}


def _num(d, key):
    v = d.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _str(d, key):
    v = d.get(key)
    return ascii_safe(v).strip().upper() if isinstance(v, str) else ""


def call_name(call):
    """'SWA4322' -> 'SOUTHWEST 4322'; anything else is left alone."""
    if len(call) > 3 and call[:3] in AIRLINES and "0" <= call[3] <= "9":
        return "%s %s" % (AIRLINES[call[:3]], call[3:])
    return call


def type_name(code, category=""):
    if code in TYPES:
        return TYPES[code]
    if category == "A7":                      # the feed's class for rotorcraft
        return (code + " HELICOPTER").strip()
    return code


def parse(body, home, radius_mi, fresh_s):
    """List of planes in the air inside the circle, nearest first.
    A cut-off or garbled answer raises ValueError."""
    doc = json.loads(body)
    acs = doc.get("ac") if isinstance(doc, dict) else None
    if not isinstance(acs, list):
        raise ValueError("no aircraft list")
    out = []
    for a in acs:
        if not isinstance(a, dict):
            continue
        alt = _num(a, "alt_baro")
        if alt is None:
            alt = _num(a, "alt_geom") if a.get("alt_baro") != "ground" else None
        lat, lon = _num(a, "lat"), _num(a, "lon")
        if alt is None or lat is None or lon is None:
            continue                          # on the ground, or no position
        age = _num(a, "seen_pos")
        if age is not None and age > fresh_s:
            continue
        mi, brg = miles_and_bearing(home[0], home[1], lat, lon)
        dst, dr = _num(a, "dst"), _num(a, "dir")
        if dst is not None and dr is not None:    # the feed's own figures (true great-circle)
            mi, brg = dst * MI_PER_NM, dr
        if mi > radius_mi:
            continue
        gs = _num(a, "gs")
        rate = _num(a, "baro_rate")
        if rate is None:
            rate = _num(a, "geom_rate")
        trk = _num(a, "track")
        if trk is None:
            trk = _num(a, "true_heading")
        call = _str(a, "flight") or _str(a, "r") or _str(a, "hex")
        code = _str(a, "t")
        out.append({
            "call": call, "name": call_name(call), "reg": _str(a, "r"),
            "type": code, "type_name": type_name(code, _str(a, "category")),
            "alt": int(alt), "mph": None if gs is None else gs * MI_PER_NM,
            "track": trk, "fpm": rate or 0, "mi": mi, "brg": brg,
        })
    out.sort(key=lambda p: p["mi"])
    return out


class Planes:
    def __init__(self, cfg):
        self.cfg = cfg
        self.c = cfg["planes"]
        loc = cfg["location"]
        nm = int(self.c["radius_mi"] / MI_PER_NM + 1)
        self.urls = [(name, pat % (loc["lat"], loc["lon"], nm)) for name, pat in FEEDS]
        self.feed = 0                 # which feed the next request goes to
        self.last_feed = "-"          # the one that answered last (Diagnostics)
        self.list = None              # planes, nearest first (None = never fetched)
        self.pick = 0                 # which one the screen and the gauges show
        self.pick_call = ""
        self.next_at = 0              # time.time() of the next try
        self.updated = None           # time.time() of the last good fetch
        self.ok = 0
        self.fails = 0
        self.rounds = 0
        self.last_error = ""
        self.last_ms = 0

    def due(self, now):
        return now >= self.next_at

    def wake(self, now=None):
        """The screen has just been opened: fetch now if what we have is old."""
        if now is None:
            now = time.time()
        if self.updated is None or now - self.updated > self.c["every_s"]:
            self.next_at = 0
        self.pick = 0
        self.pick_call = ""

    def update(self, now=None):
        """One request. True when there is new data to show."""
        if now is None:
            now = time.time()
        self.next_at = now + self.c["every_s"]
        use = self.feed
        name, url = self.urls[use]
        self.feed = 0                 # whatever happens, the next request starts with adsb.fi...
        t0 = time.ticks_ms()
        try:
            try:
                code, body = net.http_get(url, timeout_s=10, max_bytes=MAX_BYTES)
            finally:
                self.last_ms = time.ticks_diff(time.ticks_ms(), t0)
            if code != 200:
                raise ValueError("HTTP %s" % code)
            loc = self.cfg["location"]
            planes = parse(body, (loc["lat"], loc["lon"]), self.c["radius_mi"],
                           self.c["fresh_s"])
        except Exception as e:
            self.fails += 1
            self.last_error = ("%s %s: %s" % (name, type(e).__name__, e))[:60]
            print("planes:", self.last_error)
            if use == 0 and len(self.urls) > 1:
                self.feed = 1         # ...unless adsb.fi just failed: then the backup, at the usual time
            else:
                self.next_at = now + max(self.c["every_s"], 60)     # both had a go: go easy
            return False
        self.last_feed = name
        self.list = planes
        self.ok += 1
        self.rounds += 1
        self.updated = now
        # keep showing the same plane if the user stepped to one and it is still here
        self.pick = 0
        if self.pick_call:
            for i in range(len(planes)):
                if planes[i]["call"] == self.pick_call:
                    self.pick = i
                    break
            else:
                self.pick_call = ""
        return True

    def step(self):
        """The screen was tapped: show the next plane out."""
        if self.list:
            self.pick = (self.pick + 1) % len(self.list)
            self.pick_call = self.list[self.pick]["call"] if self.pick else ""

    def stale(self, now=None):
        if now is None:
            now = time.time()
        return self.updated is None or now - self.updated > 4 * max(self.c["every_s"], 60)

    def shown(self):
        """The plane the screen is showing, or None."""
        if not self.list or self.stale():
            return None
        return self.list[min(self.pick, len(self.list) - 1)]

    def readings(self):
        """For the gauges: the shown plane's height and where to look for it."""
        p = self.shown()
        if p is None:
            return {}
        return {"plane_alt_kft": p["alt"] / 1000, "plane_bearing": p["brg"], "plane_mi": p["mi"]}
