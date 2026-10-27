# ui.py - drawing helpers for the Presto's 480x480 screen
#
# Look follows the Screen UX mockup (screen-ux\ in the project folder): near-
# black background, amber / brass text, a title strip at the top and a
# PREV / MENU / NEXT strip at the bottom (also the touch targets).
#
# Text (roadmap 5.15b, 2026-10-07): smooth type drawn by PicoVector from two
# font files in the Presto's /fonts folder, or in / (presto\fonts\ in the repo):
#   font "A"  Barlow Condensed Medium - everything
#   font "D"  Special Elite           - On This Day and the Fitzgerald screen
# Shapes are still plain PicoGraphics. Diagnostics and the crash screen keep
# the built-in bitmap8 font (btext): smooth text costs about 1-1.6 ms a
# character and Diagnostics redraws every second.
#
# text() takes a SIZE in pixels (not a scale) and y = the TOP of the capital
# letters; PicoVector itself wants the baseline, text() works that out.
# Word spacing is PicoVector's own default (a space drawn twice the font's
# width) - Jason's pick from renders\smooth_text_preview_2026-10-07_5_word_spacing.png.
# If PicoVector or a font file is missing, text() falls back to the built-in
# font so the unit still shows something (see font_error).

try:
    import os
except ImportError:
    os = None

W = H = 480
HEADER_H = 56
FOOTER_Y = 424
BODY_Y = HEADER_H + 8
BODY_H = FOOTER_Y - BODY_Y - 8

COLOURS = {
    "bg": (10, 7, 5),
    "panel": (28, 20, 12),
    "amber": (232, 176, 75),
    "text": (217, 154, 74),
    "dim": (140, 100, 50),
    "cream": (240, 225, 190),
    "red": (225, 60, 40),
    "green": (90, 200, 120),
    "line": (70, 50, 25),
    "face": (50, 30, 10),      # dial colours, as picked on the gauges (roadmap 1.8b)
    "brass": (200, 135, 45),
}

DEG = "\xb0"

FONTS = {"A": "BarlowCondensed-Medium.af", "D": "SpecialElite-Regular.af"}
CAP = {"A": 0.65, "D": 0.67}      # height of a capital letter / font size

# type sizes used across the screens (pixels; a capital is about 2/3 of this)
T_NOTE = 22
T_BODY = 26
T_HEAD = 36


