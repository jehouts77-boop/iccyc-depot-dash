# net.py - WiFi and memory-safe HTTP (ported from the Model 100 project)
#
# http_get() rules learned the hard way on the Model 100 (plan doc, Learnings 5):
#   - chunks are collected in a list and joined ONCE (bytes += copies everything)
#   - max_bytes caps how much is kept; HTTP/1.0 + Connection: close means
#     hanging up early is allowed, the caller just gets a shorter body
#   - callers pull out the few JSON fields they need with the scan helpers
#     below instead of json.loads() on a big response
#   - (2026-10-17) a site that won't open a connection -> switch to a public
#     DNS server and try once more; see PUBLIC_DNS below

import time
from textutil import bytes_to_ascii

try:
    import network
except ImportError:          # desktop simulator
    network = None

USER_AGENT = "ICCYC-Depot-Dash/1.0 (desk clock; github.com/jehouts77-boop/iccyc-depot-dash)"

_wlan = None
_ssid = None
_started = None              # ticks_ms when the current connect attempt began

# Where the time went in http_get (added 2026-10-07 to find a 7 s freeze):
#   (total, name lookup, connect, TLS, wait for the first byte, body, redirects,
#    bytes, end of the URL) - all times in ms. `last` = the most recent request,
#   `slow` = the slowest since start. Shown on the Diagnostics screen.
last = None
slow = None

# DNS fallback (added 2026-10-17, desk). Found that day: the router's DNS
# (handed out by DHCP) kept answering api.adsb.lol with an address that
# never accepts a connection, while a public DNS server gave a working one. A
# gift unit can meet the same thing at any house, for any site. So: when a
# connection can't be opened (or the name can't be looked up), switch the unit
# to a public DNS server and try once more. It stays switched until the next
# restart (or until the router's DHCP renews the lease and puts its own back -
# then the same thing simply happens again if needed). Only the DNS server
# changes; the unit's own address stays under DHCP.
PUBLIC_DNS = ("1.1.1.1", "8.8.8.8")   # Cloudflare, then Google
CONNECT_TIMEOUT_S = 5                 # opening the connection only (a good one took
#                                       145 ms on the desk Presto); the request itself
#                                       still gets the caller's timeout_s
dns_now = None                        # None = the router's own; else the public one in use
dns_switches = 0                      # times switched (Diagnostics)


def wlan():
    global _wlan
    if _wlan is None and network is not None:
        _wlan = network.WLAN(network.STA_IF)
        _wlan.active(True)
    return _wlan


def start_connect(ssid, password):
    """Start connecting and return at once; check with status()."""
    global _ssid, _started
    w = wlan()
    if w is None or not ssid:
        return False
    try:
        if w.isconnected():
            w.disconnect()
        w.connect(ssid, password)
    except Exception as e:
        print("wifi connect error:", e)
        return False
    _ssid = ssid
    _started = time.ticks_ms()
    return True


def status(timeout_s=20):
    """'up', 'connecting', 'failed' or 'off' (no network set)."""
    w = wlan()
    if w is None or _ssid is None:
        return "off"
    if w.isconnected():
        return "up"
    if _started is not None and time.ticks_diff(time.ticks_ms(), _started) < timeout_s * 1000:
        return "connecting"
    return "failed"


def info():
    """(ssid, ip, rssi) - rssi None if this firmware can't report it."""
    w = wlan()
    if w is None or not w.isconnected():
        return _ssid, None, None
    ip = w.ifconfig()[0]
    try:
        rssi = w.status("rssi")
    except Exception:
        rssi = None
    return _ssid, ip, rssi


def link_code():
    """The radio's own status number while connecting (rp2: -3 wrong password,
    -2 network not found, -1 failed, 1 joining, 3 connected), or None."""
    w = wlan()
    if w is None:
        return None
    try:
        return w.status()
    except Exception:
        return None


def scan():
    """(True, [(shown name, rssi, secured, real name), ...] strongest first) or
    (False, message). The shown name is plain ASCII for the screen; the real
    name is what to connect with (they differ only for names with accents etc.).
    Doesn't trust the scan's 'hidden' field - it was wrong on the Model 100's
    radio (the same CYW43 chip as the Presto's) - a hidden network already
    shows up with an empty name."""
    w = wlan()
    if w is None:
        return False, "NO RADIO"
    try:
        results = w.scan()
        if not results:
            time.sleep_ms(500)
            results = w.scan()
    except Exception as e:
        return False, "SCAN ERROR: %s" % e
    seen = {}
    for entry in results:
        ssid = bytes_to_ascii(entry[0]).strip()
        if not ssid:
            continue
        rssi, security = entry[3], entry[4]
        try:
            real = entry[0].decode()
        except Exception:
            real = ssid
        if ssid not in seen or rssi > seen[ssid][1]:
            seen[ssid] = (ssid, rssi, security != 0, real)
    nets = sorted(seen.values(), key=lambda t: -t[1])
    if not nets:
        return False, "RAW %d, ALL BLANK NAMES" % len(results)
    return True, nets


