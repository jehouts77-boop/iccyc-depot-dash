# ICCYC hub PCB - placement draft P3 (2026-10-11; P2 -> P3: 4 M3 mounting holes, an I2C add-on header, the amp's GAIN / SD spares, the MODEL 80 / TYPE 085 lettering; P1 -> P2: spare holes 1.7 mm like the socket pads, boxed and titled SPARE on the silkscreen).
# Single source for the hub PCB: outline, every part and connector, every pin's net, the checks, and the
# pictures. Change the board HERE and re-run:   python3 hub_pcb.py
# (needs KiCad 7's Python module "pcbnew"; writes hub_pcb.kicad_pcb, hub_pcb_placement.png, hub_pcb_report.txt)
#
# Decided with Jason 2026-10-11: he solders through-hole parts himself; the Zeros and the amp sit in female
# sockets; every wire that leaves the board plugs onto a pin header (ready-made jumper cables) except power
# (JST-PH sockets: the xiwai lead plugs straight in; a PH-to-PH cable goes to the Presto); OSH Park, 6 boards;
# each Zero's unused pins come out to labelled spare holes so the spare boards can be reused.
#
# Same circuit as the perfboard hub (hub_layout.py): the checks below compare every Zero / amp pin's net with
# the perfboard's, and every off-board wire with the perfboard's list.
#
# COORDINATES: Jason's view, as everywhere in this project - parts side facing you, the board as it sits on the
# hub shelf (P1) seen from the back of the panel, cut tab at the bottom. Origin = the board's lower-left
# corner, x to the right, y UP, millimetres. (KiCad's own y runs down; kc() converts.)
# Same placement as the perfboard where it was proven: the perfboard grid is used for the two Zeros and the amp,
# so they land exactly where Jason's bare Zeros and amp already fitted (all 23 pins, 2026-10-09).
import json, math, os, re, sys
import pcbnew

BOARD_W, BOARD_H = 70.0, 50.0       # = the perfboard (Jason, calipers 2026-10-09); P1 rev E1 pocket is 70.4 x 50.4
LEDGE      = 3.5                    # P1's ledge supports the board this far in from every edge (underside)
HOLE_KEEP  = 4.5                    # no hole / pad closer than this to an edge: pins poke out underneath and
                                    # would sit on the ledge (ledge 3.5 + 1.0 margin)
SLOT       = (33.6, 19.5, 39.1, 32.0)   # cable slot (x0, y0, x1, y1): the Qw/ST cable and the Presto power lead
                                        # come up through it from the Presto (VERIFY at the bench)
FP = "/usr/share/kicad/footprints"
OX, OY = 100.0, 100.0               # where the board sits on KiCad's sheet
def kc(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(float(OX + x)), pcbnew.FromMM(float(OY + BOARD_H - y)))
def jv(p):   return (pcbnew.ToMM(p.x) - OX, OY + BOARD_H - pcbnew.ToMM(p.y))

# perfboard grid (hub_layout.py): column A..X, row 1..18
COLS = "ABCDEFGHIJKLMNOPQRSTUVWX"; PITCH = 2.54
MX = (BOARD_W - 23*PITCH)/2; MY = (BOARD_H - 17*PITCH)/2
def g(h): return (MX + COLS.index(h[0])*PITCH, MY + (int(h[1:]) - 1)*PITCH)

# ------------------------------------------------------------------ parts
# Each part: ref, library, footprint, pin 1 position, direction of the pin row ("down", "right", ...),
# value, {pin number: (net, label)}.
P = []
def part(ref, lib, fp, p1, d, value, pins, note=""):
    P.append(dict(ref=ref, lib=lib, fp=fp, p1=p1, d=d, value=value, pins=pins, note=note))

SOCK, HDR = "Connector_PinSocket_2.54mm", "Connector_PinHeader_2.54mm"
LEFT  = ["5V","GND","3V3","GP29","GP28","GP27","GP26","GP15","GP14"]
RIGHT = [f"GP{i}" for i in range(9)]
BOT   = ["GP13","GP12","GP11","GP10","GP9"]
Z11 = {"5V":"+5V","GND":"GND","GP0":"SDA","GP1":"SCL","GP2":"ENC_A","GP3":"ENC_B","GP4":"ENC_SW",
       "GP5":"SW_CHIME","GP6":"SW_DAYNIGHT","GP7":"SW_BACKLIGHT","GP8":"SW_WIFEMODE",
       "GP9":"LED_WIFI_R","GP10":"LED_OTA_R","GP11":"BCLK","GP12":"LRC","GP13":"DIN"}
Z10 = {"5V":"+5V","GND":"GND","3V3":"3V3_G","GP0":"SDA","GP1":"SCL","GP2":"SCK","GP3":"MOSI",
       "GP4":"CS1","GP5":"DC1","GP6":"RST1","GP7":"CS2","GP8":"DC2","GP9":"RST2"}
def zero(tag, lc, use):
    li = COLS.index(lc); name = tag[2:]
    spare = lambda p: f"{tag}_{p}"            # unused pin -> its own net, brought out to a spare hole
    net = lambda p: use.get(p, spare(p))
    part(f"J{name}L", SOCK, "PinSocket_1x09_P2.54mm_Vertical", g(f"{COLS[li]}16"), "down", f"{tag} left",
         {i+1: (net(p), p) for i, p in enumerate(LEFT)})
    part(f"J{name}R", SOCK, "PinSocket_1x09_P2.54mm_Vertical", g(f"{COLS[li+6]}16"), "down", f"{tag} right",
         {i+1: (net(p), p) for i, p in enumerate(RIGHT)})
    part(f"J{name}B", SOCK, "PinSocket_1x05_P2.54mm_Vertical", g(f"{COLS[li+1]}7"), "right", f"{tag} bottom",
         {i+1: (net(p), p) for i, p in enumerate(BOT)})
zero("0x11", "E", Z11)
zero("0x10", "O", Z10)
# amp (MAX98357A), 7 pins in column C, top to bottom Vin GND SD GAIN DIN BCLK LRC (confirmed 2026-10-09);
# SD and GAIN stay unconnected, as on the breadboard
AMP = [("+5V","Vin"),("GND","GND"),("AMP_SD","SD"),("AMP_GAIN","GAIN"),("DIN","DIN"),("BCLK","BCLK"),("LRC","LRC")]
part("JAMP", SOCK, "PinSocket_1x07_P2.54mm_Vertical", g("C16"), "down", "amp",
     {i+1: n for i, n in enumerate(AMP)})

# pilot-light resistors, 330 R, lying flat, 10.16 mm lead spacing
RES = ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal")
part("RA", *RES, (14.0, 10.5), "right", "330R WiFi", {1: ("LED_WIFI_R", "GP9"), 2: ("LED_WIFI", "WIFI +")})
part("RB", *RES, (14.0, 13.5), "right", "330R OTA",  {1: ("LED_OTA_R", "GP10"), 2: ("LED_OTA", "OTA +")})

# ---- wires that leave the board
PH = ("Connector_JST", "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical")
# JST-PH polarity (changed 2026-10-11): pin 1 = ground, pin 2 = +5 V - the usual LiPo-battery order (Adafruit, SparkFun,
# Pololu's cables: black on pin 1, red on pin 2). The Presto's battery socket takes the same xiwai plug with red on +,
# so it follows the same order. VERIFY before the first power-up: the red wire lands on the board's "+" mark.
part("JPWR",    *PH, (48.0, 9.5),  "right", "POWER IN (xiwai lead)",      {1: ("GND","-"), 2: ("+5V","+")})
part("JPRESTO", *PH, (35.35, 13.0), "right", "PRESTO battery lead",       {1: ("GND","-"), 2: ("+5V","+")})
part("JQW", HDR, "PinHeader_1x04_P2.54mm_Vertical", (36.35, 43.0), "down", "Qw/ST",
     {1: ("GND","GND blk"), 2: ("QW_3V3_NC","red: NOT connected"), 3: ("SDA","SDA blu"), 4: ("SCL","SCL yel")})
part("JKNOB", HDR, "PinHeader_1x05_P2.54mm_Vertical", (6.0, 17.66), "down", "KNOB",
     {1: ("ENC_A","A"), 2: ("GND","C"), 3: ("ENC_B","B"), 4: ("ENC_SW","SW"), 5: ("GND","SW G")})
