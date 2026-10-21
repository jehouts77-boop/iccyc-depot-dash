# textutil.py - text helpers (ported from the Model 100 project's m100_home.py)
#
# Why by hand: this MicroPython's str.encode('ascii', 'replace') raises
# instead of replacing, so text from web APIs (weather.gov's degree signs,
# curly quotes, dashes) is cleaned character by character here.

DEG = "\xb0"          # kept as-is: the screen code draws it as a small ring

_SWAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
}


def ascii_safe(text, keep_degree=True):
    out = []
    for ch in text:
        o = ord(ch)
        if 32 <= o < 127:
            out.append(ch)
        elif ch == DEG and keep_degree:
            out.append(ch)
        elif ch in _SWAP:
            out.append(_SWAP[ch])
        elif ch in "\n\t\r":
            out.append(" ")
        else:
            out.append("?")
    return "".join(out)


def bytes_to_ascii(buf):
    """Raw bytes -> str, anything outside printable ASCII becomes '?'."""
    return "".join(chr(b) if 32 <= b < 127 else "?" for b in buf)


def word_wrap(text, width):
    """Split text into lines of at most `width` characters, on spaces."""
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            while len(word) > width:           # a word longer than a line
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:width])
                word = word[width:]
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= width:
                line += " " + word
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines
