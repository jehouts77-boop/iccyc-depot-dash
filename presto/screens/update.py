# screens/update.py - the UPDATES page (roadmap 5.13), opened from Settings.
# Shows what ota.py is doing and has three buttons: BACK, CHECK NOW, and -
# once an update has been installed - PUT BACK OLD (tap twice), which
# restores the files the last update replaced and restarts.
# Updates normally need nobody: the unit checks by itself every night.

import time
import timeutil
import ui as U
from screens.base import Screen
from screens.wifi import button, inside

SURE_MS = 5000            # how long PUT BACK OLD waits for the second tap


class Update(Screen):
    key = "update"
    title = "UPDATES"
    short = "UPDATES"
    hold = True               # the app's "idle -> back to the Clock" leaves this screen alone

    B_BACK = (12, 410, 132, 58)
    B_CHECK = (150, 410, 150, 58)
    B_UNDO = (306, 410, 162, 58)

    def __init__(self):
        self.shown = None
        self.sure_at = None       # ticks of the first tap on PUT BACK OLD

    def open(self, app):
        app.show(self)

    def enter(self, app):
        self.shown = None
        self.sure_at = None

    def _stamp(self, app):
        o = app.ota
        return (o.state, o.msg, self.sure_at is not None)

    def tick(self, app, now):
        if self.sure_at is not None and time.ticks_diff(now, self.sure_at) > SURE_MS:
            self.sure_at = None
        return "full" if self._stamp(app) != self.shown else None

    def on_knob(self, app, n):
        return True

    def on_press(self, app):
        if not app.ota.busy():
            app.go(app.ring_index)            # back to Settings
        return True

    def on_touch(self, app, x, y):
        o = app.ota
        if inside(self.B_BACK, x, y):
            app.go(app.ring_index)
        elif inside(self.B_CHECK, x, y) and not o.busy():
            self.sure_at = None
            o.start()
        elif inside(self.B_UNDO, x, y) and o.can_undo():
            if self.sure_at is None:
                self.sure_at = time.ticks_ms()
            else:
                self.sure_at = None
                o.undo()
        return True

    def draw(self, app):
        u = app.ui
        o = app.ota
        c = o.c
        self.shown = self._stamp(app)
        u.clear()
        u.header(self.title, app.clock_text())
        colour = "red" if o.state == "failed" or o.undone == o.msg and o.msg else \
            "green" if o.msg == "UP TO DATE" else "amber"
        lines = u.wrap(o.msg, 36, U.W - 40)[:3]
        y = 84 + (3 - len(lines)) * 20
        for line in lines:
            u.text(line, U.W // 2, y, 36, colour, "center")
            y += 40
        y = 216
        if o.checked:
            t = timeutil.local(app.cfg["tz"], o.checked)
            when = "%s %s" % (timeutil.date_line(t), timeutil.hhmm(t))
        else:
            when = "NEVER"
        rows = (
            ("LAST CHECK", when),
            ("NEXT", ("TONIGHT AT " + c.get("time", "03:30")) if c.get("auto", True)
             else "ONLY WHEN YOU TAP CHECK NOW"),
            ("FROM", c["repo"]),
            ("BRANCH", c["branch"]),
            ("VERSION", "%s  %s" % (app.VERSION, (o.tree[:7] or "-").upper())),
        )
        for name, val in rows:
            u.text(name, 20, y, U.T_NOTE, "dim")
            u.text(val, 150, y, U.T_NOTE, "text", max_w=U.W - 170)
            y += 30
        if o.trial:
            u.text("NEW VERSION ON TRIAL FOR ITS FIRST MINUTE", U.W // 2, y + 4, 20, "dim", "center")
        button(u, self.B_BACK, "< BACK", "dim")
        if o.busy():
            button(u, self.B_CHECK, "WORKING", "dim")
        else:
            button(u, self.B_CHECK, "CHECK NOW", "bg", "amber")
        if o.can_undo():
            if self.sure_at is None:
                button(u, self.B_UNDO, "PUT BACK OLD", "text", size=24)
            else:
                button(u, self.B_UNDO, "TAP AGAIN", "bg", "red", 24)
