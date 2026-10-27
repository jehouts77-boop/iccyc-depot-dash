# ICCYC Depot Dashboard ("Control Console")

A desk instrument built as a Christmas gift for two friends: a railroad-flavoured
clock and information panel with a 4" square touchscreen, two round analog-style
gauges, a knob, four toggle switches, two pilot lights and a chime speaker, in a
3D-printed case with an engraved brass nameplate. ICCYC = a running
joke among friends.

**Status (2026-10-26):** every screen is built and has run on a real unit: the
screen ring, Home menu, knob, switches, chime schedule, gauges, Diagnostics,
WiFi setup, the on-screen settings, smooth text, the Overhead planes and ISS
pages (the ham-radio listener connects; a real ISS hearing hasn't shown on a
unit yet), BACK TO CLOCK, every month of On This Day, and checking GitHub for
updates (a real over-the-air update is still to be tested). The first console
is fully assembled on the hub PCB. Three units are being built for Christmas
2026; the case
and hub board files are in [`hardware/`](hardware/README.md).

This README is written so that someone - or an AI assistant - with no other
context can understand, change and extend the project.

## Hardware

| Part | Job |
|---|---|
| Pimoroni Presto (RP2350B, 480x480 touchscreen, WiFi) | Runs the app in `presto/`. Everything that might change lives here, because only the Presto can update over WiFi. |
| RP2040-Zero at I2C **0x10** ("Gauges") | Draws both round GC9A01 240x240 gauge screens. Firmware: `coproc/gauges/`. |
| RP2040-Zero at I2C **0x11** ("Controls") | Reads the EC11 knob (with push button) and 4 toggle switches, drives 2 pilot LEDs, plays WAV chime clips from its own flash through a MAX98357A amp. |
| Presto Qw/ST port (I2C0: SDA GP40, SCL GP41, 100 kHz) | The only link to both co-processors, shared bus. |
| Hub board (70 × 50 mm PCB) | Carries both Zeros and the amp in sockets, the pilot-light resistors, the 5 V rail; every wire leaves it on a pin header. Files: `hardware/hub-pcb/`. |
| Panel-mount USB-C socket, 5 V 3 A charger | Powers everything through one 5 V rail. **Unplug it before plugging a USB cable into any board inside.** |
| 4 toggle switches, 2 pilot lights, EC11 knob, CQRobot speaker, 2 × GC9A01 round screens | The panel. |
| Engraved brass nameplate | One per unit, with its serial number. |

Why co-processors: the Presto has no free GPIO pins - only the Qw/ST I2C port.
The co-processors have no WiFi, so their firmware is kept minimal ("dumb
instruments"): they only do what the Presto tells them over I2C. Updating them
means opening the case and plugging in USB.

The I2C register map is in [`docs/i2c-protocol.md`](docs/i2c-protocol.md).

## What it shows

Turn the knob (or tap PREV / NEXT at the bottom) to go round the screens:

- **Clock** - a railroad station clock: roman hours, a red 24-hour ring, a sweep second hand.
- **Weather** - the latest observation from the nearest airport weather station and the forecast (api.weather.gov).
- **Lantern Time** - sunrise, sunset and the countdown to dark, worked out on the device; moon phase.
- **On This Day** - one or two events from history for today's date (500+ entries for the year).
- **Nearest Train** - where the nearest Amtrak train is, how far, how fast and how late (Amtraker).
- **Overhead** - two pages, swapped with the button at the bottom right:
  - **PLANES** - a small radar-style scope and the nearest plane's flight, type, distance, height and speed (adsb.fi, with adsb.lol as a backup). Tap for the next plane.
  - **ISS** - where the International Space Station is right now (wheretheiss.at), how far, which way, and whether it's above the horizon; and when it was last heard over ham radio (see "The ISS radio" below).
- **Settings** - WiFi, chime, brightness, what the gauges show, BACK TO CLOCK, updates.

The two round gauges follow the screen (e.g. temperature and wind on the Clock,
altitude and direction to the plane on Overhead). Long-press the knob for
Diagnostics.

## The ISS radio (listen-only)

The console listens to APRS-IS, the internet side of ham radio's position
reporting system, for packets sent by the ISS's radio (callsign RS0ISS) or
relayed through it, and shows when it was last heard. It logs in with
passcode -1, which means **receive only: it never transmits anything**, so
no licence is needed to run it. Each unit needs its own login name in
`/config.json`: `{"iss": {"aprs_login": "..."}}` - a ham's own callsign, or
any name that isn't a callsign (the default is ICCYC1; give a second unit
ICCYC2, and so on). The ISS radio is often quiet for days.