# one row toward the switch row, in the panel's order seen from the back (WIFE MODE at the left ... CHIME at the
# right), every part with its own ground pin
CTRL = [("SW_WIFEMODE","WIFE"),("GND","G"),("SW_BACKLIGHT","BKLT"),("GND","G"),("LED_OTA","OTA+"),("GND","OTA-"),
        ("LED_WIFI","WIFI+"),("GND","WIFI-"),("SW_DAYNIGHT","DAY"),("GND","G"),("SW_CHIME","CHIME"),("GND","G")]
part("JCTRL", HDR, "PinHeader_1x12_P2.54mm_Vertical", (10.0, 6.5), "right", "SWITCHES + LIGHTS",
     {i+1: n for i, n in enumerate(CTRL)})
GAUGE = lambda cs, dc, rst: [("3V3_G","VCC"),("GND","GND"),("SCK","SCL"),("MOSI","SDA"),(dc,"DC"),(cs,"CS"),(rst,"RST")]
part("JG1", HDR, "PinHeader_1x07_P2.54mm_Vertical", (62.0, 42.0), "down", "GAUGE I",
     {i+1: n for i, n in enumerate(GAUGE("CS1","DC1","RST1"))})
part("JG2", HDR, "PinHeader_1x07_P2.54mm_Vertical", (62.0, 21.0), "down", "GAUGE II",
     {i+1: n for i, n in enumerate(GAUGE("CS2","DC2","RST2"))})

# ---- spare holes (for reusing the spare boards): every unused Zero pin, 2.54 mm in from its socket pin
SP = ("TestPoint", "TestPoint_THTPad_D2.0mm_Drill1.0mm")   # a bare plated hole; takes a header pin or a wire
def spare(ref, xy, net, lab): part(ref, *SP, xy, "down", "spare", {1: (net, lab)})
for i, p in enumerate(LEFT):
    if p not in Z11:
        x, y = g(f"E{16-i}"); spare(f"S11_{p}", (x + PITCH, y), f"0x11_{p}", p)
    if p not in Z10:
        x, y = g(f"O{16-i}"); spare(f"S10_{p}", (x + PITCH, y), f"0x10_{p}", p)
for i, p in enumerate(BOT):
    if p not in Z10:
        x, y = g(f"{COLS[COLS.index('P')+i]}7"); spare(f"S10_{p}", (x, y - PITCH), f"0x10_{p}", p)
# amp's unused pins (Jason, 2026-10-11): GAIN and SD beside the amp, plus a GND hole next to them, so a short
# wire GAIN -> GND later raises the amp from 9 dB to 12 dB with no new board
spare("SP_AMP_GND",  (g("C15")[0] + PITCH, g("C15")[1]), "GND", "GND")
spare("SP_AMP_SD",   (g("C14")[0] + PITCH, g("C14")[1]), "AMP_SD", "SD")
spare("SP_AMP_GAIN", (g("C13")[0] + PITCH, g("C13")[1]), "AMP_GAIN", "GAIN")
# add-on I2C header (Jason, 2026-10-11): a small sensor can join the Presto's I2C link later. Qwiic pin order;
# 3.3 V from 0x10's own regulator
part("JI2C", HDR, "PinHeader_1x04_P2.54mm_Vertical", (4.6, 22.5), "right", "I2C add-on",
     {1: ("GND","GND"), 2: ("3V3_G","3V3"), 3: ("SDA","SDA"), 4: ("SCL","SCL")})
spare("SP_5V", (55.5, 14.5), "+5V", "5V"); spare("SP_GND", (55.5, 12.0), "GND", "GND"); spare("SP_3V3", (55.5, 9.5), "3V3_G", "3V3")

# ------------------------------------------------------------------ build the KiCad board
for _f in ("hub_pcb.kicad_pcb", "hub_pcb.kicad_pro", "hub_pcb.kicad_prl"):
    if os.path.exists(_f): os.remove(_f)
board = pcbnew.NewBoard("hub_pcb.kicad_pcb")      # a board with its own project file (the zone filler needs one)
ds = board.GetDesignSettings()
# OSH Park 2-layer rules: 6 mil trace / 6 mil space, 10 mil drill, 5 mil annular ring, 15 mil copper to edge
ds.m_TrackMinWidth = pcbnew.FromMM(0.1524); ds.m_MinClearance = pcbnew.FromMM(0.1524)
ds.m_MinThroughDrill = pcbnew.FromMM(0.254); ds.m_HoleClearance = pcbnew.FromMM(0.1524)
ds.m_CopperEdgeClearance = pcbnew.FromMM(0.381)

def seg(layer, a, b, w=0.15):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(kc(*a)); s.SetEnd(kc(*b))
    s.SetLayer(layer); s.SetWidth(pcbnew.FromMM(w)); board.Add(s)
def rect(layer, x0, y0, x1, y1, w=0.15):
    for a, b in (((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0))): seg(layer, a, b, w)
JUST = {"c": pcbnew.GR_TEXT_H_ALIGN_CENTER, "l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}
def text(layer, s, x, y, h=1.0, angle=0, bold=False, just="c"):
    t = pcbnew.PCB_TEXT(board); t.SetText(s); t.SetPosition(kc(x, y)); t.SetLayer(layer)
    t.SetHorizJustify(JUST[just])
    if layer == pcbnew.B_SilkS: t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(h), pcbnew.FromMM(h))); t.SetTextThickness(pcbnew.FromMM(h*0.15))
    t.SetBold(bold)
    if angle: t.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    board.Add(t)

# outline with 1 mm corner chamfers would change the pocket fit -> plain rectangle, like the perfboard
rect(pcbnew.Edge_Cuts, 0, 0, BOARD_W, BOARD_H, 0.1)
x0, y0, x1, y1 = SLOT; r = (x1 - x0)/2         # slot with round ends (OSH Park routes it with a mill)
seg(pcbnew.Edge_Cuts, (x0, y0 + r), (x0, y1 - r), 0.1); seg(pcbnew.Edge_Cuts, (x1, y0 + r), (x1, y1 - r), 0.1)
for cy, sgn in ((y1 - r, 1), (y0 + r, -1)):
    a = pcbnew.PCB_SHAPE(board); a.SetShape(pcbnew.SHAPE_T_ARC); a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(pcbnew.FromMM(0.1))
    a.SetArcGeometry(kc(x0, cy), kc((x0+x1)/2, cy + sgn*r), kc(x1, cy)); board.Add(a)

nets = {}
def netcode(n):
    if n not in nets:
        ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni
    return nets[n]

DIRV = {"down": (0, -1), "up": (0, 1), "right": (1, 0), "left": (-1, 0)}
errs, notes = [], []
pads = {}                     # (ref, pin) -> dict(x, y, net, label, drill, size)
for d in P:
    fp = pcbnew.FootprintLoad(os.path.join(FP, d["lib"] + ".pretty"), d["fp"])
    assert fp, d["fp"]
    fp.SetReference(d["ref"]); fp.SetValue(d["value"]); board.Add(fp)
    ok = False
    for rot in (0, 90, 180, 270):         # pick the rotation that puts pin 2 on the wanted side of pin 1
        fp.SetOrientationDegrees(rot); fp.SetPosition(kc(0, 0))
        p1 = fp.FindPadByNumber("1"); off = jv(p1.GetPosition())
        fp.SetPosition(kc(d["p1"][0] - off[0], d["p1"][1] - off[1]))
        p2 = fp.FindPadByNumber("2")
        if p2 is None: ok = True; break
        a, b = jv(fp.FindPadByNumber("1").GetPosition()), jv(p2.GetPosition())
        v = DIRV[d["d"]]
        if (b[0]-a[0])*v[0] + (b[1]-a[1])*v[1] > 1.0: ok = True; break
    if not ok: errs.append(f"{d['ref']}: no rotation gives direction {d['d']}")
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    for pad in fp.Pads():
        num = pad.GetNumber()
        if num not in [str(k) for k in d["pins"]]:
            if num: errs.append(f"{d['ref']} pad {num} has no net assigned")
            continue
        net, lab = d["pins"][int(num)]
        pad.SetNet(netcode(net))
        if d["ref"].startswith(("S1", "SP_")):          # spare holes: same 1.7 mm pad as the socket pins (Jason, 2026-10-11)
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.7), pcbnew.FromMM(1.7)))
        x, y = jv(pad.GetPosition())
        pads[(d["ref"], int(num))] = dict(x=x, y=y, net=net, label=lab, drill=pcbnew.ToMM(pad.GetDrillSize().x),
                                          size=pcbnew.ToMM(pad.GetSize().x))

