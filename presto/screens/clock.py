# screens/clock.py - roadmap 5.3: the Clock, the screen the unit rests on.
#
# Look agreed 2026-10-07 (renders\clock_mockup_2026-10-07.png, face B
# "Railroad 24", full screen): a 12-hour roman dial (IIII, not IV, as clock
# dials have it) with a red 13-24 ring inside it, the way 24-hour railway
# watches were marked; the maker's name and town on the dial; the 24-hour time
# and the date in a window; brass / cream / red to match the two gauges.
#
# No header or footer are drawn, but the bottom strip still works by touch
# (left = previous, middle = menu, right = next) and so does the knob.
#
# The dial, numerals and hands are plain PicoGraphics shapes (circle, polygon,
# line) - the roman numerals are built from strokes. The lettering (13-24
# ring, maker's name, town, time and date) is smooth text from ui.py
# (roadmap 5.15b); the shapes were left as they are (Jason, 2026-10-07).
#
# Seconds hand: config "clock" -> "seconds". Each second the dial is redrawn
# inside a clip box around the old and new hand, and only that box is sent to
# the screen. Diagnostics shows how long that takes ("CLOCK sec"); if the
# Presto can't keep up, set "seconds" to false and the face only changes once
# a minute.

import math
import time
import timeutil
import ui as U
from screens.base import Screen

CX = CY = 240
R_RIM = 232               # brass rim, outer edge
R_FACE = 224              # dial face
R_TRACK_O = 216           # minute track, outer line
R_TRACK_I = 204           # minute track, inner line
R_NUM = 174               # middle of the roman numerals
NUM_H = 40                # numeral height
R_24 = 126                # middle of the red 13-24 ring
R_HOUR = 104              # hand lengths
R_MIN = 170
R_SEC = 186
SEC_TAIL = 40
WINDOW_Y = 292            # middle of the time window
WINDOW_W, WINDOW_H = 112, 40
MAKER_Y = 170

ROMAN = ("XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI")
GLYPH_W = {"I": 7, "V": 22, "X": 22}
GLYPH_GAP = 4
THICK = 6.0               # heavy stroke of a numeral
THIN = 2.4                # light stroke and the bars across top and bottom
UNSET = ("unset",)        # what "shown" holds while the clock has no time yet
TAPS = 5                  # taps on the maker's name that start the hidden screen (fitz.py)
TAP_WINDOW_MS = 4000      # ...all within this long


def _pt(r, across, deg):
    """Screen point: r out from the centre along the direction deg (clockwise
    from 12 o'clock), then `across` sideways (clockwise)."""
    a = math.radians(deg)
    s, c = math.sin(a), math.cos(a)
    return (int(round(CX + r * s + across * c)), int(round(CY - r * c + across * s)))


def _quad(deg, x0, r0, x1, r1, w):
    """A stroke from (x0 across, r0 out) to (x1, r1), w wide (measured across)."""
    h = w / 2
    return [_pt(r0, x0 - h, deg), _pt(r0, x0 + h, deg), _pt(r1, x1 + h, deg),
            _pt(r1, x1 - h, deg)]


def _numeral(s, deg):
    """Polygons for one roman numeral, standing with its top toward the rim."""
    width = sum(GLYPH_W[ch] for ch in s) + GLYPH_GAP * (len(s) - 1)
    top, bot = R_NUM + NUM_H / 2, R_NUM - NUM_H / 2
    polys = []
    x = -width / 2
    for ch in s:
        w = GLYPH_W[ch]
        if ch == "I":
            polys.append(_quad(deg, x + w / 2, top, x + w / 2, bot, THICK))
        elif ch == "V":
            polys.append(_quad(deg, x + THICK / 2, top, x + w / 2, bot, THICK))
            polys.append(_quad(deg, x + w - THIN / 2, top, x + w / 2, bot, THIN))
        else:                                   # X
            polys.append(_quad(deg, x + THICK / 2, top, x + w - THICK / 2, bot, THICK))
            polys.append(_quad(deg, x + w - THIN / 2, top, x + THIN / 2, bot, THIN))
        x += w + GLYPH_GAP
    # the bars across the top and bottom that tie a clock numeral together
    e = width / 2 + 2
    polys.append([_pt(top, -e, deg), _pt(top, e, deg), _pt(top - THIN, e, deg),
                  _pt(top - THIN, -e, deg)])
    polys.append([_pt(bot + THIN, -e, deg), _pt(bot + THIN, e, deg), _pt(bot, e, deg),
                  _pt(bot, -e, deg)])
    return polys


def _blade(deg, length, tail, w):
    """A hand: w wide at the centre, tapering to a point."""
    h = w / 2
    return [_pt(-tail, -h, deg), _pt(-tail, h, deg), _pt(length * 0.6, h, deg),
            _pt(length, 0, deg), _pt(length * 0.6, -h, deg)]


def _box(points, pad):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0 = max(0, min(xs) - pad), max(0, min(ys) - pad)
    x1, y1 = min(U.W, max(xs) + pad + 1), min(U.H, max(ys) + pad + 1)
    return (x0, y0, x1 - x0, y1 - y0)


def _join(a, b):
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1 = max(a[0] + a[2], b[0] + b[2])
    y1 = max(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0)


