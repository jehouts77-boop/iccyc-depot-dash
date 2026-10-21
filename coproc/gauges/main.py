# main.py - ICCYC Depot Dashboard, Gauges co-processor (0x10) firmware v1.1
#
# Runs on the RP2040-Zero at I2C address 0x10. Drives both round GC9A01 gauge
# screens and follows the Presto over I2C, using the Gauges part of
# iccyc-i2c-protocol.md (v0.2):
#
#   0x00-0x0B  header (magic, board, versions, heartbeat, flags, fault,
#              loop ms, free KB, write count, boot id)
#   0x10       BACKLIGHT  0 = both screens off (display-off command 28h);
#                         1-255 = on, colours scaled to this brightness
#   0x11       SWEEP      counter: each change = full-scale needle sweep
#   0x20-0x5F  Gauge I block, 0x60-0x9F Gauge II block:
#     +0x00 STYLE (0 dial, 1 compass)  +0x01 DECIMALS (0-2)
#     +0x02 MIN (s16)  +0x04 MAX (s16)  +0x06 MAJOR_TICKS  +0x07 MINOR_TICKS
#     +0x08 SHOW (bit0 readout, bit1 numbered ticks)  +0x09 GLIDE
#     +0x10 LABEL (16 chars)  +0x20 UNITS (8 chars, 0xB0 = degree sign)
#     +0x28 READOUT_TEXT (8 chars, v0.2): if not empty, shown in the big
#           readout INSTEAD of the number (e.g. a compass pointing at the
#           wind with "12 MPH" under it). Empty (first byte 0) = the number.
#     +0x30 VALUE (s16)       +0x38 SHOWN (s16, written by this board)
#
# v1.1 (2026-09-30): READOUT_TEXT added. v1.0: first full-protocol version.
#
# Built on the partial-redraw method confirmed on hardware 2026-09-30
# (validation\gauge_partial_test.py): only the rectangle around the old + new
# needle (and the readout when it changes) is sent to the screen.
#
# Keep this firmware "dumb": it only draws what the Presto asks for. What a
# gauge shows, and when, is decided on the Presto (which can update over WiFi).
#
# Board files needed: /main.py (this file), /drivers/boolpalette.py,
# /drivers/gc9a01/gc9a01.py (same driver files as the validation scripts).

import gc
import os
import time
import math
import struct
from array import array
import machine
from machine import Pin, SPI

ADDR = 0x10
FW_MAJOR, FW_MINOR = 1, 1
CPU_HZ = 200_000_000     # tested clean 2026-09-29
SPI_BAUD = 60_000_000    # tested clean 2026-09-29
FLIP_Y = False           # confirmed 2026-09-30 (red square showed upper-left)
GLIDE_MS_PER_UNIT = 7.5  # GLIDE register -> ms: default 40 = 300 ms (picked 2026-09-30)
SWEEP_MS = 1400          # each half of the startup / SWEEP needle sweep
FRAME_MS = 10            # shortest frame; the loop sleeps if a frame is quicker

PIN_SCK, PIN_MOSI = 2, 3
GAUGE_PINS = ((4, 5, 6), (7, 8, 9))   # (cs, dc, rst) for Gauge I, Gauge II

# ---- Registers ----
R_MAGIC, R_BOARD, R_PROTO, R_FW_MAJ, R_FW_MIN = 0x00, 0x01, 0x02, 0x03, 0x04
R_HEARTBEAT, R_FLAGS, R_FAULT, R_LOOP_MS, R_FREE_KB = 0x05, 0x06, 0x07, 0x08, 0x09
R_WRITES, R_BOOT_ID = 0x0A, 0x0B
R_BACKLIGHT, R_SWEEP = 0x10, 0x11
BLOCKS = (0x20, 0x60)
O_STYLE, O_DEC, O_MIN, O_MAX, O_MAJOR, O_MINOR, O_SHOW, O_GLIDE = 0, 1, 2, 4, 6, 7, 8, 9
O_LABEL, O_UNITS, O_TEXT, O_VALUE, O_SHOWN = 0x10, 0x20, 0x28, 0x30, 0x38
SETUP_LEN = 0x28                      # +0x00-0x27: the setup (not TEXT / VALUE / SHOWN)
FAULT_SCREEN, FAULT_MEMORY, FAULT_SETUP = 1, 2, 3