# ---- silkscreen: each group of spare holes boxed and titled SPARE, each hole named (Jason, 2026-10-11:
#      "smaller and clearly marked" - so they don't read as a second socket row)
SILK = []                                           # (kind, data) - also drawn in the picture
def silk_box(x0, y0, x1, y1):
    rect(pcbnew.F_SilkS, x0, y0, x1, y1, 0.15); SILK.append(("box", (x0, y0, x1, y1)))
def silk_text(t, x, y, h=0.8, angle=0, bold=False, just="c", bottom=False):
    text(pcbnew.B_SilkS if bottom else pcbnew.F_SilkS, t, x, y, h, angle, bold, just)
    SILK.append(("btext" if bottom else "text", (t, x, y, h, angle, bold, just)))
def spare_group(refs, title_at, label_side, title_angle=0, title="SPARE"):
    ps = [pads[(r, 1)] for r in refs]
    xs = [p["x"] for p in ps]; ys = [p["y"] for p in ps]
    silk_box(min(xs) - 1.25, min(ys) - 1.25, max(xs) + 1.25, max(ys) + 1.25)
    silk_text(title, *title_at, h=0.9, angle=title_angle, bold=True)
    for r, p in zip(refs, ps):
        if label_side == "none": continue
        if label_side == "right": silk_text(p["label"], p["x"] + (2.9 if len(p["label"]) > 3 else 2.5), p["y"], 0.8)
        else:                     silk_text(p["label"], p["x"], p["y"] - 3.1, 0.8, angle=90)
order = lambda tag, names: [f"{tag}_{n}" for n in names if (f"{tag}_{n}", 1) in pads]
spare_group(order("S11", LEFT), (20.3, 38.97), "right")
spare_group(order("S10", LEFT), (45.7, 36.43), "right")
spare_group(order("S10", BOT), (40.4, 16.11), "below")
spare_group(["SP_5V", "SP_GND", "SP_3V3"], (55.5, 16.9), "right")
spare_group(["SP_AMP_GND", "SP_AMP_SD", "SP_AMP_GAIN"], (g("C16")[0] + PITCH, g("C16")[1]), "none", title="AMP")

# ---- four M3 mounting holes for reuse (Jason, 2026-10-11): over P1's ledge, no copper, unused in this project
MOUNT = [(3.5, 3.5), (BOARD_W - 3.5, 3.5), (3.5, BOARD_H - 3.5), (BOARD_W - 3.5, BOARD_H - 3.5)]
for i, (mx, my) in enumerate(MOUNT):
    fp = pcbnew.FootprintLoad(os.path.join(FP, "MountingHole.pretty"), "MountingHole_3.2mm_M3")
    fp.SetReference(f"H{i+1}"); fp.SetPosition(kc(mx, my)); board.Add(fp)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    for (ref, n), p in pads.items():
        if math.hypot(p["x"] - mx, p["y"] - my) < 1.6 + p["size"]/2 + 1.0: errs.append(f"mounting hole H{i+1} too close to {ref}.{n}")

# ---- the nod to the original (Jason, 2026-10-11): the brass plate's wording along the top edge
silk_text("ICCYC CONTROL CONSOLE \u00b7 MODEL 80 \u00b7 TYPE 085", BOARD_W/2, BOARD_H - 2.6, 1.3, bold=True)
silk_text("HUB REV A \u00b7 2026", 52.0, 2.4, 1.1, bold=True)

# ---- what plugs in where (silkscreen, parts side). Text stays off every pad (KiCad's check fails otherwise).
def pin_labels(ref, dx, dy, just, angle=0, names=None, h=0.8):
    for (r, n), p in sorted(pads.items()):
        if r != ref: continue
        silk_text((names or {}).get(n, p["label"]), p["x"] + dx, p["y"] + dy, h, angle, just=just)
pin_labels("JCTRL", 0, -1.6, "r", 90, names={i+1: t for i, t in enumerate(
    ["WIFE", "G", "BKLT", "G", "OTA+", "OTA-", "WIFI+", "WIFI-", "DAY", "G", "CHIME", "G"])})
pin_labels("JKNOB", 1.6, 0, "l", names={1: "A", 2: "C", 3: "B", 4: "SW", 5: "G"})
silk_text("KNOB", 3.0, 12.6, 0.9, 90, bold=True)
for ref, title, ty in (("JG1", "GAUGE I", 34.4), ("JG2", "GAUGE II", 13.4)):
    pin_labels(ref, 1.5, 0, "l"); silk_text(title, 68.4, ty, 0.9, 90, bold=True)
pin_labels("JQW", -1.5, 0, "r", names={1: "GND", 2: "NC", 3: "SDA", 4: "SCL"})
silk_text("Qw/ST", 36.35, 45.4, 0.8, bold=True)
for n, t in ((1, "G"), (2, "3V3"), (3, "SDA"), (4, "SCL")):          # alternate below / above: 2.54 mm is too tight for 3 letters side by side
    silk_text(t, pads[("JI2C", n)]["x"], pads[("JI2C", n)]["y"] + (-2.6 if n % 2 else 2.2), 0.8)
silk_text("I2C", 2.3, 22.5, 0.9, 90, bold=True)
pin_labels("JAMP", -1.5, 0, "r", names={i+1: t for i, t in enumerate(["VIN", "GND", "SD", "GAIN", "DIN", "BCLK", "LRC"])})
for ref, title, tx, ty, j in (("JPWR", "POWER IN", 49.0, 5.2, "c"), ("JPRESTO", "PRESTO", 32.7, 13.0, "r")):
    silk_text(title, tx, ty, 0.9, bold=True, just=j)
    for pn in (1, 2):
        silk_text("+" if pads[(ref, pn)]["net"] == "+5V" else "-", pads[(ref, pn)]["x"], pads[(ref, pn)]["y"] + 1.75, 0.9, bold=True)
silk_text("Ra 330", 19.08, 10.5, 0.8); silk_text("Rb 330", 19.08, 13.5, 0.8)
for name, cx in (("0x11 CONTROLS", 23.57), ("0x10 GAUGES", 48.97)):
    silk_text(name, cx + 3.9, 29.5, 1.1, 90, bold=True)
    silk_text("USB", cx, 40.6, 0.9, bold=True)
    for a, b in (((cx - 2.4, 40.1), (cx - 2.4, 41.4)), ((cx - 2.4, 41.4), (cx - 2.9, 40.9)), ((cx - 2.4, 41.4), (cx - 1.9, 40.9))):
        seg(pcbnew.F_SilkS, a, b, 0.15); SILK.append(("line", (a, b)))
# ---- the underside, where you solder: names so you know which part's pins you're looking at
for t, x, y, ang in (("0x11", 27.5, 29.5, 90), ("0x10", 52.9, 29.5, 90), ("AMP", 8.0, 44.2, 0), ("GAUGE I", 68.4, 34.4, 90),
                     ("GAUGE II", 68.4, 13.4, 90), ("KNOB", 3.0, 12.6, 90), ("SWITCHES + LIGHTS", 24.0, 3.7, 0),
                     ("POWER IN", 49.0, 5.2, 0), ("PRESTO", 30.4, 13.0, 0), ("Qw/ST", 36.35, 45.4, 0), ("I2C", 2.3, 22.5, 90)):
    silk_text(t, x, y, 0.9, ang, bold=True, bottom=True)

# ------------------------------------------------------------------ checks
# 1. every pad inside the board and clear of the ledge band
for (ref, n), p in pads.items():
    if min(p["x"], p["y"], BOARD_W - p["x"], BOARD_H - p["y"]) < HOLE_KEEP:
        errs.append(f"{ref}.{n} at ({p['x']:.2f},{p['y']:.2f}) is within {HOLE_KEEP} mm of the edge (ledge)")
    sx0, sy0, sx1, sy1 = SLOT
    if sx0 - 1.0 < p["x"] < sx1 + 1.0 and sy0 - 1.0 < p["y"] < sy1 + 1.0:
        errs.append(f"{ref}.{n} too close to the cable slot")
