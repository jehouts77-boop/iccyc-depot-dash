# aprs.py - read APRS packets (roadmap 5.7a, the ISS heard over ham radio)
#
# APRS is ham radio's position-reporting system. Ground stations that hear a
# packet pass it to the internet side, APRS-IS, as one text line:
#
#   N0CALL-7>APK004,RS0ISS*,qAR,N0CALL-10:=4903.50N/07201.75W-Test message
#   ^ sender  ^ to   ^ path (who relayed it)  ^ payload (what was sent)
#
# A '*' in the path marks a station that has already repeated the packet; a
# packet with RS0ISS* (or NA1SS*) in its path went up to the International
# Space Station and back down.
#
# Positions come in three formats, and the ISS digipeater passes all three
# (seen in the 2026-10-13 capture, validation\aprs_iss_capture.py):
#   plain       =4903.50N/07201.75W-       degrees + minutes as text
#   compressed  =/5L!!<*e7>7P[             base-91 digits, 13 characters
#   Mic-E       'v&?l ?SI]                 latitude hidden in the "to" field,
#                                          longitude in the first payload bytes
#                                          (Kenwood and Yaesu radios send this)
# Objects (;) and items ()) carry a position too, under their own name.
# Messages (:), status (>), telemetry (T) and the rest have none.
#
# The ISS's own beacon (first one caught 2026-10-14, via an igate):
#   RS0ISS>0P0PS5,APRSAT,qAR,N0CALL:'v&?l ?SI]ARISS-International Space Station=
# It is Mic-E, and its position decodes to about 0N 0E: a dummy, not where the
# station is. So for packets FROM the ISS (from_iss True) the position is dropped
# and the last path entry - the ground station that heard it - is kept as "heard_by".
#
# parse_line(line) -> dict, or None for a line that is not a packet.
# Nothing here touches the network: the listener (still to build) hands lines in.

import math

ISS_CALLS = ("RS0ISS", "NA1SS", "ARISS")
EARTH_MI = 3958.8


def miles_and_bearing(lat1, lon1, lat2, lon2):
    """Great-circle distance (miles) and starting compass bearing from 1 to 2.
    (The flat-map version in trains.py is fine to 300 miles; stations heard via
    the ISS can be 1,500 miles away.)"""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    d = 2 * EARTH_MI * math.asin(min(1.0, math.sqrt(a)))
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return d, math.degrees(math.atan2(y, x)) % 360


def _clean(s):
    return "".join(c if " " <= c <= "~" else "?" for c in s).strip()


def _num(s):
    """'4903.5 ' -> 4903.55: a space is position ambiguity, so take the middle."""
    if " " in s:
        s = s.replace(" ", "5", 1).replace(" ", "0")
    return float(s)


# ---------- plain:  DDMM.mmN / DDDMM.mmW ----------
def _plain(p):
    """p starts at the latitude. -> (lat, lon, symbol, rest) or None."""
    if len(p) < 19 or p[7] not in "NnSs" or p[17] not in "EeWw":
        return None
    try:
        lat = int(p[0:2]) + _num(p[2:7]) / 60
        lon = int(p[9:12]) + _num(p[12:17]) / 60
    except ValueError:
        return None
    if p[7] in "Ss":
        lat = -lat
    if p[17] in "Ww":
        lon = -lon
    return lat, lon, p[8] + p[18], p[19:]


# ---------- compressed: table, 4 lat, 4 lon, code, 3 more ----------
def _b91(s):
    v = 0
    for c in s:
        n = ord(c) - 33
        if n < 0 or n > 90:
            raise ValueError("not base 91")
        v = v * 91 + n
    return v


def _compressed(p):
    if len(p) < 13:
        return None
    try:
        lat = 90 - _b91(p[1:5]) / 380926
        lon = -180 + _b91(p[5:9]) / 190463
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon, p[0] + p[9], p[13:]


def _position(p):
    if not p:
        return None
    if "0" <= p[0] <= "9":
        return _plain(p)
    return _compressed(p)


# ---------- Mic-E ----------
def _mic_e(dest, info):
    """dest = the 'to' field (6 letters/digits), info = payload after ` or '."""
    dest = dest.split("-")[0]
    if len(dest) < 6 or len(info) < 8:
        return None
    digits = ""
    for c in dest[:6]:
        if "0" <= c <= "9":
            digits += c
        elif "A" <= c <= "J":
            digits += chr(ord(c) - 17)
        elif "P" <= c <= "Y":
            digits += chr(ord(c) - 32)
        elif c in "KLZ":
            digits += " "
        else:
            return None
    try:
        lat = int(digits[0:2].replace(" ", "0")) + _num(digits[2:4] + "." + digits[4:6]) / 60
    except ValueError:
        return None
    north = "P" <= dest[3] <= "Z"
    plus100 = "P" <= dest[4] <= "Z"
    west = "P" <= dest[5] <= "Z"
    d = ord(info[0]) - 28 + (100 if plus100 else 0)
    if 180 <= d <= 189:
        d -= 80
    elif 190 <= d <= 199:
        d -= 190
    m = ord(info[1]) - 28
    if m >= 60:
        m -= 60
    h = ord(info[2]) - 28
    if not (0 <= d <= 179 and 0 <= m <= 59 and 0 <= h <= 99):
        return None
    lon = d + (m + h / 100) / 60
    return (lat if north else -lat), (-lon if west else lon), info[7] + info[6], info[8:]


