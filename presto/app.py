# app.py - the ICCYC Depot Dashboard app on the Presto
#
# One loop, about 100 times a second:
#   - every 20 ms: read the Controls board (knob, button, switches, audio)
#   - touch: tap a row / the PREV MENU NEXT strip
#   - every second: check both boards (restart? missing?), WiFi, clock sync,
#     the readings the gauges follow
#   - chime: on the hour etc., unless muted
#   - gauges: send only what changed
#   - screen: redraw only what changed
#
# Controls (decided 2026-09-30): turn = previous / next screen, press = Home
# menu (turn to pick, press to open), long press = Diagnostics, touch works
# too. Untouched for config "idle_s" -> back to the Clock (0 = never).
# Switches: CHIME (mute), DAY/NIGHT (manual brightness, no automatic
# dimming), BACKLIGHT (off = Presto + gauges dark, pilot lights dim; the
# clock and chime keep running), WIFE MODE (mute + night brightness, no
# announcement).

import gc
import time
from machine import I2C, Pin

import config
import net
import timeutil
import coproc
import chime
import weather
import otd
import almanac
import trains
import planes
import iss
import isslisten
import ota
import gaugekinds as GK
import ui as U
import screens
from screens import fitz as fitz_rules

VERSION = "0.2"
POLL_MS = 20
CHIME_MS = 250
LOOP_MS = 10
KNOB_SETTLE_MS = 150      # after a knob click, wait this long for another before drawing:
#                           spinning through several screens draws only the last one
#                           (a screen of smooth text takes a few tenths of a second)
NTP_EVERY_S = 6 * 3600
WIFI_RETRY_S = 60
NTP_RETRY_S = 60
OTA_LED_MIN_MS = 3000     # the OTA light shows a check for at least this long, however quick it was
FETCH_SETTLE_MS = 1000    # a screen's own data (trains, planes, ISS) is fetched only once the knob
#                           and touch have rested this long: turning past a screen no longer
#                           starts its request, which held up the knob for seconds (desk, 2026-10-17)