# 2. no two pads closer than 2.0 mm centre to centre (sockets / headers need their own 2.54 grid)
pl = list(pads.items())
for i, ((r1, n1), a) in enumerate(pl):
    for (r2, n2), b in pl[i+1:]:
        dd = math.hypot(a["x"]-b["x"], a["y"]-b["y"])
        lim = 1.9 if r1 == r2 and r1 in ("JPWR", "JPRESTO") else 2.4
        if dd < lim: errs.append(f"pads {r1}.{n1} and {r2}.{n2} only {dd:.2f} mm apart")
# 3. same circuit as the perfboard: every Zero / amp pin's net vs hub_layout.py
PERF2PCB = {"5V": "+5V", "3V3": "3V3_G"}
try:
    holes = json.load(open("hub_holes.json"))
    def perfnet(h): n = holes[h]["net"]; return PERF2PCB.get(n, n)
    checked = 0
    for ref, lc, n9, tag in (("J11", "E", 9, "0x11"), ("J10", "O", 9, "0x10")):
        li = COLS.index(lc)
        for i in range(9):
            for side, col in (("L", COLS[li]), ("R", COLS[li+6])):
                pn = pads[(ref + side, i+1)]["net"]; hn = perfnet(f"{col}{16-i}")
                if hn == "NC": hn = None
                if hn is None and not pn.startswith(tag + "_"): errs.append(f"{ref}{side}.{i+1}: perfboard unused, PCB {pn}")
                if hn is not None and hn != pn: errs.append(f"{ref}{side}.{i+1}: perfboard {hn}, PCB {pn}")
                checked += 1
        for i in range(5):
            pn = pads[(ref + "B", i+1)]["net"]; hn = perfnet(f"{COLS[li+1+i]}7")
            if hn == "NC": hn = None
            if (hn or None) != (None if pn.startswith(tag + "_") else pn): errs.append(f"{ref}B.{i+1}: perfboard {hn}, PCB {pn}")
            checked += 1
    for i in range(7):
        pn = pads[("JAMP", i+1)]["net"]; hn = perfnet(f"C{16-i}")
        if hn == "NC": hn = None
        if (hn or None) != (None if pn.startswith("AMP_") else pn): errs.append(f"JAMP.{i+1}: perfboard {hn}, PCB {pn}")
        checked += 1
    notes.append(f"perfboard comparison: {checked} Zero / amp pins checked against hub_layout.py")
    # off-board wires: every perfboard wire's net must appear on a PCB connector
    offnets = {p["net"] for (ref, n), p in pads.items() if ref.startswith(("JPWR","JPRESTO","JQW","JKNOB","JCTRL","JG"))}
    for h, d in holes.items():
        if d["kind"] in ("wire", "wire-from-below") and perfnet(h) not in offnets:
            errs.append(f"perfboard wire {h} ({d['label']}) has no PCB connector pin")
    # resistors: same nets each side
    for r, a, b in (("RA", "LED_WIFI_R", "LED_WIFI"), ("RB", "LED_OTA_R", "LED_OTA")):
        if {pads[(r,1)]["net"], pads[(r,2)]["net"]} != {a, b}: errs.append(f"{r} nets wrong")
except FileNotFoundError:
    errs.append("hub_holes.json missing: run hub_layout.py first")
# 4. connector pin counts per net (the gauges: one each of CS / DC / RST, shared SCK / MOSI / VCC / GND)
cnt = {}
for p in pads.values(): cnt[p["net"]] = cnt.get(p["net"], 0) + 1
for n in ("AMP_SD","AMP_GAIN","CS1","DC1","RST1","CS2","DC2","RST2","ENC_A","ENC_B","ENC_SW","DIN","BCLK","LRC",
          "SW_CHIME","SW_DAYNIGHT","SW_BACKLIGHT","SW_WIFEMODE","LED_WIFI","LED_OTA","LED_WIFI_R","LED_OTA_R"):
    if cnt.get(n) != 2: errs.append(f"net {n} has {cnt.get(n)} pins (expected 2)")
for n, k in (("SDA", 4), ("SCL", 4), ("SCK", 3), ("MOSI", 3), ("3V3_G", 5)):
    if cnt.get(n) != k: errs.append(f"net {n} has {cnt.get(n)} pins (expected {k})")

# ------------------------------------------------------------------ copper (routing), 2026-10-11
# Trace widths: power wider than signals. +5 V carries up to ~0.7 A in a full-volume chime (wiring-plan.md,
# section 1); 0.6 mm of 1 oz copper carries well over 1 A with little warming. 3.3 V to the gauges is ~0.05 A.
import hub_router
WIDTH = {"+5V": 0.6, "GND": 0.6, "3V3_G": 0.4}
widths = lambda net: WIDTH.get(net, 0.25)
def outside(X, Y):
    out = (X <= 0) | (X >= BOARD_W) | (Y <= 0) | (Y >= BOARD_H)
    sx0, sy0, sx1, sy1 = SLOT; r = (sx1 - sx0)/2; cxs = (sx0 + sx1)/2
    yc = np.clip(Y, sy0 + r, sy1 - r)
    out |= np.hypot(X - cxs, Y - yc) < r
    for mx, my in MOUNT: out |= np.hypot(X - mx, Y - my) < 1.6
    return out
import numpy as np
pad_objs = {}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        net = pad.GetNetname()
        if net and pad.GetNumber(): pad_objs[(fp.GetReference(), pad.GetNumber())] = (pad, net)
cnt_pads = {}
for k, (p, n) in pad_objs.items(): cnt_pads[n] = cnt_pads.get(n, 0) + 1
span = lambda n: max([abs(pads[k]["x"] - pads[j]["x"]) + abs(pads[k]["y"] - pads[j]["y"])
                      for k in pads for j in pads if pads[k]["net"] == n and pads[j]["net"] == n] + [0])
sig = sorted([n for n in cnt_pads if cnt_pads[n] >= 2 and n not in ("+5V", "GND", "3V3_G")], key=span, reverse=True)
# Ground: the five pins that carry the boards' and the amp's current back to POWER IN get real 0.6 mm traces;
# every other ground pin (gauges, switches, knob, lights, headers) is joined by the ground fill on both faces.
POWER_GND = {("JPWR", 1), ("JPRESTO", 1), ("J11L", 2), ("J10L", 2), ("JAMP", 2)}
ORDER = ["+5V"] + sig + ["3V3_G", "GND"]
only = lambda net, k: net != "GND" or k in POWER_GND
R, unrouted = hub_router.route_all(board, BOARD_W, BOARD_H, kc, jv, outside,
                                   {(r, int(n)): v for (r, n), v in pad_objs.items()}, widths, ORDER, only=only)
for net, ks in unrouted.items(): errs.append(f"router could not connect {net}: {ks}")
R.write(board, netcode)
ntr = sum(len(v) for v in R.segs.values()); nvia = sum(len(v) for v in R.vias.values())
notes.append(f"copper: {ntr} trace segments, {nvia} vias")
# ground fill ("pour") on both faces: every bit of empty copper becomes ground, joined to the ground pins
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(netcode("GND"))
    ol = z.Outline(); ol.NewOutline()
    FE = 0.5     # fill stops 0.5 mm short of the board edge (KiCad's filler did not apply the edge rule by itself here)
    for (x, y) in ((FE, FE), (BOARD_W - FE, FE), (BOARD_W - FE, BOARD_H - FE), (FE, BOARD_H - FE)): ol.Append(kc(x, y))
    z.SetLocalClearance(pcbnew.FromMM(0.3)); z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.4)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)
for mx, my in MOUNT:     # keep the ground fill 1 mm clear of each mounting hole (a screw head may sit there)
    k = pcbnew.ZONE(board); k.SetIsRuleArea(True); k.SetDoNotAllowCopperPour(True)
    k.SetDoNotAllowTracks(False); k.SetDoNotAllowVias(False); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); k.SetLayerSet(ls)
    ol = k.Outline(); ol.NewOutline()
    for i in range(24): ol.Append(kc(mx + 2.6*math.cos(i*math.pi/12), my + 2.6*math.sin(i*math.pi/12)))
    board.Add(k)
