# coproc/controls/main.py - the Controls co-processor (0x11) firmware, fw 0.5.
# fw 0.5 (2026-10-26): the OTA light gets its own brightness, register 0x23 LED_OTA_BRIGHT
# (protocol v0.3); 0x22 LED_BRIGHT is now the WiFi light only. The green OTA LED is much
# brighter than the amber WiFi one at the same setting (found on the first assembled unit).
# 0x23 starts at 255 like 0x22; the Presto writes both. Nothing else changed.
# fw 0.4 (2026-10-25): pins moved for the hub PCB rev A. The board's 5-pin socket under each Zero
# sits one row too low for the real Zero, so it stays empty and the pilot lights and amp move to
# side pins, joined to the old holes by five short wires (hub-revA-rework.md). Only the two pin
# lines below changed. fw 0.3 (GP9-GP13) stays on the breadboard desk rig.
# Added to the repo 2026-10-14 exactly as it runs on the boards: it began as the
# validation script controls_test.py (header below) and was confirmed on hardware
# 2026-09-30. It implements the whole Controls part of docs/i2c-protocol.md.
# Copy it to the 0x11 board as main.py, plus the clips/ folder as /clips.
#
# controls_test.py - ICCYC Depot Dashboard, roadmap VAL steps 1.4 / 1.9 / 1.10
#
# THROWAWAY VALIDATION SCRIPT - runs on Co-processor B (Controls), an RP2040-Zero.
# Reads the knob (EC11 encoder + push button) and the 4 toggle switches, drives
# the 2 pilot lights, plays chime clips from its own flash, and exposes all of
# it over I2C at 0x11 using the register layout from iccyc-i2c-protocol.md
# (v0.1) - so this doubles as a first draft of the real Controls firmware.
#
# Rev 2026-09-29 (protocol v0.1): BOOT_ID is also copied to 0x19, inside the
# input block, so the Presto sees a restart on the same read as the counters.
# Rev 2026-09-30 (fw 0.3, roadmap 1.9 Part 2): chime playback added - protocol
# registers 0x16-0x18 and 0x30-0x33. Clips play in the BACKGROUND: the sound
# chip asks for the next chunk of the file by itself (an "interrupt"), so the
# main loop keeps reading the knob and switches while a clip plays.
#
# Pair it with controls_presto_test.py (2026-09-30 version) on the Presto.
# Save to the board as main.py so it runs on USB power without Thonny.
#
# Clips: .wav files (mono, 8- or 16-bit, any sample rate) in /clips on this
# board. They're numbered in alphabetical order: clip 0 = first name, etc.
#
# Wiring (all inputs use the chip's built-in pull-up resistors, so every input
# is simply "pin to GND through the part"):
#   Encoder A -> GP2, encoder B -> GP3, encoder C (middle pin) -> GND
#   Encoder push-button: one pin -> GP4, other pin -> GND
#   Toggle switches: one leg -> GP5 / GP6 / GP7 / GP8, other leg -> GND
#   Pilot LEDs: GP29 (WiFi) / GP28 (OTA) -> resistor  [fw 0.3: GP9 / GP10] -> LED long leg (+); LED short leg (-) -> GND
#   Amp (MAX98357A): BCLK -> GP26, LRC -> GP27, DIN -> GP15 [fw 0.3: 11 / 12 / 13], Vin -> 5V, GND -> GND

import time
import os
import gc
import struct
import micropython
from machine import Pin, PWM, I2CTarget, I2S

ADDR = 0x11
FW_MAJOR, FW_MINOR = 0, 5

PIN_ENC_A = 2
PIN_ENC_B = 3
PIN_BTN = 4
SWITCH_PINS = (5, 6, 7, 8)     # bit 0 CHIME, 1 DAY-NIGHT, 2 BACKLIGHT, 3 WIFE MODE
LED_PINS = (29, 28)            # WiFi, OTA   (fw 0.3: 9, 10)
PIN_BCLK, PIN_LRC, PIN_DIN = 26, 27, 15   # LRC must be BCLK + 1 (RP2040 rule)   (fw 0.3: 11, 12, 13)

STEPS_PER_DETENT = 4   # confirmed 2026-09-30: one click = 1
ENC_REVERSE = False    # confirmed 2026-09-30: clockwise counts up
DEBOUNCE_MS = 20
LOOP_MS = 5

CLIP_DIR = "/clips"
CHUNK = 2048           # bytes of sound handed to the sound chip per refill
IBUF = 8192            # sound chip's own buffer: ~256 ms at 16 kHz 16-bit