## Files

```
presto/                 -> copy to the Presto's flash (root)
  main.py               starts app.py; shows and logs any crash, then restarts
  app.py                main loop: controls, touch, switches, chime, gauges, screens
  config.py             settings: DEFAULTS here, this unit's values in /config.json
  coproc.py             the Presto side of the I2C protocol (Gauges + Controls)
  gaugekinds.py         what a gauge can show (setup + which reading it follows)
  chime.py              when to chime; strike counts; mute rules
  timeutil.py           NTP, US Central time with daylight saving, time strings
  net.py                WiFi, memory-safe http_get, hand-scanning JSON helpers
  weather.py            api.weather.gov: latest observation + forecast (station/grid in config)
  sun.py                sunrise, sunset, twilight, sun direction, moon phase (pure maths)
  almanac.py            today's sun and moon for config "location", in local time
  fitz_data.py          words for screens/fitz.py (sources: data/fitz/fitzgerald_sources.md)
  trains.py             nearest Amtrak train from api-v3.amtraker.com (stations in config "train")
  planes.py             planes in the air near config "location" from adsb.fi, adsb.lol as backup (config "planes")
  iss.py                where the ISS is now, from wheretheiss.at (config "iss")
  aprs.py               reads APRS (ham radio) packets: positions in all three formats, objects, text
  isslisten.py          the always-on listen-only APRS-IS connection for the ISS page
  otd.py                On This Day: reads otd_data/MM.json (current month only)
  ota.py                over-the-air updates from GitHub (see Updates below)
  otaguard.py           undoes an update that was cut short or keeps crashing; never updated itself
  otd_data/             On This Day entries, one JSON file per month (built - don't edit)
  textutil.py           ascii_safe, word_wrap
  ui.py                 colours, header/footer, smooth text (PicoVector) and the built-in font
  fonts/                the two .af font files - copy them to the Presto's / (see fonts/README.md)
  screens/              one file per screen; the ring order is in screens/__init__.py
coproc/gauges/          -> copy to the 0x10 board: main.py + drivers/
coproc/controls/        -> copy to the 0x11 board: main.py + clips/ as /clips (see its README)
hardware/               the case (OpenSCAD + STLs), the hub board (KiCad + Gerbers), the wiring - see hardware/README.md
docs/i2c-protocol.md    register map and rules for the I2C link
data/otd/otd_master.csv On This Day master list: one row per event, with its source link
tools/build_otd.py      builds presto/otd_data/ from the master list (python tools/build_otd.py)
tools/make_chimes.py    makes the synthesised whistle clip in coproc/controls/clips/ (needs numpy + scipy)
tools/cut_bell.py       cuts the bell clip from data/chimes/freesound_591868_... (CC0 recording; needs ffmpeg)
tools/build_telegraph.py cuts the telegraph clips from data/chimes/sounder_recording_2026-10-10.wav (Jason's own sounder)
```

## Updates (over the air)

A unit updates itself from GitHub: every night at 03:30 it asks for the list
of files on the branch it follows (config `"ota"`: `repo`, `branch`, `auto`,
`time`), downloads only the files under `presto/` that differ from its own
(`.py`, `.json`, `.af`), checks each one (size, git fingerprint, and that a
`.py` file compiles), swaps them in and restarts. Settings > UPDATES shows the
state and has CHECK NOW and PUT BACK OLD.

- **Units follow the `release` branch, not `main`.** `main` is the working
  branch. To publish: confirm a commit on a real unit, then
  `git push origin <that commit>:release`.
- No password is used, so the repo must be public for updates to work.
- `main.py` and `otaguard.py` are never updated (they are the safety net: an
  update that is interrupted, or that crashes twice at start-up, is undone
  automatically and that version is skipped until a newer one is published).
  Changing either of them means a USB cable.
- `/config.json` and `secrets.py` are never touched. Files deleted from the
  repo stay on the unit.
- On a unit you load by USB during development, put `{"ota": {"auto": false}}`
  in its `/config.json`, or the nightly update will put the released files
  back over your newer ones.