mem = bytearray(256)
mem[R_MAGIC], mem[R_BOARD], mem[R_PROTO] = 0xC5, ADDR, 0
mem[R_FW_MAJ], mem[R_FW_MIN] = FW_MAJOR, FW_MINOR
mem[R_BOOT_ID] = os.urandom(1)[0]
mem[R_BACKLIGHT] = 255


def put_s16(off, v):
    struct.pack_into("<h", mem, off, v)


# Power-up defaults (protocol): dial, 0-100, 11 long ticks, labels, value 0
for i, base in enumerate(BLOCKS):
    mem[base + O_STYLE] = 0
    mem[base + O_DEC] = 0
    put_s16(base + O_MIN, 0)
    put_s16(base + O_MAX, 100)
    mem[base + O_MAJOR] = 11
    mem[base + O_MINOR] = 1
    mem[base + O_SHOW] = 1
    mem[base + O_GLIDE] = 40
    lab = b"GAUGE I" if i == 0 else b"GAUGE II"
    mem[base + O_LABEL:base + O_LABEL + len(lab)] = lab

# Everything the Presto writes (0x10-0x9F) is copied here when a write
# transaction ENDS, and the loop only reads the copy - so a half-written group
# is never acted on (protocol rule 3).
SHADOW_START, SHADOW_END = 0x10, 0xA0
shadow = bytearray(mem[SHADOW_START:SHADOW_END])
shadow_new = False


def on_write(t):
    global shadow_new
    shadow[:] = mem[SHADOW_START:SHADOW_END]
    shadow_new = True
    mem[R_WRITES] = (mem[R_WRITES] + 1) & 0xFF


def sh(reg):                     # shadow byte by register number
    return shadow[reg - SHADOW_START]


def sh_s16(reg):
    return struct.unpack_from("<h", shadow, reg - SHADOW_START)[0]


# ---- Screens ----
machine.freq(CPU_HZ)
spi = SPI(0, baudrate=SPI_BAUD, sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=None)
from drivers.gc9a01.gc9a01 import GC9A01 as SSD, _lcopy   # 4-bit colour driver
import framebuf