def _mic_e_comment(rest):
    """Mic-E extras: a radio-type mark at the front ('>' ']' '`' or "'"), an
    altitude 'xxx}' and a one- or two-character radio code at the end."""
    if rest[:1] in (">", "]", "`", "'"):
        tail = {"]": 1, "`": 2, "'": 2}.get(rest[0], 0)
        rest = rest[1:]
        if tail and len(rest) >= tail:
            rest = rest[:-tail]
    if len(rest) >= 4 and rest[3] == "}":
        rest = rest[4:]
    return rest


def _comment(rest, symbol=""):
    """Drop the machine parts a person doesn't want to read."""
    if symbol[1:] == "_":
        return "WEATHER STATION"            # the rest is wind/temperature/rain codes
    if len(rest) >= 7 and rest[3] == "/" and rest[:3].isdigit() and rest[4:7].isdigit():
        rest = rest[7:]                     # course/speed  049/001
    elif rest[:3] in ("PHG", "RNG", "DFS") and len(rest) >= 7:
        rest = rest[7:]                     # station power / range
    i = rest.find("/A=")
    if i != -1 and len(rest) >= i + 9:
        rest = rest[:i] + rest[i + 9:]      # altitude  /A=000613
    rest = rest.lstrip("/")
    if rest.endswith("}") and "{" in rest:
        rest = rest[:rest.rfind("{")]       # a program's tag, e.g. {UISS54}
    return _clean(rest)


def parse_line(line):
    """One APRS-IS line -> dict, or None (server comments, garbage).
    Keys: src, dest, path, via_iss, from_iss, heard_by, kind, name, lat, lon,
    symbol, comment."""
    if not line or line[0] == "#":
        return None
    head, sep, payload = line.partition(":")
    if not sep or ">" not in head or not payload:
        return None
    src, _, rest = head.partition(">")
    parts = rest.split(",")
    dest, path = parts[0], parts[1:]
    out = {"src": _clean(src), "dest": dest, "path": path, "via_iss": via_iss(path),
           "from_iss": src.split("-")[0] in ISS_CALLS,
           "heard_by": _clean(path[-1]) if path else "",
           "kind": "other", "name": _clean(src), "lat": None, "lon": None,
           "symbol": "", "comment": ""}
    t, body = payload[0], payload[1:]
    pos = None
    if t in "!=":
        out["kind"] = "position"
        pos = _position(body)
    elif t in "/@":
        out["kind"] = "position"
        pos = _position(body[7:])           # after a 7-character time stamp
    elif t in "`'":
        out["kind"] = "position"
        pos = _mic_e(dest, body)
        if pos is not None:
            pos = pos[:3] + (_mic_e_comment(pos[3]),)
    elif t == ";" and len(body) >= 17:
        out["kind"] = "object"
        out["name"] = _clean(body[:9])
        pos = _position(body[17:])          # name(9) live/killed(1) time(7)
    elif t == ")":
        out["kind"] = "item"
        for i in range(3, min(10, len(body))):
            if body[i] in "!_":
                out["name"] = _clean(body[:i])
                pos = _position(body[i + 1:])
                break
    elif t == "}":                          # a packet passed on from another network
        inner = parse_line(body)
        if inner is not None:
            inner["path"] = path + inner["path"]
            inner["via_iss"] = inner["via_iss"] or out["via_iss"]
            return inner
    elif t == ":":
        out["kind"] = "message"
        out["comment"] = _clean(body[10:])  # addressee(9) ':' text
    elif t == ">":
        out["kind"] = "status"
        out["comment"] = _clean(body)
    elif t == "T":
        out["kind"] = "telemetry"
    else:
        # free text with no APRS type mark: what people send each other through the
        # ISS ("PM53 402103", "599 PM53", "R TU 73" - grid squares and signal reports)
        out["comment"] = _clean(payload)
    if pos is not None:
        out["lat"], out["lon"], out["symbol"], rest = pos
        out["comment"] = _comment(rest, out["symbol"])
        if out["from_iss"]:
            out["lat"] = out["lon"] = None  # its beacon's position is a dummy (about 0N 0E)
    elif out["kind"] in ("position", "object", "item"):
        out["comment"] = _clean(body)       # position we couldn't read: keep the text
    return out


def via_iss(path):
    """True if one of the ISS's callsigns has repeated this packet."""
    starred = -1
    for i in range(len(path)):
        if path[i].endswith("*"):
            starred = i                     # this one and every one before it have repeated
    for i in range(starred + 1):
        if path[i].rstrip("*").split("-")[0] in ISS_CALLS:
            return True
    return False
