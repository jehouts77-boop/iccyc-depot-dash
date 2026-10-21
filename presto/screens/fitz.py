# screens/fitz.py - roadmap 5.10a: the Edmund Fitzgerald remembrance.
#
# Hidden: it is not in the screen ring or the Home menu. It starts when
#   - someone taps the maker's name on the Clock face five times (one tap per
#     letter of ICCYC), or
#   - by itself every 10 November at 18:10 local time, from 2027 on
#     (config "fitz"; 6:10 p.m. Central is 7:10 p.m. Eastern, the time of the
#     ship's last radio message).
#
# What it shows (look and words agreed 2026-10-07, renders\fitz_mockup_2026-10-07.png):
# a line drawing of a Great Lakes freighter, then the title, the history one
# card at a time, the crew - one name and one toll of the bell for each of the
# 29 - and two closing lines. Then back to the Clock.
#
# The bell is silent if the CHIME switch is off or WIFE MODE is on; the screen
# runs all the same and the dots still fill in. Quiet hours don't apply.
# Any press, turn or touch ends it.

import time
import ui as U
import fitz_data as FD
from screens.base import Screen

SHIP_X, SHIP_BASE, SHIP_W = 20, 118, 440
STRETCH = 1.9             # height exaggeration, so a 729 ft hull shows its houses
TEXT_TOP, TEXT_BOTTOM = 166, 426
TALLY_Y = 448
F = "D"                   # this screen's typeface: Special Elite (typewriter)


def draw_ship(u, x0=SHIP_X, base=SHIP_BASE, width=SHIP_W):
    """A laker in profile, bow to the right. Units below are feet along the
    hull and feet above the water; not a scale plan of the real ship."""
    d = u.d
    k = width / 729.0

    def pt(x, y):
        return (int(round(x0 + x * k)), int(round(base - y * k * STRETCH)))

    def path(pts, colour="brass"):
        u.pen(colour)
        for i in range(len(pts) - 1):
            a, b = pt(*pts[i]), pt(*pts[i + 1])
            d.line(a[0], a[1], b[0], b[1], 2)

    # hull: stern, bottom at the water, raked stem; then the deck line
    path(((0, 24), (0, 9), (8, 0), (720, 0), (729, 26)))
    path(((0, 24), (108, 24), (108, 15), (655, 15), (655, 26), (729, 26)))
    # after house, boat deck, stack with its band, mainmast, lifeboat
    path(((14, 24), (14, 35), (96, 35), (96, 24)))
    path(((20, 35), (20, 43), (74, 43), (74, 35)))
    path(((42, 43), (40, 66), (60, 66), (62, 43)))
    path(((41, 58), (61, 58)), "cream")
    path(((86, 35), (86, 74)))
    path(((80, 66), (92, 66)))
    path(((24, 46), (36, 46)), "cream")
    # forward house: texas deck, pilothouse and its windows, foremast
    path(((666, 26), (666, 37), (714, 37), (714, 26)))
    path(((676, 37), (676, 48), (708, 48), (708, 37)))
    path(((672, 49), (712, 49)))
    path(((690, 49), (690, 82)))
    path(((683, 72), (697, 72)))
    path(((680, 43), (704, 43)), "cream")
    # 21 hatches along the spar deck
    for i in range(21):
        x = 128 + i * 24.6
        path(((x, 18), (x + 12, 18)), "cream")
    # the lake
    u.pen("dim")
    for i in range(12):
        x = x0 - 14 + i * 40 + (i % 2) * 10
        y = base + 8 + (i % 3) * 5
        d.line(x, y, x + 22, y, 2)


class Fitz(Screen):
    key = "fitz"
    title = "EDMUND FITZGERALD"
    short = "FITZ"
    hold = True               # the app's "idle -> back to the Clock" leaves this screen alone

    def __init__(self):
        self.steps = []       # (kind, index, milliseconds)
        self.i = 0
        self.step_at = 0
        self.started = False
        self.tolled = 0       # how many names have been shown
        self.bells = 0        # how many tolls were actually sounded
        self.runs = 0

    def enter(self, app):
        c = app.cfg["fitz"]
        steps = [("title", 0, c["title_ms"])]
        for n, text in enumerate(FD.CARDS):
            steps.append(("card", n, max(c["card_min_ms"], len(text) * c["card_ms_per_char"])))
        for n in range(len(FD.CREW)):
            steps.append(("crew", n, c["toll_ms"]))
        for n in range(len(FD.CLOSING)):
            steps.append(("close", n, c["close_ms"]))
        self.steps = steps
        self.i = 0
        self.started = False
        self.tolled = self.bells = 0
        self.runs += 1

    # ---------- the sequence ----------
    def _begin_step(self, app, now):
        self.step_at = now
        kind, n, _ = self.steps[self.i]
        if kind == "crew":
            self.tolled = n + 1
            if app.chime_on and not app.wife_mode:
                c = app.cfg["fitz"]
                clip = app.cfg["chime_sounds"].get(c["bell"], 0)
                steps = app.cfg["volume_steps"]
                vol = steps[max(0, min(app.cfg["chime"]["volume_step"], len(steps) - 1))]
                app.controls.play(clip, vol)
                self.bells += 1

    def tick(self, app, now):
        if not self.started:                  # first tick after the first draw
            self.started = True
            self._begin_step(app, now)
            return None
        if time.ticks_diff(now, self.step_at) < self.steps[self.i][2]:
            return None
        if self.i + 1 >= len(self.steps):
            app.end_fitz()
            return None
        self.i += 1
        self._begin_step(app, now)
        return "full"

    # ---------- drawing ----------
    def _tally(self, u):
        for i in range(len(FD.CREW)):
            u.pen("cream" if i < self.tolled else "line")
            u.d.circle(U.W // 2 + (i - 14) * 15, TALLY_Y, 4)

    def _block(self, u, text, colour):
        u.block(text, U.W // 2, TEXT_TOP, TEXT_BOTTOM, (28, 24, 21), colour, F)

    def draw(self, app):
        u = app.ui
        u.clear()
        draw_ship(u)
        u.rect(40, 150, U.W - 80, 2, "line")
        kind, n, _ = self.steps[self.i] if self.steps else ("title", 0, 0)
        cx = U.W // 2
        if kind == "title":
            u.text(FD.TITLE[0], cx, 246, 34, "amber", "center", F)
            u.text(FD.TITLE[1], cx, 296, 34, "cream", "center", F)
        elif kind == "card":
            self._block(u, FD.CARDS[n], "cream")
        elif kind == "crew":
            name, rank, home, age = FD.CREW[n]
            u.text(name.upper(), cx, 218, 34, "amber", "center", F)
            u.text(rank.upper(), cx, 264, 22, "cream", "center", F)
            u.text(("%s  -  AGE %d" % (home, age)).upper(), cx, 294, 20, "dim", "center", F)
        else:
            self._block(u, FD.CLOSING[n], "amber")
        self._tally(u)

    # ---------- any input ends it ----------
    def on_knob(self, app, n):
        app.end_fitz()
        return True

    def on_press(self, app):
        app.end_fitz()
        return True

    def on_touch(self, app, x, y):
        app.end_fitz()
        return True


def due(cfg, t, last_year):
    """True in the minute the remembrance runs by itself. t = local time."""
    c = cfg["fitz"]
    if not c["auto"] or t[0] < c["auto_from_year"] or t[0] == last_year:
        return False
    return (t[1], t[2]) == (c["month"], c["day"]) and "%02d:%02d" % (t[3], t[4]) == c["time"]
