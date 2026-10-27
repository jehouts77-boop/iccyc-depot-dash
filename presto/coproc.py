# coproc.py - the Presto's side of the co-processor protocol (iccyc-i2c-protocol.md v0.1)
#
# Two classes, one per board:
#   Gauges   (0x10) - write gauge setups, values, backlight, sweep
#   Controls (0x11) - read knob / button / switches / audio, drive the pilot
#                     lights and the chime
#
# The rules from the protocol doc that shape this code:
#   1. state, not commands - we write what we want; writing it again is harmless
#   2. counters, not events - differences are (new - old) & 0xFF
#   3. one group per transaction - each group is ONE writeto_mem call
#   5. after a board restarts (BOOT_ID changes) we re-send everything
# Plus the 2026-09-30 open item: a board that stops answering shows as
# MISSING (and is re-checked quietly once a second) instead of piling up
# bus errors 50 times a second.

import struct
import time

MAGIC = 0xC5
MISSING_AFTER = 3        # failed reads in a row before a board counts as missing


class Board:
    def __init__(self, i2c, addr, name):
        self.i2c = i2c
        self.addr = addr
        self.name = name
        self.present = False
        self.boot_id = None
        self.header = bytes(12)
        self.fw = None
        self.fails = 0            # failed transfers in a row
        self.bus_errors = 0       # failures while the board was present
        self.restarts = 0         # BOOT_ID changes seen
        self.next_try = 0         # ticks_ms: when to retry a missing board

    # -- low level --
    def _read(self, reg, n):
        try:
            b = self.i2c.readfrom_mem(self.addr, reg, n)
            self.fails = 0
            return b
        except OSError:
            self._failed()
            return None

    def _write(self, reg, data):
        if not self.present:
            return False
        try:
            self.i2c.writeto_mem(self.addr, reg, data)
            self.fails = 0
            return True
        except OSError:
            self._failed()
            return False

    def _failed(self):
        self.fails += 1
        if self.present:
            self.bus_errors += 1
            if self.fails >= MISSING_AFTER:
                self.present = False
                print("%s board (0x%02X) missing" % (self.name, self.addr))
        self.next_try = time.ticks_add(time.ticks_ms(), 1000)

    # -- header, about once a second --
    def check(self):
        """Read the header. Returns 'new' if the board (re)appeared or
        restarted - the caller must re-send everything - else None."""
        if not self.present and time.ticks_diff(time.ticks_ms(), self.next_try) < 0:
            return None
        h = self._read(0x00, 12)
        if h is None:
            return None
        if h[0] != MAGIC or h[1] != self.addr:
            self._failed()
            return None
        self.header = h
        self.fw = "%d.%d" % (h[3], h[4])
        was = self.present
        self.present = True
        if not was or h[11] != self.boot_id:
            if was:
                self.restarts += 1
            self.boot_id = h[11]
            return "new"
        return None

    # header fields for the diagnostics screen
    def heartbeat(self):
        return self.header[5]

    def fault(self):
        return self.header[7]

    def loop_ms(self):
        return self.header[8]

    def free_kb(self):
        return self.header[9]


class Gauges(Board):
    BLOCKS = (0x20, 0x60)

    def __init__(self, i2c, addr=0x10):
        super().__init__(i2c, addr, "Gauges")
        self._setups = [None, None]       # last setup bytes wanted, per gauge
        self._values = [None, None]
        self._texts = [b"", b""]          # readout text wanted (v0.2); b"" = the number
        self._sent_texts = [None, None]
        self._backlight = 255
        self._sweep = 0
        self._sent_setups = [None, None]  # what the board actually has
        self._sent_values = [None, None]
        self._sent_backlight = None

    @staticmethod
    def pack_setup(style=0, dec=0, vmin=0, vmax=100, major=11, minor=1, show=1, glide=40,
                   label="", units=""):
        b = bytearray(0x28)
        b[0], b[1] = style, dec
        struct.pack_into("<hh", b, 2, vmin, vmax)
        b[6], b[7], b[8], b[9] = major, minor, show, glide
        lab = label.encode()[:16] if isinstance(label, str) else label[:16]
        uni = units.encode()[:8] if isinstance(units, str) else units[:8]
        # MicroPython encodes "\xb0" as 2 UTF-8 bytes; the protocol wants 0xB0
        lab = lab.replace(b"\xc2\xb0", b"\xb0")
        uni = uni.replace(b"\xc2\xb0", b"\xb0")
        b[0x10:0x10 + len(lab)] = lab
        b[0x20:0x20 + len(uni)] = uni
        return bytes(b)

    def setup(self, i, **kw):
        self._setups[i] = self.pack_setup(**kw)

    def value(self, i, v):
        self._values[i] = max(-32768, min(32767, int(v)))

    def text(self, i, s):
        """Big readout shows this instead of the number ('' = the number). v0.2."""
        b = s.encode()[:9].replace(b"\xc2\xb0", b"\xb0")[:8] if isinstance(s, str) else s[:8]
        self._texts[i] = b

    def backlight(self, level):
        self._backlight = max(0, min(255, int(level)))

    def sweep(self):
        self._sweep = (self._sweep + 1) & 0xFF
        self._write(0x11, bytes((self._sweep,)))

    def forget(self):
        """After a restart: the board has none of our state any more."""
        self._sent_setups = [None, None]
        self._sent_values = [None, None]
        self._sent_texts = [None, None]
        self._sent_backlight = None

    def sync(self):
        """Send whatever changed since last time (setup before value)."""
        if not self.present:
            return
        for i in range(2):
            base = self.BLOCKS[i]
            s = self._setups[i]
            if s is not None and s != self._sent_setups[i]:
                if self._write(base, s):
                    self._sent_setups[i] = s
                    self._sent_values[i] = None     # re-send the value after a new setup
            t = self._texts[i]
            if t != self._sent_texts[i]:
                # one 8-byte write, zero-padded (empty = back to the number)
                if self._write(base + 0x28, t + bytes(8 - len(t))):
                    self._sent_texts[i] = t
            v = self._values[i]
            if v is not None and v != self._sent_values[i]:
                if self._write(base + 0x30, struct.pack("<h", v)):
                    self._sent_values[i] = v
        if self._backlight != self._sent_backlight:
            if self._write(0x10, bytes((self._backlight,))):
                self._sent_backlight = self._backlight

    def shown(self, i):
        b = self._read(self.BLOCKS[i] + 0x38, 2)
        return None if b is None else struct.unpack("<h", b)[0]


