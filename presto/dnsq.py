# dnsq.py - name lookups with a time limit, and a memory of the answers
# (added 2026-11-28 for APP 0.4; roadmap 7.1's screen-freeze finding).
#
# Why: MicroPython's socket.getaddrinfo() has no time limit. During the soak
# test a hung lookup froze the screen, knob and clock for ~28 s on all three
# units at once (Fri 11/13 ~11:01), and shorter 7-15 s stalls came from the
# same place. So the unit now asks the DNS server itself, over UDP:
#   - at most ASK_S seconds per server, two servers at most: the router's own
#     server first (the one DHCP handed out), then a public one (see PUBLIC);
#     a name whose router address wouldn't connect asks only the public ones
#     from then on (until the next restart);
#   - each answer is kept for its time-to-live (between KEEP_MIN_S and
#     KEEP_MAX_S), so most requests need no lookup at all;
#   - if no server answers, the last address that worked for that name is
#     used (an old address almost always still works);
#   - only if no server answers AND nothing is kept does the request fail -
#     straight away, and the screen's own retry tries again later;
#   - getaddrinfo() is still the safety net, but only for an answer this code
#     can't read (it never waits on a server that doesn't answer).
# Worst case for a lookup: about 2 x ASK_S = 4 s (was ~28 s).
#
# Only IPv4 addresses are asked for (type A) - the ISS listener already put
# IPv4 first (2026-10-14) because an IPv6 address there never connected.

import time
import socket
import struct

try:
    import network
except ImportError:          # desktop simulator
    network = None

ASK_S = 2                    # longest wait for one server's answer
KEEP_MIN_S = 60
KEEP_MAX_S = 3600            # kept answers are asked again at least hourly
KEEP_N = 16                  # names remembered (the unit uses about 8)
PUBLIC = ("1.1.1.1", "8.8.8.8")   # Cloudflare, then Google (as before 0.4)

_kept = {}                   # name -> [address, ticks_ms when it goes stale]
_public_names = set()        # names whose router answer wouldn't connect: public only
#                              until the next restart (as the 10/17 switch did)
_public_i = 0                # which public server to ask next
router = None                # the router's DNS server, as last read

# Counters for the Diagnostics screen
asked = 0                    # lookups that went to a server
hits = 0                     # answered from memory, still fresh
public = 0                   # answered by the public server (the router's didn't)
old = 0                      # no answer: used the last address that worked
fails = 0                    # no answer and nothing kept: the request failed
safety = 0                   # handed to getaddrinfo (an answer we couldn't read)
last_ms = 0                  # how long the most recent lookup that went out took


def sockaddr(ip, port):
    """A socket address for a numeric IP. getaddrinfo() on a number answers at
    once (lwIP checks for a number before any lookup), and its result is the
    form every MicroPython port accepts for connect() / sendto()."""
    return socket.getaddrinfo(ip, port)[0][-1]


def _is_ip(host):
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() for p in parts)


def router_dns():
    """The DNS server DHCP handed out, as text, or None."""
    global router
    s = None
    try:
        s = network.ipconfig("dns")
    except Exception:
        try:
            w = network.WLAN(network.STA_IF)
            if w.isconnected():
                s = w.ifconfig()[3]
        except Exception:
            pass
    if s and _is_ip(str(s)) and str(s) != "0.0.0.0":
        router = str(s)
    return router


def _query(name, qid):
    q = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)     # standard query, recursion wanted
    for label in name.split("."):
        if label:
            b = label.encode()
            q += bytes((len(b),)) + b
    return q + b"\x00" + struct.pack(">HH", 1, 1)           # type A, class IN


def _skip_name(msg, i):
    """Index just past the name that starts at msg[i] (labels or a pointer)."""
    while True:
        n = msg[i]
        if n == 0:
            return i + 1
        if n & 0xC0 == 0xC0:
            return i + 2
        i += 1 + n


