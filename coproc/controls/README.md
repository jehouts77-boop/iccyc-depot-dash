# Controls co-processor (0x11)

`main.py` here is the firmware the 0x11 boards run (fw 0.3). It began as the
validation script `controls_test.py` and implements the whole Controls part of
`docs/i2c-protocol.md`: knob, button, switches, pilot lights and chime playback.
Confirmed on hardware 2026-09-30; added to this repo on 2026-10-14 (unchanged apart from a header note).
Copy `main.py` to the board's root and the `clips/` folder to `/clips`.

## Chime clips (`clips/`)

The board plays WAV clips from its own `/clips` folder: 16 kHz, mono, 16-bit.
Clips are numbered in **alphabetical order of their file names**, which is
why the names start with a digit.

| File | Sound | Made by |
|---|---|---|
| `1_bell.wav` | a locomotive bell ringing, about 8 strikes, 1.8 s | `tools/cut_bell.py`, from a CC0 recording (FunWithSound, freesound.org/s/591868) |
| `2_whistle.wav` | one blast of a three-chime steam whistle, 2.6 s | `tools/make_chimes.py` (synthesised) |
| `3_telegraph_iccyc.wav` | a telegraph sounder tapping out ICCYC, 4.9 s | `tools/build_telegraph.py`, from Jason's recording |
| `4_telegraph_strike.wav` | one click-clack of the sounder, 0.3 s: the hour-count strike | `tools/build_telegraph.py`, from Jason's recording |

Clip numbers are 0, 1, 2, 3 in that order. `presto/config.py` matches:
`chime_sounds` = bell 0, whistle 1, telegraph 2; `chime.strike_clip` = 3.
All four together are about 300 KB.

The telegraph is Jason's own sounder, recorded by him on 2026-10-10
(`data/chimes/sounder_recording_2026-10-10.wav`). Its pace is the sounder's
own, tightened by 20 ms a gap (as recorded the word ran 5.3 s).

Status 2026-10-17: all four played on the desk unit's speaker (0x11). Jason
then swapped the synthesised bell for the recorded one above (version B of two
cuts); on 0x11 and approved on the unit's speaker the same day.
