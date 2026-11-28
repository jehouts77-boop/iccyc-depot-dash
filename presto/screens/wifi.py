# screens/wifi.py - roadmap 5.12: WiFi setup on the unit itself (no phone, no
# hotspot - decided 2026-10-07).
#
# Not in the screen ring. It opens
#   - by itself at start-up when the unit has no WiFi saved (a welcome page), and
#   - from the WIFI row on the Settings screen.
#
# Pages (look agreed from renders\wifi_setup_mockup_2026-10-07.png):
#   welcome -> scan -> pick a network -> type the password -> joining ->
#   connected (saved to /config.json) or couldn't join (nothing changed).
#
# APP 0.4 (2026-11-28): with a network saved, the WIFI row opens a "saved"
# page first: the network, CONNECTED or not, CHANGE NETWORK (the list as
# before) and FORGET. FORGET asks first (the knob's press = KEEP IT), then
# wipes the network and password from /config.json, hangs up and shows the
# welcome page - the unit is then as on its first start (roadmap 7.2, and
# the way to clear a gift unit's WiFi before it is wrapped).
#
# Touch does everything. The knob works too: on the list it moves the
# highlight and a press chooses; on the keyboard it steps from key to key and
# a press types that key - slower, but exact.
#
# A network with no password skips the keyboard. Hidden networks (no name
# broadcast) are not supported in this version.
#
# The password is shown while it is typed and is stored as plain text in
# /config.json on the unit (which never goes to GitHub).

import time
import config
import net
import ui as U
from screens.base import Screen

ROWS_SHOWN = 6            # networks per page
ROW_H = 50
LIST_Y = 66
JOIN_TIMEOUT_S = 25
SETTLE_MS = 2000          # ignore the radio's answer for this long after asking to join
MAX_LEN = 63              # longest WiFi password
FLASH_MS = 140            # how long a touched key stays lit

KEY_W, KEY_H, KEY_PITCH = 46, 52, 56
KEYS_X, KEYS_Y = 10, 156
FIELD = (12, 68, U.W - 24, 52)

LAYERS = {
    "abc": ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
    "ABC": ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"),
    "123": ("1234567890", "-/:;()$&@", ".,?!'\"_"),
    "#+=": ("[]{}#%^*+=", "\\|~<>`@&$", ".,?!'\"_"),
}
SWAP = {"abc": "ABC", "ABC": "abc", "123": "#+=", "#+=": "123"}     # the key left of row 3


def bars_for(rssi):
    if rssi is None:
        return 0
    return 4 if rssi >= -55 else 3 if rssi >= -67 else 2 if rssi >= -78 else 1


def draw_bars(u, x, y, level, colour):
    for i in range(4):
        h = 6 + i * 5
        u.rect(x + i * 8, y + 21 - h, 5, h, colour if i < level else "line")


def draw_lock(u, x, y, colour="dim"):
    u.pen(colour)
    u.d.circle(x + 7, y + 7, 6)
    u.pen("bg")
    u.d.circle(x + 7, y + 7, 3)
    u.rect(x, y + 7, 15, 12, colour)


