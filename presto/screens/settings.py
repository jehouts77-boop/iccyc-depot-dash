# screens/settings.py - the Settings menu. Each row opens its own page:
#   WIFI       screens/wifi.py      choose a network, type the password
#   CHIME      screens/setpages.py  sound, volume, when, quiet hours
#   BRIGHTNESS screens/setpages.py  screen / gauges / pilot lights, day and night
#   GAUGES     screens/setpages.py  what the two gauges show on each screen
#   UPDATES    screens/update.py    over-the-air updates
#   BACK TO CLOCK  no page: each tap steps to the next choice in IDLE_CHOICES
# Tap a row. The knob still moves to the previous / next screen from here.
# Everything is kept in /config.json (config.py); updates never touch it.

import config
import ui as U
from screens.base import Screen
from screens.setpages import WHEN

ROW_Y, ROW_PITCH, ROW_H = 66, 49, 44
ROWS = ("WIFI", "CHIME", "BRIGHTNESS", "GAUGES", "UPDATES", "BACK TO CLOCK")
# config "idle_s": seconds untouched before the unit goes back to the Clock; 0 = never
IDLE_CHOICES = ((180, "3 MIN"), (1800, "30 MIN"), (10800, "3 HRS"), (0, "NEVER"))


def idle_label(s):
    for v, label in IDLE_CHOICES:
        if v == s:
            return label
    return "NEVER" if not s else "%d MIN" % (s // 60)


class Settings(Screen):
    key = "settings"
    title = "SETTINGS"
    short = "SETTINGS"

    def _summary(self, app, name):
        c = app.cfg
        if name == "WIFI":
            return app.wifi_creds()[0] or "NOT SET"
        if name == "CHIME":
            when = c["chime"]["mode"].upper()
            for k, label in WHEN:
                if k == c["chime"]["mode"]:
                    when = label
            return when if c["chime"]["mode"] == "off" else "%s, %s" % (c["chime"]["sound"], when)
        if name == "BRIGHTNESS":
            return "DAY %d%%  NIGHT %d%%" % (int(c["bright_day"]["screen"] * 100 + 0.5),
                                            int(c["bright_night"]["screen"] * 100 + 0.5))
        if name == "GAUGES":
            return "WHAT EACH ONE SHOWS"
        if name == "BACK TO CLOCK":
            return idle_label(c["idle_s"])
        return app.ota.msg.split(" (")[0]

    def draw(self, app):
        self.frame(app)
        u = app.ui
        for i in range(len(ROWS)):
            y = ROW_Y + i * ROW_PITCH
            x = u.text(ROWS[i], 28, y + 14, 34, "text")
            if ROWS[i] != "BACK TO CLOCK":           # that row has no page to open
                u.text(">", U.W - 20, y + 14, 34, "dim", "right")
            s = self._summary(app, ROWS[i])
            right = U.W - 20 if ROWS[i] == "BACK TO CLOCK" else U.W - 44
            room = right - x - 16
            if u.text_w(s, 22) <= room:
                u.text(s, right, y + 18, 22, "amber" if ROWS[i] == "BACK TO CLOCK" else "dim", "right")
            else:                                  # too long: whole words from the left
                u.text(s, x + 16, y + 18, 22, "dim", max_w=room)
        u.text("UNIT %s   APP %s" % (app.cfg["unit"]["serial"], app.VERSION), U.W // 2, 370, 20,
               "dim", "center")
        u.text("TAP A ROW  -  THE KNOB STILL CHANGES SCREENS", U.W // 2, 398, 18, "dim", "center")

    def on_touch(self, app, x, y):
        i = (y - ROW_Y) // ROW_PITCH
        if y < ROW_Y or not 0 <= i < len(ROWS) or y >= U.FOOTER_Y:
            return False
        name = ROWS[i]
        if name == "WIFI":
            app.wifi.open(app)
        elif name == "CHIME":
            app.set_chime.open(app)
        elif name == "BRIGHTNESS":
            app.set_bright.open(app)
        elif name == "GAUGES":
            app.set_gauges.open(app)
        elif name == "BACK TO CLOCK":
            vals = [v for v, _ in IDLE_CHOICES]
            cur = app.cfg["idle_s"]
            app.cfg["idle_s"] = vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else vals[0]
            try:
                config.save()                 # saved at once: one small write per tap
            except Exception as e:
                print("settings not saved:", e)
            app.redraw()
        else:
            app.update.open(app)
        return True
