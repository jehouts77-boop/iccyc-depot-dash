# isslisten.py - hears the ISS over ham radio (roadmap 5.7a, stage 1: "ISS LAST HEARD")
#
# Keeps one connection open to APRS-IS, the internet side of ham radio's APRS,
# as a listener only (passcode -1: it can never transmit). The server is asked
# to send just two kinds of packet:
#   b/RS0ISS*/NA1SS*   sent BY the ISS - its beacon, every ~3 min during a pass
#   d/RS0ISS*/NA1SS*   relayed BY the ISS - hams talking through it
# Found in the 2026-10-14 capture (validation\aprs_iss_capture.py): a few passes
# a day get heard, by ground stations all over the world; the beacon's own
# position is a dummy (about 0N 0E), so where the ISS was is looked up from
# wheretheiss.at the moment a packet arrives (app.py does that request).
#
# Unlike the screens' data, this listens all the time: a pass lasts minutes and
# can come at any hour. It costs nothing between packets - the server sends a
# one-line keep-alive about every 20 s.
#
# Connection rules (from the capture test):
#   - every address the name resolves to is tried, IPv4 first, each with a
#     socket of its own kind (an IPv6 address first left the test stuck for 2 h)
#   - silence for SILENCE_S = dead: hang up and reconnect
#   - failed tries back off: 15 s, 30, 60 ... up to 5 min, reset once connected
#
# The last packet heard is kept in /iss_heard.json, so a restart (or the
# nightly update) doesn't forget it.
#
# Login name: config iss.aprs_login. A ham's unit can use their own callsign
# (set in that unit's /config.json); the others use a name that isn't a
# callsign (ICCYC1, ICCYC2) - the server
# answers "unverified", which is all a listener needs. Give each unit its own.

import json
import time
try:
    import usocket as socket
except ImportError:
    import socket
import aprs
import dnsq

SERVERS = (("rotate.aprs2.net", 14580), ("noam.aprs2.net", 14580))
FILTER = "b/RS0ISS*/NA1SS* d/RS0ISS*/NA1SS*"
SILENCE_S = 120
RETRY_S = (15, 30, 60, 120, 300)
CONNECT_TIMEOUT_S = 5
MAX_LINE = 600
SAVE_PATH = "/iss_heard.json"


