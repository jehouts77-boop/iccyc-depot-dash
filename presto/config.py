# config.py - per-unit settings
#
# Two layers:
#   DEFAULTS (this file)  - part of the shared "engine"; OTA updates replace it.
#   /config.json          - this unit's own values (WiFi, serial, anything
#                           changed on the Settings screen). OTA NEVER touches
#                           it. Only keys that differ from DEFAULTS need to be in it.
#
# To fork for another house: change "location" and "ota" in /config.json.

import json

try:
    import os
except ImportError:
    os = None

PATH = "/config.json"

DEFAULTS = {
    "unit": {"serial": "100069", "name": "BENCH"},
    "wifi": {"ssid": "", "password": ""},
    # Wentzville, MO - weather.gov places this point in Wentzville itself (checked 2026-09-30)
    "location": {"name": "WENTZVILLE MO", "lat": 38.8114, "lon": -90.8529},
    "tz": {"std_offset_h": -6, "us_dst": True},          # US Central
    "ntp_host": "pool.ntp.org",
    # Updates (roadmap 5.13, ota.py): which GitHub repo and branch this unit
    # follows. "release" only gets code confirmed on a real unit. auto: check
    # and install by itself every night at "time" (local). Set auto to false
    # in /config.json on a unit that is loaded by USB during development, or
    # the nightly update will put the released files back over newer ones.
    "ota": {"repo": "jehouts77-boop/iccyc-depot-dash", "branch": "release", "auto": True,
            "time": "03:30"},
    # api.weather.gov, looked up 2026-09-30 for the location above: nearest
    # observation station and the forecast grid square (see weather.py)
    "weather": {"station": "KSUS", "grid": "LSX/72,82", "obs_every_s": 600,
                "fc_every_s": 1800},

    # Clock face (roadmap 5.3). seconds: false = no seconds hand (the face then
    # only changes once a minute). maker: the name on the dial; the line under
    # it is location "name".
    "clock": {"seconds": True, "maker": "ICCYC"},

    # The Edmund Fitzgerald remembrance (roadmap 5.10a, screens/fitz.py).
    # Runs by itself on month/day at "time" (local), from auto_from_year on;
    # any day by tapping the maker's name on the Clock five times. "bell" is a
    # name from chime_sounds. Timings in milliseconds.
    "fitz": {"auto": True, "auto_from_year": 2027, "month": 11, "day": 10, "time": "18:10",
             "bell": "RAILROAD BELL", "toll_ms": 5000, "title_ms": 6000,
             "card_min_ms": 6000, "card_ms_per_char": 55, "close_ms": 9000},

    # Nearest Train (roadmap 5.6, trains.py). stations: whose train lists to
    # read; watch: the station the screen times trains at (WAH = Washington,
    # MO, the closest stop to Wentzville). Fetch every every_s while a moving
    # train is within near_mi miles, else every far_every_s. A position older
    # than fresh_s is not trusted.
    "train": {"stations": ["WAH"], "watch": "WAH", "every_s": 180, "far_every_s": 600,
              "near_mi": 60, "fresh_s": 900},

    # Overhead (roadmap 5.7, planes.py): planes in the air within radius_mi of
    # "location". Fetched every every_s seconds, only while the screen is up.
    # A plane whose last position is older than fresh_s seconds is left out.
    "planes": {"radius_mi": 30, "every_s": 15, "fresh_s": 60},
    # The ISS page of Overhead (roadmap 5.7a, iss.py): where the space station is,
    # from wheretheiss.at every every_s seconds, only while that page is up.
    "iss": {"every_s": 10,
            # Stage 1 (isslisten.py): the name this unit listens to ham radio under.
            # A licensed ham's unit can use their own callsign: set it in that
            # unit's /config.json, not here. Otherwise a name that isn't a
            # callsign: ICCYC1, ICCYC2, ... (a different one for each unit).
            "aprs_login": "ICCYC1"},

    "idle_s": 180,                 # back to the Clock after this long untouched; 0 = never
                                   # (Settings > BACK TO CLOCK: 3 min / 30 min / 3 hrs / never)
    "long_press_ms": 800,

    # Brightness (on-screen settings). Presto screen 0.0-1.0; gauges 1-255
    # (their colours are scaled); pilot lights 0-255: "leds" = the WiFi light,
    # "ota_led" = the OTA light (its own level since 2026-10-26: the green LED
    # is much brighter than the amber one at the same setting; needs Controls
    # fw 0.5 - older boards use "leds" for both).
    # 2026-10-26 defaults from the first assembled unit (Jason): day WiFi light
    # 5/10, night gauges 6/10 (they looked dimmer than the screen at 90).
    "bright_day": {"screen": 1.0, "gauges": 255, "leds": 128, "ota_led": 51},
    "bright_night": {"screen": 0.25, "gauges": 153, "leds": 50, "ota_led": 25},
    "leds_dark": 12,               # both pilot lights while BACKLIGHT is off

    # Switch positions: bit 0 CHIME, 1 DAY-NIGHT, 2 BACKLIGHT, 3 WIFE MODE.
    # The Controls board reports 1 when a switch is CLOSED (to GND). With
    # switch_invert = 0, OPEN = normal (chime on, day, lights on, wife mode
    # off) and CLOSED = chime muted / night / dark / wife mode - so a board
    # with nothing wired behaves normally. Set a bit here to flip that switch
    # if it ends up upside-down at assembly (protocol Open item, M4).
    "switch_invert": 0,

    # Chime (on-screen: sound + volume). mode: off / hourly / hourly_count /
    # half_hourly. hourly_count = the sound, then one strike per hour (1-12).
    # strike_clip = the clip number of the strike: one click-clack of the
    # telegraph sounder. It is not in chime_sounds, so it is not offered as a
    # chime sound on the Settings page.
    "chime": {
        "mode": "hourly",
        "sound": "RAILROAD BELL",
        "strike_clip": 3,
        "volume_step": 3,
        "quiet_start": "22:00",
        "quiet_end": "07:00",
        "strike_gap_ms": 700,
    },
    # Clip numbers on the Controls board = alphabetical order of the .wav
    # names in its /clips folder (coproc/controls/clips): 1_bell, 2_whistle,
    # 3_telegraph_iccyc, 4_telegraph_strike. TELEGRAPH taps out ICCYC.
    "chime_sounds": {"RAILROAD BELL": 0, "STEAM WHISTLE": 1, "TELEGRAPH": 2},
    "volume_steps": [0, 40, 80, 128, 190, 255],

    # What the two gauges show on each screen (on-screen setting). Kinds are
    # listed in gaugekinds.py. Defaults approved 2026-09-30.
    "gauges": {
        "home": ["temp", "wind_dir"],
        "clock": ["temp", "wind_dir"],
        "weather": ["humidity", "pressure"],
        "lantern": ["daylight_left", "sun_dir"],
        "onthisday": ["temp", "wind_dir"],
        "train": ["train_speed", "train_dir"],
        "overhead": ["plane_alt", "plane_dir"],
        "overhead_iss": ["iss_elev", "iss_dir"],          # the ISS page of Overhead
        "settings": ["wifi_signal", "free_mem"],
        "diag": ["wifi_signal", "free_mem"],
    },
}