# ---- Registers (protocol v0.1) ----
R_HEARTBEAT, R_FLAGS, R_FAULT, R_LOOP_MS, R_FREE_KB, R_WRITES, R_BOOT_ID = 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B
R_ENC, R_BTN_DOWN, R_BTN_UP, R_BTN_STATE, R_SWITCHES, R_SWITCH_COUNT = 0x10, 0x11, 0x12, 0x13, 0x14, 0x15
R_AUDIO_STATE, R_AUDIO_DONE, R_CLIP_COUNT = 0x16, 0x17, 0x18
R_BOOT_ID_COPY = 0x19   # v0.1: same value as 0x0B
R_LED_WIFI, R_LED_OTA, R_LED_BRIGHT, R_LED_OTA_BRIGHT = 0x20, 0x21, 0x22, 0x23   # 0x23: fw 0.5
R_CLIP, R_VOLUME, R_PLAY, R_STOP = 0x30, 0x31, 0x32, 0x33
# Test-only diagnostics in the chime block's reserved space (not in the protocol):
R_DIAG_REFILLS = 0x3C   # refills done, wraps at 256
R_DIAG_GAP_MS = 0x3D    # longest wait between refills this clip, ms (max 255)
R_DIAG_BUF_MS = 0x3E    # how many ms of sound the buffer holds at this clip's rate
R_DIAG_STARVED = 0x3F   # refills that came too late (buffer ran dry = a gap/click)

mem = bytearray(64)
mem[0], mem[1], mem[2], mem[3], mem[4] = 0xC5, ADDR, 0, FW_MAJOR, FW_MINOR
mem[R_BOOT_ID] = os.urandom(1)[0]
mem[R_BOOT_ID_COPY] = mem[R_BOOT_ID]
mem[R_LED_BRIGHT] = 255
mem[R_LED_OTA_BRIGHT] = 255
mem[R_VOLUME] = 128


def on_write(t):
    mem[R_WRITES] = (mem[R_WRITES] + 1) & 0xFF


i2c = I2CTarget(0, ADDR, sda=Pin(0), scl=Pin(1), mem=mem)
i2c.irq(on_write, trigger=I2CTarget.IRQ_END_WRITE, hard=False)

# ---- Encoder: quadrature decoding in a hard interrupt ----
# The two encoder pins (A, B) switch in a fixed order as the knob turns. The
# table maps (previous state, new state) -> +1, -1 or 0 (0 = bounce/invalid).
pin_a = Pin(PIN_ENC_A, Pin.IN, Pin.PULL_UP)
pin_b = Pin(PIN_ENC_B, Pin.IN, Pin.PULL_UP)
_QTABLE = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)
_enc_state = (pin_a.value() << 1) | pin_b.value()
enc_steps = 0


def _enc_irq(p):
    global _enc_state, enc_steps
    s = (pin_a.value() << 1) | pin_b.value()
    enc_steps += _QTABLE[(_enc_state << 2) | s]
    _enc_state = s


pin_a.irq(_enc_irq, Pin.IRQ_RISING | Pin.IRQ_FALLING, hard=True)
pin_b.irq(_enc_irq, Pin.IRQ_RISING | Pin.IRQ_FALLING, hard=True)


# ---- Debounced inputs (button + switches) ----
class Debounced:
    def __init__(self, pin_no, now):
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)
        self.stable = self.pin.value()
        self.cand = self.stable
        self.since = now

    def update(self, now):
        """True when the stable state just changed"""
        v = self.pin.value()
        if v != self.cand:
            self.cand = v
            self.since = now
        elif v != self.stable and time.ticks_diff(now, self.since) >= DEBOUNCE_MS:
            self.stable = v
            return True
        return False

    def closed(self):   # pulled up, so closed / pressed / on reads 0
        return self.stable == 0


now = time.ticks_ms()
button = Debounced(PIN_BTN, now)
switches = [Debounced(p, now) for p in SWITCH_PINS]


def switch_bits():
    bits = 0
    for i, s in enumerate(switches):
        if s.closed():
            bits |= 1 << i
    return bits


mem[R_SWITCHES] = switch_bits()
mem[R_BTN_STATE] = 1 if button.closed() else 0

# ---- Pilot lights ----
leds = []
for p in LED_PINS:
    pwm = PWM(Pin(p))
    pwm.freq(1000)
    pwm.duty_u16(0)
    leds.append(pwm)


