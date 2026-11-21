# ota.py - over-the-air updates from GitHub (roadmap 5.13; Presto only)
#
# Decided 2026-10-07 (Jason): a unit checks by itself once a night and
# installs what it finds; units follow the "release" branch, which only ever
# gets code that has been confirmed on a real unit. Settings > UPDATES shows
# the state and has CHECK NOW and PUT BACK THE OLD VERSION.
#
# Where from: config "ota" -> repo + branch. No password, so the repo must be
# public (a private repo simply answers "not found" and nothing happens).
#   1. ONE request lists every file in the branch with its fingerprint (git
#      blob SHA-1) and size:  api.github.com/repos/<repo>/git/trees/<branch>?recursive=1
#   2. Only repo files under presto/ ending .py .json .af are looked at; they
#      map to the same path on the Presto (presto/screens/x.py -> /screens/x.py).
#      Each one's fingerprint is compared with the file on the Presto, so only
#      files that really differ are downloaded:  raw.githubusercontent.com/<repo>/<branch>/<path>
#   3. Each download goes to /ota_new and must match the listed size and
#      fingerprint; a .py file must also compile. Anything wrong: stop, change
#      nothing, try again the next night.
#   4. Only when every file is in and checked: swap them in (old copies to
#      /ota_old), restart on trial. otaguard.py undoes it if the new version
#      does not stay up.
#
# Never touched: main.py and otaguard.py (the safety net), /config.json,
# secrets.py, and anything outside the list in step 2. Files removed from the
# repo are left on the Presto.
#
# One web request per call to step(), like weather.py - the app calls it once
# a second while an update is under way, so the clock keeps running.

import json
import os
import time
import net
import otaguard as G

try:
    import hashlib
    import binascii
except ImportError:
    hashlib = None

API = "https://api.github.com/repos/%s/git/trees/%s?recursive=1"
RAW = "https://raw.githubusercontent.com/%s/%s/%s"
PREFIX = "presto/"
KINDS = (".py", ".json", ".af")
NEVER = ("/main.py", "/otaguard.py", "/config.json", "/secrets.py")
TREE_MAX_BYTES = 300_000
FILE_MAX_BYTES = 400_000
STATE = "/ota_state.json"
CONFIRM_AFTER_S = 60          # the app must run this long before an update stands

# Update log (added 2026-11-21): on the first real round trip (APP 0.1 -> 0.2,
# then PUT BACK OLD) the bench unit refused 0.2 as it should but came back up
# still running 0.2 - the file put back was not the old one. Nothing in the
# code explains it (a desktop simulation of every short sequence puts 0.1
# back), so each install / confirm / undo now writes what it found and did to
# /ota_log.txt, shown on Diagnostics page 2 (turn the knob).
LOG = "/ota_log.txt"
LOG_MAX = 3000                # bytes; past this the older half is dropped