def parse(msg, qid):
    """(addresses, ttl) from a reply. ([], 0) = the name doesn't exist / no A
    record. Raises ValueError for a reply this code can't read."""
    if len(msg) < 12:
        raise ValueError("short reply")
    rid, flags, qd, an, _, _ = struct.unpack(">HHHHHH", msg[:12])
    if rid != qid:
        raise ValueError("wrong id")
    if flags & 0x0200:
        raise ValueError("cut short")                        # TC: too big for UDP
    rcode = flags & 0x000F
    if rcode == 3:                                           # NXDOMAIN
        return [], 0
    if rcode != 0:
        raise ValueError("server error %d" % rcode)
    i = 12
    for _ in range(qd):
        i = _skip_name(msg, i) + 4
    addrs, ttl = [], KEEP_MAX_S
    for _ in range(an):
        i = _skip_name(msg, i)
        typ, cls, t, rdlen = struct.unpack(">HHIH", msg[i:i + 10])
        i += 10
        if typ == 1 and cls == 1 and rdlen == 4:             # an A record (CNAMEs are skipped)
            addrs.append("%d.%d.%d.%d" % tuple(msg[i:i + 4]))
            ttl = min(ttl, t)
        i += rdlen
    if i > len(msg):
        raise ValueError("cut off")
    return addrs, ttl


def _ask(server, name):
    """Ask one server. (addresses, ttl), or None if it didn't answer in time.
    Raises ValueError for a reply that can't be read."""
    try:
        import random
        qid = random.getrandbits(16)
    except Exception:
        qid = time.ticks_ms() & 0xFFFF
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(ASK_S)
        s.sendto(_query(name, qid), sockaddr(server, 53))
        end = time.ticks_add(time.ticks_ms(), ASK_S * 1000)
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            msg = s.recv(512)
            try:
                return parse(msg, qid)
            except ValueError as e:
                if str(e) != "wrong id":                     # a late reply to an earlier ask: skip
                    raise
        return None
    except OSError:                                          # timed out, or no route (WiFi down)
        return None
    finally:
        s.close()


def _keep(name, addr, ttl):
    if name not in _kept and len(_kept) >= KEEP_N:
        _kept.pop(next(iter(_kept)))
    keep = max(KEEP_MIN_S, min(KEEP_MAX_S, ttl))
    _kept[name] = [addr, time.ticks_add(time.ticks_ms(), keep * 1000)]


def forget(name):
    _kept.pop(name, None)


def resolve(name, public_first=False):
    """The IPv4 address for `name`, as text. Raises OSError if it can't be found.
    public_first: skip the router's server and anything kept (used when an
    address from it wouldn't connect - the adsb.lol problem of 2026-10-17).
    That name then stays with the public servers until the next restart."""
    global asked, hits, public, old, fails, safety, last_ms, _public_i
    if _is_ip(name):
        return name
    if public_first:
        _public_names.add(name)
    skip_router = name in _public_names
    k = _kept.get(name)
    if k and not public_first and time.ticks_diff(k[1], time.ticks_ms()) > 0:
        hits += 1
        return k[0]
    asked += 1
    t0 = time.ticks_ms()
    servers = []
    r = None if skip_router else router_dns()
    if r:
        servers.append(r)
    pub = [p for p in PUBLIC if p != r]
    servers.append(pub[_public_i % len(pub)])
    if not r and len(pub) > 1:                  # no router asked: both public ones
        servers.append(pub[(_public_i + 1) % len(pub)])
    unreadable = None
    try:
        for n, server in enumerate(servers):
            try:
                got = _ask(server, name)
            except ValueError as e:
                unreadable = e
                continue
            if got is None:
                if server in PUBLIC:
                    _public_i += 1                           # next time, the other public one
                continue
            addrs, ttl = got
            if not addrs:
                raise OSError(-2, "no such name")            # same number getaddrinfo gives
            if server != r:
                public += 1
            _keep(name, addrs[0], ttl)
            return addrs[0]
        if k:                                                # nobody answered: the old address
            old += 1
            return k[0]
        if unreadable is not None:                           # an answer we couldn't read
            safety += 1
            print("dns: %s - asking getaddrinfo (%s)" % (name, unreadable))
            return socket.getaddrinfo(name, 80)[0][-1][0]
        fails += 1
        raise OSError(-2, "no DNS answer")
    finally:
        last_ms = time.ticks_diff(time.ticks_ms(), t0)


def summary():
    """Short counts for the Diagnostics screen: lookups that went out, answered
    by the public server, old address used, failed (cache hits not shown)."""
    return "DNS %d pub %d old %d fail %d" % (asked, public, old, fails)