def button(u, box, label, colour="text", fill="panel", size=26):
    x, y, w, h = box
    u.rect(x, y, w, h, "line")
    u.rect(x + 2, y + 2, w - 4, h - 4, fill)
    u.text(label, x + w // 2, y + (h - int(size * 0.65)) // 2, size, colour, "center")


def inside(box, x, y):
    return box[0] <= x < box[0] + box[2] and box[1] <= y < box[1] + box[3]


def keys_for(layer):
    """[(box, label, what)] - what is the character to type, or one of
    'swap', 'del', 'layer', ' ', 'join', 'back'. Also the knob's order."""
    out = []
    rows = LAYERS[layer]
    for ri in range(3):
        row = rows[ri]
        y = KEYS_Y + ri * KEY_PITCH
        x0 = KEYS_X + (0 if len(row) == 10 else 23 if len(row) == 9 else 69)
        if ri == 2:
            out.append(((KEYS_X, y, 64, KEY_H), SWAP[layer], "swap"))
        for ci in range(len(row)):
            out.append(((x0 + ci * KEY_W + 1, y, KEY_W - 3, KEY_H), row[ci], row[ci]))
        if ri == 2:
            out.append(((U.W - KEYS_X - 66, y, 64, KEY_H), "DEL", "del"))
    y = KEYS_Y + 3 * KEY_PITCH
    out.append(((KEYS_X, y, 87, KEY_H), "123" if layer in ("abc", "ABC") else "abc", "layer"))
    out.append(((KEYS_X + 92, y, 276, KEY_H), "SPACE", " "))
    out.append(((KEYS_X + 373, y, 87, KEY_H), "JOIN", "join"))
    out.append(((12, 418, 148, 50), "< NETWORKS", "back"))
    return out


class WifiSetup(Screen):
    key = "wifi"
    title = "WIFI SETUP"
    short = "WIFI"
    hold = True               # the app's "idle -> back to the Clock" leaves this screen alone

    B_BACK = (12, 410, 148, 58)
    B_SCAN = (166, 410, 148, 58)
    B_MORE = (320, 410, 148, 58)
    B_START = (110, 350, 260, 64)
    B_DONE = (140, 400, 200, 60)
    B_RETRY = (24, 400, 210, 60)
    B_OTHER = (246, 400, 210, 60)
    B_CHANGE = (60, 300, 360, 60)         # saved page
    B_FORGET = (320, 410, 148, 58)
    B_KEEP = (24, 400, 210, 60)           # forget page
    B_WIPE = (246, 400, 210, 60)

    def __init__(self):
        self.page = "welcome"
        self.first = False        # opened by itself at start-up (no WiFi saved)
        self.nets = []            # [(shown name, rssi, secured, real name)]
        self.scan_error = ""
        self.sel = 0
        self.top = 0              # first network shown
        self.net = None           # the network being joined
        self.typed = ""
        self.layer = "abc"
        self.keys = keys_for("abc")
        self.knob_key = None      # index of the key the knob is on, or None
        self.lit = None           # index of the key lit by a touch
        self.lit_at = 0
        self.dirty = []           # key indexes to redraw; -1 = the password box
        self.join_at = 0
        self.why = ""
        self.ip = ""
        self.scans = self.joins = self.fails = 0
        self.drawn_state = None   # the WiFi state the saved page was drawn with
        self.forgets = 0

    # ---------- opening and closing ----------
    def open(self, app, first=False):
        self.first = first
        self.why = ""
        if first:
            self.page = "welcome"
        elif app.wifi_creds()[0]:
            self.page = "saved"                # APP 0.4: show what is saved first
        else:
            self.page = "scan"
        app.show(self)

    def enter(self, app):
        self.drawn_scan = False

    def _close(self, app):
        app.wifi_busy = False
        if self.first:
            app.go(0)                          # first start: on to the Clock
        else:
            app.go(app.ring_index)             # back to Settings

    # ---------- scanning ----------
    def _rescan(self, app):
        self.page = "scan"
        self.drawn_scan = False
        app.redraw()

    def _do_scan(self, app):
        self.scans += 1
        ok, res = net.scan()
        if ok:
            self.nets, self.scan_error = res, ""
        else:
            self.nets, self.scan_error = [], res
        self.sel = self.top = 0
        self.page = "pick"

    # ---------- forgetting (APP 0.4) ----------
    def _forget(self, app):
        self.forgets += 1
        w = app.cfg["wifi"]
        w["ssid"], w["password"] = "", ""
        try:
            config.save()
            self.why = ""
        except Exception as e:                 # forgotten until the next restart only
            self.why = "NOT WIPED FROM MEMORY: %s" % e
        net.forget()
        app.wifi_busy = False
        app.wifi_state = net.status()          # 'off': the WiFi lamp goes out
        app.update_leds()
        self.net = None
        self.typed = ""
        self.first = True                      # from here on, as on a first start
        self.page = "welcome"
        app.redraw()

    # ---------- joining ----------
    def _join(self, app):
        self.joins += 1
        self.page = "joining"
        self.why = ""
        app.wifi_busy = True                   # the app must not reconnect by itself now
        self.join_at = time.ticks_ms()
        if not net.start_connect(self.net[3], self.typed):
            self._failed(app, "THE RADIO DID NOT START.")
        app.redraw()

    def _failed(self, app, why):
        self.fails += 1
        self.why = why
        self.page = "fail"
        app.wifi_busy = False
        app.wifi_setup()                       # back to the network that was saved (if any)
        app.redraw()

    def _joined(self, app):
        w = app.cfg["wifi"]
        w["ssid"], w["password"] = self.net[3], self.typed
        try:
            config.save()
            self.why = ""
        except Exception as e:                 # still connected; just not remembered
            self.why = "NOT SAVED: %s" % e
        self.ip = net.info()[1] or ""
        self.typed = ""
        self.page = "ok"
        app.wifi_busy = False
        app.redraw()

    def tick(self, app, now):
        if self.page == "saved":
            if app.wifi_state != self.drawn_state:   # e.g. CONNECTING -> CONNECTED
                return "full"
            return None
        if self.page == "scan":
            if not self.drawn_scan:            # let "SCANNING" reach the screen first
                self.drawn_scan = True
                return None
            self._do_scan(app)
            return "full"
        if self.page == "joining":
            state = net.status(JOIN_TIMEOUT_S)
            if time.ticks_diff(now, self.join_at) < SETTLE_MS:
                return None                    # the old network may still read "connected"
            if state == "up":
                self._joined(app)
            elif state != "connecting":
                self._failed(app, "")
            else:
                code = net.link_code()         # the radio may say why, before the time is up
                if code == -3:
                    self._failed(app, "THE PASSWORD WAS NOT ACCEPTED.")
                elif code == -2:
                    self._failed(app, "THE NETWORK WAS NOT FOUND.")
            return None
        if self.page == "keys":
            if self.lit is not None and time.ticks_diff(now, self.lit_at) >= FLASH_MS:
                self.dirty.append(self.lit)
                self.lit = None
            if self.dirty:
                return self._redraw_parts(app)
        return None

    # ---------- inputs ----------
    def on_knob(self, app, n):
        if self.page == "pick" and self.nets:
            self.sel = (self.sel + n) % len(self.nets)
            self.top = (self.sel // ROWS_SHOWN) * ROWS_SHOWN
            app.redraw()
        elif self.page == "keys":
            old = self.knob_key
            self.knob_key = (n - 1 if old is None else old + n) % len(self.keys)
            if old is not None:
                self.dirty.append(old)
            self.dirty.append(self.knob_key)
        return True

    def on_press(self, app):
        if self.page == "welcome":
            self._close(app)                   # skip for now
        elif self.page == "pick" and self.nets:
            self._choose(app, self.sel)
        elif self.page == "keys" and self.knob_key is not None:
            self._key(app, self.knob_key)
        elif self.page == "ok":
            self._close(app)
        elif self.page == "fail":
            self._retry(app)
        elif self.page == "saved":
            self._close(app)                   # back to Settings
        elif self.page == "forget":
            self.page = "saved"                # the safe choice: KEEP IT
            app.redraw()
        return True

    def on_touch(self, app, x, y):
        p = self.page
        if p == "welcome":
            if inside(self.B_START, x, y):
                self._rescan(app)
        elif p == "pick":
            if inside(self.B_BACK, x, y):
                self._close(app)
            elif inside(self.B_SCAN, x, y):
                self._rescan(app)
            elif inside(self.B_MORE, x, y) and len(self.nets) > ROWS_SHOWN:
                self.top += ROWS_SHOWN
                if self.top >= len(self.nets):
                    self.top = 0
                self.sel = self.top
                app.redraw()
            else:
                i = (y - LIST_Y) // ROW_H
                if y >= LIST_Y and 0 <= i < ROWS_SHOWN and self.top + i < len(self.nets):
                    self._choose(app, self.top + i)
        elif p == "keys":
            for i in range(len(self.keys)):
                if inside(self.keys[i][0], x, y):
                    self._key(app, i)
                    break
        elif p == "ok":
            if inside(self.B_DONE, x, y):
                self._close(app)
        elif p == "fail":
            if inside(self.B_RETRY, x, y):
                self._retry(app)
            elif inside(self.B_OTHER, x, y):
                self._rescan(app)
        elif p == "saved":
            if inside(self.B_BACK, x, y):
                self._close(app)
            elif inside(self.B_CHANGE, x, y):
                self._rescan(app)
            elif inside(self.B_FORGET, x, y):
                self.page = "forget"
                app.redraw()
        elif p == "forget":
            if inside(self.B_KEEP, x, y):
                self.page = "saved"
                app.redraw()
            elif inside(self.B_WIPE, x, y):
                self._forget(app)
        return True

    def _choose(self, app, i):
        self.sel = i
        self.net = self.nets[i]
        self.typed = ""
        if self.net[2]:                        # has a password: ask for it
            self._layer("abc")
            self.page = "keys"
            app.redraw()
        else:
            self._join(app)

    def _retry(self, app):
        if self.net is not None and self.net[2]:
            self.page = "keys"
            app.redraw()
        else:
            self._rescan(app)

    def _layer(self, layer):
        self.layer = layer
        self.keys = keys_for(layer)
        self.knob_key = None
        self.lit = None
        self.dirty = []

    def _key(self, app, i):
        what = self.keys[i][2]
        if what == "swap":
            self._layer(SWAP[self.layer])
            app.redraw()
        elif what == "layer":
            self._layer("123" if self.layer in ("abc", "ABC") else "abc")
            app.redraw()
        elif what == "back":
            self._rescan(app)
        elif what == "join":
            if self.typed:
                self._join(app)
        else:
            if what == "del":
                self.typed = self.typed[:-1]
            elif len(self.typed) < MAX_LEN:
                self.typed += what
            if self.lit is not None and self.lit != i:
                self.dirty.append(self.lit)
            self.lit = i
            self.lit_at = time.ticks_ms()
            self.dirty.append(i)
            self.dirty.append(-1)

    # ---------- drawing ----------
    def _draw_key(self, u, i):
        box, label, what = self.keys[i]
        x, y, w, h = box
        hot = i == self.lit
        knob = i == self.knob_key
        if len(what) == 1 and what != " ":
            u.rect(x, y, w, h, "amber" if knob else "line")
            u.rect(x + 2, y + 2, w - 4, h - 4, "amber" if hot else "panel")
            u.text(label, x + w // 2, y + 14, 36, "bg" if hot else "cream", "center")
            return
        colour = {"del": "red", " ": "dim", "back": "dim", "join": "bg"}.get(what, "amber")
        fill = "amber" if (what == "join" or hot) else "panel"
        if hot:
            colour = "bg"
        if knob:                               # the knob's key: a bright frame
            u.rect(x - 2, y - 2, w + 4, h + 4, "cream")
        button(u, box, label, colour, fill, 26 if what == "join" else 24)

    def _draw_field(self, u):
        x, y, w, h = FIELD
        u.rect(x, y, w, h, "line")
        u.rect(x + 2, y + 2, w - 4, h - 4, "bg")
        shown = self.typed
        while shown and u.text_w(shown, 32) > w - 34:      # too long: show the end of it
            shown = shown[1:]
        end = u.text(shown, x + 12, y + 16, 32, "cream")
        u.rect(end + 3, y + 12, 3, 30, "amber")            # cursor
        u.rect(x, y + h + 2, w, 26, "bg")
        if self.typed:
            note = "%d CHARACTER%s  -  SHOWN AS YOU TYPE" % (len(self.typed),
                                                             "" if len(self.typed) == 1 else "S")
        else:
            note = "TYPE THE WIFI PASSWORD, THEN JOIN"
        u.text(note, x + 2, y + h + 8, 20, "dim")

    def _redraw_parts(self, app):
        """Redraw only the keys / password box that changed; return the box to send."""
        u = app.ui
        x0, y0, x1, y1 = U.W, U.H, 0, 0
        todo, self.dirty = self.dirty, []
        for i in todo:
            if i == -1:
                self._draw_field(u)
                b = (FIELD[0], FIELD[1], FIELD[2], FIELD[3] + 30)
            else:
                if i >= len(self.keys):
                    continue
                b = self.keys[i][0]
                b = (b[0] - 2, b[1] - 2, b[2] + 4, b[3] + 4)
                u.rect(b[0], b[1], b[2], b[3], "bg")
                self._draw_key(u, i)
            x0, y0 = min(x0, b[0]), min(y0, b[1])
            x1, y1 = max(x1, b[0] + b[2]), max(y1, b[1] + b[3])
        if x1 <= x0:
            return None
        return (x0, y0, x1 - x0, y1 - y0)

    def draw(self, app):
        u = app.ui
        u.clear()
        cx = U.W // 2
        p = self.page
        name = self.net[0] if self.net else ""
        if p == "welcome":
            u.header("WELCOME")
            u.text(app.cfg["clock"]["maker"], cx, 96, 64, "cream", "center")
            u.text("CONTROL CONSOLE", cx, 152, 30, "brass", "center")
            u.text("THIS UNIT NEEDS YOUR WIFI FOR THE", cx, 222, 24, "text", "center")
            u.text("TIME, THE WEATHER AND THE TRAINS.", cx, 250, 24, "text", "center")
            u.text("YOU WILL NEED YOUR WIFI PASSWORD.", cx, 292, 24, "dim", "center")
            if self.why:                       # FORGET couldn't wipe /config.json
                u.text(self.why, 20, 318, 20, "red", max_w=U.W - 40)
            button(u, self.B_START, "SET UP WIFI", "bg", "amber", 32)
            u.text("OR PRESS THE KNOB TO SKIP FOR NOW", cx, 440, 20, "dim", "center")
        elif p == "saved":
            st = app.wifi_state
            self.drawn_state = st
            ssid, ip, rssi = net.info()
            u.header(self.title, "SAVED NETWORK")
            u.text("THIS UNIT JOINS", cx, 92, 24, "dim", "center")
            u.text(app.wifi_creds()[0], cx, 128, 40, "cream", "center", max_w=U.W - 40)
            if st == "up":
                u.text("CONNECTED", cx, 196, 34, "green", "center")
                if ip:
                    u.text("ADDRESS " + ip, cx, 242, 24, "dim", "center")
            elif st == "connecting":
                u.text("CONNECTING", cx, 196, 34, "amber", "center")
            else:
                u.text("NOT CONNECTED", cx, 196, 34, "red", "center")
                u.text("IT KEEPS TRYING ONCE A MINUTE", cx, 242, 24, "dim", "center")
            button(u, self.B_CHANGE, "CHANGE NETWORK", "amber", "panel", 28)
            button(u, self.B_BACK, "< BACK", "dim")
            button(u, self.B_FORGET, "FORGET", "red")
        elif p == "forget":
            u.header("FORGET NETWORK")
            u.text("FORGET THIS NETWORK?", cx, 100, U.T_HEAD, "amber", "center")
            u.text(app.wifi_creds()[0], cx, 156, 34, "cream", "center", max_w=U.W - 40)
            u.text("THE NETWORK AND ITS PASSWORD ARE", cx, 222, 24, "text", "center")
            u.text("WIPED FROM THIS UNIT. IT GOES OFFLINE", cx, 250, 24, "text", "center")
            u.text("AND SHOWS THE WELCOME PAGE, AS ON", cx, 278, 24, "text", "center")
            u.text("ITS FIRST START.", cx, 306, 24, "text", "center")
            u.text("PRESS THE KNOB TO KEEP IT", cx, 352, 20, "dim", "center")
            button(u, self.B_KEEP, "KEEP IT", "bg", "amber", 28)
            button(u, self.B_WIPE, "FORGET", "red", "panel", 28)
        elif p == "scan":
            u.header(self.title)
            u.text("LOOKING FOR NETWORKS", cx, 200, U.T_HEAD, "amber", "center")
            u.text("THIS TAKES A FEW SECONDS", cx, 250, U.T_NOTE, "dim", "center")
        elif p == "pick":
            u.header(self.title, "CHOOSE A NETWORK" if self.nets else "")
            if not self.nets:
                u.text("NO NETWORKS FOUND", cx, 180, U.T_HEAD, "amber", "center")
                if self.scan_error:
                    u.text(self.scan_error, 20, 240, U.T_NOTE, "dim", max_w=U.W - 40)
            for k in range(ROWS_SHOWN):
                i = self.top + k
                if i >= len(self.nets):
                    break
                shown, rssi, secured, _ = self.nets[i]
                y = LIST_Y + k * ROW_H
                on = i == self.sel
                if on:
                    u.rect(8, y, U.W - 16, 44, "panel")
                    u.rect(8, y, 4, 44, "amber")
                u.text(shown, 28, y + 11, 32, "amber" if on else "text", max_w=330)
                if secured:
                    draw_lock(u, U.W - 96, y + 12)
                draw_bars(u, U.W - 64, y + 10, bars_for(rssi), "amber" if on else "text")
            if self.nets:
                n = len(self.nets)
                if n > ROWS_SHOWN:
                    note = "%d TO %d OF %d  -  TAP ONE, OR TURN + PRESS THE KNOB" % (
                        self.top + 1, min(n, self.top + ROWS_SHOWN), n)
                else:
                    note = "%d FOUND  -  TAP ONE, OR TURN + PRESS THE KNOB" % n
                u.text(note, cx, 376, 20, "dim", "center")
            button(u, self.B_BACK, "< BACK", "dim")
            button(u, self.B_SCAN, "SCAN AGAIN", "amber")
            if len(self.nets) > ROWS_SHOWN:
                button(u, self.B_MORE, "MORE v", "text")
        elif p == "keys":
            u.header("WIFI PASSWORD")
            u.text(name, U.W - 16, 20, U.T_BODY, "dim", "right")
            self._draw_field(u)
            for i in range(len(self.keys)):
                self._draw_key(u, i)
            u.text("OR TURN THE KNOB TO A KEY AND PRESS", 320, 436, 20, "dim", "center")
            self.dirty = []
        elif p == "joining":
            u.header(self.title)
            u.text("JOINING", cx, 150, 64, "amber", "center")
            u.text(name, cx, 236, 34, "cream", "center")
            u.text("THIS CAN TAKE UP TO %d SECONDS" % JOIN_TIMEOUT_S, cx, 300, U.T_NOTE, "dim",
                   "center")
        elif p == "ok":
            u.header(self.title)
            u.text("CONNECTED", cx, 120, 64, "green", "center")
            draw_bars(u, cx - 16, 196, bars_for(net.info()[2]) or 3, "green")
            u.text(name, cx, 240, 34, "cream", "center")
            if self.ip:
                u.text("ADDRESS " + self.ip, cx, 284, 24, "dim", "center")
            if self.why:
                u.text(self.why, 20, 330, 24, "red", max_w=U.W - 40)
            else:
                u.text("SAVED. THIS UNIT WILL REMEMBER IT.", cx, 330, 24, "text", "center")
            button(u, self.B_DONE, "DONE", "bg", "amber", 30)
        else:                                  # fail
            u.header(self.title)
            u.text("COULDN'T JOIN", cx, 120, 64, "red", "center")
            u.text(name, cx, 208, 34, "cream", "center")
            if self.why:
                u.text(self.why, cx, 276, 24, "text", "center")
            else:
                u.text("THE PASSWORD MAY BE WRONG, OR THE", cx, 262, 24, "text", "center")
                u.text("NETWORK IS TOO FAR AWAY.", cx, 290, 24, "text", "center")
            u.text("NOTHING WAS CHANGED.", cx, 330, 24, "dim", "center")
            if self.net is not None and self.net[2]:
                button(u, self.B_RETRY, "TRY THE PASSWORD", "bg", "amber", 26)
            button(u, self.B_OTHER, "OTHER NETWORK", "amber")
