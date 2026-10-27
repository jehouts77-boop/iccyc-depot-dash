# screens/lantern.py - roadmap 5.5: Lantern Time - when to light the lantern.
#
# Look agreed 2026-10-07 (renders\lantern_mockup_2026-10-07.png, layout B): a
# 24-hour ring with noon at the top and midnight at the bottom - bright for
# daylight, dim for twilight, dark for night - and a red pointer at "now".
# In the middle, what's next: from sunrise on, DARK BY (the end of civil
# twilight - the moment to light the lantern, Jason's call) with a countdown;
# once it's dark, SUNRISE with a countdown and the moon in its phase.
#
# Nothing here comes from the internet: almanac.py / sun.py work it out from
# the date and config "location". The screen redraws once a minute.
# Gauges on this screen (config "gauges" -> "lantern"): daylight left + the
# sun's direction.

import math
import timeutil
import sun
import ui as U
from almanac import hm, span
from screens.base import Screen

CX, CY = 240, 212
R_OUT, R_IN = 128, 104
STEP_DEG = 4              # the ring is drawn in slices this wide
FOOT_Y = 374


def _pt(r, deg):
    a = math.radians(deg)
    return (int(round(CX + r * math.sin(a))), int(round(CY - r * math.cos(a))))


def _ang(minutes):
    """Minutes after local midnight -> degrees round the ring (noon = 0 = top)."""
    return (minutes - 720) / 4.0


def draw_moon(u, cx, cy, r, age):
    """The moon's disc with its lit part, as seen from the northern hemisphere
    (lit on the right while it grows, on the left while it shrinks)."""
    d = u.d
    u.pen("panel")
    d.circle(cx, cy, r)
    k = math.cos(2 * math.pi * age / sun.SYNODIC)        # +1 new ... -1 full
    side = 1 if age < sun.SYNODIC / 2 else -1
    pts = []
    n = 14
    for i in range(n + 1):                               # the lit edge, top to bottom
        a = math.pi * i / n
        pts.append((int(round(cx + side * r * math.sin(a))), int(round(cy - r * math.cos(a)))))
    for i in range(n, -1, -1):                           # the shadow line, back up
        a = math.pi * i / n
        pts.append((int(round(cx + side * r * math.sin(a) * k)),
                    int(round(cy - r * math.cos(a)))))
    u.pen("cream")
    d.polygon(pts)


class LanternTime(Screen):
    key = "lantern"
    title = "LANTERN TIME"
    short = "LANTERN"

    def __init__(self):
        self.shown = None

    def enter(self, app):
        self.shown = None

    def tick(self, app, now):
        return "full" if self._stamp(app) != self.shown else None

    @staticmethod
    def _stamp(app):
        return (timeutil.clock_set(), app.local()[4])

    def _band(self, u, m0, m1, colour):
        """Fill the ring between two times of day."""
        a0, a1 = _ang(m0), _ang(m1)
        if a1 <= a0:
            return
        u.pen(colour)
        n = max(1, int((a1 - a0) / STEP_DEG + 0.5))
        for i in range(n):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            if i < n - 1:
                b1 += 0.6                                # overlap, so no hairline gaps
            u.d.polygon([_pt(R_IN, b0), _pt(R_OUT, b0), _pt(R_OUT, b1), _pt(R_IN, b1)])

    def draw(self, app):
        self.frame(app)
        self.shown = self._stamp(app)
        u = app.ui
        d = u.d
        al = app.almanac
        if not timeutil.clock_set() or al.day is None:
            u.text("WAITING FOR THE CLOCK", U.W // 2, 200, U.T_HEAD, "amber", "center")
            return
        t = al.t
        # the ring: night, then twilight, then daylight on top
        self._band(u, 0, 1440, "panel")
        if t["rise"] is not None and t["set"] is not None:
            if t["dawn"] is not None and t["dusk"] is not None:
                self._band(u, t["dawn"], t["dusk"], "dim")
            self._band(u, t["rise"], t["set"], "amber")
        elif al.el is not None and al.el > 0:
            self._band(u, 0, 1440, "amber")              # midnight sun
        u.pen("bg")
        for h in range(24):                              # hour marks cut into the ring
            a = _ang(h * 60)
            p0, p1 = _pt(R_IN, a), _pt(R_OUT, a)
            d.line(p0[0], p0[1], p1[0], p1[1], 2 if h % 6 else 4)
        for a, lab in ((0, "12"), (90, "18"), (180, "24"), (270, "06")):
            x, y = _pt(R_OUT + 16, a)
            u.text(lab, x, y - 8, 24, "dim", "center")
        a = _ang(al.now_min)                             # "now"
        u.pen("red")
        d.polygon([_pt(R_IN - 16, a), _pt(R_OUT + 4, a - 3), _pt(R_OUT + 4, a + 3)])
        # the middle: what's next
        name, when, mins = al.next_event()
        u.text(name, CX, CY - 62, 24, "dim", "center")
        u.text(hm(when), CX, CY - 38, 62, "amber", "center")
        if mins is not None:
            u.text("IN " + span(mins), CX, CY + 14, 26, "cream", "center")
        if name == "DARK BY":
            u.text("LIGHT THE", CX, CY + 42, U.T_NOTE, "dim", "center")
            u.text("LANTERN", CX, CY + 62, U.T_NOTE, "dim", "center")
        else:
            draw_moon(u, CX, CY + 62, 16, al.moon[0])
        # corners and the two lines underneath
        u.text("RISE", 16, 70, U.T_NOTE, "dim")
        u.text(hm(t["rise"]), 16, 90, 34, "text")
        u.text("SET", U.W - 16, 70, U.T_NOTE, "dim", "right")
        u.text(hm(t["set"]), U.W - 16, 90, 34, "text", "right")
        if al.length is not None:
            s = "DAYLIGHT " + span(al.length)
            if al.change_s:              # vs yesterday (2026-10-26: was "-2 M 20 S", unclear)
                c = abs(al.change_s)
                d = ("%d M %02d S" % (c // 60, c % 60)) if c >= 60 else ("%d S" % c)
                s += ", %s %s" % (d, "LONGER" if al.change_s > 0 else "SHORTER")
            u.text(s, 20, FOOT_Y, 24, "text")
        u.text("FIRST LIGHT " + hm(t["dawn"]), 20, FOOT_Y + 24, 24, "dim")
        u.text("%s %d%%" % (al.moon[2], int(al.moon[1] * 100 + 0.5)), U.W - 20, FOOT_Y + 24,
               24, "dim", "right")