# ...and 0.5 mm clear of the cable slot
k = pcbnew.ZONE(board); k.SetIsRuleArea(True); k.SetDoNotAllowCopperPour(True)
k.SetDoNotAllowTracks(False); k.SetDoNotAllowVias(False); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); k.SetLayerSet(ls)
ol = k.Outline(); ol.NewOutline()
_sx0, _sy0, _sx1, _sy1 = SLOT; _r = (_sx1 - _sx0)/2 + 0.5; _cx = (_sx0 + _sx1)/2
for i in range(13): a = math.pi*i/12; ol.Append(kc(_cx + _r*math.cos(a), _sy1 - (_sx1 - _sx0)/2 + _r*math.sin(a)))
for i in range(13): a = math.pi + math.pi*i/12; ol.Append(kc(_cx + _r*math.cos(a), _sy0 + (_sx1 - _sx0)/2 + _r*math.sin(a)))
board.Add(k)
board.BuildConnectivity()
_filler = pcbnew.ZONE_FILLER(board); _zones = board.Zones(); _filler.Fill(_zones)
# Stitching vias (2026-10-11, after a review): small ground vias wherever both faces' fill is solid around the spot,
# on a 5 mm grid, so the top fill's pieces and the bottom fill are tied together in many places, not only at the
# ground pins. Then fill again so the fill makes room for them.
def _fills():
    out = []
    for z in board.Zones():
        if not z.GetIsRuleArea(): out.append(z.GetFilledPolysList(z.GetLayerSet().Seq()[0]))
    return out
_fl = _fills(); n_stitch = 0
other_copper = [(jv(p.GetPosition()), pcbnew.ToMM(max(p.GetSize().x, p.GetSize().y))/2) for fp in board.GetFootprints() for p in fp.Pads()]
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA": other_copper.append((jv(t.GetPosition()), hub_router.VIA_D/2))
_txt = []                                   # keep stitching vias out of printed lettering
for d in board.GetDrawings():
    if d.GetClass() == "PCB_TEXT":
        bb = d.GetBoundingBox(); (ax0, ay1), (ax1, ay0) = jv(bb.GetOrigin()), jv(bb.GetEnd())
        _txt.append((min(ax0, ax1) - 0.6, min(ay0, ay1) - 0.6, max(ax0, ax1) + 0.6, max(ay0, ay1) + 0.6))
for gx in np.arange(2.5, BOARD_W - 2.4, 5.0):
    for gy in np.arange(2.5, BOARD_H - 2.4, 5.0):
        ring = [(gx + 0.95*math.cos(a), gy + 0.95*math.sin(a)) for a in np.linspace(0, 2*math.pi, 12, endpoint=False)] + [(gx, gy)]
        if not all(ps.Contains(kc(x, y)) for ps in _fl for (x, y) in ring): continue
        if any(math.hypot(gx - q[0], gy - q[1]) < r + 0.4 + 0.6 for q, r in other_copper): continue
        if any(t0 <= gx <= t2 and t1 <= gy <= t3 for t0, t1, t2, t3 in _txt): continue
        v = pcbnew.PCB_VIA(board); v.SetPosition(kc(gx, gy)); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(netcode("GND")); board.Add(v); n_stitch += 1
        other_copper.append(((gx, gy), 0.3))
board.BuildConnectivity(); _zones = board.Zones(); _filler.Fill(_zones)
notes.append(f"ground stitching vias: {n_stitch}")

# 4b. my own check of the ground fill: KiCad's filler and check both missed the fill touching the board edge and the slot
#     (found 2026-10-11 in a review; fixed above). Measure every filled-copper corner against edge, slot and holes.
def edge_dist(x, y):
    d = min(x, y, BOARD_W - x, BOARD_H - y)
    sx0, sy0, sx1, sy1 = SLOT; r = (sx1 - sx0)/2; yc = min(max(y, sy0 + r), sy1 - r)
    d = min(d, math.hypot(x - (sx0 + sx1)/2, y - yc) - r)
    for mx, my in MOUNT: d = min(d, math.hypot(x - mx, y - my) - 1.6)
    return d
for z in board.Zones():
    if z.GetIsRuleArea(): continue
    lay = z.GetLayerSet().Seq()[0]; ps = z.GetFilledPolysList(lay); md = 99
    for i in range(ps.OutlineCount()):
        for ch in [ps.Outline(i)] + [ps.Hole(i, j) for j in range(ps.HoleCount(i))]:
            for kk in range(ch.PointCount()): md = min(md, edge_dist(*jv(ch.CPoint(kk))))
    if md < 0.45: errs.append(f"ground fill on {pcbnew.LayerName(lay)} only {md:.2f} mm from an edge / the slot / a hole")
    notes.append(f"ground fill {pcbnew.LayerName(lay)}: {ps.OutlineCount()} pieces, closest to an edge / slot / hole {md:.2f} mm")
md = min(edge_dist(*jv(p)) - 0 for p in []) if False else 99
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA": continue
    a, c = jv(t.GetStart()), jv(t.GetEnd()); n = max(2, int(math.hypot(c[0]-a[0], c[1]-a[1])/0.05))
    for i in range(n):
        u = i/(n - 1); md = min(md, edge_dist(a[0] + u*(c[0]-a[0]), a[1] + u*(c[1]-a[1])) - pcbnew.ToMM(t.GetWidth())/2)
if md < 0.381: errs.append(f"a trace is {md:.2f} mm from an edge / the slot / a hole")
notes.append(f"traces: closest to an edge / slot / hole {md:.2f} mm")
pcbnew.SaveBoard("hub_pcb.kicad_pcb", board)
# 5. KiCad's own design-rule check (OSH Park numbers above). Unrouted connections are expected until routing;
#    courtyard overlaps are accepted only where listed: spare holes are bare holes (no plastic), and each Zero's
#    side sockets meet its bottom socket corner to corner (the Zero's own pin layout; it fitted the perfboard).
pcbnew.WriteDRCReport(board, "hub_pcb_drc.txt", pcbnew.EDA_UNITS_MILLIMETRES, True)
ACCEPT_OVERLAP = lambda a, b: a.startswith(("S1", "SP_")) or b.startswith(("S1", "SP_")) or \
                 {a[:3], b[:3]} in ({"J11"}, {"J10"}) or {a, b} in ({"JG2", "H2"}, {"JKNOB", "H1"})
# JG2 / H2 and JKNOB / H1: only the courtyards touch; an M3 screw head (5.5 mm) still clears the header plastic
# (by ~0.6 mm and ~0.2 mm). The holes are for a future project; this one doesn't use them.
drc = open("hub_pcb_drc.txt").read().split("\n[")
kinds = {}
for blk in drc[1:]:
    k = blk.split("]")[0]
    if k in ("silk_overlap", "lib_footprint_issues", "starved_thermal"):
        kinds[k] = kinds.get(k, 0) + 1; continue
    refs = re.findall(r"Footprint (\S+)", blk.split("\n**")[0])
    if k == "courtyards_overlap" and len(refs) == 2 and ACCEPT_OVERLAP(*refs):
        kinds["courtyards_overlap (accepted)"] = kinds.get("courtyards_overlap (accepted)", 0) + 1; continue
    errs.append("DRC: " + blk.split("\n")[0] + " " + " / ".join(refs))
if "Found 0 unconnected pads" not in open("hub_pcb_drc.txt").read(): errs.append("KiCad: some pads are not connected")
for blk in drc[1:]:              # two printed labels on top of each other would be unreadable
    if blk.startswith("silk_overlap") and sum("PCB Text" in i for i in re.findall(r"@\([^)]*\): (.*)", blk)) == 2:
        errs.append("silkscreen labels overlap: " + " / ".join(re.findall(r"PCB Text '([^']*)'", blk)))
