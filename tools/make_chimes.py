"""Make the synthesised chime clips for the Controls board (roadmap 5.10).

    python tools/make_chimes.py            -> writes coproc/controls/clips/

The bell and the whistle are generated from maths (no recordings), so there is
no licence to track. Output: 16 kHz mono 16-bit WAV, the format proven in
roadmap 1.9. The same seed gives the same files every time.

Approved by ear on a computer by Jason, 2026-10-10. Heard on the unit's
speaker 2026-10-17: the whistle stays; the synthesised bell was replaced by a
recorded one (tools/cut_bell.py), so this script now writes the whistle only
(the bell function is kept, written as 0_bell_synth_old.wav only if asked:
python tools/make_chimes.py <folder> --old-bell).

The telegraph is NOT made here: two synthesised tries were rejected the same
evening ("goofy and melodic", then "tap dancing"), so it will be cut from
Jason's own recording of a real sounder.
"""
import os, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 16000
PEAK = 0.89            # -1 dBFS
rng = np.random.default_rng(1975)

def t_axis(sec): return np.arange(int(sec * SR)) / SR
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)
def fade_out(x, sec):
    n = int(sec * SR); x = x.copy(); x[-n:] *= np.linspace(1, 0, n) ** 2; return x
def norm(x): return x / np.max(np.abs(x)) * PEAK
def save(path, x):
    x = np.clip(norm(x), -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())

# ---- railroad bell: one strike of a bronze locomotive bell --------------------
BELL_PRIME = 560.0     # Hz; the strike note sits an octave above (1120 Hz)
BELL_LEN = 3.4
# (ratio to prime, level, decay time-constant s) - classic bell partial series, a little "clangy"
BELL_PARTIALS = [(0.5, 0.55, 2.6), (1.0, 0.80, 1.7), (1.19, 0.70, 1.2), (1.5, 0.35, 0.9),
                 (2.0, 1.00, 1.0), (2.51, 0.30, 0.6), (2.66, 0.22, 0.5), (3.01, 0.45, 0.55),
                 (4.17, 0.30, 0.32), (5.43, 0.18, 0.22), (6.80, 0.10, 0.15)]
def bell(prime=BELL_PRIME, length=BELL_LEN):
    t = t_axis(length); x = np.zeros_like(t)
    for ratio, lvl, tau in BELL_PARTIALS:
        f = prime * ratio
        if f > SR * 0.45: continue
        beat = rng.uniform(0.4, 1.6)          # each partial is a slightly split pair -> slow shimmer
        ph1, ph2 = rng.uniform(0, 2 * np.pi, 2)
        x += lvl * np.exp(-t / tau) * (0.6 * np.sin(2 * np.pi * f * t + ph1)
                                       + 0.4 * np.sin(2 * np.pi * (f + beat) * t + ph2))
    strike = bp(rng.standard_normal(len(t)), 1800, 6500) * np.exp(-t / 0.006)   # clapper hit
    x = x + 0.9 * strike / np.max(np.abs(strike))
    x[: int(0.0015 * SR)] *= np.linspace(0, 1, int(0.0015 * SR))
    return fade_out(x, 0.25)

# ---- steam whistle: one blast of a three-chime whistle ------------------------
WHISTLE_NOTES = [311.1, 370.0, 466.2]   # D#4, F#4, A#4
WHISTLE_LEN = 2.6
def whistle(notes=WHISTLE_NOTES, length=WHISTLE_LEN):
    t = t_axis(length); n = len(t)
    # steam pressure: comes up, holds, lets go
    amp = np.minimum(1, t / 0.14) ** 1.5 * np.minimum(1, (length - t) / 0.38) ** 1.3
    # pitch follows pressure: flat at the start, sags at the end
    bend = 1 - 0.07 * np.exp(-t / 0.10) - 0.05 * np.clip((t - (length - 0.38)) / 0.38, 0, 1) ** 2
    wob = lp(rng.standard_normal(n), 7) ; wob = wob / np.max(np.abs(wob))
    x = np.zeros(n)
    for i, f0 in enumerate(notes):
        w2 = lp(rng.standard_normal(n), 5); w2 = w2 / np.max(np.abs(w2))
        f = f0 * bend * (1 + 0.004 * w2)
        ph = 2 * np.pi * np.cumsum(f) / SR
        late = np.minimum(1, t / (0.10 + 0.05 * i)) ** 2          # the chambers don't speak together
        for h in range(1, 9):
            if f0 * h > SR * 0.45: break
            x += late * (1.0 / h ** 0.95) * (0.8 if h % 2 == 0 else 1.0) * np.sin(h * ph + rng.uniform(0, 6.28))
    hiss = hp(rng.standard_normal(n), 1800) * 0.07 + bp(rng.standard_normal(n), 500, 2500) * 0.10
    x = x / np.max(np.abs(x))
    x = (x * (1 + 0.10 * wob) + hiss * (1 + 0.5 * np.exp(-t / 0.15))) * amp
    return x

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(os.path.dirname(here), "coproc", "controls", "clips")
    os.makedirs(out, exist_ok=True)
    save(os.path.join(out, "2_whistle.wav"), whistle())
    print("wrote 2_whistle.wav to", out)
    if "--old-bell" in sys.argv:        # NOT into clips/: it would become clip 0
        save(os.path.join(out, "0_bell_synth_old.wav"), bell())
        print("wrote 0_bell_synth_old.wav - keep it out of the board's /clips")