class Clock(Screen):
    key = "clock"
    title = "CLOCK"
    short = "CLOCK"

    def __init__(self):
        self.dial = None          # polygons that never change, built once
        self.shown = None         # (hour, minute, second or None) on screen now
        self.sec_box = None       # box round the seconds hand on screen now
        self.sec_ms = 0           # how long the last seconds-hand redraw took
        self.sec_max_ms = 0
        self.taps = []            # times of recent taps on the maker's name

    def enter(self, app):
        self.shown = None

    def on_touch(self, app, x, y):
        """Five quick taps on the maker's name open the hidden screen."""
        if not (CX - 100 <= x <= CX + 100 and MAKER_Y - 12 <= y <= MAKER_Y + 52):
            self.taps = []
            return False                  # elsewhere: the app checks the bottom strip
        now = time.ticks_ms()
        self.taps = [t for t in self.taps if time.ticks_diff(now, t) < TAP_WINDOW_MS]
        self.taps.append(now)
        if len(self.taps) >= TAPS:
            self.taps = []
            app.start_fitz()
        return True

    # ---------- geometry ----------
    def _build(self):
        polys = []
        for i in range(60):
            polys.append(_quad(i * 6, 0, R_TRACK_I, 0, R_TRACK_O, 5 if i % 5 == 0 else 1.6))
        for i, s in enumerate(ROMAN):
            polys.extend(_numeral(s, i * 30))
        self.dial = polys

    @staticmethod
    def _sec_points(sec):
        deg = sec * 6
        return (_pt(-SEC_TAIL, 0, deg), _pt(R_SEC, 0, deg), _pt(-SEC_TAIL * 0.7, 0, deg))

    def _now(self, app):
        return app.local() if timeutil.clock_set() else None

    # ---------- drawing ----------
    def _paint(self, app, t, sec):
        """Draw the whole face into the buffer (inside the current clip box)."""
        u = app.ui
        d = u.d
        u.clear()
        u.pen("brass")
        d.circle(CX, CY, R_RIM)
        u.pen("face")
        d.circle(CX, CY, R_FACE)
        for r, colour in ((R_TRACK_O, "cream"), (R_TRACK_O - 2, "face"),
                          (R_TRACK_I, "cream"), (R_TRACK_I - 2, "face")):
            u.pen(colour)
            d.circle(CX, CY, r)
        u.pen("cream")
        for p in self.dial:
            d.polygon(p)
        for i in range(12):                      # the red 13-24 ring
            x, y = _pt(R_24, 0, i * 30)
            u.text(str(i + 12 if i else 24), x, y - 8, 24, "red", "center")
        c = app.cfg["clock"]
        u.text(c["maker"], CX, MAKER_Y, 36, "cream", "center")
        u.text(app.cfg["location"]["name"], CX, MAKER_Y + 32, 24, "brass", "center")
        # time window + date
        x0, y0 = CX - WINDOW_W // 2, WINDOW_Y - WINDOW_H // 2
        u.rect(x0 - 2, y0 - 2, WINDOW_W + 4, WINDOW_H + 4, "brass")
        u.rect(x0, y0, WINDOW_W, WINDOW_H, "bg")
        if t is None:
            u.text("--:--", CX, WINDOW_Y - 12, 36, "amber", "center")
            u.text("CLOCK NOT SET", CX, WINDOW_Y + 28, 24, "brass", "center")
        else:
            u.text(timeutil.hhmm(t), CX, WINDOW_Y - 12, 36, "amber", "center")
            u.text(timeutil.date_line(t), CX, WINDOW_Y + 28, 24, "brass", "center")
            # hands: hour and minute move once a minute
            u.pen("cream")
            hdeg = (t[3] % 12) * 30 + t[4] / 2
            d.polygon(_blade(hdeg, R_HOUR, 14, 14))
            d.polygon(_blade(t[4] * 6, R_MIN, 18, 9))
            if sec is not None:
                tail, tip, weight = self._sec_points(sec)
                u.pen("red")
                d.line(tail[0], tail[1], tip[0], tip[1], 3)
                d.circle(weight[0], weight[1], 5)
        u.pen("brass")
        d.circle(CX, CY, 9)
        u.pen("bg")
        d.circle(CX, CY, 3)

    def draw(self, app):
        if self.dial is None:
            self._build()
        t = self._now(app)
        sec = t[5] if (t is not None and app.cfg["clock"]["seconds"]) else None
        self._paint(app, t, sec)
        self.shown = UNSET if t is None else (t[3], t[4], sec)
        self.sec_box = None if sec is None else _box(self._sec_points(sec), 7)

    def tick(self, app, now):
        t = self._now(app)
        if t is None:                             # clock not set (yet)
            return None if self.shown == UNSET else "full"
        want_sec = t[5] if app.cfg["clock"]["seconds"] else None
        if self.shown is None or self.shown == UNSET or (t[3], t[4]) != self.shown[:2] \
                or (want_sec is None) != (self.shown[2] is None):
            return "full"                         # new minute: hands, window, date
        if want_sec is None or want_sec == self.shown[2]:
            return None
        # new second: redraw only the box round the old and the new hand
        t0 = time.ticks_ms()
        new_box = _box(self._sec_points(want_sec), 7)
        box = _join(self.sec_box, new_box) if self.sec_box else new_box
        app.ui.clip(box)                          # shapes and text both stay inside it
        self._paint(app, t, want_sec)
        app.ui.unclip()
        self.shown = (t[3], t[4], want_sec)
        self.sec_box = new_box
        self.sec_ms = time.ticks_diff(time.ticks_ms(), t0)
        if self.sec_ms > self.sec_max_ms:
            self.sec_max_ms = self.sec_ms
        return box
