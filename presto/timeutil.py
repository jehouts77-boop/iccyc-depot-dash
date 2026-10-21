# timeutil.py - clock: NTP sync and local time with US daylight saving
#
# The Presto's clock (RTC) is kept in UTC; NTP sets it. Local time is worked
# out here on the board, so there's no time-zone service to depend on.
# US rule (since 2007): daylight time starts the 2nd Sunday of March at
# 2:00 AM local standard time and ends the 1st Sunday of November at 2:00 AM
# local daylight time.

import time

try:
    import ntptime
except ImportError:
    ntptime = None

last_sync = None         # time.time() of the last good sync (None = never)
sync_tries = 0
sync_fails = 0


def sync(host=None):
    """Set the clock from NTP. True on success. Blocks up to ~1 s."""
    global last_sync, sync_tries, sync_fails
    sync_tries += 1
    if ntptime is None:
        sync_fails += 1
        return False
    try:
        if host:
            ntptime.host = host
        ntptime.settime()
        last_sync = time.time()
        return True
    except Exception as e:
        print("NTP failed:", e)
        sync_fails += 1
        return False


def clock_set():
    """False until the clock has a believable date (it starts in 2021/2000)."""
    return time.gmtime()[0] >= 2025


def _nth_sunday(year, month, n):
    """Day of month of the nth Sunday (n = 1, 2, ...)."""
    wd = time.gmtime(time.mktime((year, month, 1, 12, 0, 0, 0, 0)))[6]   # Mon = 0
    first = 1 + (6 - wd) % 7
    return first + 7 * (n - 1)


def is_dst(utc, std_offset_h):
    """True if US daylight time is in effect at this UTC time."""
    y = time.gmtime(utc)[0]
    # 2:00 local standard = 2 - offset in UTC (e.g. 8:00 UTC for Central)
    start = time.mktime((y, 3, _nth_sunday(y, 3, 2), 2 - std_offset_h, 0, 0, 0, 0))
    # 2:00 local daylight = 2 - (offset + 1) in UTC (e.g. 7:00 UTC)
    end = time.mktime((y, 11, _nth_sunday(y, 11, 1), 1 - std_offset_h, 0, 0, 0, 0))
    return start <= utc < end


def offset_s(utc, cfg_tz):
    off = cfg_tz["std_offset_h"]
    if cfg_tz.get("us_dst", True) and is_dst(utc, off):
        off += 1
    return off * 3600


def local(cfg_tz, utc=None):
    """Local time tuple: (year, month, day, hour, minute, second, weekday Mon=0, yearday)."""
    if utc is None:
        utc = time.time()
    return time.gmtime(utc + offset_s(utc, cfg_tz))


DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def hhmm(t):
    return "%02d:%02d" % (t[3], t[4])


def hhmmss(t):
    return "%02d:%02d:%02d" % (t[3], t[4], t[5])


def date_line(t):
    return "%s %s %d" % (DAYS[t[6]], MONTHS[t[1] - 1], t[2])


def minutes(hhmm_str):
    """'22:00' -> 1320"""
    h, m = hhmm_str.split(":")
    return int(h) * 60 + int(m)


def in_window(t, start_str, end_str):
    """True if local time t is inside [start, end) - the window may wrap midnight."""
    now = t[3] * 60 + t[4]
    a, b = minutes(start_str), minutes(end_str)
    if a == b:
        return False
    return a <= now < b if a < b else (now >= a or now < b)
