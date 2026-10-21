# gaugekinds.py - everything a round gauge can show
#
# Each kind is a gauge setup (protocol v0.1, Gauges block) plus the name of
# the reading in app.data it follows. Values are sent scaled by DECIMALS, so
# 29.92 inHg with dec 2 is 2992. When a reading isn't available yet
# (None in app.data), the needle rests at the start and the number is hidden.
#
# Adding a kind = one entry here; then name it in config "gauges".

DIAL, COMPASS = 0, 1
DEG = "\xb0"

KINDS = {
    #  kind          style    dec  min    max   major minor numbers label            units      reading
    "temp":          (DIAL,    0,  -20,   110,  14,   1,   True,  "OUTSIDE TEMP",  DEG + "F", "temp_f"),
    "wind_dir":      (COMPASS, 0,    0,     0,   4,   2,   False, "WIND FROM",     DEG,       "wind_dir"),
    "wind_speed":    (DIAL,    0,    0,    60,   7,   1,   True,  "WIND",          "MPH",     "wind_mph"),
    "humidity":      (DIAL,    0,    0,   100,  11,   1,   True,  "HUMIDITY",      "%",       "humidity"),
    "pressure":      (DIAL,    2, 2850,  3100,   6,   4,   False, "BAROMETER",     "IN",      "pressure_inhg"),
    "daylight_left": (DIAL,    1,    0,   150,   6,   1,   True,  "DAYLIGHT LEFT", "H",       "daylight_left_h"),
    "sun_dir":       (COMPASS, 0,    0,     0,   4,   2,   False, "SUN",           DEG,       "sun_az"),
    "train_speed":   (DIAL,    0,    0,   100,  11,   1,   True,  "TRAIN SPEED",   "MPH",     "train_mph"),
    "train_dir":     (COMPASS, 0,    0,     0,   4,   2,   False, "TO TRAIN",      DEG,       "train_bearing"),
    "plane_alt":     (DIAL,    1,    0,   500,  11,   1,   True,  "ALTITUDE",      "K FT",    "plane_alt_kft"),
    "plane_dir":     (COMPASS, 0,    0,     0,   4,   2,   False, "TO PLANE",      DEG,       "plane_bearing"),
    "iss_elev":      (DIAL,    0,  -90,    90,   7,   2,   True,  "ISS ELEVATION", DEG,       "iss_elev"),
    "iss_dir":       (COMPASS, 0,    0,     0,   4,   2,   False, "TO ISS",        DEG,       "iss_bearing"),
    "wifi_signal":   (DIAL,    0, -100,   -30,   8,   1,   True,  "WIFI SIGNAL",   "DB",      "wifi_rssi"),
    "free_mem":      (DIAL,    0,    0,   100,  11,   1,   True,  "FREE MEMORY",   "%",       "free_mem_pct"),
    "seconds":       (DIAL,    0,    0,    60,   7,   4,   True,  "SECONDS",       "",        "seconds"),
}

GLIDE = 40            # protocol GLIDE units; 40 = the 300 ms glide picked 2026-09-30

# Readout text (protocol v0.2, Gauges fw 1.1): a kind listed here shows this
# text in the big readout instead of its own number - e.g. the wind compass
# points where the wind comes from and says how fast. Max 8 characters.
# If the reading is missing, the gauge's own number is shown instead.
def _wind(v):
    return "CALM" if v < 1 else "%d MPH" % round(v)


def _far(v):
    return "%d MI" % round(v)


READOUTS = {
    "wind_dir":  ("wind_mph", _wind),
    "train_dir": ("train_mi", "%.1f MI"),
    "plane_dir": ("plane_mi", "%.1f MI"),
    "iss_dir":   ("iss_mi", _far),
}


def readout_text(kind, data):
    r = READOUTS.get(kind)
    if r is None:
        return ""
    v = data.get(r[0])
    if v is None:
        return ""
    f = r[1]
    return (f(v) if callable(f) else f % v)[:8]


def setup_for(kind, have_value=True):
    """Keyword arguments for coproc.Gauges.setup()."""
    k = KINDS.get(kind) or KINDS["seconds"]
    style, dec, vmin, vmax, major, minor, numbers, label, units, _ = k
    show = (1 if have_value else 0) | (2 if numbers else 0)
    return dict(style=style, dec=dec, vmin=vmin, vmax=vmax, major=major, minor=minor,
                show=show, glide=GLIDE, label=label, units=units)


def reading_for(kind):
    k = KINDS.get(kind) or KINDS["seconds"]
    return k[9]


def rest_value(kind):
    k = KINDS.get(kind) or KINDS["seconds"]
    return 0 if k[0] == COMPASS else k[2]