class Listener:
    def __init__(self, cfg, save_path=None):
        self.cfg = cfg
        self.save_path = save_path or SAVE_PATH
        self.sock = None
        self.buf = b""
        self.state = "off"            # off / listening / waiting
        self.server = ""
        self.login_reply = ""
        self.next_try = 0             # time.time() of the next connect
        self.tries = 0                # failed tries in a row (for the back-off)
        self.last_rx = 0
        self.connects = 0
        self.drops = 0
        self.fails = 0
        self.packets = 0
        self.last_error = ""
        self.heard = None             # what the ISS page shows (see _keep)
        self.want_pos = False         # app.py: look up where the ISS is, for self.heard
        self._load()

    # ---------- the last packet, kept across restarts ----------
    def _load(self):
        try:
            with open(self.save_path) as f:
                h = json.load(f)
            if isinstance(h, dict) and isinstance(h.get("t"), (int, float)):
                self.heard = h
        except (OSError, ValueError):
            pass

    def _save(self):
        try:
            with open(self.save_path, "w") as f:
                json.dump(self.heard, f)
        except OSError as e:
            self.last_error = "save: %s" % e

    # ---------- connection ----------
    def due(self, now=None):
        if now is None:
            now = time.time()
        return self.sock is None and now >= self.next_try

    def connect(self, now=None):
        """One try at connecting (blocks up to a few seconds). True when up."""
        if now is None:
            now = time.time()
        login = self.cfg["iss"].get("aprs_login") or "ICCYC1"
        last = None
        for host, port in SERVERS:
            try:                                  # APP 0.4: dnsq (time limit, IPv4 only)
                addrs = [dnsq.sockaddr(dnsq.resolve(host), port)]
            except Exception as e:
                last = e
                continue
            for addr in addrs:
                s = None
                try:
                    s = socket.socket()
                    s.settimeout(CONNECT_TIMEOUT_S)
                    s.connect(addr)
                    s.send(("user %s pass -1 vers ICCYC-Console 1.0 filter %s\r\n"
                            % (login, FILTER)).encode())
                    s.settimeout(0)               # from here on: never wait for data
                    self.sock, self.buf, self.server = s, b"", host
                    self.state = "listening"
                    self.last_rx = now
                    self.connects += 1
                    self.tries = 0
                    return True
                except Exception as e:
                    last = e
                    dnsq.forget(host)             # ask afresh next time (round-robin names)
                    if s is not None:
                        try:
                            s.close()
                        except Exception:
                            pass
        self.fails += 1
        self.last_error = ("%s: %s" % (type(last).__name__, last))[:60] if last else "no servers"
        self._wait(now)
        return False

    def _wait(self, now):
        self.state = "waiting"
        self.next_try = now + RETRY_S[min(self.tries, len(RETRY_S) - 1)]
        self.tries += 1

    def _hang_up(self, now, why):
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.drops += 1
        self.last_error = why[:60]
        self.tries = 0                    # it was working: first retry soon
        self._wait(now)

    def stop(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.state = "off"

    # ---------- reading ----------
    def poll(self, now=None):
        """Read whatever has arrived, without waiting. True if self.heard changed."""
        if self.sock is None:
            return False
        if now is None:
            now = time.time()
        changed = False
        while True:
            try:
                data = self.sock.recv(512)
            except OSError as e:
                code = e.args[0] if e.args else None
                if code in (11, 35, 110, 115, 116, 10035) or type(e).__name__ in (
                        "BlockingIOError", "timeout", "TimeoutError"):
                    break                     # nothing more for now
                self._hang_up(now, "%s: %s" % (type(e).__name__, e))
                return changed
            if not data:
                self._hang_up(now, "server closed the connection")
                return changed
            self.last_rx = now
            self.buf += data
            while True:
                i = self.buf.find(b"\n")
                if i == -1:
                    break
                raw, self.buf = self.buf[:i], self.buf[i + 1:]
                line = "".join(chr(b) if 32 <= b < 127 else "?" for b in raw.rstrip(b"\r"))
                if self._line(line, now):
                    changed = True
            if len(self.buf) > MAX_LINE:
                self.buf = b""                # a line that never ends: drop it
        if now - self.last_rx > SILENCE_S:
            self._hang_up(now, "silent for %d s" % SILENCE_S)
        return changed

    def _line(self, line, now):
        if line.startswith("#"):
            if "logresp" in line:
                self.login_reply = line[2:].strip()[:60]
            return False
        try:
            p = aprs.parse_line(line)
        except Exception:
            return False                      # one bad line must never stop the listener
        if p is None or not (p["from_iss"] or p["via_iss"]):
            return False
        self.packets += 1
        self._keep(p, now)
        return True

    def _keep(self, p, now):
        """What the ISS page shows: the newest packet, and where the ISS was then."""
        h = {"t": now, "kind": "beacon" if p["from_iss"] else "relay", "by": p["heard_by"],
             "src": p["src"], "text": p["comment"][:40], "lat": None, "lon": None}
        self.heard = h
        self.want_pos = True
        self._save()

    def place(self, pos, now=None):
        """app.py looked up the ISS: pos = iss.py's dict, or None if that failed."""
        if now is None:
            now = time.time()
        self.want_pos = False
        h = self.heard
        if h is None or pos is None or now - h["t"] > 120:
            return
        h["lat"], h["lon"] = pos["lat"], pos["lon"]
        self._save()

    def status(self):
        """One line for Diagnostics."""
        return "%s %s c%d d%d f%d p%d" % (self.state.upper(), self.server.split(".")[0],
                                          self.connects, self.drops, self.fails, self.packets)