values = {}
load_error = None


def _merge(base, over):
    # (always builds new dicts, so changing a value never changes DEFAULTS)
    out = {}
    for k, v in base.items():
        if isinstance(v, dict):
            o = over.get(k)
            out[k] = _merge(v, o if isinstance(o, dict) else {})
        elif k in over:
            out[k] = over[k]
        elif isinstance(v, list):
            out[k] = list(v)
        else:
            out[k] = v
    for k, v in over.items():
        if k not in out:
            out[k] = v
    return out


def _diff(base, cur):
    """Only what differs from DEFAULTS goes in the file."""
    out = {}
    for k, v in cur.items():
        if k not in base:
            out[k] = v
        elif isinstance(v, dict) and isinstance(base[k], dict):
            d = _diff(base[k], v)
            if d:
                out[k] = d
        elif v != base[k]:
            out[k] = v
    return out


def load():
    global values, load_error
    over = {}
    load_error = None
    try:
        with open(PATH) as f:
            over = json.load(f)
    except OSError:
        pass                              # no file yet: all defaults
    except ValueError as e:
        load_error = "config.json unreadable: %s" % e
        print(load_error)
    values = _merge(DEFAULTS, over)
    return values


def save():
    """Write /config.json safely: temp file first, then swap it in."""
    data = json.dumps(_diff(DEFAULTS, values))
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        f.write(data)
    if os is not None:
        try:
            os.remove(PATH)
        except OSError:
            pass
        os.rename(tmp, PATH)


def get(key):
    return values[key]


def set(key, value, sub=None):
    if sub is None:
        values[key] = value
    else:
        values[key][sub] = value
