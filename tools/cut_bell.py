# cut_bell.py - makes coproc/controls/clips/1_bell.wav (the RAILROAD BELL chime)
#
# Source: "Train Horn 61 with Train Bell" by FunWithSound,
# https://freesound.org/s/591868/ - Creative Commons 0 (no credit required),
# kept as data/chimes/freesound_591868_train_horn_61_with_bell.mp3.
# Picked by Jason 2026-10-17 (version "B") to replace the synthesised bell.
#
# The recording has three horn blasts; between the first two (1.2 - 4.5 s) the
# locomotive bell rings alone, about 4 strikes a second. This takes 1.18 - 3.00 s
# (about 8 strikes), removes everything below 900 Hz (engine and wheel rumble,
# any trace of the horn; the bell's own tones are 1.1 - 6 kHz), fades in over
# 10 ms and out over 0.35 s, halves the rate to 16 kHz mono and sets the peak
# to -1 dBFS like the other clips.
#
# Needs ffmpeg, numpy, scipy.   python tools/cut_bell.py [output.wav]

import os
import subprocess
import sys
import tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt, resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "chimes", "freesound_591868_train_horn_61_with_bell.mp3")
START_S, END_S = 1.18, 3.00
HIGHPASS_HZ = 900
FADE_IN_S, FADE_OUT_S = 0.01, 0.35


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "coproc", "controls", "clips", "1_bell.wav")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "src.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-ac", "1", "-ar", "32000", wav], check=True)
        r, x = wavfile.read(wav)
    x = x.astype(float) / 32768
    y = sosfiltfilt(butter(4, HIGHPASS_HZ, "hp", fs=r, output="sos"), x)
    seg = y[int(START_S * r):int(END_S * r)].copy()
    n = int(FADE_IN_S * r)
    seg[:n] *= np.linspace(0, 1, n)
    n = int(FADE_OUT_S * r)
    seg[-n:] *= np.linspace(1, 0, n) ** 2
    z = resample_poly(seg, 1, 2)                     # 32 kHz -> 16 kHz
    z = z / np.abs(z).max() * 10 ** (-1 / 20)        # peak -1 dBFS
    wavfile.write(out, 16000, (z * 32767).astype(np.int16))
    print("wrote %s (%.2f s)" % (out, len(z) / 16000))


if __name__ == "__main__":
    main()
