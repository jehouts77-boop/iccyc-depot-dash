# screens/setpages.py - the pages behind the Settings menu: CHIME, BRIGHTNESS
# and GAUGES (the on-screen settings decided 2026-09-30; look agreed
# 2026-10-07, renders\settings_mockup_2026-10-07.png).
#
# On a page: tap a row (or a box on GAUGES) to pick it, then tap - / + or
# turn the knob to change it. A knob press lets go of the row; another press,
# or < SETTINGS, goes back. Changes take effect at once and are written to
# /config.json a moment after the last change (and on leaving the page).
#
# These pages are not in the screen ring. Their gauges are the Settings pair,
# except on GAUGES while a box is picked: then the two real gauges show that
# row's pair, so the choice can be seen on the gauge itself.

import time
import config
import timeutil
import gaugekinds as GK
import ui as U
from screens.base import Screen
from screens.wifi import button, inside

ROW_Y, ROW_PITCH, ROW_H = 66, 52, 46
VAL_X = 190
SAVE_AFTER_MS = 1500
B_BACK = (12, 414, 150, 54)
B_EXTRA = (318, 414, 150, 54)

WHEN = (("off", "OFF"), ("hourly", "EVERY HOUR"), ("hourly_count", "HOUR + STRIKES"),
        ("half_hourly", "HOUR + HALF HOUR"))


