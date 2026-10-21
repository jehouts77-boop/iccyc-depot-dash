# trains.py - where the nearest Amtrak train is (roadmap 5.6)
#
# Data: the Amtraker API (api-v3.amtraker.com, free, no key). The all-trains
# feed is 1.2 MB - far too big - so this asks two small questions instead:
#   /v3/stations/WAH   ~260 bytes: which trains call at Washington, MO today
#   /v3/trains/311     ~4-9 KB:    one train - position, speed, every stop
# Washington is the nearest station to Wentzville on the Missouri River Runner
# line (config "train"). One request per call to update(), like weather.py, so
# the app loop never waits for two in a row. The app only fetches while the
# Nearest Train screen is showing: it is a free hobby service, and each
# request holds up the screen for a moment.
#
# Two things learned from the real feed (2026-10-07):
#   - a train number can answer with a stale record from weeks ago, so a train
#     is only believed if its ID matches the station's list ("311-7") and its
#     last position report is recent;
#   - a train that hasn't left its first station yet is "Predeparture": its
#     timetable is good, its position is just the starting platform.

import json
import math
import time
import net
from textutil import ascii_safe
from weather import iso_to_utc

BASE = "https://api-v3.amtraker.com/v3"
LIST_MAX_BYTES = 4_000
TRAIN_MAX_BYTES = 40_000
COMPASS8 = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def compass8(deg):
    return COMPASS8[int((deg % 360) / 45 + 0.5) % 8]


def miles_and_bearing(lat1, lon1, lat2, lon2):
    """Distance in miles and compass bearing from point 1 to point 2. A flat
    map is close enough at these distances (within 1% out to 300 miles)."""
    dy = (lat2 - lat1) * 69.05
    dx = (lon2 - lon1) * 69.17 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.sqrt(dx * dx + dy * dy), math.degrees(math.atan2(dx, dy)) % 360


def parse_station(body):
    """Train IDs calling at a station today, e.g. ['311-7', '319-7']."""
    i = body.find('"trains":[')
    if i == -1:
        raise ValueError("no train list")
    j = body.find("]", i)
    inner = body[i + 10:j if j != -1 else len(body)]
    return [p.strip().strip('"') for p in inner.split(",") if p.strip().strip('"')]


def parse_train(body, want_id):
    """The record whose trainID is want_id, or None (not running / stale record).

    Uses json.loads (changed 2026-10-07): the Presto has megabytes free and its
    built-in JSON reader takes a few ms, where scanning a 20-stop train by hand
    took about 6 s. A cut-off or garbled answer raises ValueError, which
    update() counts as a failure and keeps the old data."""
    doc = json.loads(body)
    if isinstance(doc, dict):                 # {"311": [record, ...]}
        lists = doc.values()
    else:                                     # [] when that number isn't running
        lists = (doc,)
    for recs in lists:
        if not isinstance(recs, list):
            continue
        for rec in recs:
            if isinstance(rec, dict) and rec.get("trainID") == want_id:
                return _train(rec)
    return None


def _str(d, key):
    v = d.get(key)
    return v if isinstance(v, str) else ""


def _num(d, key):
    v = d.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _train(rec):
    stops = []
    for st in rec.get("stations") or ():
        stops.append({
            "code": ascii_safe(_str(st, "code")), "name": ascii_safe(_str(st, "name")).upper(),
            "sch": iso_to_utc(_str(st, "schArr")),
            "arr": iso_to_utc(_str(st, "arr")),
            "dep": iso_to_utc(_str(st, "dep")),
            "gone": st.get("status") == "Departed",
        })
    return {
        "id": _str(rec, "trainID"),
        "num": _str(rec, "trainNum"),
        "route": ascii_safe(_str(rec, "routeName")).upper(),
        "lat": _num(rec, "lat"),
        "lon": _num(rec, "lon"),
        "mph": _num(rec, "velocity"),
        "heading": ascii_safe(_str(rec, "heading")),
        "state": _str(rec, "trainState"),
        "orig": _str(rec, "origCode"),
        "dest": _str(rec, "destCode"),
        "seen": iso_to_utc(_str(rec, "lastValTS")),
        "stops": stops,
    }