W = H = 240
CX = CY = 120
displays = []
try:
    for cs, dc, rst in GAUGE_PINS:
        displays.append(SSD(spi, Pin(cs, Pin.OUT, value=1), Pin(dc, Pin.OUT, value=0),
                            Pin(rst, Pin.OUT, value=1)))
        gc.collect()
    # one plain background frame per gauge: face, ticks, numbers, label
    backgrounds = [framebuf.FrameBuffer(bytearray(W * H // 2), W, H, framebuf.GS4_HMSB)
                   for _ in displays]
except Exception as e:
    print("screen start failed:", e)
    mem[R_FAULT] = FAULT_SCREEN

# ---- Colours: 4-bit mode = a 16-entry lookup table, picked on the real panel
# 2026-09-30 (roadmap 1.8b). BACKLIGHT 1-254 scales them down.
PALETTE = (
    ("bg", (0, 0, 0)),
    ("face", (50, 30, 10)),
    ("rim", (200, 135, 45)),
    ("tick", (240, 225, 190)),
    ("needle", (225, 60, 40)),
    ("text", (240, 225, 190)),
    ("hub", (200, 135, 45)),
    ("north", (225, 60, 40)),
)
C = {name: i for i, (name, _) in enumerate(PALETTE)}


def set_brightness(level):
    k = level / 255
    for i, (_, (r, g, b)) in enumerate(PALETTE):
        c = SSD.rgb(int(r * k), int(g * k), int(b * k))
        SSD.lut[i * 2] = c & 0xFF
        SSD.lut[i * 2 + 1] = c >> 8


# ---- Drawing ----
R_RIM, R_FACE = 118, 110
LABEL_Y = 150
READ_Y_DIAL = 186                # readout (2x text, 16 px tall): below the end numbers
READ_Y_COMPASS = 162             # compass: between the label and the S
READ_H = 16
RD_CHARS = 8                     # readout: up to 8 characters at 2x (128 px)


def polar(r, deg):
    a = math.radians(deg)
    return int(CX + r * math.sin(a) + 0.5), int(CY - r * math.cos(a) + 0.5)


_glyph = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_HLSB)


def text2x(fb, s, x, y, c):
    """Built-in 8x8 font drawn at double size (16 px tall)."""
    for ch in s:
        _glyph.fill(0)
        if ch == "\xb0":                  # degree sign: a small ring
            _glyph.ellipse(3, 2, 2, 2, 1)
        else:
            _glyph.text(ch, 0, 0, 1)
        for gy in range(8):
            for gx in range(8):
                if _glyph.pixel(gx, gy):
                    fb.fill_rect(x + gx * 2, y + gy * 2, 2, 2, c)
        x += 16


def text1x(fb, s, x, y, c):
    for ch in s:
        if ch == "\xb0":
            fb.ellipse(x + 3, y + 2, 2, 2, c)
        else:
            fb.text(ch, x, y, c)
        x += 8


def cstr(b):
    """Zero-padded bytes -> str (0xB0 kept as the degree sign)."""
    out = []
    for v in b:
        if v == 0:
            break
        out.append(chr(v) if 32 <= v < 127 or v == 0xB0 else "?")
    return "".join(out)


class Gauge:
    def __init__(self, idx):
        self.idx = idx
        self.base = BLOCKS[idx]
        self.setup = None                 # last good setup bytes
        self.style = 0
        self.dec = 0
        self.vmin, self.vmax = 0, 100
        self.label, self.units = "", ""
        self.show = 1
        self.tau = 300
        self.shown = 0.0                  # needle position now (0-1 dial / degrees compass)
        self.drawn_pos = 0.0              # needle position on the screen
        self.target = 0.0
        self.drawn_text = None
        self.rd_text = None
        self.rd_fb = framebuf.FrameBuffer(bytearray(RD_CHARS * 16 * READ_H // 2),
                                          RD_CHARS * 16, READ_H, framebuf.GS4_HMSB)

    # -- setup --
    def check_setup(self):
        """Apply the shadow setup block if it changed. Returns True if applied."""
        b = bytes(shadow[self.base - SHADOW_START:self.base - SHADOW_START + SETUP_LEN])
        if b == self.setup:
            return False
        style, dec = b[O_STYLE], b[O_DEC]
        vmin, vmax = struct.unpack_from("<hh", b, O_MIN)
        major, minor = b[O_MAJOR], b[O_MINOR]
        if style > 1 or dec > 2 or (style == 0 and (vmin >= vmax or major < 2)) \
                or major > 37 or minor > 9:
            self.setup = b                # remember, so it isn't re-checked every frame
            mem[R_FAULT] = FAULT_SETUP    # keep the last good setup (protocol)
            return False
        self.setup = b
        self.style, self.dec = style, dec
        self.vmin, self.vmax = vmin, vmax
        self.major, self.minor, self.show = major, minor, b[O_SHOW]
        self.tau = b[O_GLIDE] * GLIDE_MS_PER_UNIT
        self.label = cstr(b[O_LABEL:O_LABEL + 16])
        self.units = cstr(b[O_UNITS:O_UNITS + 8])
        if mem[R_FAULT] == FAULT_SETUP:
            mem[R_FAULT] = 0
        self.draw_background()
        self.target = self.pos_of(sh_s16(self.base + O_VALUE))
        self.shown = self.target if self.style == 1 else min(max(self.shown, 0.0), 1.0)
        self.drawn_pos = self.shown
        self.drawn_text = None
        return True

    def read_y(self):
        return READ_Y_COMPASS if self.style == 1 else READ_Y_DIAL

    def pos_of(self, value):
        if self.style == 1:
            return value % 360
        f = (value - self.vmin) / (self.vmax - self.vmin)
        return min(max(f, 0.0), 1.0)

    def value_of(self, pos):
        if self.style == 1:
            return int(pos % 360 + 0.5) % 360
        return math.floor(self.vmin + pos * (self.vmax - self.vmin) + 0.5)

    def angle(self, pos):
        return pos if self.style == 1 else -135.0 + 270.0 * pos

    def fmt(self, v):
        s = "%d" % abs(v)
        if self.dec:
            s = "0" * max(0, self.dec + 1 - len(s)) + s
            s = s[:-self.dec] + "." + s[-self.dec:]
        return ("-" if v < 0 else "") + s + self.units

    def draw_background(self):
        fb = backgrounds[self.idx]
        fb.fill(C["bg"])
        fb.ellipse(CX, CY, R_RIM, R_RIM, C["rim"], True)
        fb.ellipse(CX, CY, R_FACE, R_FACE, C["face"], True)
        if self.style == 1:
            majors = [i * 90 for i in range(4)]
            steps = 4 * (self.minor + 1)
            for k in range(steps):
                deg = 360 * k / steps
                r_in = 90 if k % (self.minor + 1) == 0 else 98
                self._tick(fb, deg, r_in)
            for deg, letter in zip(majors, "NESW"):
                x, y = polar(74, deg)
                text2x(fb, letter, x - 8, y - 8, C["north"] if letter == "N" else C["tick"])
        else:
            n = self.major - 1
            steps = n * (self.minor + 1)
            for k in range(steps + 1):
                deg = -135.0 + 270.0 * k / steps
                major = k % (self.minor + 1) == 0
                self._tick(fb, deg, 88 if major else 97)
                if major and self.show & 2:
                    v = self.vmin + (self.vmax - self.vmin) * (k // (self.minor + 1)) // n
                    s = self.fmt(v)[:-len(self.units)] if self.units else self.fmt(v)
                    x, y = polar(74, deg)
                    text1x(fb, s, x - len(s) * 4, y - 4, C["text"])
        lab = self.label
        text1x(fb, lab, CX - len(lab) * 4, LABEL_Y, C["text"])

    def _tick(self, fb, deg, r_in):
        x0, y0 = polar(r_in, deg)
        x1, y1 = polar(104, deg)
        fb.line(x0, y0, x1, y1, C["tick"])
        fb.line(x0 + 1, y0, x1 + 1, y1, C["tick"])

    # -- per frame --
    def needle_box(self, pos):
        deg = self.angle(pos)
        pts = (polar(92, deg), polar(6, deg - 90), polar(6, deg + 90))
        return (min(p[0] for p in pts + ((CX - 9, 0),)) - 2,
                min(p[1] for p in pts + ((0, CY - 9),)) - 2,
                max(p[0] for p in pts + ((CX + 9, 0),)) + 2,
                max(p[1] for p in pts + ((0, CY + 9),)) + 2)

    def readout(self):
        """The number under the needle: the value the Presto sent (the needle
        glides to it; the readout doesn't count up through every step)."""
        if not self.show & 1:
            return ""
        t = self.base + O_TEXT - SHADOW_START
        if shadow[t]:                          # READOUT_TEXT set: show it instead
            return cstr(shadow[t:t + 8])
        v = sh_s16(self.base + O_VALUE)
        if self.style == 1:
            v %= 360
        else:
            v = min(max(v, self.vmin), self.vmax)
        return self.fmt(v)

    def compose(self, pos):
        """Background + readout + needle into the screen's frame buffer."""
        d = displays[self.idx]
        d.blit(backgrounds[self.idx], 0, 0)
        s = self.readout()
        if s:
            if s != self.rd_text:             # draw the 2x text once per change
                self.rd_text = s
                self.rd_fb.fill(0)
                text2x(self.rd_fb, s[:RD_CHARS], 0, 0, C["text"])
            w = min(len(s), RD_CHARS) * 16
            d.blit(self.rd_fb, CX - w // 2, self.read_y(), 0)   # colour 0 = see-through
        deg = self.angle(pos)
        tx, ty = polar(92, deg)
        lx, ly = polar(6, deg - 90)
        rx, ry = polar(6, deg + 90)
        needle_pts[0], needle_pts[1], needle_pts[2] = tx, ty, lx
        needle_pts[3], needle_pts[4], needle_pts[5] = ly, rx, ry
        d.poly(0, 0, needle_pts, C["needle"], True)
        d.ellipse(CX, CY, 9, 9, C["hub"], True)
        return s


needle_pts = array("h", [0] * 6)


def readout_box(s, y):
    w = min(len(s), RD_CHARS) * 16
    return (CX - w // 2 - 2, y, CX + w // 2 + 1, y + READ_H - 1)


def union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def set_window(d, x0, y0, x1, y1):
    if FLIP_Y:
        y0, y1 = H - 1 - y1, H - 1 - y0
    d._wcd(b"\x2a", bytes((0, x0, 0, x1)))
    d._wcd(b"\x2b", bytes((0, y0, 0, y1)))


def send_rect(d, box):
    x0 = max(0, box[0]) & ~1
    x1 = min(W - 1, box[2]) | 1
    y0 = max(0, box[1])
    y1 = min(H - 1, box[3])
    if x1 < x0 or y1 < y0:
        return 0
    set_window(d, x0, y0, x1, y1)
    d._wcmd(b"\x2c")
    d._dc(1)
    d._cs(0)
    nbytes = (x1 - x0 + 1) // 2
    lb = d._linebuf
    out = memoryview(lb)[: nbytes * 4]
    buf = d.mvb
    lut = SSD.lut
    rows = range(y1, y0 - 1, -1) if FLIP_Y else range(y0, y1 + 1)
    for y in rows:
        _lcopy(lb, buf[y * (W // 2) + x0 // 2:], lut, nbytes, False)
        d._spi.write(out)
    d._cs(1)
    return (x1 - x0 + 1) * (y1 - y0 + 1)


def full_show(d):
    set_window(d, 0, 0, W - 1, H - 1)
    d.show()


# ---- Running state ----
gauges = [Gauge(i) for i in range(len(displays))]
brightness = -1                  # forces the first apply
screens_on = True
last_sweep = None
sweep_t0 = None                  # ticks_ms when a sweep started (None = no sweep)


def apply_backlight(level):
    """0 = display off (28h), 1-255 = on at that colour brightness."""
    global brightness, screens_on
    if level == 0:
        if screens_on:
            for d in displays:
                d._wcmd(b"\x28")
            screens_on = False
        brightness = 0
        return
    wake = not screens_on
    if wake:
        for d in displays:
            d._wcmd(b"\x29")         # back on at once
        screens_on = True
    if level != brightness or wake:
        # (on waking, re-send everything: needles kept moving while it was dark)
        if level != brightness:
            set_brightness(level)
            brightness = level
        redraw_all()


def redraw_all():
    for g in gauges:
        s = g.compose(g.shown)
        g.drawn_text = s
        g.drawn_pos = g.shown
        full_show(displays[g.idx])


def sweep_pos(g, t):
    """Needle position during a sweep, t = ms since it started."""
    p = t / SWEEP_MS
    p = p if p <= 1 else 2 - p
    p = (1 - math.cos(math.pi * p)) / 2          # ease in and out
    return p * 359.9 if g.style == 1 else p


def start():
    global last_sweep, sweep_t0
    for g in gauges:
        g.check_setup()
    apply_backlight(sh(R_BACKLIGHT))
    last_sweep = sh(R_SWEEP)
    sweep_t0 = time.ticks_ms()                   # power-up sweep (protocol)
    mem[R_FLAGS] = 0x01                          # READY


def frame(now, dt):
    """One pass: setup, backlight, sweep, glide, partial redraw. Returns px sent."""
    global shadow_new, last_sweep, sweep_t0
    sent = 0
    if shadow_new:
        shadow_new = False
        full = False
        for g in gauges:
            if g.check_setup():
                full = True
                s = g.compose(g.shown)
                g.drawn_text = s
                g.drawn_pos = g.shown
                if screens_on and brightness > 0:
                    full_show(displays[g.idx])
                    sent += W * H
        if sh(R_SWEEP) != last_sweep:
            last_sweep = sh(R_SWEEP)
            sweep_t0 = now
        apply_backlight(sh(R_BACKLIGHT))
    sweeping = None
    if sweep_t0 is not None:
        sweeping = time.ticks_diff(now, sweep_t0)
        if sweeping >= 2 * SWEEP_MS:
            sweep_t0 = sweeping = None       # done: needles glide to their values
    for g in gauges:
        base = g.base
        if sweeping is not None:
            new = sweep_pos(g, sweeping)
        else:
            target = g.pos_of(sh_s16(base + O_VALUE))
            if g.style == 1:                     # compass: go the short way round
                diff = (target - g.shown + 540) % 360 - 180
                target = g.shown + diff
            a = 1.0 if g.tau <= 0 else 1.0 - math.exp(-dt / g.tau)
            new = g.shown + (target - g.shown) * a
            if abs(target - new) < (0.5 if g.style == 1 else 0.002):
                new = target
        if g.style == 1:
            new %= 360
        g.shown = new
        struct.pack_into("<h", mem, base + O_SHOWN, g.value_of(new))
        # redraw only when the needle moved a visible amount or the text changed
        moved = abs(((new - g.drawn_pos + 540) % 360 - 180) if g.style == 1
                    else new - g.drawn_pos) >= (0.3 if g.style == 1 else 0.001)
        txt = g.readout()
        if not moved and txt == g.drawn_text:
            continue
        box = union(g.needle_box(g.drawn_pos), g.needle_box(new))
        s = g.compose(new)
        if s != g.drawn_text:
            box2 = union(readout_box(g.drawn_text or "", g.read_y()), readout_box(s, g.read_y()))
        else:
            box2 = None
        g.drawn_pos = new
        g.drawn_text = s
        if screens_on and brightness > 0:
            d = displays[g.idx]
            sent += send_rect(d, box)
            if box2:
                sent += send_rect(d, box2)
    return sent


def run():
    t_last = t_mem = time.ticks_ms()
    while True:
        now = time.ticks_ms()
        dt = time.ticks_diff(now, t_last)
        t_last = now
        try:
            frame(now, dt)
        except MemoryError:
            mem[R_FAULT] = FAULT_MEMORY
            gc.collect()
        mem[R_HEARTBEAT] = (mem[R_HEARTBEAT] + 1) & 0xFF
        if time.ticks_diff(now, t_mem) > 1000:
            t_mem = now
            gc.collect()
            mem[R_FREE_KB] = min(255, gc.mem_free() // 1024)
        took = time.ticks_diff(time.ticks_ms(), now)
        mem[R_LOOP_MS] = min(255, took)
        if took < FRAME_MS:
            time.sleep_ms(FRAME_MS - took)


from machine import I2CTarget
i2c = I2CTarget(0, ADDR, sda=Pin(0), scl=Pin(1), mem=mem)
i2c.irq(on_write, trigger=I2CTarget.IRQ_END_WRITE, hard=False)

if displays and mem[R_FAULT] != FAULT_SCREEN:
    start()
    print("Gauges fw %d.%d at 0x%02X, boot id %d, free %d"
          % (FW_MAJOR, FW_MINOR, ADDR, mem[R_BOOT_ID], gc.mem_free()))
    if "_SIM" not in globals():          # the desktop simulator drives frames itself
        run()
else:
    mem[R_FLAGS] = 0x02                   # FAULT: screens didn't start; I2C still answers
    while "_SIM" not in globals():
        mem[R_HEARTBEAT] = (mem[R_HEARTBEAT] + 1) & 0xFF
        time.sleep_ms(10)
