# screens/base.py - what every screen can do
#
#   draw(app)            draw the whole screen (the app calls presto.update())
#   tick(app, now)       called every loop; return "full" to redraw everything,
#                        an (x, y, w, h) box to redraw only that part (after
#                        drawing it yourself), or None for no change
#   on_knob(app, n)      return True if the screen used the knob itself;
#                        False lets the app move to the previous/next screen
#   on_press(app)        return True if used; False = the app opens the Home menu
#   on_touch(app, x, y)  return True if used; False = the app checks the footer
#
# key picks this screen's gauge pair from config "gauges".

import ui as U


class Screen:
    key = ""
    title = ""
    short = ""                # name in the neighbours' footers

    def enter(self, app):
        pass

    def draw(self, app):
        pass

    def tick(self, app, now):
        return None

    def on_knob(self, app, n):
        return False

    def on_press(self, app):
        return False

    def on_touch(self, app, x, y):
        return False

    def frame(self, app):
        """Header and footer used by the ring screens."""
        u = app.ui
        u.clear()
        u.header(self.title, app.clock_text())
        prev_s, next_s = app.neighbours()
        u.footer(prev_s.short, next_s.short)


class Placeholder(Screen):
    def __init__(self, key, title, short, note):
        self.key, self.title, self.short, self.note = key, title, short, note

    def draw(self, app):
        self.frame(app)
        u = app.ui
        u.text("COMING SOON", U.W // 2, 176, 48, "amber", "center")
        u.text(self.note, U.W // 2, 240, U.T_BODY, "dim", "center")
        g = app.cfg["gauges"].get(self.key, ["", ""])
        u.text("GAUGES: %s / %s" % (g[0].upper(), g[1].upper()), U.W // 2, 300, U.T_NOTE,
               "dim", "center")