def _step_time(hhmm, n):
    """'22:00' moved n half-hours, round the clock."""
    m = (timeutil.minutes(hhmm) + 30 * n) % 1440
    return "%02d:%02d" % (m // 60, m % 60)


class Page(Screen):
    key = "settings"          # the gauges show the Settings pair
    hold = True               # the app's "idle -> back to the Clock" leaves these pages alone
    note = "TAP A ROW, THEN - / + OR TURN THE KNOB"
    extra = ""                # label of the button at the bottom right, if any

    def __init__(self):
        self.sel = None
        self.dirty = []           # rows to redraw
        self.changed_at = None    # ticks of the last change not yet saved
        self.saves = 0

    # --- what a page defines ---
    def rows(self, app):
        """[(name, kind, value)] - kind 'text' (value = str) or 'bar' (value = (n, of))."""
        return []

    def step(self, app, i, n):
        pass

    def on_extra(self, app):
        pass

    # --- shared behaviour ---
    def open(self, app):
        app.show(self)

    def enter(self, app):
        self.sel = None
        self.dirty = []

    def _save(self):
        if self.changed_at is not None:
            self.changed_at = None
            try:
                config.save()
                self.saves += 1
            except Exception as e:
                print("settings not saved:", e)

    def _back(self, app):
        self._save()
        app.go(app.ring_index)                # the Settings menu

    def _change(self, app, n):
        if self.sel is None or not n:
            return
        self.step(app, self.sel, n)
        self.changed_at = time.ticks_ms()
        self.dirty.append(self.sel)

    def _pick(self, i):
        if i != self.sel:
            if self.sel is not None:
                self.dirty.append(self.sel)
            self.sel = i
            if i is not None:
                self.dirty.append(i)

    def on_knob(self, app, n):
        self._change(app, n)
        return True

    def on_press(self, app):
        if self.sel is not None:
            self._pick(None)
        else:
            self._back(app)
        return True

    def on_touch(self, app, x, y):
        if inside(B_BACK, x, y):
            self._back(app)
        elif self.extra and inside(B_EXTRA, x, y):
            self.on_extra(app)
        else:
            i = (y - ROW_Y) // ROW_PITCH
            if y >= ROW_Y and 0 <= i < len(self.rows(app)):
                if i == self.sel and x >= U.W - 124:
                    self._change(app, -1 if x < U.W - 68 else 1)
                else:
                    self._pick(i)
        return True

    def tick(self, app, now):
        if self.changed_at is not None and time.ticks_diff(now, self.changed_at) >= SAVE_AFTER_MS:
            self._save()
        if not self.dirty:
            return None
        todo, self.dirty = self.dirty, []
        rows = self.rows(app)
        y0, y1 = U.H, 0
        for i in todo:
            if i is None or i >= len(rows):
                continue
            y = ROW_Y + i * ROW_PITCH
            app.ui.rect(0, y - 2, U.W, ROW_H + 4, "bg")
            self._row(app.ui, i, rows[i])
            y0, y1 = min(y0, y - 2), max(y1, y + ROW_H + 2)
        return (0, y0, U.W, y1 - y0) if y1 > y0 else None

    def _row(self, u, i, row):
        name, kind, val = row
        y = ROW_Y + i * ROW_PITCH
        on = i == self.sel
        if on:
            u.rect(8, y, U.W - 16, ROW_H, "panel")
            u.rect(8, y, 4, ROW_H, "amber")
        u.text(name, 24, y + 14, 28, "amber" if on else "text")
        if kind == "bar":
            n, of = val
            pitch = 24 if of <= 6 else 16
            for k in range(of):
                u.rect(VAL_X + k * pitch, y + 12, pitch - 4, 22,
                       ("amber" if on else "text") if k < n else "line")
        else:
            u.text(val, VAL_X, y + 14, 28, "cream" if on else "text", max_w=162 if on else 270)
        if on:
            button(u, (U.W - 122, y + 3, 52, 40), "-", "bg", "amber", 34)
            button(u, (U.W - 64, y + 3, 52, 40), "+", "bg", "amber", 34)

    def draw(self, app):
        u = app.ui
        u.clear()
        u.header(self.title, app.clock_text())
        rows = self.rows(app)
        for i in range(len(rows)):
            self._row(u, i, rows[i])
        u.text(self.note_for(app), U.W // 2, 386, 20, "dim", "center")
        button(u, B_BACK, "< SETTINGS", "dim", size=24)
        if self.extra:
            button(u, B_EXTRA, self.extra, "amber", size=24)
        self.dirty = []

    def note_for(self, app):
        return self.note


class ChimePage(Page):
    title = "CHIME"
    short = "CHIME"
    extra = "HEAR IT"

    def _sounds(self, app):
        return sorted(app.cfg["chime_sounds"], key=lambda k: app.cfg["chime_sounds"][k])

    def rows(self, app):
        c = app.cfg["chime"]
        when = c["mode"].upper()
        for k, label in WHEN:
            if k == c["mode"]:
                when = label
        return [("SOUND", "text", c["sound"]),
                ("VOLUME", "bar", (c["volume_step"], len(app.cfg["volume_steps"]) - 1)),
                ("WHEN", "text", when),
                ("QUIET FROM", "text", c["quiet_start"]),
                ("QUIET UNTIL", "text", c["quiet_end"])]

    def step(self, app, i, n):
        c = app.cfg["chime"]
        if i == 0:
            names = self._sounds(app)
            k = names.index(c["sound"]) if c["sound"] in names else 0
            c["sound"] = names[(k + n) % len(names)]
        elif i == 1:
            top = len(app.cfg["volume_steps"]) - 1
            c["volume_step"] = max(0, min(top, c["volume_step"] + n))
        elif i == 2:
            keys = [k for k, _ in WHEN]
            k = keys.index(c["mode"]) if c["mode"] in keys else 1
            c["mode"] = keys[(k + n) % len(keys)]
        elif i == 3:
            c["quiet_start"] = _step_time(c["quiet_start"], n)
        else:
            c["quiet_end"] = _step_time(c["quiet_end"], n)

    def on_extra(self, app):
        app.chime.test(app.cfg, app.controls)      # plays even if muted: it's a test

    def note_for(self, app):
        c = app.cfg["chime"]
        if c["quiet_start"] == c["quiet_end"]:
            return "QUIET FROM = UNTIL: NO QUIET HOURS"
        return self.note


# brightness: (name, config group, key, lowest step, config value at the top step)
LEVELS = (("DAY SCREEN", "bright_day", "screen", 1, 1.0), ("DAY GAUGES", "bright_day", "gauges", 1, 255),
          ("DAY LIGHTS", "bright_day", "leds", 0, 255), ("NIGHT SCREEN", "bright_night", "screen", 1, 1.0),
          ("NIGHT GAUGES", "bright_night", "gauges", 1, 255), ("NIGHT LIGHTS", "bright_night", "leds", 0, 255))


def _level(cfg, row):
    _, grp, key, low, top = row
    return max(low, min(10, int(cfg[grp][key] * 10 / top + 0.5)))


class BrightPage(Page):
    title = "BRIGHTNESS"
    short = "BRIGHT"

    def rows(self, app):
        return [(r[0], "bar", (_level(app.cfg, r), 10)) for r in LEVELS]

    def step(self, app, i, n):
        r = LEVELS[i]
        k = max(r[3], min(10, _level(app.cfg, r) + n))
        v = r[4] * k / 10
        app.cfg[r[1]][r[2]] = v if r[2] == "screen" else int(v + 0.5)
        app.apply_lighting()                       # seen at once, if that mode is on now

    def enter(self, app):
        Page.enter(self, app)
        self.switches = None

    def tick(self, app, now):
        sw = (app.night, app.wife_mode, app.dark)
        if sw != self.switches:                    # a switch was flipped: the note changes
            first = self.switches is None
            self.switches = sw
            if not first:
                return "full"
        return Page.tick(self, app, now)

    def note_for(self, app):
        if app.dark:
            return "THE BACKLIGHT SWITCH IS OFF: NOTHING SHOWS UNTIL IT IS ON"
        mode = "NIGHT" if (app.night or app.wife_mode) else "DAY"
        return "THE SWITCHES SAY %s: %s ROWS CHANGE AS YOU WATCH" % (mode, mode)


GAUGE_ROWS = (("CLOCK", "clock"), ("WEATHER", "weather"), ("LANTERN", "lantern"), ("THIS DAY", "onthisday"),
              ("TRAIN", "train"), ("OVERHEAD", "overhead"), ("SETTINGS", "settings"))
ALSO = {"clock": "home", "settings": "diag"}       # these follow the row named first
G_Y, G_PITCH = 88, 40
G_X = (184, 330)
B_MINUS, B_PLUS, B_RESET = (200, 414, 80, 54), (286, 414, 80, 54), (372, 414, 96, 54)
SURE_MS = 5000


class GaugesPage(Page):
    title = "GAUGES"
    short = "GAUGES"

    def __init__(self):
        Page.__init__(self)
        self.kinds = sorted(GK.KINDS, key=lambda k: GK.KINDS[k][7])     # by the name on the dial
        self.sure_at = None

    def enter(self, app):
        Page.enter(self, app)
        self.sure_at = None

    def gauge_pair(self, app):
        """While a box is picked the real gauges show that row's pair (app.sync_gauges)."""
        if self.sel is None:
            return None
        return app.cfg["gauges"][GAUGE_ROWS[self.sel[0]][1]]

    def _box(self, sel):
        return (G_X[sel[1]], G_Y + sel[0] * G_PITCH + 2, 140, 34)

    def step(self, app, sel, n):
        key = GAUGE_ROWS[sel[0]][1]
        pair = app.cfg["gauges"][key]
        k = self.kinds.index(pair[sel[1]]) if pair[sel[1]] in self.kinds else 0
        pair[sel[1]] = self.kinds[(k + n) % len(self.kinds)]
        if key in ALSO:
            app.cfg["gauges"][ALSO[key]] = list(pair)

    def on_touch(self, app, x, y):
        if inside(B_BACK, x, y):
            self._back(app)
        elif inside(B_MINUS, x, y):
            self._change(app, -1)
        elif inside(B_PLUS, x, y):
            self._change(app, 1)
        elif inside(B_RESET, x, y):
            if self.sure_at is None:
                self.sure_at = time.ticks_ms()
            else:
                self.sure_at = None
                for k, v in config.DEFAULTS["gauges"].items():
                    app.cfg["gauges"][k] = list(v)
                self.changed_at = time.ticks_ms()
                self._pick(None)
            app.redraw()
        else:
            hit = None
            for r in range(len(GAUGE_ROWS)):
                for j in (0, 1):
                    if inside(self._box((r, j)), x, y):
                        hit = (r, j)
            was = self.sel
            self._pick(hit)
            if (was is None) != (hit is None):
                app.redraw()                       # the - / + buttons light up or go out
        return True

    def tick(self, app, now):
        if self.sure_at is not None and time.ticks_diff(now, self.sure_at) > SURE_MS:
            self.sure_at = None
            return "full"
        if self.changed_at is not None and time.ticks_diff(now, self.changed_at) >= SAVE_AFTER_MS:
            self._save()
        if not self.dirty:
            return None
        todo, self.dirty = self.dirty, []
        x0, y0, x1, y1 = U.W, U.H, 0, 0
        for sel in todo:
            if sel is None:
                continue
            b = self._box(sel)
            self._draw_box(app, sel)
            x0, y0 = min(x0, b[0]), min(y0, b[1])
            x1, y1 = max(x1, b[0] + b[2]), max(y1, b[1] + b[3])
        return (x0, y0, x1 - x0, y1 - y0) if x1 > x0 else None

    def _draw_box(self, app, sel):
        u = app.ui
        x, y, w, h = self._box(sel)
        on = sel == self.sel
        kind = app.cfg["gauges"][GAUGE_ROWS[sel[0]][1]][sel[1]]
        label = GK.KINDS[kind][7] if kind in GK.KINDS else kind.upper()
        u.rect(x, y, w, h, "amber" if on else "line")
        u.rect(x + 2, y + 2, w - 4, h - 4, "panel")
        size = 22 if u.text_w(label, 22) <= w - 10 else 18
        u.text(label, x + w // 2, y + (h - int(size * 0.65)) // 2, size, "amber" if on else "text",
               "center")

    def draw(self, app):
        u = app.ui
        u.clear()
        u.header(self.title, app.clock_text())
        u.text("SCREEN", 24, 64, 20, "dim")
        u.text("GAUGE I", G_X[0] + 6, 64, 20, "dim")
        u.text("GAUGE II", G_X[1] + 6, 64, 20, "dim")
        for r in range(len(GAUGE_ROWS)):
            u.text(GAUGE_ROWS[r][0], 24, G_Y + r * G_PITCH + 11, 24, "text")
            self._draw_box(app, (r, 0))
            self._draw_box(app, (r, 1))
        u.text("TAP A BOX, THEN TURN THE KNOB: THE REAL GAUGE SHOWS IT", U.W // 2, 378, 20, "dim",
               "center")
        button(u, B_BACK, "< SETTINGS", "dim", size=24)
        live = self.sel is not None
        button(u, B_MINUS, "-", "bg" if live else "dim", "amber" if live else "panel", 34)
        button(u, B_PLUS, "+", "bg" if live else "dim", "amber" if live else "panel", 34)
        if self.sure_at is None:
            button(u, B_RESET, "RESET", "dim", size=24)
        else:
            button(u, B_RESET, "SURE?", "bg", "red", 24)
        self.dirty = []

    def on_press(self, app):
        if self.sel is not None:
            self._pick(None)
            app.redraw()
        else:
            self._back(app)
        return True
