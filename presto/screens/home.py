# screens/home.py - the Home menu (knob press from any screen)
# Turn the knob to move the highlight, press to open; or tap a row.

import ui as U
from screens.base import Screen

ROW_H = 48
TOP = U.BODY_Y + 4


class Home(Screen):
    key = "home"
    title = "ICCYC  DEPOT DASHBOARD"
    short = "MENU"

    def __init__(self):
        self.sel = 0

    def enter(self, app):
        self.sel = app.ring_index        # highlight the screen we came from

    def draw(self, app):
        u = app.ui
        u.clear()
        u.header("ICCYC", "DEPOT DASHBOARD")
        for i, s in enumerate(app.ring):
            y = TOP + i * ROW_H
            if i == self.sel:
                u.rect(8, y, U.W - 16, ROW_H - 6, "panel")
                u.rect(8, y, 4, ROW_H - 6, "amber")
            u.text(s.title, 28, y + 10, 34, "amber" if i == self.sel else "text")
            u.text(">", U.W - 28, y + 10, 34, "dim", "right")
        u.hint("TURN + PRESS THE KNOB  -  OR TAP")

    def on_knob(self, app, n):
        self.sel = (self.sel + n) % len(app.ring)
        app.redraw()
        return True

    def on_press(self, app):
        app.go(self.sel)
        return True

    def on_touch(self, app, x, y):
        i = (y - TOP) // ROW_H
        if y >= TOP and 0 <= i < len(app.ring):
            app.go(i)
        return True