class UI:
    def __init__(self, display):
        self.d = display
        self.muted = False         # set by the app each frame: draws the mute icon in headers
        self.pens = {k: display.create_pen(*rgb) for k, rgb in COLOURS.items()}
        try:
            display.set_font("bitmap8")
        except Exception:
            pass
        self.v = None                 # PicoVector, or None = built-in font only
        self.font_error = ""
        self.files = {}               # font -> the path it was found at
        self._font = None             # font and size PicoVector is set to now
        self._size = 0
        self._clip = None
        try:
            for k in FONTS:           # in /fonts (where updates put them) or in /
                name = FONTS[k]
                try:
                    os.stat("fonts/" + name)
                    self.files[k] = "fonts/" + name
                except OSError:
                    os.stat(name)     # OSError if the font file isn't on the Presto
                    self.files[k] = name
            from picovector import PicoVector, Transform, ANTIALIAS_BEST
            v = PicoVector(display)
            v.set_antialiasing(ANTIALIAS_BEST)
            v.set_transform(Transform())
            self.v = v
        except Exception as e:
            self.font_error = "FONTS: %s: %s" % (type(e).__name__, e)
            print(self.font_error)

    def pen(self, name):
        self.d.set_pen(self.pens[name])

    def clear(self):
        self.pen("bg")
        self.d.clear()

    def rect(self, x, y, w, h, colour):
        self.pen(colour)
        self.d.rectangle(x, y, w, h)

    def mute_icon(self, x, y, s, colour):
        """A speaker with a small X beside it (the chime is muted), s pixels
        tall, top-left at (x, y). Plain shapes (2026-10-26)."""
        d = self.d
        self.pen(colour)
        d.rectangle(int(x), int(y + s * 0.32), max(2, int(s * 0.22)), max(2, int(s * 0.36)))
        d.polygon([(int(x + s * 0.18), int(y + s * 0.32)), (int(x + s * 0.5), int(y)),
                   (int(x + s * 0.5), int(y + s)), (int(x + s * 0.18), int(y + s * 0.68))])
        t = max(2, int(s / 9 + 0.5))
        a, b = x + s * 0.66, x + s * 1.02
        d.line(int(a), int(y + s * 0.3), int(b), int(y + s * 0.7), t)
        d.line(int(a), int(y + s * 0.7), int(b), int(y + s * 0.3), t)

    # ---------- clip box (the Clock's seconds hand redraws only a small box) ----------
    def clip(self, box):
        self._clip = box
        self.d.set_clip(*box)
        if self.v is not None:
            self.v.set_clip(tuple(box))

    def unclip(self):
        self._clip = None
        self.d.remove_clip()
        if self.v is not None:
            self.v.set_clip(None)         # None = the whole screen

    # ---------- smooth text ----------
    def _use(self, font, size):
        # set_font() reads the whole font file again, so only call it when the
        # typeface really changes; a new size alone is cheap
        if font != self._font:
            self.v.set_font(self.files[font], size)
            self._font, self._size = font, size
        elif size != self._size:
            self.v.set_font_size(size)
            self._size = size

    @staticmethod
    def _scale(size):
        """Built-in font scale that comes closest to a smooth size (fallback)."""
        return max(1, (size + 5) // 11)

    def text_w(self, s, size, font="A"):
        """Width in pixels."""
        if self.v is None:
            return self.btext_w(s, self._scale(size))
        if not s:
            return 0
        self._use(font, size)
        return int(self.v.measure_text(s)[2])

    def text(self, s, x, y, size=T_BODY, colour="text", align="left", font="A", max_w=0):
        """Draw one line. y = top of the capitals. max_w (left-aligned text
        only): draw only the words that fit in that many pixels.
        Returns the x just past the text."""
        if self.v is None:
            return self.btext(s, x, y, self._scale(size), colour, align)
        if not s:
            return x
        c = self._clip
        if c is not None:
            # redrawing a small box: skip text that can't be inside it (this
            # check costs nothing; drawing or measuring the text would)
            reach = len(s) * size
            if y > c[1] + c[3] or y + size < c[1] or x - reach > c[0] + c[2] or x + reach < c[0]:
                return x
        self._use(font, size)
        w = 0
        if align != "left" or not max_w:
            w = int(self.v.measure_text(s)[2])
        if align == "center":
            x -= w // 2
        elif align == "right":
            x -= w
        self.pen(colour)
        base = int(y + size * CAP[font] + 0.5)
        if max_w:
            self.v.text(s, int(x), base, max_width=int(max_w), max_height=int(size * 1.5))
        else:
            self.v.text(s, int(x), base)
        return int(x) + w

    def wrap(self, text, size, max_w, font="A"):
        """Split text into lines no wider than max_w pixels."""
        if self.v is None:
            sc = self._scale(size)
            fits = lambda t: self.btext_w(t, sc) <= max_w
        else:
            self._use(font, size)
            fits = lambda t: self.v.measure_text(t)[2] <= max_w
        lines, line = [], ""
        for word in text.split():
            trial = word if not line else line + " " + word
            if line and not fits(trial):
                lines.append(line)
                line = word
            else:
                line = trial
        if line:
            lines.append(line)
        return lines

    def block(self, text, cx, top, bottom, sizes, colour, font="A", max_w=W - 32):
        """A paragraph, centred left-to-right and top-to-bottom between top and
        bottom, in the first of `sizes` that fits."""
        for size in sizes:
            pitch = int(size * 1.25)
            lines = self.wrap(text, size, max_w, font)
            if len(lines) * pitch <= bottom - top:
                break
        y = top + (bottom - top - len(lines) * pitch) // 2 + (pitch - int(size * CAP[font])) // 2
        for ln in lines:
            self.text(ln, cx, y, size, colour, "center", font)
            y += pitch

    # ---------- built-in bitmap8 text (Diagnostics, fallback) ----------
    def btext_w(self, s, scale):
        """Width in pixels, counting a degree sign as a small ring."""
        w = 0
        for i, part in enumerate(s.split(DEG)):
            if i:
                w += 3 * scale
            if part:
                w += self.d.measure_text(part, scale)
        return w

    def btext(self, s, x, y, scale=2, colour="text", align="left", wrap=2000):
        # wrap: PicoGraphics wraps text at this x width; 2000 = never on a 480 screen
        if align == "center":
            x -= self.btext_w(s, scale) // 2
        elif align == "right":
            x -= self.btext_w(s, scale)
        self.pen(colour)
        for i, part in enumerate(s.split(DEG)):
            if i:                                  # degree sign: a small ring
                r = max(1, scale)
                self.d.circle(x + r + 1, y + r + 1, r + 1)
                self.pen("bg")
                self.d.circle(x + r + 1, y + r + 1, max(0, r - 1))
                self.pen(colour)
                x += 3 * scale
            if part:
                self.d.text(part, x, y, wrap, scale)
                x += self.d.measure_text(part, scale)
        return x

    # ---------- the strips at the top and bottom ----------
    def header(self, title, right="", plain=False):
        """plain = built-in font (Diagnostics)."""
        self.rect(0, 0, W, HEADER_H, "panel")
        self.rect(0, HEADER_H - 2, W, 2, "line")
        if plain:
            self.btext(title, 16, 16, 3, "amber")
            if right:
                self.btext(right, W - 16, 22, 2, "dim", "right")
            return
        self.text(title, 16, 16, T_HEAD, "amber")
        rx = W - 16
        if right:
            rx = self.text(right, W - 16, 20, T_BODY, "dim", "right") - self.text_w(right, T_BODY)
        if self.muted:                     # the chime is muted: a small icon left of the clock
            self.mute_icon(rx - 38, 18, 22, "dim")

    def footer(self, prev_name, next_name):
        self.rect(0, FOOTER_Y, W, H - FOOTER_Y, "panel")
        self.rect(0, FOOTER_Y, W, 2, "line")
        y = FOOTER_Y + 20
        self.text("< " + prev_name, 14, y, T_BODY, "dim")
        self.text("MENU", W // 2, y, T_BODY, "amber", "center")
        self.text(next_name + " >", W - 14, y, T_BODY, "dim", "right")

    def hint(self, s, plain=False):
        """A one-line footer without buttons (Home menu, Diagnostics)."""
        self.rect(0, FOOTER_Y, W, H - FOOTER_Y, "panel")
        if plain:
            self.btext(s, W // 2, FOOTER_Y + 20, 2, "dim", "center")
        else:
            self.text(s, W // 2, FOOTER_Y + 20, T_NOTE, "dim", "center")

    @staticmethod
    def footer_zone(x, y):
        """Which footer button a touch hit: 'prev', 'menu', 'next' or None."""
        if y < FOOTER_Y:
            return None
        if x < W // 3:
            return "prev"
        if x < 2 * W // 3:
            return "menu"
        return "next"