notes.append("KiCad DRC, counted but not errors: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
json.dump({f"{r}.{n}": p for (r, n), p in pads.items()}, open("hub_pcb_pads.json", "w"), indent=1)
rep = [f"parts: {len(P)}   pads: {len(pads)}   nets: {len(nets)}",
       "ERRORS: " + ("none" if not errs else ""), *["  " + e for e in errs], *notes]
open("hub_pcb_report.txt", "w").write("\n".join(rep) + "\n"); print("\n".join(rep))
if errs: sys.exit(1)

# ------------------------------------------------------------------ picture (Jason's view)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle, FancyArrowPatch
NETCOL = {"+5V":"#d62728","GND":"#222222","3V3_G":"#ff7f0e","SDA":"#1f77b4","SCL":"#c9a800"}
def netcolor(n):
    if n in NETCOL: return NETCOL[n]
    if n in ("DIN","BCLK","LRC"): return "#9467bd"
    if n in ("SCK","MOSI","CS1","DC1","RST1","CS2","DC2","RST2"): return "#2ca02c"
    if n.startswith("LED"): return "#e377c2"
    if n.startswith(("0x1","AMP_","QW_")): return "#ffffff"
    return "#17becf"
brd = pcbnew.LoadBoard("hub_pcb.kicad_pcb")
fab = []                                   # every footprint's own body outline (KiCad fabrication layer)
for fp in brd.GetFootprints():
    for it in fp.GraphicalItems():
        if it.GetLayer() == pcbnew.F_Fab and it.GetClass() in ("MGRAPHIC", "FP_SHAPE", "PCB_SHAPE"):
            fab.append((fp.GetReference(), jv(it.GetStart()), jv(it.GetEnd())))
ELEV = [  # boards that sit up on the sockets: (name, x0, y0, x1, y1, note)
    ("0x11  controls", 23.57 - 8.9, 18.65 - 1.3, 23.57 + 8.9, 18.65 - 1.3 + 24.4),
    ("0x10  gauges",   48.97 - 8.9, 18.65 - 1.3, 48.97 + 8.9, 18.65 - 1.3 + 24.4),
]
AMPBOX = (12.15 - 18.7, 33.89 - 8.75, 12.15, 33.89 + 8.75)

def draw(ax, under):
    X = (lambda x: BOARD_W - x) if under else (lambda x: x)
    ax.add_patch(Rectangle((0, 0), BOARD_W, BOARD_H, fc="#1f5f3a", ec="#0b2a18", lw=1.5, zorder=0))
    ax.add_patch(Rectangle((LEDGE, LEDGE), BOARD_W - 2*LEDGE, BOARD_H - 2*LEDGE, fc="none", ec="#cfe8b0",
                           lw=0.9, ls=(0, (4, 3)), zorder=0.5))
    x0, y0, x1, y1 = SLOT
    ax.add_patch(FancyBboxPatch((min(X(x0), X(x1)), y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={(x1-x0)/2}",
                                fc="white", ec="#0b2a18", lw=1, zorder=1))
    if not under:
        for ref, a, b in fab:
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#f4f1e6", lw=1.0, zorder=2)
        for name, ex0, ey0, ex1, ey1 in ELEV:
            ax.add_patch(FancyBboxPatch((ex0, ey0), ex1 - ex0, ey1 - ey0, boxstyle="round,pad=0,rounding_size=1",
                         fc="#2f6fb5", ec="#9cc3ff", lw=1.3, alpha=0.30, zorder=5))
            ax.add_patch(Rectangle(((ex0 + ex1)/2 - 4.5, ey1 - 1.4), 9, 2.7, fc="#bbbbbb", ec="#444", alpha=0.85, zorder=5.1))
            ax.text((ex0 + ex1)/2, ey1, "USB", fontsize=6, ha="center", va="center", zorder=5.2)
            ax.text((ex0 + ex1)/2, (ey0 + ey1)/2 + 1.5, name, fontsize=8.5, ha="center", va="center", rotation=90,
                    color="white", weight="bold", zorder=5.2)
        ax.add_patch(Rectangle((AMPBOX[0], AMPBOX[1]), AMPBOX[2] - AMPBOX[0], AMPBOX[3] - AMPBOX[1],
                               fc="#7b3fa0", ec="#d6b3ef", lw=1.3, alpha=0.32, zorder=5))
        ax.text(AMPBOX[0] - 7.5, AMPBOX[3] + 1.0, "AMP on its socket, body hangs\noff the edge toward the speaker", fontsize=7, ha="left", va="bottom", color="#5b2a78", weight="bold", zorder=6, bbox=dict(fc="white", ec="none", pad=0.5))
        ax.add_patch(Rectangle((AMPBOX[0] + 0.5, 30.2), 6.6, 7.3, fc="#3aa655", ec="#1c5a2c", alpha=0.7, zorder=5.1))
        ax.text(AMPBOX[0] + 3.8, 33.85, "spkr", fontsize=5.5, ha="center", va="center", rotation=90, zorder=5.2)
    for (ref, n), p in pads.items():
        c = netcolor(p["net"]); sq = (n == 1 and not ref.startswith(("S1", "SP_")))
        if ref.startswith(("S1", "SP_")):          # spare hole: bare gold ring, nothing plugged in
            ax.add_patch(Circle((X(p["x"]), p["y"]), p["size"]/2, fc="#d4af37", ec="#d4af37", lw=0.8, zorder=3))
            ax.add_patch(Circle((X(p["x"]), p["y"]), p["drill"]/2, fc="#0d0d0d" if under else "#333", ec="none", zorder=3.1)); continue
        if sq: ax.add_patch(Rectangle((X(p["x"]) - p["size"]/2, p["y"] - p["size"]/2), p["size"], p["size"], fc=c, ec="#d4af37", lw=1.2, zorder=3))
        else:  ax.add_patch(Circle((X(p["x"]), p["y"]), p["size"]/2, fc=c, ec="#d4af37", lw=1.2, zorder=3))
        ax.add_patch(Circle((X(p["x"]), p["y"]), p["drill"]/2, fc="#0d0d0d" if under else "#333", ec="none", zorder=3.1))
    for mx, my in MOUNT:
        ax.add_patch(Circle((X(mx), my), 1.6, fc="white", ec="#0b2a18", lw=1, zorder=1))
    ax.set_xlim(-14, 84); ax.set_ylim(-9, 57); ax.set_aspect("equal"); ax.axis("off")

LAB = {  # connector labels for the picture (silkscreen labels come with routing)
    "JPWR": ("POWER IN\n(xiwai)", 0, -3.4), "JPRESTO": ("PRESTO\nlead", 0, 3.2), "JQW": ("Qw/ST", 0, 3.0),
    "JKNOB": ("", 0, 0), "JI2C": ("I2C add-on", 0, -3.3), "JCTRL": ("", 0, 0), "JG1": ("GAUGE I", 11.5, 0), "JG2": ("GAUGE II", 11.5, 0),
    "RA": ("Ra 330", 0, 0), "RB": ("Rb 330", 0, 0)}
fig = plt.figure(figsize=(15, 17.5))
ax = fig.add_axes([0.01, 0.44, 0.98, 0.50]); draw(ax, False)
fig.text(0.02, 0.985, "ICCYC hub PCB - PLACEMENT DRAFT P3 (2026-10-11: + mounting holes, I2C add-on, amp spares, lettering).  PARTS SIDE, your view: back of the panel facing you, "
             "cut tab at the bottom.\nNo copper drawn yet - this is where everything sits.  70 x 50 mm, same outline as the perfboard.",
             fontsize=11, ha="left", va="top", weight="bold")
for ref, (t, dx, dy) in LAB.items():
    ps = [p for (r, n), p in pads.items() if r == ref]
    cx = sum(p["x"] for p in ps)/len(ps); cy = sum(p["y"] for p in ps)/len(ps)
    if t: ax.text(cx + dx, cy + dy, t, fontsize=7.5 if not ref.startswith("JG") else 9, ha="center", va="center",
                  color="#2ca02c" if ref.startswith("JG") else "white", weight="bold", zorder=7)
for ref in ("JCTRL", "JKNOB", "JG1", "JG2", "JQW", "JPWR", "JPRESTO", "JI2C"):
    for (r, n), p in pads.items():
        if r != ref: continue
        if ref == "JCTRL": ax.text(p["x"], p["y"] + 1.6, p["label"], fontsize=5.6, ha="center", va="bottom", rotation=90, color="white", zorder=7)
        elif ref in ("JG1", "JG2"): ax.text(p["x"] + 1.4, p["y"], p["label"], fontsize=6, ha="left", va="center", color="white", zorder=7)
        elif ref == "JI2C": ax.text(p["x"], p["y"] - 1.3, p["label"], fontsize=5.5, ha="center", va="top", color="white", zorder=7)
        elif ref == "JKNOB": ax.text(p["x"] + 1.3, p["y"], p["label"], fontsize=6, ha="left", va="center", color="white", zorder=7)
        elif ref == "JQW": ax.text(p["x"] - 1.3, p["y"], p["label"].split(":")[0].replace(" blk","").replace(" blu","").replace(" yel","").replace("red","3V3 x"), fontsize=5.5, ha="right", va="center", color="white", zorder=7)
        else: ax.text(p["x"], p["y"] - 1.3, p["label"], fontsize=7, ha="center", va="top", color="white", weight="bold", zorder=7)
def draw_silk(ax, bottom):
    X = (lambda x: BOARD_W - x) if bottom else (lambda x: x)
    HA = {"c": "center", "l": "left", "r": "right"}
    for kind, d in SILK:
        if kind == "box" and not bottom:
            x0, y0, x1, y1 = d; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="white", lw=1.0, zorder=6))
        elif kind == "line" and not bottom:
            (a, b) = d; ax.plot([a[0], b[0]], [a[1], b[1]], color="white", lw=1.0, zorder=6)
        elif kind == ("btext" if bottom else "text"):
            t, x, y, h, ang, bold, just = d
            ha = HA[just]
            if bottom and just != "c": ha = {"left": "right", "right": "left"}[ha]
            ax.text(X(x), y, t, fontsize=h*6.2, ha=ha, va="center", rotation=ang, rotation_mode="anchor", color="white",
                    weight="bold" if bold else "normal", zorder=7)