def dns_server():
    """The DNS server in use now, as text ('-' if unknown)."""
    try:
        return str(network.ipconfig("dns"))
    except Exception:
        pass
    w = wlan()
    try:
        return w.ifconfig()[3] if w is not None and w.isconnected() else "-"
    except Exception:
        return "-"


def use_public_dns():
    """Switch to the next public DNS server. True if the switch worked.
    network.ipconfig(dns=...) changes the DNS server alone; w.ifconfig((...))
    would also fix the address and stop DHCP, so it is not used here."""
    global dns_now, dns_switches
    if network is None:
        return False
    nxt = PUBLIC_DNS[0] if dns_now not in PUBLIC_DNS else \
        PUBLIC_DNS[(PUBLIC_DNS.index(dns_now) + 1) % len(PUBLIC_DNS)]
    try:
        network.ipconfig(dns=nxt)
    except Exception as e:
        print("dns: could not switch to %s: %s" % (nxt, e))
        return False
    dns_now = nxt
    dns_switches += 1
    print("dns: switched to", nxt)
    return True


def _connect(host, port, timeout_s, ph):
    """Look the name up and open a plain connection to it. If either step fails,
    switch to a public DNS server and try once more (see PUBLIC_DNS above).
    ph[0] / ph[1] collect the lookup and connect times."""
    import socket
    for attempt in (1, 2):
        t = time.ticks_ms()
        try:
            addr = socket.getaddrinfo(host, port)[0][-1]
        except OSError as e:
            ph[0] += time.ticks_diff(time.ticks_ms(), t)
            if attempt == 1 and use_public_dns():
                print("net: lookup of %s failed (%s) - trying again" % (host, e))
                continue
            raise
        t1 = time.ticks_ms()
        ph[0] += time.ticks_diff(t1, t)
        s = socket.socket()
        s.settimeout(min(CONNECT_TIMEOUT_S, timeout_s))
        try:
            s.connect(addr)
        except OSError as e:
            s.close()
            ph[1] += time.ticks_diff(time.ticks_ms(), t1)
            if attempt == 1 and use_public_dns():
                print("net: %s at %s did not answer (%s) - trying again" % (host, addr, e))
                continue
            raise
        ph[1] += time.ticks_diff(time.ticks_ms(), t1)
        s.settimeout(timeout_s)
        return s


def url_quote(s):
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    return "".join(ch if ch in safe else "%%%02X" % (ord(ch) & 0xFF) for ch in s)


def http_get(url, timeout_s=10, max_redirects=3, user_agent=USER_AGENT, max_bytes=None,
             headers=None):
    """GET over HTTP/1.0. Returns (status, body_str). Raises on socket errors,
    so callers wrap it in try/except. Records where the time went (see `last`)."""
    global last, slow
    ph = [0, 0, 0, 0, 0, 0, 0]       # lookup, connect, TLS, first byte, body, redirects, bytes
    t0 = time.ticks_ms()
    try:
        return _http_get(url, timeout_s, max_redirects, user_agent, max_bytes, headers, ph)
    finally:
        last = (time.ticks_diff(time.ticks_ms(), t0),) + tuple(ph) + (url[-24:],)
        if slow is None or last[0] > slow[0]:
            slow = last


def _http_get(url, timeout_s, max_redirects, user_agent, max_bytes, headers, ph):
    import ssl
    for _ in range(max_redirects + 1):
        scheme, rest = url.split("://", 1)
        host_part, _, path = rest.partition("/")
        path = "/" + path
        if ":" in host_part:
            host, port_s = host_part.split(":", 1)
            port = int(port_s)
        else:
            host = host_part
            port = 443 if scheme == "https" else 80
        s = _connect(host, port, timeout_s, ph)     # lookup + connect (DNS fallback inside)
        t1 = time.ticks_ms()
        try:
            if scheme == "https":
                t = t1
                s = ssl.wrap_socket(s, server_hostname=host)
                t1 = time.ticks_ms()
                ph[2] += time.ticks_diff(t1, t)
            t = t1
            req = "GET %s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n" % (path, host)
            if user_agent:
                req += "User-Agent: %s\r\n" % user_agent
            if headers:
                for k, v in headers.items():
                    req += "%s: %s\r\n" % (k, v)
            s.write((req + "\r\n").encode())
            chunks = []
            total = 0
            while True:
                chunk = s.read(512)
                if not chunks:                       # first read: the server has answered
                    t1 = time.ticks_ms()
                    ph[3] += time.ticks_diff(t1, t)
                    t = t1
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if max_bytes is not None and total >= max_bytes:
                    break
        finally:
            s.close()
        ph[4] += time.ticks_diff(time.ticks_ms(), t)
        ph[6] += total
        resp = b"".join(chunks)
        chunks = None
        head, _, body = resp.partition(b"\r\n\r\n")
        # split into lines first: bytes_to_ascii turns a newline into "?" (fixed
        # 2026-10-07 - before this the headers were never seen, so a redirect was
        # never followed)
        lines = [bytes_to_ascii(ln) for ln in head.split(b"\r\n")]
        code = int(lines[0].split()[1])
        hdrs = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                hdrs[k.strip().lower()] = v.strip()
        if code in (301, 302, 303, 307, 308) and "location" in hdrs:
            loc = hdrs["location"]
            url = loc if "://" in loc else "%s://%s%s" % (scheme, host_part, loc)
            ph[5] += 1
            continue
        try:
            return code, body.decode("utf-8")
        except UnicodeError:
            return code, bytes_to_ascii(body)
    return None, "TOO MANY REDIRECTS"




