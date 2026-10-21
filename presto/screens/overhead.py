# screens/overhead.py - roadmap 5.7: Overhead - the planes near the unit.
# Data: planes.py (adsb.fi, adsb.lol as backup), fetched only while this screen is showing.
#
# Look agreed 2026-10-07 (renders\overhead_planes_mockup_2026-10-07.png,
# layout A): a small scope on the left - north up, the unit in the middle,
# rings at a third and two thirds of the range, each plane a dot with a tick
# showing which way it is flying - and the nearest plane's details on the
# right. A tap steps to the next plane out (and back to the nearest after the
# last); the red dot and the gauges follow.
# Gauges on this screen (config "gauges" -> "overhead"): the shown plane's
# altitude + a compass pointing at it with the distance underneath.
#
# The ISS page (roadmap 5.7a, drafted 2026-10-13): the button at the bottom
# right swaps between PLANES and ISS. The ISS page shows where the space
# station is now (iss.py, wheretheiss.at, fetched only while that page is up):
# a scope whose middle ring is the horizon - inside it the ISS is above the
# horizon from here - plus its distance, direction, height, speed and whether
# it is in sunlight. Gauges on that page (config "gauges" -> "overhead_iss"):
# elevation above the horizon + a compass pointing at it.
# Bottom strip of the ISS page (stage 1, 2026-10-14): when the ISS was last heard over
# ham radio - isslisten.py keeps listening in the background - and where it was then.

import math
import time
import timeutil
import ui as U
from trains import compass8
from aprs import miles_and_bearing as gc_miles
from screens.base import Screen

CX, CY, R = 128, 232, 112          # the scope
COL = 262                          # left edge of the details
SWAP = (352, 366, 112, 50)         # the PLANES / ISS button (x, y, w, h)


def commas(n):
    """12345 -> '12,345' (MicroPython's format has no thousands comma)."""
    s = str(int(n))
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    return s + out


def climb_word(fpm):
    return "CLIMBING" if fpm > 300 else "DESCENDING" if fpm < -300 else "LEVEL"