ax.text(2.5, 12.6, "KNOB", fontsize=7.5, ha="center", va="center", rotation=90, color="white", weight="bold", zorder=7)
draw_silk(ax, False)
arr = dict(arrowstyle="-|>", mutation_scale=16, lw=2.2)
ax.add_patch(FancyArrowPatch((66, 24), (80, 24), color="#2ca02c", **arr)); ax.text(73, 26, "to the\nGAUGES", ha="center", fontsize=9, color="#2ca02c", weight="bold")
ax.add_patch(FancyArrowPatch((3, 12), (-12, 12), color="#17becf", **arr)); ax.text(-6, 14.3, "to the KNOB", ha="center", fontsize=8.5, color="#0f8a97", weight="bold")
ax.add_patch(FancyArrowPatch((24, -1.5), (24, -8), color="#17becf", **arr)); ax.text(26, -6.3, "to the switch row\n(toggles + pilot lights)", fontsize=8.5, color="#0f8a97", weight="bold")
ax.add_patch(FancyArrowPatch((49, -8), (49, -1.5), color="#d62728", **arr)); ax.text(51, -6.3, "power lead from\nthe back plate", fontsize=8.5, color="#d62728", weight="bold")
ax.text(36.35, 25.7, "CABLE\nSLOT", fontsize=6.5, ha="center", va="center", color="#555", rotation=90, zorder=7)
ax.text(-13.8, 33.9, "speaker\nwires\n<-", fontsize=7.5, color="#5b2a78", va="center")

ax2 = fig.add_axes([0.01, 0.02, 0.56, 0.38]); draw(ax2, True)
ax2.set_title("UNDERSIDE (board flipped left-to-right). Only pin ends poke through here:\n"
              "trim them flush, under 2 mm. Dashed line = P1's ledge: no pin outside it.", fontsize=10, loc="left", weight="bold")
axl = fig.add_axes([0.58, 0.02, 0.41, 0.39]); axl.axis("off")
L = ["WHAT'S WHERE",
     "Same parts in the same places as the perfboard: the amp's socket in",
     "the perfboard's column C, 0x11 in E-K, 0x10 in O-U (your bare Zeros",
     "fitted these holes on 2026-10-09). Blue / purple boxes = the Zeros",
     "and the amp, sitting about 8.5 mm up on their sockets.",
     "",
     "CONNECTORS (you solder, all on top)",
     "  POWER IN   JST-PH 2-pin: the xiwai lead plugs straight in",
     "  PRESTO     JST-PH 2-pin: PH-to-PH cable to the Presto's battery plug",
     "  Qw/ST      4 pins: the kit's JST-SH -> female-socket cable",
     "             (its red 3.3 V wire lands on a pin that goes nowhere)",
     "  GAUGE I/II 7 pins each, in the module's own order",
     "  KNOB       5 pins: A, C, B, SW, SW G",
     "  SWITCHES   12 pins in the panel's order seen from the back,",
     "             each part with its own ground pin (no ground bus)",
     "",
     "CABLE SLOT  5.5 x 12.5 mm, between the Zeros: the Qw/ST cable and",
     "  the Presto power lead come up through it from the Presto",
     "  (the Qw/ST port sits right under it). VERIFY at the bench.",
     "",
     "SPARE HOLES (plain gold rings, boxed + titled SPARE on the board)",
     "  every unused Zero pin, wired to that pin, plus 5V / GND / 3V3,",
     "  for reusing the spare boards later. Nothing to solder now.",
     "",
     "CHECKED BY SCRIPT (hub_pcb.py)  53 Zero / amp pins = the perfboard's;",
     "  every perfboard wire has a pin; nothing on the ledge or by the slot;",
     "  KiCad's check: no parts collide. Copper: next, after your OK.",
     "",
     "FOR REUSE (added 2026-10-11)  4 x M3 mounting holes in the corners;",
     "  an I2C add-on header (GND 3V3 SDA SCL) for a sensor later; the",
     "  amp's GAIN + SD by the amp with a GND hole (wire GAIN to GND = 12 dB)",
     "",
     "OPEN (doesn't block the copper)",
     "  - the perfboard flat in P1's pocket (when you're at the bench)",
     "  - Presto power lead: through the slot, or over the bottom edge",
     "  - gauge pins + room for a plug behind each gauge"]
for i, t in enumerate(L):
    axl.text(0.0, 1 - i*0.0285, t, transform=axl.transAxes, va="top", fontsize=8.6,
             weight="bold" if t and t == t.upper() and not t.startswith(" ") else "normal", family="monospace" if t.startswith(" ") else None)
fig.savefig("hub_pcb_placement.png", dpi=120, facecolor="white")
print("picture saved")


# ------------------------------------------------------------------ copper pictures (both sides), 2026-10-11
from matplotlib.path import Path
from matplotlib.patches import PathPatch
TRACECOL = lambda n: {"GND": "#111111"}.get(n, netcolor(n) if netcolor(n) != "#ffffff" else "#bfbfbf")
def poly_patches(ps, X, **kw):
    out = []
    for i in range(ps.OutlineCount()):
        verts, codes = [], []
        chains = [ps.Outline(i)] + [ps.Hole(i, j) for j in range(ps.HoleCount(i))]
        for ch in chains:
            pts = [jv(ch.CPoint(k)) for k in range(ch.PointCount())]
            if len(pts) < 3: continue
            verts += [(X(x), y) for x, y in pts] + [(0, 0)]
            codes += [Path.MOVETO] + [Path.LINETO]*(len(pts) - 1) + [Path.CLOSEPOLY]
        if verts: out.append(PathPatch(Path(verts, codes), **kw))
    return out