class Trains:
    def __init__(self, cfg):
        self.cfg = cfg
        self.c = cfg["train"]
        self.ids = None               # train IDs on today's list (None = never fetched)
        self.trains = {}              # id -> record
        self.queue = []               # what to fetch next: ("list", code) / ("train", id)
        self.round_at = 0             # time.time() when the next round starts
        self.updated = None           # time.time() of the last finished round
        self.ok = 0
        self.fails = 0
        self.rounds = 0
        self.last_error = ""
        self.last_ms = 0

    # ---------- fetching ----------
    def _get(self, url, max_bytes):
        t0 = time.ticks_ms()
        try:
            code, body = net.http_get(url, timeout_s=10, max_bytes=max_bytes)
        finally:
            self.last_ms = time.ticks_diff(time.ticks_ms(), t0)
        if code != 200:
            raise ValueError("HTTP %s" % code)
        return body

    def due(self, now):
        return bool(self.queue) or now >= self.round_at

    def wake(self, now=None):
        """The screen has just been opened: fetch now if what we have is old."""
        if now is None:
            now = time.time()
        if self.updated is None or now - self.updated > self.c["every_s"]:
            self.round_at = 0

    def update(self, now=None):
        """One request. True when a round has just finished (new data to show)."""
        if now is None:
            now = time.time()
        if not self.queue:
            self.queue = [("list", code) for code in self.c["stations"]]
            self._new_ids = []
            self.round_at = now + 120                 # if this round dies, start over then
        kind, what = self.queue.pop(0)
        try:
            if kind == "list":
                for tid in parse_station(self._get("%s/stations/%s" % (BASE, what),
                                                   LIST_MAX_BYTES)):
                    if tid not in self._new_ids:
                        self._new_ids.append(tid)
                if not self.queue or self.queue[0][0] != "list":   # last list in: now the trains
                    self.ids = self._new_ids
                    for tid in list(self.trains):
                        if tid not in self.ids:
                            del self.trains[tid]
                    self.queue = [("train", tid) for tid in self.ids]
            else:
                rec = parse_train(self._get("%s/trains/%s" % (BASE, what.split("-")[0]),
                                            TRAIN_MAX_BYTES), what)
                if rec is None:
                    self.trains.pop(what, None)
                else:
                    self.trains[what] = rec
            self.ok += 1
        except Exception as e:
            self.fails += 1
            self.last_error = ("%s: %s" % (type(e).__name__, e))[:60]
            print("trains:", self.last_error)
            if kind == "list":
                self.queue = []                       # no list: give up this round
                return False
        if self.queue:
            return False
        self.rounds += 1
        self.updated = now
        near = self.nearest(now)
        soon = near is not None and near[1] <= self.c["near_mi"]
        self.round_at = now + (self.c["every_s"] if soon else self.c["far_every_s"])
        return True

    # ---------- what the screen and gauges ask for ----------
    def _home(self):
        loc = self.cfg["location"]
        return loc["lat"], loc["lon"]

    def nearest(self, now=None):
        """(record, miles, bearing) of the closest train that is moving on the
        line and was heard from lately, or None."""
        if now is None:
            now = time.time()
        best = None
        la, lo = self._home()
        for rec in self.trains.values():
            if rec["state"] != "Active" or rec["lat"] is None or rec["lon"] is None:
                continue
            if rec["seen"] is None or now - rec["seen"] > self.c["fresh_s"]:
                continue
            mi, brg = miles_and_bearing(la, lo, rec["lat"], rec["lon"])
            if best is None or mi < best[1]:
                best = (rec, mi, brg)
        return best

    def upcoming(self, now=None):
        """[(time at the watch station, record)] still to come, soonest first."""
        if now is None:
            now = time.time()
        out = []
        for rec in self.trains.values():
            for st in rec["stops"]:
                if st["code"] == self.c["watch"]:
                    if not st["gone"] and st["arr"] is not None and st["arr"] > now - 60:
                        out.append((st["arr"], rec))
                    break
        out.sort(key=lambda p: p[0])
        return out

    @staticmethod
    def next_stop(rec):
        """Index of the first stop the train hasn't left, or None."""
        for i, st in enumerate(rec["stops"]):
            if not st["gone"]:
                return i
        return None

    def readings(self, now=None):
        near = self.nearest(now)
        if near is None:
            return {}
        rec, mi, brg = near
        return {"train_mph": rec["mph"] or 0, "train_bearing": brg, "train_mi": mi}
