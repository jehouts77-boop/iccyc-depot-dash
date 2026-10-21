# otaguard.py - the safety net behind over-the-air updates (roadmap 5.13)
#
# main.py calls check() before it starts the app. This file and main.py are
# the two files an update NEVER replaces: whatever an update does to the rest,
# the code that can undo it stays as it was. Keep it small and dependency-free.
#
# How an update is installed (ota.py): the new files are downloaded and
# checked in /ota_new, then /ota_pending.json is written and the files are
# swapped in one by one - the old copy of each goes to /ota_old - and the unit
# restarts "on trial". Once the app has run for a minute it deletes the
# pending note (ota.confirm) and the update stands.
#
# check() puts the old files back if
#   - the power went off in the middle of the swap (stage "swapping"), or
#   - the unit has started MAX_TRIES times on trial without the app ever
#     running for that minute (a crash loop: main.py restarts after a crash).
# The version that failed is remembered in /ota_bad.json so the next nightly
# check does not install the very same files again.

import json
import os

ROOT = ""                 # the tests point this at a folder; on the Presto it is "/"
MAX_TRIES = 2
PENDING = "/ota_pending.json"
LAST = "/ota_last.json"
BAD = "/ota_bad.json"
OLD = "/ota_old"
NEW = "/ota_new"
message = ""              # what check() did at this start-up, for the UPDATES screen


def _read(name):
    try:
        with open(ROOT + name) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write(name, obj):
    with open(ROOT + name, "w") as f:
        json.dump(obj, f)


def exists(path):
    try:
        os.stat(ROOT + path)
        return True
    except OSError:
        return False


def remove(path):
    try:
        os.remove(ROOT + path)
    except OSError:
        pass


def make_dirs(path):
    """Create the folders a file path needs (path = '/a/b/file')."""
    parts = path.split("/")[1:-1]
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            os.mkdir(ROOT + cur)
        except OSError:
            pass


def restore(note):
    """Put back the files an install replaced. note = the pending / last note."""
    n = 0
    for path in note.get("files", ()):
        if exists(OLD + path):
            remove(path)
            make_dirs(path)
            os.rename(ROOT + OLD + path, ROOT + path)
            n += 1
        elif path in note.get("added", ()) and not exists(NEW + path):
            remove(path)              # a file the update added, and it was moved in: take it out
            n += 1
        # otherwise: the swap never reached this file - it is still the old one
    return n


def rollback(note, why):
    n = restore(note)
    _write(BAD, {"tree": note.get("tree", ""), "why": why})
    remove(PENDING)
    remove(LAST)
    return n


def check():
    """Call once at start-up, before the app. Returns a short message when it
    put the old version back (for the screen / the log), else ''."""
    global message
    message = _check()
    return message


def _check():
    note = _read(PENDING)
    if note is None:
        if exists(PENDING):               # unreadable note: nothing safe to do with it
            remove(PENDING)
        return ""
    if note.get("stage") == "swapping":
        n = rollback(note, "power lost during the install")
        return "UPDATE UNDONE (INTERRUPTED): %d FILES PUT BACK" % n
    tries = note.get("tries", 0) + 1
    if tries > MAX_TRIES:
        n = rollback(note, "the new version did not stay running")
        return "UPDATE UNDONE (IT KEPT CRASHING): %d FILES PUT BACK" % n
    note["tries"] = tries
    _write(PENDING, note)
    return ""