def http_download(url, dest, timeout_s=15, max_bytes=None, user_agent=USER_AGENT):
    """GET a file straight into `dest` on the flash, byte for byte (fonts are
    not text), never holding more than one chunk in memory. Returns
    (status, bytes written). No redirects. Raises on socket errors.
    Separate from http_get() on purpose: that one is confirmed on hardware
    and stays as it is. Used by ota.py."""
    import ssl
    scheme, rest = url.split("://", 1)
    host_part, _, path = rest.partition("/")
    if ":" in host_part:
        host, port_s = host_part.split(":", 1)
        port = int(port_s)
    else:
        host = host_part
        port = 443 if scheme == "https" else 80
    s = _connect(host, port, timeout_s, [0, 0])  # lookup + connect (DNS fallback inside)
    try:
        if scheme == "https":
            s = ssl.wrap_socket(s, server_hostname=host)
        req = "GET /%s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n" % (path, host)
        if user_agent:
            req += "User-Agent: %s\r\n" % user_agent
        s.write((req + "\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:          # the headers end at the first blank line
            chunk = s.read(512)
            if not chunk:
                break
            head += chunk
            if len(head) > 8192:
                raise ValueError("headers too long")
        head, _, first = head.partition(b"\r\n\r\n")
        code = int(head.split(b"\r\n")[0].split()[1])
        if code != 200:
            return code, 0
        n = 0
        with open(dest, "wb") as f:
            chunk = first
            while chunk:
                n += len(chunk)
                if max_bytes is not None and n > max_bytes:
                    raise ValueError("file too big")
                f.write(chunk)
                chunk = s.read(1024)
        return code, n
    finally:
        s.close()


# ---- Hand-scanning JSON (pull a few fields out of a big response) ----

# Speed note (found on the Presto 2026-10-07): in MicroPython s[i] on a str is
# NOT instant - it counts characters from the start every time, so a loop that
# walks a 6 KB string with s[i] does about 20 million steps (a 20-stop train
# took ~6 s to read). These helpers therefore step through the text with
# `for c in ...` (which is instant per character) and never index a long string
# inside a loop.

def find_matching_bracket(s, open_idx):
    """s[open_idx] is '{' or '['; returns the index of its match, skipping
    anything inside quoted strings. -1 if the text is cut off first."""
    depth = 0
    in_str = esc = False
    i = open_idx
    for c in (s[open_idx:] if open_idx else s):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{" or c == "[":
            depth += 1
        elif c == "}" or c == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def json_str_after(s, marker, start=0):
    """Read the JSON string right after `marker` (e.g. '"name":"'). '' if absent."""
    idx = s.find(marker, start)
    if idx == -1:
        return ""
    out = []
    esc = False
    uni = None                      # collecting the 4 hex digits of a \uXXXX
    for c in s[idx + len(marker):]:
        if uni is not None:
            uni += c
            if len(uni) == 4:
                try:
                    out.append(chr(int(uni, 16)))
                except ValueError:
                    out.append("?")
                uni = None
        elif esc:
            esc = False
            if c == "u":
                uni = ""
            else:
                out.append(" " if c in "ntr" else c)
        elif c == "\\":
            esc = True
        elif c == '"':
            break
        else:
            out.append(c)
    return "".join(out)


def json_num_after(s, marker, start=0):
    """Read the number right after `marker` (e.g. '"value":'). None if absent
    or null. Returns an int when it has no decimal point, else a float."""
    idx = s.find(marker, start)
    if idx == -1:
        return None
    i = idx + len(marker)
    txt = ""
    for c in s[i:i + 40]:           # a short piece: no number is longer than this
        if c == " " and not txt:
            continue
        if c not in "-+.0123456789eE":
            break
        txt += c
    if not txt:
        return None
    try:
        return float(txt) if ("." in txt or "e" in txt or "E" in txt) else int(txt)
    except ValueError:
        return None