class Overhead(Screen):
    key = "overhead"
    title = "OVERHEAD"
    short = "OVERHEAD"

    def __init__(self):
        self.shown = None
        self.page = "planes"             # or "iss"; kept when you come back to the screen

    def enter(self, app):
        self.shown = None
        self._wake(app)

    def _wake(self, app):
        if self.page == "iss":
            app.iss.wake()
        else:
            app.planes.wake()

    def _stamp(self, app):
        if self.page == "iss":
            h = app.listener.heard
            return ("iss", app.iss.rounds, app.iss.fails, app.local()[4],
                    h and h["t"], h and h["lat"])
        pl = app.planes
        return ("planes", pl.rounds, pl.fails, pl.pick, app.local()[4])

    def tick(self, app, now):
        return "full" if self._stamp(app) != self.shown else None

    def gauge_pair(self, app):
        """app.sync_gauges: the ISS page has its own pair."""
        if self.page == "iss":
            return app.cfg["gauges"].get("overhead_iss")
        return None

    def on_touch(self, app, x, y):
        bx, by, bw, bh = SWAP
        if bx - 8 <= x < bx + bw + 8 and by - 8 <= y < U.FOOTER_Y:
            self.page = "iss" if self.page == "planes" else "planes"
            self._wake(app)
            app.redraw()
            return True
        if U.BODY_Y <= y < U.FOOTER_Y and self.page == "planes":
            app.planes.step()
            app.redraw()
            return True
        return False

    def _swap_button(self, app):
        u = app.ui
        x, y, w, h = SWAP
        u.rect(x, y, w, h, "line")
        u.rect(x + 2, y + 2, w - 4, h - 4, "panel")
        label = "ISS  >" if self.page == "planes" else "PLANES  >"
        u.text(label, x + w // 2, y + 13, 26, "amber", "center")

    # ---------- drawing ----------
    def _ring(self, u, r, colour="line"):
        u.pen(colour)
        u.d.circle(CX, CY, r)
        u.pen("bg")
        u.d.circle(CX, CY, r - (2 if r == R else 1))

    def _scope(self, app, planes, pick):
        u = app.ui
        d = u.d
        rng = app.planes.c["radius_mi"]
        self._ring(u, R)
        self._ring(u, R * 2 // 3)
        self._ring(u, R // 3)
        u.rect(CX - R, CY, 2 * R, 1, "line")
        u.rect(CX, CY - R, 1, 2 * R, "line")
        u.text("N", CX, CY - R - 20, 22, "dim", "center")
        u.text("%d" % (rng // 3), CX + 4, CY - R // 3 - 15, 18, "line")
        u.text("%d MI" % rng, CX + 4, CY - R + 12, 18, "dim")
        u.pen("brass")
        d.circle(CX, CY, 4)                                # the unit
        order = [i for i in range(len(planes)) if i != pick]
        if planes:
            order.append(pick)                             # the shown plane last, on top
        for i in order:
            p = planes[i]
            r = min(1.0, p["mi"] / rng) * (R - 3)
            b = math.radians(p["brg"])
            x, y = int(CX + r * math.sin(b)), int(CY - r * math.cos(b))
            hot = i == pick
            if p["track"] is not None:
                t = math.radians(p["track"])
                n = 16 if hot else 12
                u.pen("amber" if hot else "dim")
                d.line(x, y, int(x + n * math.sin(t)), int(y - n * math.cos(t)), 2)
            u.pen("red" if hot else "cream")
            d.circle(x, y, 6 if hot else 4)

    def draw(self, app):
        self.frame(app)
        self.shown = self._stamp(app)
        if self.page == "iss":
            self._draw_iss(app)
            return
        u = app.ui
        pl = app.planes
        rng = pl.c["radius_mi"]
        if pl.list is None:
            u.text("LOOKING FOR PLANES", U.W // 2, 188, U.T_HEAD, "amber", "center")
            why = pl.last_error or ("WIFI " + app.wifi_state.upper())
            for i, line in enumerate(u.wrap(why, U.T_NOTE, U.W - 40)[:2]):
                u.text(line, U.W // 2, 240 + i * 24, U.T_NOTE, "dim", "center")
            self._swap_button(app)
            return
        old = pl.stale()
        planes = [] if old else pl.list
        pick = min(pl.pick, len(planes) - 1) if planes else -1
        self._scope(app, planes, pick)
        if planes:
            p = planes[pick]
            head = "NEAREST" if pick == 0 else "PLANE %d OF %d" % (pick + 1, len(planes))
            u.text(head, COL, 70, 22, "dim")
            room = U.W - COL - 12
            cut = room                             # only if it fits at no size: whole words
            for size in (44, 36, 30):              # the biggest that fits: "SOUTHWEST 4322"
                if u.text_w(p["name"], size) <= room:
                    cut = 0
                    break
            u.text(p["name"], COL, 94 + (44 - size) // 3, size, "amber", max_w=cut)
            u.text(p["type_name"], COL, 134, 22, "text", max_w=U.W - COL - 8)
            dist = ("%.1f" % p["mi"]) if p["mi"] < 100 else ("%d" % (p["mi"] + 0.5))
            x = u.text(dist, COL, 172, 72, "cream")
            u.text("MI " + compass8(p["brg"]), x + 8, 198, 30, "cream")
            u.text(commas(p["alt"]) + " FT", COL, 236, 30, "text")
            u.text(climb_word(p["fpm"]), U.W - 16, 240, 22, "dim", "right")
            if p["mph"] is not None:
                u.text("%d MPH" % round(p["mph"]), COL, 270, 30, "text")
            if p["track"] is not None:
                u.text("HEADING " + compass8(p["track"]), U.W - 16, 274, 22, "dim", "right")
        elif old:
            u.text("NO FRESH", COL, 120, 36, "amber")
            u.text("PLANE DATA", COL, 156, 36, "amber")
            if pl.last_error:
                for i, line in enumerate(u.wrap(pl.last_error, 20, U.W - COL - 12)[:3]):
                    u.text(line, COL, 204 + i * 22, 20, "dim")
        else:
            u.text("CLEAR SKY", COL, 120, 44, "amber")
            u.text("NO PLANES IN THE AIR", COL, 172, 22, "text")
            u.text("WITHIN %d MILES" % rng, COL, 196, 22, "text")
        u.rect(16, 360, U.W - 32, 2, "line")
        self._swap_button(app)
        right = SWAP[0] - 14                       # the strip's text stops short of the button
        if planes:
            n = len(planes)
            u.text("%d PLANE%s WITHIN %d MI" % (n, "" if n == 1 else "S", rng), 20, 372, 24, "text")
            if n > 1:
                u.text("TAP FOR NEXT", 20, 398, 20, "dim")
        if pl.updated is not None:
            t = timeutil.local(app.cfg["tz"], pl.updated)
            u.text("AS OF " + timeutil.hhmm(t) + (" - OLD" if old else ""), right, 398, 20,
                   "red" if old else "dim", "right")

    # ---------- the ISS page ----------
    def _iss_scope(self, app, p, track):
        """North up, the unit in the middle. The middle ring is the horizon: inside
        it the ISS is above the horizon from here. The outer ring is 1.5 times as far;
        beyond that the dot waits on the edge, on the right bearing."""
        u = app.ui
        d = u.d
        hz = p["horizon_mi"] if p else 1400
        far = hz * 1.5
        self._ring(u, R)
        self._ring(u, R * 2 // 3, "dim")
        self._ring(u, R // 3)
        u.rect(CX - R, CY, 2 * R, 1, "line")
        u.rect(CX, CY - R, 1, 2 * R, "line")
        u.text("N", CX, CY - R - 20, 22, "dim", "center")
        u.text("HORIZON", CX + 4, CY + R * 2 // 3 + 3, 18, "dim")      # below: the range label is on top
        u.text("%s MI" % commas(int(far / 100 + 0.5) * 100), CX + 4, CY - R + 12, 18, "line")
        u.pen("brass")
        d.circle(CX, CY, 4)
        h = app.listener.heard                         # where it was last heard, if
        if h and h.get("lat") is not None and time.time() - h["t"] < 3600:   # within the hour
            loc = app.cfg["location"]
            hm, hb = gc_miles(loc["lat"], loc["lon"], h["lat"], h["lon"])
            hr = min(1.0, hm / far) * (R - 3)
            hx, hy = int(CX + hr * math.sin(math.radians(hb))), int(CY - hr * math.cos(math.radians(hb)))
            u.pen("amber")
            d.circle(hx, hy, 6)
            u.pen("bg")
            d.circle(hx, hy, 4)
        if not p:
            return
        r = min(1.0, p["mi"] / far) * (R - 3)
        b = math.radians(p["brg"])
        x, y = int(CX + r * math.sin(b)), int(CY - r * math.cos(b))
        if track is not None:
            t = math.radians(track)
            u.pen("amber")
            d.line(x, y, int(x + 18 * math.sin(t)), int(y - 18 * math.cos(t)), 2)
        u.pen("red")
        d.circle(x, y, 7 if p["elev"] > 0 else 5)

    def _draw_iss(self, app):
        u = app.ui
        st = app.iss
        if st.now is None:
            u.text("FINDING THE ISS", U.W // 2, 188, U.T_HEAD, "amber", "center")
            why = st.last_error or ("WIFI " + app.wifi_state.upper())
            for i, line in enumerate(u.wrap(why, U.T_NOTE, U.W - 40)[:2]):
                u.text(line, U.W // 2, 240 + i * 24, U.T_NOTE, "dim", "center")
            u.rect(16, 360, U.W - 32, 2, "line")
            self._swap_button(app)
            return
        old = st.stale()
        p = None if old else st.now
        self._iss_scope(app, p, None if old else st.track)
        u.text("SPACE STATION", COL, 70, 22, "dim")
        if p:
            up = p["elev"] > 0
            e = round(p["elev"])
            word = "%d%s %s HORIZON" % (abs(e), U.DEG, "ABOVE" if up else "BELOW")
            room = U.W - COL - 12
            for size in (36, 30, 26, 22):
                if u.text_w(word, size) <= room:
                    break
            u.text(word, COL, 96 + (36 - size) // 3, size, "amber" if up else "text")
            u.text("OVER " + iss_lat_lon(p["lat"], p["lon"]), COL, 134, 22, "text")
            dist = commas(p["mi"]) if p["mi"] >= 1000 else "%d" % round(p["mi"])
            size = 72 if u.text_w(dist, 72) <= 150 else 56
            x = u.text(dist, COL, 172 + (72 - size) // 3, size, "cream")
            u.text("MI " + compass8(p["brg"]), x + 8, 198, 30, "cream")
            u.text("%d MI UP" % round(p["alt_mi"]), COL, 236, 30, "text")
            if p["sunlit"] is not None:
                u.text("IN SUNLIGHT" if p["sunlit"] else "IN SHADOW", U.W - 16, 240, 22,
                       "dim", "right")
            if p["mph"] is not None:
                u.text(commas(p["mph"]) + " MPH", COL, 270, 30, "text")
            if st.track is not None:
                u.text("HEADING " + compass8(st.track), U.W - 16, 274, 22, "dim", "right")
        else:
            u.text("NO FRESH", COL, 120, 36, "amber")
            u.text("ISS DATA", COL, 156, 36, "amber")
            if st.last_error:
                for i, line in enumerate(u.wrap(st.last_error, 20, U.W - COL - 12)[:3]):
                    u.text(line, COL, 204 + i * 22, 20, "dim")
        if old and st.updated is not None:
            t = timeutil.local(app.cfg["tz"], st.updated)
            u.text("AS OF " + timeutil.hhmm(t) + " - OLD", COL, 306, 20, "red")
        u.rect(16, 360, U.W - 32, 2, "line")
        self._swap_button(app)
        self._heard_strip(app)

    def _heard_strip(self, app):
        """The bottom strip says when the ISS was last heard over ham radio (stage 1,
        look OK'd by Jason 2026-10-14). app.listener.heard = None (never) or a dict:
        t (time.time()), kind "beacon" | "relay", by (the ground station that passed
        it on), src + text (a relayed packet), lat/lon (where the ISS was then)."""
        u = app.ui
        h = app.listener.heard
        room = SWAP[0] - 14 - 20
        if h is None:
            u.text("ISS NOT HEARD YET", 20, 370, 24, "text")
            u.text("ITS RADIO CAN BE QUIET FOR DAYS", 20, 398, 20, "dim", max_w=room)
            return
        age = time.time() - h["t"]
        fresh = age < 3600
        what = "ISS RELAYED" if h["kind"] == "relay" else "ISS LAST HEARD"
        u.text("%s %s" % (what, ago_text(age)), 20, 370, 24, "amber" if fresh else "text",
               max_w=room)
        if h["kind"] == "relay":
            line = "%s: %s" % (h["src"], h.get("text") or "POSITION")
        elif h.get("lat") is not None:
            line = "OVER %s - VIA %s" % (iss_lat_lon(h["lat"], h["lon"]), h["by"])
        else:
            line = "VIA " + h["by"]
        u.text(line.upper(), 20, 398, 20, "dim", max_w=room)


def ago_text(s):
    """Seconds -> 'JUST NOW', '14 MIN AGO', '3 HRS AGO', '2 DAYS AGO'."""
    if s < 90:
        return "JUST NOW"
    if s < 3600:
        return "%d MIN AGO" % (s // 60)
    if s < 48 * 3600:
        h = int(s // 3600)
        return "%d HR%s AGO" % (h, "" if h == 1 else "S")
    return "%d DAYS AGO" % (s // 86400)


def iss_lat_lon(lat, lon):
    """'12N 45W' - whole degrees."""
    return "%d%s %d%s" % (abs(round(lat)), "N" if lat >= 0 else "S",
                          abs(round(lon)), "E" if lon >= 0 else "W")
