# sun.py - sunrise, sunset, twilight, where the sun is, and the moon's phase,
# all worked out on the Presto from the date and the unit's latitude and
# longitude (config "location"). No internet needed.
#
# Method: NOAA's "General Solar Position Calculations" (the short series for
# the equation of time and the sun's declination). Checked against a reference library for Wentzville over four years: sunrise
# and sunset within about a minute, the sun's direction within half a degree. The numbers are kept small on purpose: the Presto's MicroPython
# uses single-precision floats, which can't hold a Julian date accurately.
#
# Times are minutes after midnight UTC for the given UTC date and may fall
# outside 0..1440 (US evenings are after midnight UTC); the caller adds its
# UTC offset. Longitude is degrees east (negative in the Americas).

import math

RISE_SET = 90.833         # sun's centre this far from overhead at sunrise/sunset
CIVIL = 96.0              # ...and at civil dawn / dusk ("dark enough for a lantern")
SYNODIC = 29.530588       # days from new moon to new moon
_CUM = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def day_of_year(y, m, d):
    leap = 1 if (m > 2 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 0
    return _CUM[m - 1] + d + leap


def _solar_doy(y, m, d):
    """Day of the year, nudged by the leap-year cycle: the calendar slips up to
    three quarters of a day against the sun between leap years, which is worth
    a minute of sunrise near the equinoxes."""
    y4 = y - 2000
    return day_of_year(y, m, d) + (y4 + 3) // 4 - 0.2422 * y4


def _eqtime_decl(doy, hour):
    """Equation of time (minutes) and declination (radians)."""
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                   - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    return eq, decl


def _event(doy, lat, lon, zenith, rising):
    """UTC minutes when the sun crosses `zenith`, or None if it doesn't that day."""
    la = math.radians(lat)
    t = 720 - 4 * lon                        # first guess: local solar noon
    for _ in range(2):                       # second pass uses the sun's place at the event
        eq, decl = _eqtime_decl(doy, t / 60)
        c = math.cos(math.radians(zenith)) / (math.cos(la) * math.cos(decl)) \
            - math.tan(la) * math.tan(decl)
        if c > 1 or c < -1:
            return None                      # polar day or night
        ha = math.degrees(math.acos(c))
        t = 720 - 4 * (lon + (ha if rising else -ha)) - eq
    return t


def times(y, m, d, lat, lon):
    """{'dawn', 'rise', 'noon', 'set', 'dusk'}: UTC minutes for that UTC date."""
    doy = _solar_doy(y, m, d)
    eq, _ = _eqtime_decl(doy, 12 - lon / 15)
    return {
        "dawn": _event(doy, lat, lon, CIVIL, True),
        "rise": _event(doy, lat, lon, RISE_SET, True),
        "noon": 720 - 4 * lon - eq,
        "set": _event(doy, lat, lon, RISE_SET, False),
        "dusk": _event(doy, lat, lon, CIVIL, False),
    }


def position(y, m, d, utc_min, lat, lon):
    """(azimuth, elevation) in degrees; azimuth clockwise from north."""
    eq, decl = _eqtime_decl(_solar_doy(y, m, d), utc_min / 60)
    ha = math.radians(((utc_min + eq + 4 * lon) / 4 - 180))
    la = math.radians(lat)
    cz = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    cz = max(-1.0, min(1.0, cz))
    elev = 90 - math.degrees(math.acos(cz))
    az = math.degrees(math.atan2(math.sin(ha),
                                 math.cos(ha) * math.sin(la) - math.tan(decl) * math.cos(la)))
    return (az + 180) % 360, elev


def _days_2000(y, m, d):
    """Whole days since 2000-01-01."""
    y4 = y - 2000
    return y4 * 365 + (y4 + 3) // 4 - (y4 + 99) // 100 + (y4 + 399) // 400 \
        + day_of_year(y, m, d) - 1


MOON_NAMES = ("NEW MOON", "WAXING CRESCENT", "FIRST QUARTER", "WAXING GIBBOUS",
              "FULL MOON", "WANING GIBBOUS", "LAST QUARTER", "WANING CRESCENT")


def moon(y, m, d, utc_min=720):
    """(age in days since new, lit fraction 0-1, name). Mean phase: can be off
    by half a day or so, which is fine for a name and a picture."""
    # a new moon fell on 2000-01-06 at 18:14 UTC = day 5.76 of this count
    whole = (_days_2000(y, m, d) - 5) % 59061176        # keeps the number small
    age = (whole + utc_min / 1440 - 0.76) % SYNODIC
    lit = (1 - math.cos(2 * math.pi * age / SYNODIC)) / 2
    return age, lit, MOON_NAMES[int(age / SYNODIC * 8 + 0.5) % 8]
