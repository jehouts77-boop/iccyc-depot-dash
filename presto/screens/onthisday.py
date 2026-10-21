# screens/onthisday.py - roadmap 5.9: a day in history (railroads, ships, radio,
# Apple, WWII, air and space, St. Louis ...). Entries come from otd.py.
# Several entries on one day take turns every ROTATE_MS; tap to see the next.

import time
import timeutil
import ui as U
from screens.base import Screen

ROTATE_MS = 20_000
MONTHS = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
          "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")
CATEGORY_NAMES = {
    "RAIL": "RAILROADS", "COMPUTER": "COMPUTERS", "SEA": "MARITIME", "WWII": "WORLD WAR II",
    "RADIO": "RADIO & TV", "TELEGRAPH": "TELEGRAPH", "FARM": "FARM MACHINERY",
    "AUTO": "AUTOMOBILES", "WEATHER": "WEATHER", "STL": "ST. LOUIS & MISSOURI",
    "SKY": "AIR & SPACE",
}
TEXT_TOP = 186
TEXT_BOTTOM = 394
F = "D"                   # this screen's own typeface: Special Elite (typewriter)


class OnThisDayScreen(Screen):
    key = "onthisday"
    title = "ON THIS DAY"
    short = "THIS DAY"

    def __init__(self):
        self.index = 0
        self.shown_day = None
        self.switched = 0

    def enter(self, app):
        self.switched = time.ticks_ms()

    def _today(self, app):
        t = app.local()
        return t, app.otd.entries(t)

    def draw(self, app):
        self.frame(app)
        u = app.ui
        if not timeutil.clock_set():
            u.text("WAITING FOR THE CLOCK", U.W // 2, 200, U.T_HEAD, "amber", "center")
            return
        t, (entries, archive) = self._today(app)
        self.shown_day = (t[1], t[2])
        if not entries:
            u.text("NO ENTRIES LOADED", U.W // 2, 200, U.T_HEAD, "amber", "center")
            u.text(app.otd.error or "copy the otd_data folder to the Presto", U.W // 2, 250,
                   U.T_NOTE, "dim", "center")
            return
        self.index %= len(entries)
        year, cat, text = entries[self.index]
        cx = U.W // 2
        if archive:
            head = "FROM THE ARCHIVES: %s %d" % (MONTHS[archive[0] - 1][:3], archive[1])
            u.text(head, cx, 72, 22, "dim", "center", F)
        else:
            u.text("%s %d" % (MONTHS[t[1] - 1], t[2]), cx, 70, 28, "amber", "center", F)
        u.text(str(year), cx, 100, 64, "cream", "center", F)
        u.text(CATEGORY_NAMES.get(cat, cat), cx, 156, 20, "amber", "center", F)
        # body text: as big as fits
        u.block(text, cx, TEXT_TOP, TEXT_BOTTOM, (26, 22, 19), "text", F)
        if len(entries) > 1:
            u.text("%d OF %d  -  TAP FOR NEXT" % (self.index + 1, len(entries)), cx, 402, 18,
                   "dim", "center", F)

    def tick(self, app, now):
        if not timeutil.clock_set():
            return None
        t = app.local()
        if (t[1], t[2]) != self.shown_day:
            self.index = 0
            return "full"
        entries, _ = app.otd.entries(t)
        if len(entries) > 1 and time.ticks_diff(now, self.switched) >= ROTATE_MS:
            self.switched = now
            self.index += 1
            return "full"
        return None

    def on_touch(self, app, x, y):
        if U.BODY_Y <= y < U.FOOTER_Y:
            self.index += 1
            self.switched = time.ticks_ms()
            app.redraw()
            return True
        return False