- In a fork: point `ota.repo` at the fork and create a `release` branch there.

## Per-unit settings (never overwritten by updates)

`/config.json` on the Presto holds only what differs from `DEFAULTS` in
`config.py`: WiFi, unit serial, and anything changed on the Settings screen.
Updates replace the engine files but never this file.

To make a fork yours, put these in `/config.json` (the defaults are for
Wentzville, Missouri): `location` (name, lat, lon), `tz`, `weather` (`station`
and `grid` - look them up for your location at api.weather.gov/points/LAT,LON),
`train` (`stations`, `watch` - Amtrak station codes), `planes.radius_mi`,
`iss.aprs_login`, and `ota.repo` if you update from your own fork.

WiFi is set on the unit itself (`presto/screens/wifi.py`): a unit with no
WiFi saved opens a welcome page at start-up, and the WIFI row on the Settings
screen reopens it - pick a network, type the password on the touch keyboard
(or with the knob), and it is saved to `/config.json`.

During development, WiFi can instead come from a `secrets.py` on the Presto
(see `secrets.py.example`). It is listed in `.gitignore`; never commit it.

## Controls

- **Knob:** turn = previous / next screen; press = Home menu (turn to pick,
  press to open); long press (0.8 s) = Diagnostics and back.
- **Touch:** tap a Home menu row, or PREV / MENU / NEXT along the bottom. On
  Overhead, tap the scope area for the next plane and the button at the bottom
  right to swap PLANES / ISS. (The
  Clock fills the whole screen and doesn't draw that strip, but the bottom of
  the screen still works the same way: left, middle, right.)
- Untouched for `idle_s` (default 3 minutes) -> back to the Clock.
- **Switches** (up = on; DAY · NIGHT: up = day, down = night). In the code a
  closed switch = the non-normal state, and `switch_invert` (one bit per switch:
  1 CHIME, 2 DAY·NIGHT, 4 BACKLIGHT, 8 WIFE MODE) flips any that end up
  upside-down at assembly. With the toggles mounted as in this panel (each closes when
  up), up = on needs `"switch_invert": 7` in `/config.json`. CHIME mutes the chime; DAY/NIGHT picks day or night brightness (manual, no
  automatic dimming); BACKLIGHT turns the Presto and gauge screens off and dims
  the pilot lights (the clock and chime keep running); WIFE MODE mutes the
  chime and uses night brightness, with no on-screen announcement.
- **Chime modes:** off / hourly / hourly_count (plus one strike per hour) /
  half_hourly; quiet hours (default 22:00-07:00).

## Gauges follow the screen

Each screen names its two gauges in `config.py` -> `"gauges"`, using kinds from
`gaugekinds.py`. A kind whose reading isn't available yet rests at its start
with the number hidden.

## Getting it onto a Presto (by USB)

1. Flash Pimoroni's MicroPython for the Presto, if it isn't already on it.
2. With Thonny (or `mpremote`), copy everything in `presto/` to the Presto's
   root, keeping the folders (`screens/`, `otd_data/`, `fonts/`).
3. Copy `coproc/gauges/` to the 0x10 board and `coproc/controls/` (with its
   `clips/`) to the 0x11 board, each as `main.py` at the board's root.
4. Restart the Presto. With no WiFi saved it opens the WiFi page: pick your
   network and type the password. If you will keep loading files by USB, also
   set `{"ota": {"auto": false}}` in `/config.json` (see Updates above).

## Data sources

Weather: [api.weather.gov](https://api.weather.gov) (US National Weather Service).
Trains: [Amtraker](https://amtraker.com). Planes: [adsb.fi](https://adsb.fi)
open data (personal, non-commercial use), with [adsb.lol](https://adsb.lol) as
a backup. ISS position: [wheretheiss.at](https://wheretheiss.at). ISS radio:
[APRS-IS](https://www.aprs-is.net), listen-only.

## Licence

MIT - see `LICENSE`. The GC9A01 display driver in `coproc/gauges/drivers/` is
Peter Hinch's micropython-nano-gui driver (MIT, see its licence file there).
Fonts: Barlow / Barlow Condensed (SIL Open Font License) and Special Elite
(Apache 2.0) - licence files beside them in `presto/fonts/` and
`hardware/enclosure/fonts/`. The telegraph chime is the builder's own recording.
