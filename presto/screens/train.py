# screens/train.py - roadmap 5.6: Nearest Train. Data: trains.py (Amtraker).
#
# When a train is moving on the line: how far away it is and which way, its
# speed, a strip of its stops with a marker where the train is, the next stop,
# and when it passes (or passed) the watch station (config "train" -> "watch",
# Washington, MO). When nothing is moving: the next train due there.
# Gauges on this screen (config "gauges" -> "train"): train speed + a compass
# pointing at the train with the distance underneath.

import time
import timeutil
import ui as U
from trains import compass8
from screens.base import Screen

STRIP_Y = 268
STRIP_X0, STRIP_X1 = 44, 436
STRIP_STOPS = 7               # stops shown at once


class NearestTrain(Screen):
    key = "train"
    title = "NEAREST TRAIN"
    short = "TRAIN"

    def __init__(self):
        self.shown = None

    def enter(self, app):
        self.shown = None
        app.trains.wake()

    def _stamp(self, app):
        t = app.trains
        return (t.rounds, t.fails, app.local()[4])

    def tick(self, app, now):
        return "full" if self._stamp(app) != self.shown else None

    def _hm(self, app, utc):
        return "--:--" if utc is None else timeutil.hhmm(timeutil.local(app.cfg["tz"], utc))

    def draw(self, app):
        self.frame(app)
        self.shown = self._stamp(app)
        u = app.ui
        tr = app.trains
        now = time.time()
        if tr.ids is None:
            u.text("LOOKING FOR TRAINS", U.W // 2, 188, U.T_HEAD, "amber", "center")
            why = tr.last_error or ("WIFI " + app.wifi_state.upper())
            for i, line in enumerate(u.wrap(why, U.T_NOTE, U.W - 40)[:2]):
                u.text(line, U.W // 2, 240 + i * 24, U.T_NOTE, "dim", "center")
            return
        near = tr.nearest(now)
        coming = tr.upcoming(now)
        if near is not None:
            self._moving(app, near, coming, now)
        elif coming:
            self._waiting(app, coming, now)
        else:
            u.text("NO TRAINS DUE", U.W // 2, 188, U.T_HEAD, "amber", "center")
            u.text("NOTHING ON TODAY'S BOARD AT %s" % tr.c["watch"], U.W // 2, 240, U.T_NOTE,
                   "dim", "center")
        if tr.updated is not None:
            old = now - tr.updated > 3 * tr.c["far_every_s"]
            u.text("AS OF " + self._hm(app, tr.updated) + ("  - OLD" if old else ""),
                   U.W - 20, 400, U.T_NOTE, "red" if old else "dim", "right")

    # ---------- a train is moving ----------
    def _moving(self, app, near, coming, now):
        u = app.ui
        rec, mi, brg = near
        u.text(rec["route"], 20, 70, 34, "amber", max_w=U.W - 40)
        u.text("TRAIN %s   %s TO %s" % (rec["num"], rec["orig"], rec["dest"]), 20, 102, 24,
               "text")
        dist = ("%.1f" % mi) if mi < 100 else ("%d" % (mi + 0.5))
        x = u.text(dist, 18, 134, 100, "amber")
        u.text("MI", x + 8, 176, 36, "amber")       # sits on the big number's baseline
        u.text("TO THE " + compass8(brg), U.W - 20, 134, 24, "cream", "right")
        u.text("%d MPH" % round(rec["mph"] or 0), U.W - 20, 158, 36, "cream", "right")
        if rec["heading"]:
            u.text("HEADING " + rec["heading"], U.W - 20, 190, U.T_NOTE, "dim", "right")
        u.rect(16, 216, U.W - 32, 2, "line")
        self._strip(app, rec, now)
        k = app.trains.next_stop(rec)
        y = 330
        if k is not None:
            st = rec["stops"][k]
            line = "NEXT STOP  %s  %s" % (st["name"][:20], self._hm(app, st["arr"]))
            u.text(line, 20, y, 24, "cream")
            if st["arr"] is not None and st["sch"] is not None:
                late = int((st["arr"] - st["sch"]) / 60)
                if late >= 2:
                    u.text("%d MIN LATE" % late, U.W - 20, y, 24, "red", "right")
                elif late <= -2:
                    u.text("%d MIN EARLY" % -late, U.W - 20, y, 24, "green", "right")
                else:
                    u.text("ON TIME", U.W - 20, y, 24, "dim", "right")
        watch = app.trains.c["watch"]
        for st in rec["stops"]:
            if st["code"] == watch:
                word = "LEFT" if st["gone"] else "DUE"
                when = st["dep"] if st["gone"] else st["arr"]
                u.text("%s  %s %s" % (st["name"][:20], word, self._hm(app, when)), 20, y + 26,
                       24, "text")
                break
        others = [p for p in coming if p[1] is not rec]
        if others:
            when, r2 = others[0]
            u.text("THEN  TRAIN %s  %s" % (r2["num"], self._hm(app, when)), 20, 400, U.T_NOTE,
                   "dim")

    def _strip(self, app, rec, now):
        """A line of stops with the train on it, like a dispatcher's board."""
        u = app.ui
        d = u.d
        stops = rec["stops"]
        k = app.trains.next_stop(rec)
        if not stops:
            return
        kk = len(stops) - 1 if k is None else k
        first = max(0, min(kk - 2, len(stops) - STRIP_STOPS))
        show = stops[first:first + STRIP_STOPS]
        n = len(show)
        gap = (STRIP_X1 - STRIP_X0) / max(1, n - 1)
        u.rect(STRIP_X0, STRIP_Y - 1, STRIP_X1 - STRIP_X0, 3, "dim")
        for i, st in enumerate(show):
            x = int(STRIP_X0 + i * gap)
            u.pen("dim" if st["gone"] else "cream")
            d.circle(x, STRIP_Y, 6)
            if not st["gone"]:
                u.pen("bg")
                d.circle(x, STRIP_Y, 3)
            u.text(st["code"], x, STRIP_Y + 14, 24, "dim" if st["gone"] else "cream", "center")
        # the train: between the stop it left and the stop it is heading for
        if k is None:
            pos = n - 1
        elif k == 0:
            pos = 0
        else:
            a, b = stops[k - 1], stops[k]
            f = 0.5
            if a["dep"] is not None and b["arr"] is not None and b["arr"] > a["dep"]:
                f = max(0.05, min(0.95, (now - a["dep"]) / (b["arr"] - a["dep"])))
            pos = (k - 1 - first) + f
        x = int(STRIP_X0 + pos * gap)
        u.pen("red")
        d.polygon([(x, STRIP_Y - 8), (x - 9, STRIP_Y - 26), (x + 9, STRIP_Y - 26)])

    # ---------- nothing moving: the next one due ----------
    def _waiting(self, app, coming, now):
        u = app.ui
        when, rec = coming[0]
        watch = app.trains.c["watch"]
        name = watch
        for st in rec["stops"]:
            if st["code"] == watch:
                name = st["name"]
        u.text("NEXT TRAIN AT " + name[:20], 20, 72, 24, "dim")
        u.text(self._hm(app, when), 18, 102, 104, "amber")
        mins = int((when - now) / 60)
        if mins >= 0:
            u.text("IN %d H %02d M" % (mins // 60, mins % 60) if mins >= 60 else "IN %d M" % mins,
                   U.W - 20, 128, 28, "cream", "right")
        u.rect(16, 190, U.W - 32, 2, "line")
        u.text(rec["route"], 20, 206, 34, "amber", max_w=U.W - 40)
        u.text("TRAIN %s   %s TO %s" % (rec["num"], rec["orig"], rec["dest"]), 20, 238, 24,
               "text")
        state = "NOT YET DEPARTED" if rec["state"] == "Predeparture" else \
            ("NO RECENT POSITION" if rec["state"] == "Active" else rec["state"].upper()[:24])
        u.text(state, 20, 264, U.T_NOTE, "dim")
        y = 300
        for when2, r2 in coming[1:4]:
            u.text("THEN  TRAIN %s  %s" % (r2["num"], self._hm(app, when2)), 20, y, U.T_NOTE,
                   "dim")
            y += 26
