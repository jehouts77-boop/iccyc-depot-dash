"""Cut Jason's recording of his telegraph sounder into the two telegraph chime clips (roadmap 5.10).

    python tools/build_telegraph.py        (needs numpy + scipy)

Reads  data/chimes/sounder_recording_2026-10-10.wav   Jason's own recording of his own sounder,
                                                      2026-10-10
Writes coproc/controls/clips/3_telegraph_iccyc.wav    the sounder tapping out ICCYC, 4.9 s
       coproc/controls/clips/4_telegraph_strike.wav   one click-clack, for the hour-count strikes

Nothing is synthesised (two synthesised tries were rejected). Whole recorded elements are reused -
click, ring, clack and the room after it: a dot is click..clack 74 ms apart, a dash 224 ms apart.
Processing: a 120 Hz rumble filter, one odd-level click left out, 16 kHz mono 16-bit, peak -1 dB.

The two clips in the repo are the exact files Jason approved by ear on 2026-10-10. Running this
script again gives the same clips to within 0.07 % of full scale (the first build resampled the
recording with ffmpeg, this one with scipy) - not something anyone can hear.
"""
import os, sys, wave
import numpy as np
from scipy.signal import butter, sosfiltfilt, resample_poly, find_peaks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "chimes", "sounder_recording_2026-10-10.wav")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "coproc", "controls", "clips")
SR_OUT, PEAK = 16000, 0.89
MORSE = {"I": "..", "C": "-.-.", "Y": "-.--"}
PRE = 0.006                 # start each cut this long before the click
DOT_P, DASH_P = 0.160, 0.310    # click-to-click spacing: the recording's 180 / 330 ms, tightened 20 ms. Jason, 2026-10-10: 5.3 s as recorded was long, 4.4 s (-40 ms) "a bit fast", so the middle
LETTER_EXTRA = 0.125        # extra silence between letters: 211 ms after the clack, against 86 ms inside a letter (the recording's ratio)
TAIL = 0.22                 # room left after the last clack (the recording has 256 ms there)

w = wave.open(SRC); sr0 = w.getframerate(); assert w.getnchannels() == 1 and w.getsampwidth() == 2
x = np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32768.0
sr = 48000; x = resample_poly(x, sr, sr0) if sr0 != sr else x     # work at 48 kHz, as the first build did
x = sosfiltfilt(butter(2, 120, btype="high", fs=sr, output="sos"), x)      # take out rumble only
win = int(0.002 * sr); env = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, "same"))
pk, pr = find_peaks(env, height=0.07, distance=int(0.05 * sr))            # the loud hits = clicks (armature down)
clicks = pk / sr
soft, _ = find_peaks(env, height=0.03, distance=int(0.03 * sr)); soft = soft / sr
dots, dashes = [], []
for c in clicks:
    after = [s for s in soft if 0.04 < s - c < 0.30]
    if not after: continue
    gap = after[0] - c
    (dots if gap < 0.15 else dashes).append(c)
lvl = lambda c: env[int(c * sr)]
med = float(np.median([lvl(c) for c in dots + dashes]))
dots = [c for c in dots if 0.75 * med < lvl(c) < 1.25 * med]          # leave out odd-level hits (the first click is 1.4x the rest)
dashes = [c for c in dashes if 0.75 * med < lvl(c) < 1.25 * med]
print("clicks", len(clicks), "dots", len(dots), "dashes", len(dashes))

def room(c):    # seconds from this click to the next one in the recording
    later = [k for k in clicks if k > c]
    return (later[0] - c) if later else (len(x) / sr - c)
roomy_dot = max(dots, key=room)
assert room(roomy_dot) > 0.074 + TAIL + 0.02, room(roomy_dot)
def onset(c):   # the click's envelope peak sits ~2 ms after the first movement
    return c - 0.002
def cut(c, length):
    i = int((onset(c) - PRE) * sr); seg = x[i:i + int(length * sr)].copy()
    f = int(0.003 * sr); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
    return seg

def assemble(text):
    di = da = 0; parts = []; t = 0.0; places = []
    for li, ch in enumerate(text):
        for si, sym in enumerate(MORSE[ch]):
            last = (li == len(text) - 1 and si == len(MORSE[ch]) - 1)
            if sym == ".":
                c = dots[di % len(dots)]; di += 1; per = DOT_P
            else:
                c = dashes[da % len(dashes)]; da += 1; per = DASH_P
            if last:                                    # needs a real tail: the dot with the most room after it
                c = roomy_dot
            places.append((t, c, (0.074 + TAIL) if last else per - 0.004))   # stop 4 ms early: the next click must not leak in
            t += per
        t += LETTER_EXTRA
    total = places[-1][0] + places[-1][2] + 0.02
    y = np.zeros(int(total * sr))
    for at, c, length in places:
        seg = cut(c, length)
        i = int(at * sr); y[i:i + len(seg)] += seg[: len(y) - i]
    return y

def finish(y, path):
    f = int(0.06 * sr); y[-f:] *= np.linspace(1, 0, f) ** 2
    y = resample_poly(y, SR_OUT, sr)
    y = y / np.max(np.abs(y)) * PEAK
    with wave.open(path, "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR_OUT)
        o.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
    print(path, round(len(y) / SR_OUT, 2), "s", len(y) * 2 + 44, "bytes")

finish(assemble("ICCYC"), OUT + "/3_telegraph_iccyc.wav")
# hour strike: one real dot (click-clack) with its own tail; the cleanest = the median-level dot
finish(cut(roomy_dot, 0.074 + TAIL), OUT + "/4_telegraph_strike.wav")
