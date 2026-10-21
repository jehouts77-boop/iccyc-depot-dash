"""Build the Presto's On This Day files from the master list.

    python tools/build_otd.py

Reads  data/otd/otd_master.csv   (one row per event, with its source link)
Writes presto/otd_data/MM.json        (one small file per month - the Presto
                                  loads only the current month)

Every row must have a source; the build refuses rows without one, plain-ASCII
text only (the Presto's font), and at most MAX_TEXT characters.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "data", "otd", "otd_master.csv")
OUT = os.path.join(ROOT, "presto", "otd_data")
MAX_TEXT = 200
CATEGORIES = {"RAIL", "COMPUTER", "SEA", "WWII", "RADIO", "TELEGRAPH", "FARM", "AUTO",
              "WEATHER", "STL", "SKY"}
DAYS = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def main():
    months = {}
    problems = []
    with open(SRC, newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            where = "line %d (%s)" % (n, row.get("date"))
            try:
                mm, dd = (int(x) for x in row["date"].split("-"))
                ok_date = 1 <= mm <= 12 and 1 <= dd <= DAYS[mm - 1]
            except ValueError:
                ok_date = False
            if not ok_date:
                problems.append(where + ": bad date")
                continue
            text = row["text"].strip()
            if not row["source"].strip():
                problems.append(where + ": no source")
            if row["category"] not in CATEGORIES:
                problems.append(where + ": unknown category " + row["category"])
            if len(text) > MAX_TEXT:
                problems.append(where + ": text is %d chars (max %d)" % (len(text), MAX_TEXT))
            if any(ord(c) < 32 or ord(c) > 126 for c in text):
                problems.append(where + ": non-ASCII character in text")
            months.setdefault(mm, {}).setdefault("%02d" % dd, []).append(
                [int(row["year"]), row["category"], text])
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    for mm, days in sorted(months.items()):
        for d in days.values():
            d.sort(key=lambda e: e[0])
        path = os.path.join(OUT, "%02d.json" % mm)
        with open(path, "w", encoding="ascii") as f:
            json.dump(days, f, separators=(",", ":"), sort_keys=True)
        missing = [d for d in range(1, DAYS[mm - 1] + 1) if "%02d" % d not in days]
        print("%02d.json: %d days, %d entries, %d bytes%s" % (
            mm, len(days), sum(len(v) for v in days.values()), os.path.getsize(path),
            ("  (no entry yet: %s)" % ", ".join(map(str, missing))) if missing else ""))


if __name__ == "__main__":
    main()