class Controls(Board):
    def __init__(self, i2c, addr=0x11, long_press_ms=800):
        super().__init__(i2c, addr, "Controls")
        self.long_press_ms = long_press_ms
        self.last = None               # last input block (10 bytes)
        self.switches = 0              # current switch bits (raw, 1 = closed)
        self.knob_total = 0            # running total since start (diagnostics)
        self.audio_state = 0
        self.clip_count = 0
        self.presses = 0
        self.long_presses = 0
        self._down_at = None
        self._long_fired = False
        self._play = 0
        self._stop = 0
        self._leds = None
        self._leds_sent = None
        self._audio_done = None
        self.done_count = 0            # clips finished since start

    def poll(self):
        """Read the input block and return a list of events:
        ("knob", clicks) ("short",) ("long",) ("switches", bits)
        ("audio_done", n) ("restart",)."""
        if not self.present:
            return []
        b = self._read(0x10, 10)
        if b is None:
            return []
        ev = []
        if self.last is None or b[9] != self.last[9]:
            # First read, or the board restarted (BOOT_ID copy at 0x19 changed):
            # its counters went back to 0, so take these values as the new
            # starting point instead of counting the jump (protocol v0.1).
            if self.last is not None:
                ev.append(("restart",))
            self.last = b
            self.switches = b[4]
            self.audio_state, self.clip_count = b[6], b[8]
            self._audio_done = b[7]
            self._down_at = time.ticks_ms() if b[3] else None
            self._long_fired = False
            ev.append(("switches", self.switches))
            return ev
        old = self.last
        self.last = b
        d = (b[0] - old[0]) & 0xFF
        if d:
            clicks = d - 256 if d > 127 else d
            self.knob_total += clicks
            ev.append(("knob", clicks))
        now = time.ticks_ms()
        downs = (b[1] - old[1]) & 0xFF
        ups = (b[2] - old[2]) & 0xFF
        if downs and self._down_at is None:
            self._down_at = now
            self._long_fired = False
        if self._down_at is not None and not self._long_fired and b[3] \
                and time.ticks_diff(now, self._down_at) >= self.long_press_ms:
            self._long_fired = True           # long press fires while still held
            self.long_presses += 1
            ev.append(("long",))
        if ups:
            if self._down_at is not None and not self._long_fired:
                self.presses += 1
                ev.append(("short",))
            # quick extra taps between polls: count each as a short press
            for _ in range(max(0, min(ups, downs) - 1)):
                self.presses += 1
                ev.append(("short",))
            self._down_at = now if b[3] else None
            self._long_fired = False
        if (b[5] - old[5]) & 0xFF or b[4] != self.switches:
            self.switches = b[4]
            ev.append(("switches", self.switches))
        self.audio_state, self.clip_count = b[6], b[8]
        dn = (b[7] - self._audio_done) & 0xFF
        if dn:
            self._audio_done = b[7]
            self.done_count += dn
            ev.append(("audio_done", dn))
        return ev

    # -- outputs --
    def leds(self, wifi_mode, ota_mode, bright, ota_bright=None):
        """bright = the WiFi light (0x22); ota_bright = the OTA light (0x23, Controls
        fw 0.5 and later; an older board ignores it and uses 0x22 for both)."""
        if ota_bright is None:
            ota_bright = bright
        clamp = lambda v: max(0, min(255, int(v)))
        self._leds = bytes((wifi_mode, ota_mode, clamp(bright), clamp(ota_bright)))

    def play(self, clip, volume):
        self._play = (self._play + 1) & 0xFF
        # CLIP, VOLUME and PLAY in one transaction (protocol rule 3)
        return self._write(0x30, bytes((clip, max(0, min(255, volume)), self._play)))

    def volume(self, volume):
        return self._write(0x31, bytes((max(0, min(255, volume)),)))

    def stop(self):
        self._stop = (self._stop + 1) & 0xFF
        return self._write(0x33, bytes((self._stop,)))

    def forget(self):
        """After a restart: the lights must be sent again. (The input counters
        re-baseline themselves in poll() via the BOOT_ID copy.)"""
        self._leds_sent = None

    def sync(self):
        if self.present and self._leds is not None and self._leds != self._leds_sent:
            if self._write(0x20, self._leds):
                self._leds_sent = self._leds

    def check(self):
        r = super().check()
        if r == "new" and self.present:
            # our PLAY/STOP counters must move from what the board holds now
            b = self._read(0x32, 2)
            if b is not None:
                self._play, self._stop = b[0], b[1]
        return r


LED_OFF, LED_ON, LED_SLOW, LED_FAST, LED_PULSE = 0, 1, 2, 3, 4