def led_level(mode, t):
    """0.0-1.0 for a mode at time t (ms)"""
    if mode == 1:
        return 1.0
    if mode == 2:                       # slow blink, 1 per second
        return 1.0 if (t // 500) % 2 == 0 else 0.0
    if mode == 3:                       # fast blink, 4 per second
        return 1.0 if (t // 125) % 2 == 0 else 0.0
    if mode == 4:                       # slow pulse, 2 s per cycle
        p = (t % 2000) / 1000
        return p if p < 1 else 2 - p
    return 0.0                          # 0 = off (and anything unknown)


# ---- Chime playback ----
try:
    CLIPS = sorted(n for n in os.listdir(CLIP_DIR) if n.lower().endswith(".wav"))
except OSError:
    CLIPS = []
mem[R_CLIP_COUNT] = len(CLIPS)
if not CLIPS:
    mem[R_FAULT] = 2                    # protocol: 2 = no clips found in flash

# All buffers made once, up front, so playback makes no garbage.
buf = bytearray(CHUNK)                  # what goes to the sound chip (16-bit)
buf8 = bytearray(CHUNK // 2)            # 8-bit clips are read here, then widened
mv = memoryview(buf)
mv8 = memoryview(buf8)
SILENCE = bytes(CHUNK)


@micropython.viper
def _scale16(b: ptr16, n: int, vol: int):
    # 16-bit samples in place: sample * vol / 256 (vol 0-255)
    for i in range(n):
        v = b[i]
        if v & 0x8000:
            v -= 0x10000
        b[i] = (v * vol) >> 8


@micropython.viper
def _widen8(dst: ptr16, src: ptr8, n: int, vol: int):
    # 8-bit WAV is unsigned (128 = silence); make signed 16-bit and scale
    for i in range(n):
        dst[i] = (src[i] - 128) * vol


def read_wav_header(f):
    """(rate, bits, channels, data_bytes); leaves f at the sound data"""
    riff = f.read(12)
    if riff[0:4] != b"RIFF" or riff[8:12] != b"WAVE":
        raise ValueError("not a WAV file")
    rate = bits = ch = None
    while True:
        hdr = f.read(8)
        if len(hdr) < 8:
            raise ValueError("no data chunk")
        cid, size = hdr[0:4], struct.unpack("<I", hdr[4:8])[0]
        if cid == b"fmt ":
            fmt = f.read(size)
            ch, rate = struct.unpack("<HI", fmt[2:8])
            bits = struct.unpack("<H", fmt[14:16])[0]
        elif cid == b"data":
            return rate, bits, ch, size
        else:
            f.seek(size + (size & 1), 1)


# Playback state (changed by the main loop and the refill interrupt)
audio = None        # the I2S sound output while a clip is playing
wav = None          # the open clip file
bits = 16
left = 0            # bytes of sound still to read from the file
tail_left = 0       # bytes of closing silence still to send (set when a clip starts)
finished = False    # set by the refill when the clip is done; main loop cleans up
active = False      # False = ignore any refill that arrives after a stop
last_refill = 0
buf_ms = 0


def _fill():
    """Put the next chunk of sound in buf; return its length (0 = none left)"""
    global left, tail_left
    if left > 0:
        if bits == 16:
            n = wav.readinto(mv[:min(CHUNK, left)])
            left -= n
            n &= ~1
            _scale16(buf, n >> 1, mem[R_VOLUME])
            return n
        n = wav.readinto(mv8[:min(CHUNK // 2, left)])
        left -= n
        _widen8(buf, buf8, n, mem[R_VOLUME])
        return n * 2
    if tail_left > 0:
        # Closing silence: a full buffer's worth. The sound chip only asks for
        # more once a chunk is IN its buffer, not once it's been heard - so the
        # last of the clip is still in there when the file runs out. Pushing
        # silence behind it means that when we stop, only silence is thrown
        # away, not the end of the clip. (Found in the simulator 2026-09-30.)
        tail_left -= CHUNK
        mv[:] = SILENCE
        return CHUNK
    return 0


def _refill(i2s_obj):
    # Called by the sound chip each time it has taken the last chunk.
    global finished, last_refill
    if not active:
        return
    t = time.ticks_ms()
    gap = time.ticks_diff(t, last_refill)
    last_refill = t
    if gap > mem[R_DIAG_GAP_MS]:
        mem[R_DIAG_GAP_MS] = min(255, gap)
    if gap > buf_ms:
        mem[R_DIAG_STARVED] = (mem[R_DIAG_STARVED] + 1) & 0xFF
    mem[R_DIAG_REFILLS] = (mem[R_DIAG_REFILLS] + 1) & 0xFF
    try:
        n = _fill()
    except Exception:
        n = 0
    if n:
        audio.write(mv[:n])
    else:
        finished = True


def stop_clip(count_done=True):
    global audio, wav, active, finished
    active = False
    finished = False
    if audio is not None:
        audio.deinit()
        audio = None
    if wav is not None:
        wav.close()
        wav = None
    if count_done and mem[R_AUDIO_STATE] == 1:
        mem[R_AUDIO_DONE] = (mem[R_AUDIO_DONE] + 1) & 0xFF
    if mem[R_AUDIO_STATE] == 1:
        mem[R_AUDIO_STATE] = 0


def play_clip(index):
    global audio, wav, bits, left, tail_left, active, finished, last_refill, buf_ms
    stop_clip()                         # a new clip replaces one already playing
    try:
        wav = open(CLIP_DIR + "/" + CLIPS[index], "rb")
        rate, bits, ch, left = read_wav_header(wav)
        if ch != 1 or bits not in (8, 16):
            raise ValueError("need mono 8/16-bit")
    except Exception as e:
        print("clip %d: %r" % (index, e))
        if wav is not None:
            wav.close()
            wav = None
        mem[R_AUDIO_STATE] = 2          # protocol: 2 = error (missing/unreadable)
        return
    tail_left = IBUF + CHUNK
    finished = False
    buf_ms = IBUF * 1000 // (rate * 2)
    mem[R_DIAG_BUF_MS] = min(255, buf_ms)
    mem[R_DIAG_GAP_MS] = 0
    audio = I2S(0, sck=Pin(PIN_BCLK), ws=Pin(PIN_LRC), sd=Pin(PIN_DIN),
                mode=I2S.TX, bits=16, format=I2S.MONO, rate=rate, ibuf=IBUF)
    audio.irq(_refill)                  # from now on, writes don't wait
    active = True
    mem[R_AUDIO_STATE] = 1
    last_refill = time.ticks_ms()
    n = _fill()
    audio.write(mv[:n])                 # the first chunk starts it off


mem[R_FLAGS] = 0x01   # READY
print("Controls test up at 0x%02X, boot id %d, %d clips: %s"
      % (ADDR, mem[R_BOOT_ID], len(CLIPS), ", ".join(CLIPS)))

consumed = 0
detents = 0
last_play = mem[R_PLAY]
last_stop = mem[R_STOP]
last_mem_report = time.ticks_ms()


def loop_once():
    global consumed, detents, last_play, last_stop, last_mem_report
    t0 = time.ticks_ms()

    # knob turns -> ENC_COUNT (whole clicks only)
    pending = enc_steps - consumed
    while pending >= STEPS_PER_DETENT:
        detents += 1
        consumed += STEPS_PER_DETENT
        pending -= STEPS_PER_DETENT
    while pending <= -STEPS_PER_DETENT:
        detents -= 1
        consumed -= STEPS_PER_DETENT
        pending += STEPS_PER_DETENT
    mem[R_ENC] = (-detents if ENC_REVERSE else detents) & 0xFF

    # knob button
    if button.update(t0):
        if button.closed():
            mem[R_BTN_DOWN] = (mem[R_BTN_DOWN] + 1) & 0xFF
            mem[R_BTN_STATE] = 1
        else:
            mem[R_BTN_UP] = (mem[R_BTN_UP] + 1) & 0xFF
            mem[R_BTN_STATE] = 0

    # toggle switches
    changed = False
    for s in switches:
        if s.update(t0):
            changed = True
    if changed:
        mem[R_SWITCHES] = switch_bits()
        mem[R_SWITCH_COUNT] = (mem[R_SWITCH_COUNT] + 1) & 0xFF

    # chime: PLAY / STOP are counters (protocol rule 2); CLIP and VOLUME are
    # written in the same transaction as PLAY, before it (rule 3)
    if mem[R_STOP] != last_stop:
        last_stop = mem[R_STOP]
        stop_clip()
    if mem[R_PLAY] != last_play:
        last_play = mem[R_PLAY]
        if mem[R_CLIP] < len(CLIPS):
            play_clip(mem[R_CLIP])
        else:
            stop_clip()
            mem[R_AUDIO_STATE] = 2
    if finished:
        stop_clip()

    # pilot lights (squared brightness looks more even to the eye)
    for pwm, reg, breg in zip(leds, (R_LED_WIFI, R_LED_OTA), (R_LED_BRIGHT, R_LED_OTA_BRIGHT)):
        lvl = led_level(mem[reg], t0) * mem[breg] / 255
        pwm.duty_u16(int(65535 * lvl ** 2))

    # diagnostics
    mem[R_HEARTBEAT] = (mem[R_HEARTBEAT] + 1) & 0xFF
    if time.ticks_diff(t0, last_mem_report) > 1000:
        last_mem_report = t0
        # Clean up once a second and report what's free AFTER that: small,
        # regular cleanups are quick (well inside the ~256 ms of sound the
        # buffer holds), and the number is real headroom, not the sawtooth.
        gc.collect()
        mem[R_FREE_KB] = min(255, gc.mem_free() // 1024)
    elapsed = time.ticks_diff(time.ticks_ms(), t0)
    mem[R_LOOP_MS] = min(255, elapsed)
    time.sleep_ms(max(0, LOOP_MS - elapsed))


if "_SIM" not in globals():             # (the desktop simulator drives it itself)
    while True:
        loop_once()