def log(msg):
    """Append one line to the update log. Never raises: logging must not stop an update."""
    try:
        line = "%d %s\n" % (time.time(), msg)
        try:
            old = open(G.ROOT + LOG).read()
        except OSError:
            old = ""
        if len(old) + len(line) > LOG_MAX:
            old = old[len(old) // 2:]
            old = old[old.find("\n") + 1:]
        with open(G.ROOT + LOG, "w") as f:
            f.write(old + line)
    except Exception as e:
        print("ota log:", e)


def describe(path):
    """'v0.2 1a2b3c4' for an app.py, '1a2b3c4' for other files, 'NONE' if missing."""
    sha = git_sha(path)
    if sha is None:
        try:
            return "(folder)" if os.stat(G.ROOT + path)[0] & 0x4000 else "NONE"
        except OSError:
            return "NONE"
    ver = ""
    if path.endswith("app.py"):
        try:
            for ln in open(G.ROOT + path):
                if ln.startswith("VERSION"):
                    ver = "v" + ln.split("=", 1)[1].strip().strip('"') + " "
                    break
        except Exception:
            pass
    return ver + sha[:7]


def git_sha(path):
    """The git fingerprint of a file on the Presto, or None if it isn't there."""
    try:
        size = os.stat(G.ROOT + path)[6]
        h = hashlib.sha1(("blob %d\x00" % size).encode())
        with open(G.ROOT + path, "rb") as f:
            while True:
                chunk = f.read(2048)
                if not chunk:
                    break
                h.update(chunk)
        return binascii.hexlify(h.digest()).decode()
    except OSError:
        return None


def managed(repo_path):
    """Repo path -> path on the Presto, or None if updates don't handle it."""
    if not repo_path.startswith(PREFIX):
        return None
    dest = "/" + repo_path[len(PREFIX):]
    if dest in NEVER or dest.split("/")[-1] in ("secrets.py", "config.json"):
        return None
    for k in KINDS:
        if dest.endswith(k):
            return dest
    return None


def free_bytes():
    try:
        st = os.statvfs(G.ROOT or "/")
        return st[0] * st[3]
    except Exception:
        return None


class Ota:
    def __init__(self, cfg, reset=None):
        self.cfg = cfg
        self.c = cfg["ota"]
        self.reset = reset            # called after an install (machine.reset on the Presto)
        st = G._read(STATE) or {}
        self.tree = st.get("tree", "")        # the version installed here ("" = not known)
        bad = G._read(G.BAD)
        if bad and bad.get("tree") == self.tree:
            self.tree = ""                    # that version was undone: it is not what runs here
        self.checked = st.get("checked")      # time.time() of the last finished check
        self.state = "idle"       # idle / checking / downloading / installing / failed
        self.msg = "NOT CHECKED YET" if not self.checked else "UP TO DATE"
        self.queue = []
        self.todo = []            # [(dest, repo path, sha, size)] this round
        self.done = 0
        self.new_tree = ""
        self.ran_day = None       # the day the nightly check last ran
        self.checks = self.installs = self.fails = 0
        self.last_ms = 0
        self.trial = G.exists(G.PENDING)      # started on trial after an install
        self.undone = G.message               # otaguard undid an update at this start-up
        if self.undone:
            self.msg = self.undone
            log("start-up: " + self.undone)
        if self.trial:
            note = G._read(G.PENDING) or {}
            log("start-up on trial %s, try %s" % (note.get("tree", "")[:7], note.get("tries")))

    # ---------- what the screens ask ----------
    def busy(self):
        return self.state in ("checking", "downloading", "installing")

    def can_undo(self):
        return (not self.busy()) and G._read(G.LAST) is not None

    def led(self):
        """0 off, 2 slow blink (checking / downloading), 3 fast (installing)."""
        return 3 if self.state == "installing" else 2 if self.busy() else 0

    # ---------- starting ----------
    def start(self):
        if self.busy():
            return
        if hashlib is None or not hasattr(hashlib, "sha1"):
            self._fail("THIS FIRMWARE HAS NO SHA-1")
            return
        self.state = "checking"
        self.msg = "CHECKING"
        self.queue = [("tree",)]
        self.todo = []
        self.done = 0

    def nightly(self, t):
        """Call every second with the local time: starts the nightly check."""
        if not self.c.get("auto", True) or self.busy():
            return
        if "%02d:%02d" % (t[3], t[4]) == self.c.get("time", "03:30") and self.ran_day != t[7]:
            self.ran_day = t[7]
            self.start()

    def confirm(self):
        """The app has run long enough: the installed update stands."""
        if self.trial:
            note = G._read(G.PENDING)
            if note is not None:
                G._write(G.LAST, note)        # kept so it can still be undone by hand
            G.remove(G.PENDING)
            self.trial = False
            log("confirmed %s (undo note kept: %s)" % (
                (note or {}).get("tree", "")[:7], G._read(G.LAST) is not None))

    # ---------- one request per call ----------
    def step(self):
        if not self.queue:
            return
        job = self.queue.pop(0)
        t0 = time.ticks_ms()
        try:
            if job[0] == "tree":
                self._tree()
            else:
                self._get(job[1])
        except Exception as e:
            self._fail(("%s: %s" % (type(e).__name__, e))[:60])
        self.last_ms = time.ticks_diff(time.ticks_ms(), t0)
        if self.state == "downloading" and not self.queue:
            try:
                self._install()
            except Exception as e:             # e.g. the flash filled up half-way through
                note = G._read(G.PENDING)
                if note is not None:
                    G.restore(note)            # put back whatever had been swapped
                    G.remove(G.PENDING)
                self._fail(("INSTALL FAILED: %s: %s" % (type(e).__name__, e))[:60])

    def _fail(self, why):
        self.fails += 1
        self.state = "failed"
        self.msg = why
        self.queue = []
        print("ota:", why)

    def _save(self):
        try:
            G._write(STATE, {"tree": self.tree, "checked": self.checked})
        except OSError:
            pass

    def _tree(self):
        self.checks += 1
        url = API % (self.c["repo"], self.c["branch"])
        code, body = net.http_get(url, timeout_s=15, max_bytes=TREE_MAX_BYTES,
                                  headers={"Accept": "application/vnd.github+json"})
        if code == 404:
            return self._fail("NO UPDATES PUBLISHED (%s NOT FOUND)" % self.c["branch"].upper())
        if code != 200:
            return self._fail("GITHUB ANSWERED %s" % code)
        doc = json.loads(body)
        body = None
        if doc.get("truncated") or not isinstance(doc.get("tree"), list):
            return self._fail("FILE LIST INCOMPLETE")
        new_tree = doc.get("sha", "")
        self.checked = time.time()
        bad = G._read(G.BAD)
        if bad and bad.get("tree") == new_tree:
            self.state = "idle"
            self.msg = "WAITING FOR A FIX (THE LAST UPDATE WAS UNDONE)"
            return self._save()
        if new_tree and new_tree == self.tree:
            return self._up_to_date()
        todo = []
        total = 0
        for e in doc["tree"]:
            if e.get("type") != "blob":
                continue
            dest = managed(e.get("path", ""))
            if dest is None:
                continue
            if git_sha(dest) != e.get("sha"):
                todo.append((dest, e["path"], e["sha"], e.get("size", 0)))
                total += e.get("size", 0)
        doc = None
        self.new_tree = new_tree
        if not todo:                           # same files already (e.g. loaded by USB)
            self.tree = new_tree
            return self._up_to_date()
        free = free_bytes()
        if free is not None and free < total + 100_000:
            return self._fail("NOT ENOUGH ROOM (%d KB NEEDED)" % (total // 1024 + 100))
        self.todo = todo
        log("check %s: %d to get, running %s" % (new_tree[:7], len(todo), self.tree[:7] or "-"))
        self.queue = [("get", i) for i in range(len(todo))]
        self.state = "downloading"
        self.msg = "DOWNLOADING 1 OF %d" % len(todo)

    def _up_to_date(self):
        self.state = "idle"
        self.msg = "UP TO DATE"
        self._save()

    def _get(self, i):
        dest, repo_path, sha, size = self.todo[i]
        self.msg = "DOWNLOADING %d OF %d" % (i + 1, len(self.todo))
        tmp = G.NEW + dest
        if git_sha(tmp) != sha:                # (already there from an earlier try: keep it)
            G.make_dirs(tmp)
            code, n = net.http_download(RAW % (self.c["repo"], self.c["branch"], repo_path),
                                        G.ROOT + tmp, timeout_s=15, max_bytes=FILE_MAX_BYTES)
            if code != 200:
                G.remove(tmp)
                return self._fail("DOWNLOAD ANSWERED %s: %s" % (code, dest[-24:]))
            if n != size or git_sha(tmp) != sha:
                G.remove(tmp)
                return self._fail("DOWNLOAD DID NOT MATCH: %s" % dest[-28:])
        if dest.endswith(".py"):
            try:
                with open(G.ROOT + tmp) as f:
                    compile(f.read(), dest, "exec")
            except NameError:
                pass                           # this firmware has no compile(): skip the check
            except Exception as e:
                G.remove(tmp)
                return self._fail("WILL NOT RUN: %s (%s)" % (dest[-22:], type(e).__name__))
        self.done = i + 1

    def _install(self):
        self.state = "installing"
        self.msg = "INSTALLING %d FILES" % len(self.todo)
        files = [t[0] for t in self.todo]
        added = [p for p in files if not G.exists(p)]
        for p in files:                        # a clean backup folder: only this install's files
            G.remove(G.OLD + p)
        note = {"tree": self.new_tree, "from": self.tree, "files": files, "added": added,
                "stage": "swapping", "tries": 0}
        G._write(G.PENDING, note)
        log("install %s from %s: %d files" % (self.new_tree[:7], self.tree[:7] or "-", len(files)))
        for p in files:
            before = describe(p)
            if G.exists(p):
                G.make_dirs(G.OLD + p)
                os.rename(G.ROOT + p, G.ROOT + G.OLD + p)
            G.make_dirs(p)
            os.rename(G.ROOT + G.NEW + p, G.ROOT + p)
            log(" %s was %s; now %s, backup %s" % (p, before, describe(p), describe(G.OLD + p)))
        note["stage"] = "trial"
        G._write(G.PENDING, note)
        G.remove(G.BAD)
        self.tree = self.new_tree
        self._save()
        self.installs += 1
        self.msg = "INSTALLED - RESTARTING"
        if self.reset is not None:
            self.reset()

    # ---------- by hand: put the previous version back ----------
    def undo(self):
        note = G._read(G.LAST)
        if note is None or self.busy():
            return False
        files = note.get("files", ())
        before = [(p, describe(p), describe(G.OLD + p)) for p in files]
        try:
            n = G.rollback(note, "put back by hand")
        except Exception as e:
            log("undo %s FAILED: %s: %s" % (note.get("tree", "")[:7], type(e).__name__, e))
            raise
        log("undo %s: put back %d of %d" % (note.get("tree", "")[:7], n, len(files)))
        for p, was, bk in before:
            log(" %s was %s, backup %s -> now %s" % (p, was, bk, describe(p)))
        self.tree = note.get("from", "")
        self._save()
        self.msg = "OLD VERSION PUT BACK - RESTARTING"
        if self.reset is not None:
            self.reset()
        return True