def draw_copper(ax, bottom):
    X = (lambda x: BOARD_W - x) if bottom else (lambda x: x)
    layer = pcbnew.B_Cu if bottom else pcbnew.F_Cu
    ax.add_patch(Rectangle((0, 0), BOARD_W, BOARD_H, fc="#14532d", ec="#0b2a18", lw=1.5, zorder=0))      # bare board under the mask
    for z in brd.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer): continue
        for p in poly_patches(z.GetFilledPolysList(layer), X, fc="#3f8f5a", ec="none", zorder=1): ax.add_patch(p)
    for t in brd.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = jv(t.GetPosition())
            ax.add_patch(Circle((X(x), y), pcbnew.ToMM(t.GetWidth())/2, fc="#d4af37", ec="none", zorder=4))
            ax.add_patch(Circle((X(x), y), 0.2, fc="black", ec="none", zorder=4.1)); continue
        if t.GetLayer() != layer: continue
        a, b = jv(t.GetStart()), jv(t.GetEnd())
        wpt = pcbnew.ToMM(t.GetWidth())*PT_PER_MM
        ax.plot([X(a[0]), X(b[0])], [a[1], b[1]], color=TRACECOL(t.GetNetname()), lw=wpt, solid_capstyle="round", zorder=3)
    for (ref, n), p in pads.items():
        sq = (n == 1 and not ref.startswith(("S1", "SP_")))
        if sq: ax.add_patch(Rectangle((X(p["x"]) - p["size"]/2, p["y"] - p["size"]/2), p["size"], p["size"], fc="#d4af37", ec="none", zorder=4))
        else:  ax.add_patch(Circle((X(p["x"]), p["y"]), p["size"]/2, fc="#d4af37", ec="none", zorder=4))
        ax.add_patch(Circle((X(p["x"]), p["y"]), p["drill"]/2, fc="black", ec="none", zorder=4.1))
    x0, y0, x1, y1 = SLOT
    ax.add_patch(FancyBboxPatch((min(X(x0), X(x1)), y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={(x1-x0)/2}", fc="white", ec="none", zorder=5))
    for mx, my in MOUNT: ax.add_patch(Circle((X(mx), my), 1.6, fc="white", ec="none", zorder=5))
    ax.add_patch(Rectangle((LEDGE, LEDGE), BOARD_W - 2*LEDGE, BOARD_H - 2*LEDGE, fc="none", ec="#cfe8b0", lw=0.8, ls=(0, (4, 3)), zorder=5))
    if not bottom:
        for name, ex0, ey0, ex1, ey1 in ELEV:
            ax.add_patch(FancyBboxPatch((ex0, ey0), ex1 - ex0, ey1 - ey0, boxstyle="round,pad=0,rounding_size=1", fc="none", ec="#9cc3ff", lw=1.0, ls=(0, (5, 3)), zorder=5.5))
        ax.add_patch(Rectangle((AMPBOX[0], AMPBOX[1]), AMPBOX[2] - AMPBOX[0], AMPBOX[3] - AMPBOX[1], fc="none", ec="#d6b3ef", lw=1.0, ls=(0, (5, 3)), zorder=5.5))
    draw_silk(ax, bottom)
    ax.set_xlim(-8, 78); ax.set_ylim(-2, 52); ax.set_aspect("equal"); ax.axis("off")
VIA_R = hub_router.VIA_D/2
fig = plt.figure(figsize=(16, 17))
ax1 = fig.add_axes([0.0, 0.50, 0.70, 0.445]); ax2 = fig.add_axes([0.0, 0.02, 0.70, 0.445])
PT_PER_MM = (ax1.get_position().width*16*72)/86.0      # so traces are drawn at their true width
draw_copper(ax1, False); draw_copper(ax2, True)
fig.text(0.02, 0.985, "ICCYC hub PCB rev A - COPPER C3 (2026-10-11: JST-PH sockets now pin 1 = ground, pin 2 = +5 V, the usual battery order).  Checked by script + KiCad, not by Jason yet.", fontsize=13, weight="bold", va="top")
ax1.set_title("1. TOP = PARTS SIDE, your view: back of the panel facing you, cut tab at the bottom", fontsize=11, loc="left", weight="bold")
ax2.set_title("2. BOTTOM = SOLDER SIDE, flipped left-to-right (how you'll see it when you turn the board over)", fontsize=11, loc="left", weight="bold")
axl = fig.add_axes([0.70, 0.05, 0.29, 0.88]); axl.axis("off")
LL = [("HOW TO READ IT", None),
      ("Gold dots / squares = pads (square = pin 1).", None),
      ("Black dot in gold = the hole a pin goes through.", None),
      ("Small gold rings = VIAS: tiny plated holes where a", None),
      ("  trace hops to the other face. Nothing goes in them.", None),
      ("Lines = TRACES (the copper 'wires'), drawn at their", None),
      ("  real width, coloured by what they carry:", None),
      ("+5 V (0.6 mm wide)", "+5V"), ("ground, power return (0.6 mm)", "GND"), ("3.3 V to the gauges (0.4 mm)", "3V3_G"),
      ("I2C data SDA (0.25 mm)", "SDA"), ("I2C clock SCL", "SCL"), ("sound to the amp", "DIN"),
      ("gauge display lines", "SCK"), ("knob + toggles", "ENC_A"), ("pilot lights", "LED_WIFI"), ("spare pins", "0x11_GP26"),
      ("", None),
      ("Light green = GROUND FILL: all the copper left over", None),
      ("  on each face is joined to ground. Every ground pin", None),
      ("  without its own trace connects through it, with", None),
      ("  4 short 'spokes' (a thermal relief) so the pad", None),
      ("  doesn't suck the heat away from your iron.", None),
      ("Dark green = bare board (no copper).", None),
      ("Dashed outlines = where the Zeros and the amp sit,", None),
      ("  8.5 mm up on their sockets.", None),
      ("White lettering = silkscreen (printed labels).", None),
      ("", None),
      ("WHY THE WIDTHS", None),
      ("Signals carry almost no current: 0.25 mm is plenty.", None),
      ("+5 V and its ground return carry up to ~0.7 A in a", None),
      ("  loud chime, so they're 0.6 mm (good for >1 A).", None),
      ("", None),
      ("CHECKED (hub_pcb.py + KiCad's own check)", None),
      ("every pin connected; no copper closer than 0.2 mm", None),
      ("  to other copper (OSH Park allows 0.15); copper", None),
      ("  0.5 mm+ from the edge, slot and holes; nothing", None),
      ("  on P1's ledge (dashed line).", None)]
yy = 1.0
for t, n in LL:
    if n:
        axl.plot([0.0, 0.07], [yy - 0.006, yy - 0.006], transform=axl.transAxes, color=TRACECOL(n), lw=4 if WIDTH.get(n) else 2)
        axl.text(0.09, yy, t, transform=axl.transAxes, va="top", fontsize=9)
    else:
        axl.text(0.0, yy, t, transform=axl.transAxes, va="top", fontsize=9.5 if t.isupper() else 9, weight="bold" if t.isupper() else "normal")
    yy -= 0.0205
fig.savefig("hub_pcb_copper.png", dpi=110, facecolor="white")
print("copper picture saved")


# ------------------------------------------------------------------ fab files + KiCad's own drawing (independent check)
import subprocess, shutil, zipfile
shutil.rmtree("gerbers", ignore_errors=True); os.makedirs("gerbers")
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts",
                "--no-protel-ext", "-o", "gerbers/", "hub_pcb.kicad_pcb"], check=True, capture_output=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--excellon-oval-format", "alternate",
                "--excellon-zeros-format", "decimal", "--drill-origin", "absolute", "-o", "gerbers/",
                "hub_pcb.kicad_pcb"], check=True, capture_output=True)
with zipfile.ZipFile("hub_pcb_revA_gerbers.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(os.listdir("gerbers")): zf.write(os.path.join("gerbers", f), f)
try:
    import cairosvg
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs("svg", exist_ok=True)
    for name, layers, extra in (("top", "F.Cu,F.SilkS,Edge.Cuts", []), ("bot", "B.Cu,B.SilkS,Edge.Cuts", ["--mirror"])):
        subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--exclude-drawing-sheet", "--page-size-mode", "2",
                        *extra, "-o", f"svg/{name}.svg", "hub_pcb.kicad_pcb"], check=True, capture_output=True)
        cairosvg.svg2png(url=f"svg/{name}.svg", write_to=f"svg/{name}.png", output_width=1100, background_color="white")
    ims = [Image.open(f"svg/{n}.png").convert("RGB") for n in ("top", "bot")]
    out = Image.new("RGB", (1100, sum(i.height for i in ims) + 100), "white"); d = ImageDraw.Draw(out)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    d.text((10, 8), "KiCad's own drawing of hub_pcb.kicad_pcb - TOP (parts side, your view)", fill="black", font=f)
    out.paste(ims[0], (0, 38)); y = 38 + ims[0].height + 12
    d.text((10, y), "BOTTOM (solder side, flipped left-to-right)", fill="black", font=f)
    out.paste(ims[1], (0, y + 30)); out.save("hub_pcb_kicad_view.png")
    print("KiCad view + gerbers saved")
except ImportError:
    print("cairosvg missing: KiCad view skipped (pip install cairosvg)")