class App:
    VERSION = VERSION

    def __init__(self, presto):
        self.presto = presto
        self.cfg = config.load()
        self.cfg_error = config.load_error
        self.ui = U.UI(presto.display)
        i2c = I2C(0, sda=Pin(40), scl=Pin(41), freq=100_000)     # Qw/ST port
        self.gauges = coproc.Gauges(i2c)
        self.controls = coproc.Controls(i2c, long_press_ms=self.cfg["long_press_ms"])
        self.chime = chime.Chime()
        self.weather = weather.Weather(self.cfg)
        self.otd = otd.OnThisDay()
        self.almanac = almanac.Almanac(self.cfg)
        self.trains = trains.Trains(self.cfg)
        self.planes = planes.Planes(self.cfg)
        self.iss = iss.ISS(self.cfg)
        self.listener = isslisten.Listener(self.cfg)   # ISS heard over ham radio: always on
        self.ota = ota.Ota(self.cfg, self.restart)
        self.ring, self.home, self.diag = screens.build()
        self.fitz = screens.Fitz()            # hidden: see screens/fitz.py
        self.wifi = screens.WifiSetup()       # WiFi setup: from Settings, or first start
        self.update = screens.Update()        # updates: from Settings
        self.set_chime = screens.ChimePage()  # the pages behind the Settings menu
        self.set_bright = screens.BrightPage()
        self.set_gauges = screens.GaugesPage()
        self.wifi_busy = False                # True while WiFi setup is trying a network
        self.fitz_year = None                 # the year it last ran by itself
        self.ring_index = 0
        self.screen = self.ring[0]
        self.before_diag = None
        self.data = {}
        # switch state (normal until the Controls board says otherwise)
        self.chime_on, self.night, self.dark, self.wife_mode = True, False, False, False
        self.wifi_state = "off"
        self.wifi_retry_at = 0
        self.ntp_next = time.ticks_ms()
        self.started = time.ticks_ms()
        self.last_input = self.started
        self.need_full = True
        self.settle_until = None              # ticks: no full draw before this (knob turning)
        self._ota_led = 0                     # the OTA light's mode as last sent (0 off, 2 slow, 3 fast)
        self._ota_led_until = self.started    # ticks: keep showing a finished check until then
        self.loop_ms = self.loop_max_ms = self.draw_ms = 0
        self.loop_max_what = "-"              # what the slowest loop was doing (Diagnostics)
        self.loop_max_at = 0                  # ... and how many seconds after start
        self._what = ""
        self._touching = False
        self._done_events = 0

    # ---------- helpers the screens use ----------
    def local(self):
        return timeutil.local(self.cfg["tz"])

    def chime_muted(self):
        """True while the chime would stay silent (any reason)."""
        if not timeutil.clock_set():
            return not self.chime_on or self.wife_mode or self.cfg["chime"]["mode"] == "off"
        return self.chime.muted(self.cfg, self.local(), self.chime_on, self.wife_mode) != ""

    def clock_text(self):
        return timeutil.hhmm(self.local()) if timeutil.clock_set() else ""

    def neighbours(self):
        n = len(self.ring)
        return self.ring[(self.ring_index - 1) % n], self.ring[(self.ring_index + 1) % n]

    def switch_text(self):
        return "".join(("C" if self.chime_on else "c", "N" if self.night else "d",
                        "X" if self.dark else "L", "W" if self.wife_mode else "w"))

    def redraw(self):
        self.need_full = True

    def restart(self):
        """After an update was installed (or undone): start again with the new files."""
        try:
            self.controls.leds(coproc.LED_OFF, coproc.LED_FAST, self.led_bright, self.ota_bright)
            self.controls.sync()
        except Exception:
            pass
        import machine
        machine.reset()

    def show(self, screen):
        self.screen = screen
        screen.enter(self)
        self.need_full = True

    def go(self, i):
        self.ring_index = i % len(self.ring)
        self.show(self.ring[self.ring_index])

    def step_ring(self, n):
        self.go(self.ring_index + n)

    def open_home(self):
        self.show(self.home)

    def toggle_diag(self):
        if self.screen is self.diag:
            self.show(self.before_diag or self.ring[self.ring_index])
        else:
            self.before_diag = self.screen
            self.show(self.diag)

    def start_fitz(self):
        if self.screen is not self.fitz:
            self.show(self.fitz)

    def end_fitz(self):
        if self.screen is self.fitz:
            self.controls.stop()              # cut a bell that is still ringing
            self.go(0)

    # ---------- switches and brightness ----------
    def apply_switches(self, bits):
        b = bits ^ self.cfg["switch_invert"]
        self.chime_on = not (b & 1)
        self.night = bool(b & 2)
        self.dark = bool(b & 4)
        self.wife_mode = bool(b & 8)
        self.apply_lighting()

    def apply_lighting(self):
        lv = self.cfg["bright_night"] if (self.night or self.wife_mode) else self.cfg["bright_day"]
        if self.dark:
            self.presto.set_backlight(0)
            self.gauges.backlight(0)          # gauges: display-off command (1.8c)
            led_bright = ota_bright = self.cfg["leds_dark"]
        else:
            self.presto.set_backlight(lv["screen"])
            self.gauges.backlight(lv["gauges"])
            led_bright = lv["leds"]
            ota_bright = lv.get("ota_led", led_bright)
        self.led_bright = led_bright
        self.ota_bright = ota_bright
        self.update_leds()

    def update_leds(self):
        wifi_mode = {"up": coproc.LED_ON, "connecting": coproc.LED_SLOW,
                     "failed": coproc.LED_FAST}.get(self.wifi_state, coproc.LED_OFF)
        ota_mode = (coproc.LED_OFF, coproc.LED_ON, coproc.LED_SLOW, coproc.LED_FAST)[self._ota_led]
        self.controls.leds(wifi_mode, ota_mode, self.led_bright, self.ota_bright)   # OTA light: 5.13

    # ---------- readings for the gauges ----------
    def update_data(self):
        t = self.local()
        self.data["seconds"] = t[5]
        _, _, rssi = net.info()
        self.data["wifi_rssi"] = rssi
        free = gc.mem_free()
        self.data["free_mem_pct"] = free * 100 // max(1, free + gc.mem_alloc())
        wx = self.weather.readings()            # {} while missing or more than 2 h old
        for k in ("temp_f", "humidity", "pressure_inhg", "wind_mph", "wind_dir", "dewpoint_f"):
            self.data[k] = wx.get(k)
        sky = {}                                # sun and moon: worked out here, no internet
        if timeutil.clock_set():
            self.almanac.update()
            sky = self.almanac.readings()
        for k in ("daylight_left_h", "sun_az"):
            self.data[k] = sky.get(k)
        rail = self.trains.readings()
        for k in ("train_mph", "train_bearing", "train_mi"):
            self.data[k] = rail.get(k)
        page = getattr(self.screen, "page", "") if self.screen.key == "overhead" else ""
        air = self.planes.readings() if page == "planes" else {}
        for k in ("plane_alt_kft", "plane_bearing", "plane_mi"):
            self.data[k] = air.get(k)
        sat = self.iss.readings() if page == "iss" else {}
        for k in ("iss_elev", "iss_bearing", "iss_mi"):
            self.data[k] = sat.get(k)

    def sync_gauges(self):
        kinds = None
        pick = getattr(self.screen, "gauge_pair", None)
        if pick is not None:
            kinds = pick(self)                # the GAUGES page shows the pair being chosen
        if not kinds:
            kinds = self.cfg["gauges"].get(self.screen.key) or self.cfg["gauges"]["clock"]
        for i in range(2):
            kind = kinds[i]
            reading = self.data.get(GK.reading_for(kind))
            kw = GK.setup_for(kind, reading is not None)
            self.gauges.setup(i, **kw)
            if reading is None:
                v = GK.rest_value(kind)
            else:
                v = round(reading * (10 ** kw["dec"]))
            self.gauges.value(i, v)
            self.gauges.text(i, GK.readout_text(kind, self.data) if reading is not None else "")
        self.gauges.sync()

    # ---------- WiFi and clock ----------
    def wifi_creds(self):
        """(network name, password) this unit has saved; ('', '') = none yet."""
        ssid, pw = self.cfg["wifi"]["ssid"], self.cfg["wifi"]["password"]
        if not ssid:
            try:                              # during development: secrets.py
                import secrets
                ssid, pw = secrets.WIFI_SSID, secrets.WIFI_PASSWORD
            except (ImportError, AttributeError):
                pass
        return ssid or "", pw or ""

    def wifi_setup(self):
        ssid, pw = self.wifi_creds()
        if ssid:
            net.start_connect(ssid, pw)

    def every_second(self, now):
        for board in (self.gauges, self.controls):
            if board.check() == "new":
                board.forget()
                self._what = "board"
                print("%s board 0x%02X up (boot id %d) - sending everything"
                      % (board.name, board.addr, board.boot_id))
        state = net.status()
        if state != self.wifi_state:
            self.wifi_state = state
            self.update_leds()
        if state == "failed" and not self.wifi_busy \
                and time.ticks_diff(now, self.wifi_retry_at) >= 0:
            self.wifi_retry_at = time.ticks_add(now, WIFI_RETRY_S * 1000)
            self._what = "wifi"
            self.wifi_setup()
        if state == "up" and time.ticks_diff(now, self.ntp_next) >= 0 and (
                timeutil.last_sync is None or time.time() - timeutil.last_sync > NTP_EVERY_S):
            self._what = "ntp"
            if timeutil.sync(self.cfg["ntp_host"]):
                self.need_full = True             # the time on screen just jumped
            else:
                self.ntp_next = time.ticks_add(now, NTP_RETRY_S * 1000)
        # the mute icon (2026-10-26): shown whenever the chime wouldn't sound -
        # CHIME switch, WIFE MODE, quiet hours or chime mode off
        muted = self.chime_muted()
        if muted != self.ui.muted:
            self.ui.muted = muted
            self.need_full = True
        # the ISS listener: read whatever has arrived (never waits)
        if self.listener.poll() and self.screen.key == "overhead":
            self.need_full = True
        # the screen's own data waits until the user has stopped on it (FETCH_SETTLE_MS)
        rested = time.ticks_diff(now, self.last_input) >= FETCH_SETTLE_MS
        # weather: at most one request per second, only with WiFi and a real clock
        if state == "up" and timeutil.clock_set() and self.weather.due(time.time()):
            self._what = "weather"
            self.weather.update()
        elif state == "up" and timeutil.clock_set() and self.screen.key == "train" and rested \
                and self.trains.due(time.time()):
            self._what = "trains"
            self.trains.update()              # only while its screen is up; and elif, so
            #                                   there are never two requests in one second
        elif state == "up" and timeutil.clock_set() and self.screen.key == "overhead" and rested \
                and self.screen.page == "planes" and self.planes.due(time.time()):
            self._what = "planes"
            self.planes.update()
        elif state == "up" and timeutil.clock_set() and self.screen.key == "overhead" and rested \
                and self.screen.page == "iss" and self.iss.due(time.time()):
            self._what = "iss"
            self.iss.update()                 # the ISS page: only while it is showing
        elif state == "up" and timeutil.clock_set() and self.listener.want_pos:
            self._what = "iss heard"          # the ISS was just heard: where was it?
            ok = self.iss.update()
            self.listener.place(self.iss.now if ok else None)
        elif state == "up" and timeutil.clock_set() and self.ota.queue:
            self._what = "update"
            self.ota_light(now)               # light first: the request below can take seconds
            self.ota.step()                   # one file a second while an update is under way
        elif state == "up" and timeutil.clock_set() and self.listener.due():
            self._what = "iss listen"
            self.listener.connect()           # last in line: it can wait a few seconds
        if timeutil.clock_set():
            self.ota.nightly(self.local())
            if self.ota.trial and time.ticks_diff(now, self.started) > ota.CONFIRM_AFTER_S * 1000:
                self.ota.confirm()            # the new version has stayed up: it stands
        self.ota_light(now)
        self.update_data()

    def ota_light(self, now):
        """Send the OTA pilot light its mode when it changes. Fixed 2026-10-10 (5.13): a quick
        check began and ended inside one pass of every_second, so the light was only looked at
        after it was over and never came on. Now it is set before each request, and a check
        that is already over keeps blinking for OTA_LED_MIN_MS so it can be seen."""
        want = self.ota.led()
        if want:
            self._ota_led_until = time.ticks_add(now, OTA_LED_MIN_MS)
        elif self._ota_led and time.ticks_diff(now, self._ota_led_until) < 0:
            want = self._ota_led              # just finished: let it show a little longer
        if want != self._ota_led:
            self._ota_led = want
            self.update_leds()

    # ---------- inputs ----------
    def handle(self, ev):
        kind = ev[0]
        if kind == "switches":
            self.apply_switches(ev[1])
            return
        if kind == "audio_done":
            self._done_events += ev[1]
            return
        if kind == "restart":
            # the Controls board restarted: its pilot-light settings are gone
            # (the switch positions arrive as their own event right after)
            self.controls.forget()
            self.apply_lighting()
            return
        self.last_input = time.ticks_ms()
        if kind == "knob":
            if not self.screen.on_knob(self, ev[1]):
                self.step_ring(ev[1])
                self.settle_until = time.ticks_add(self.last_input, KNOB_SETTLE_MS)
        elif kind == "short":
            if not self.screen.on_press(self):
                self.open_home()
        elif kind == "long":
            self.toggle_diag()

    def touch(self):
        try:
            t = self.presto.touch_a
        except Exception:
            return
        if t.touched and not self._touching:
            self._touching = True
            self.last_input = time.ticks_ms()
            if not self.screen.on_touch(self, t.x, t.y):
                zone = U.UI.footer_zone(t.x, t.y)
                if zone == "prev":
                    self.step_ring(-1)
                elif zone == "next":
                    self.step_ring(1)
                elif zone == "menu":
                    self.open_home()
        elif not t.touched:
            self._touching = False

    # ---------- main loop ----------
    def start(self):
        try:
            for i in range(7):                # the back "glow" LEDs: off in a closed box
                self.presto.set_led_rgb(i, 0, 0, 0)
        except Exception:
            pass
        self.led_bright = self.cfg["bright_day"]["leds"]
        self.ota_bright = self.led_bright
        self.apply_lighting()
        self.wifi_setup()
        self.every_second(time.ticks_ms())
        now = time.ticks_ms()
        self.next_poll = self.next_sec = self.next_chime = now
        if self.wifi_creds()[0]:
            self.show(self.ring[0])
        else:
            self.wifi.open(self, first=True)  # no WiFi saved yet: the welcome page

    def step(self):
        now = time.ticks_ms()
        self._what = ""
        if time.ticks_diff(now, self.next_poll) >= 0:
            self.next_poll = time.ticks_add(now, POLL_MS)
            for ev in self.controls.poll():
                self.handle(ev)
            self.presto.touch_poll()
            self.touch()
        if time.ticks_diff(now, self.next_sec) >= 0:
            self.next_sec = time.ticks_add(self.next_sec, 1000)
            if time.ticks_diff(now, self.next_sec) > 0:      # fell behind: catch up
                self.next_sec = time.ticks_add(now, 1000)
            self.every_second(now)
        if time.ticks_diff(now, self.next_chime) >= 0:
            self.next_chime = time.ticks_add(now, CHIME_MS)
            if timeutil.clock_set():
                t = self.local()
                self.chime.tick(self.cfg, t, self.controls, self.chime_on,
                                self.wife_mode, self._done_events)
                if fitz_rules.due(self.cfg, t, self.fitz_year):
                    self.fitz_year = t[0]
                    self.start_fitz()
            self._done_events = 0
        # idle -> back to the Clock (not from Diagnostics)
        if self.screen is not self.ring[0] and self.screen is not self.diag \
                and not getattr(self.screen, "hold", False) and self.cfg["idle_s"] \
                and time.ticks_diff(now, self.last_input) > self.cfg["idle_s"] * 1000:
            self.go(0)
        self.sync_gauges()
        self.controls.sync()
        # screen
        if self.need_full and self.settle_until is not None \
                and time.ticks_diff(now, self.settle_until) < 0:
            pass                              # the knob is still turning: don't draw yet
        elif self.need_full:
            self.need_full = False
            self.settle_until = None
            if not self._what:
                self._what = "draw " + self.screen.key
            d0 = time.ticks_ms()
            self.screen.draw(self)
            self.presto.update()
            self.draw_ms = time.ticks_diff(time.ticks_ms(), d0)
        else:
            r = self.screen.tick(self, now)
            if r == "full":
                self.need_full = True
            elif r:
                self.presto.partial_update(*r)
        took = time.ticks_diff(time.ticks_ms(), now)
        self.loop_ms = took
        if took > self.loop_max_ms:
            self.loop_max_ms = took
            self.loop_max_what = self._what or "loop"
            self.loop_max_at = time.ticks_diff(now, self.started) // 1000
        if took < LOOP_MS:
            time.sleep_ms(LOOP_MS - took)

    def run(self):
        self.start()
        while True:
            self.step()
