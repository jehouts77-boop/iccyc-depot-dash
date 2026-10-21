# otd.py - On This Day entries (roadmap 5.9)
#
# The entries live in /otd_data/MM.json on the Presto, one small file per month,
# built from data/otd/otd_master.csv in the repo by tools/build_otd.py (every
# entry there has a source link). Only the current month is kept in memory.
# Updates (OTA) can add months and entries without touching anything else.

import json

DIR = "/otd_data"     # not "/otd": a folder named like otd.py would shadow it on import


class OnThisDay:
    def __init__(self, directory=DIR):
        self.dir = directory
        self.month = None
        self.days = {}
        self.error = ""

    def _load(self, mm):
        try:
            with open("%s/%02d.json" % (self.dir, mm)) as f:
                return json.load(f)
        except OSError:
            return {}
        except ValueError as e:
            self.error = "%02d.json unreadable: %s" % (mm, e)
            return {}

    def entries(self, t):
        """(entries, archive_date) for local time t. entries = [[year, cat, text], ...].
        archive_date is None normally; on a day with no entry yet it's (mm, dd) of
        another day's entry shown instead ("from the archives")."""
        mm, dd = t[1], t[2]
        if mm != self.month:
            self.days = self._load(mm)
            self.month = mm
        today = self.days.get("%02d" % dd)
        if today:
            return today, None
        # nothing for today yet: show another day, picked by the date so it
        # changes daily but stays put all day
        days = self.days
        src_mm = mm
        if not days:
            for k in range(1, 13):
                m = (mm + k - 1) % 12 + 1
                days = self._load(m)
                if days:
                    src_mm = m
                    break
        if not days:
            return [], None
        keys = sorted(days)
        key = keys[(t[7] if len(t) > 7 else dd) % len(keys)]
        return days[key], (src_mm, int(key))
