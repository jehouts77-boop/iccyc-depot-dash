# ICCYC hub perfboard layout - draft v2 (2026-10-09).
# Single source of truth: every hole, link and route is defined here; the script checks them and draws
# hub-board-layout.png. Change the layout HERE and re-run:  python hub_layout.py
#
# 2026-10-11: added a link-crossing check. Links 8 and 9 (under the board) cross once near N16-N17; built that way
# by Jason 2026-10-11, measured 1.7 mm at the crossing (limit 2 mm) -> accepted, listed in ACCEPTED_CROSSINGS.
#
# Hole names are the ones printed on Jason's boards: columns A-X, rows 1-18, and seen from the parts side
# (as the board sits on the hub shelf, back of the panel facing you) A is at the LEFT and row 18 at the TOP.
#
# v1 -> v2 (2026-10-09): board measured 70 x 50 mm (was assumed 61 x 46); links re-routed so that none lies
# under the board except the two I2C links; ground rail hooks into C3 / W3; amp signals land on column B.
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

COLS = "ABCDEFGHIJKLMNOPQRSTUVWX"; NROW = 18
PITCH = 2.54
BOARD_W, BOARD_H = 70.0, 50.0      # measured by Jason 2026-10-09
LEDGE = 3.5                        # the hub shelf (P1) supports the board this far in from each edge
def cx(c): return COLS.index(c)
def parse(h): return h[0], int(h[1:])

NETCOL = {"5V":"#d62728","GND":"#222222","3V3":"#ff7f0e","SDA":"#1f77b4","SCL":"#c9a800",
          "I2S":"#9467bd","GAUGE":"#2ca02c","CTRL":"#17becf","LED":"#e377c2","NC":"#bbbbbb"}
HOLES = {}
def put(h, net, kind, label):
    assert h not in HOLES, f"hole {h} used twice: {HOLES[h]} / {label}"
    HOLES[h] = dict(net=net, kind=kind, label=label)
W, B, L, S = "wire", "wire-from-below", "link", "bridge"

# --- amp (MAX98357A): 7 pins in column C, body hangs off the left edge. Order confirmed on the real amp 2026-10-09
for r, (net, lab) in zip(range(16, 9, -1), [("5V","Vin"),("GND","GND"),("NC","SD"),("NC","GAIN"),("DIN","DIN"),("BCLK","BCLK"),("LRC","LRC")]):
    put(f"C{r}", net, "pin", f"amp {lab}")
# --- RP2040-Zero (USB end toward row 18). Pin names confirmed against the silkscreen 2026-10-09; all 23 pins fit the grid
LEFT  = ["5V","GND","3V3","GP29","GP28","GP27","GP26","GP15","GP14"]
RIGHT = [f"GP{i}" for i in range(9)]
BOT   = ["GP13","GP12","GP11","GP10","GP9"]
def zero(name, lc, use):
    li = cx(lc)
    for i, p in enumerate(LEFT):  put(f"{COLS[li]}{16-i}",   use.get(p, "NC"), "pin", f"{name} {p}")
    for i, p in enumerate(RIGHT): put(f"{COLS[li+6]}{16-i}", use.get(p, "NC"), "pin", f"{name} {p}")
    for i, p in enumerate(BOT):   put(f"{COLS[li+1+i]}7",    use.get(p, "NC"), "pin", f"{name} {p}")
zero("0x11", "E", {"5V":"5V","GND":"GND","GP0":"SDA","GP1":"SCL","GP2":"ENC_A","GP3":"ENC_B","GP4":"ENC_SW",
                   "GP5":"SW_CHIME","GP6":"SW_DAYNIGHT","GP7":"SW_BACKLIGHT","GP8":"SW_WIFEMODE",
                   "GP9":"LED_WIFI_R","GP10":"LED_OTA_R","GP11":"BCLK","GP12":"LRC","GP13":"DIN"})
zero("0x10", "O", {"5V":"5V","GND":"GND","3V3":"3V3","GP0":"SDA","GP1":"SCL","GP2":"SCK","GP3":"MOSI",
                   "GP4":"CS1","GP5":"DC1","GP6":"RST1","GP7":"CS2","GP8":"DC2","GP9":"RST2"})
# --- +5 V block (C7 D7 C6 D6)
put("C7","5V",W,"POWER IN red (+5 V)");  put("D7","5V",L,"link 1 to D16")
put("D6","5V",B,"Presto lead red (+)");  put("C6","5V",S,"(solder only)")
# --- top-left power pads
put("B16","5V",L,"link 3 to P16");   put("D16","5V",L,"link 1 from D7")
put("B15","GND",L,"link 2 from G3"); put("D15","GND",S,"(solder only)"); put("A15","GND",L,"link 4 to P15")
put("P16","5V",L,"link 3 from B16"); put("P15","GND",L,"link 4 from A15")
# --- ground rail, row 3, C..W (bare wire on the solder side, hooked into C3 and W3)
rail = {"C":("rail","rail hook"), "W":("rail","rail hook"), "D":(W,"POWER IN black"), "E":(B,"Presto lead black (-)"),
        "G":(L,"link 2 to B15"), "H":(W,"ground bus -> switches, encoder, LEDs"), "K":(B,"Qw/ST black"),
        "U":(W,"Gauge I GND"), "V":(W,"Gauge II GND")}
for c in COLS[cx("C"):cx("W")+1]:
    k,l = rail.get(c, ("rail","GND rail (spare)")); put(f"{c}3", "GND", k, l)
# --- sound
put("B12","DIN",L,"link 5 from F6"); put("B11","BCLK",L,"link 6 from H6"); put("B10","LRC",L,"link 7 from G6")
put("F6","DIN",L,"link 5 to B12");   put("H6","BCLK",L,"link 6 to B11");   put("G6","LRC",L,"link 7 to B10")
# --- I2C
put("L16","SDA",B,"Qw/ST blue (SDA)");   put("M16","SDA",L,"link 8 to V16")
put("L15","SCL",B,"Qw/ST yellow (SCL)"); put("M15","SCL",L,"link 9 to V15")
put("V16","SDA",L,"link 8 from M16");    put("V15","SCL",L,"link 9 from M15")
# --- knob + toggles
for r,(n,l) in zip(range(14,7,-1),[("ENC_A","Encoder A"),("ENC_B","Encoder B"),("ENC_SW","Encoder push"),
        ("SW_CHIME","CHIME toggle"),("SW_DAYNIGHT","DAY-NIGHT toggle"),("SW_BACKLIGHT","BACKLIGHT toggle"),("SW_WIFEMODE","WIFE MODE toggle")]):
    put(f"L{r}", n, W, l)
# --- pilot-light resistors
put("J6","LED_WIFI_R","res","Ra 330R"); put("N6","LED_WIFI","res","Ra 330R"); put("O6","LED_WIFI",W,"WiFi LED + (long leg)")
put("I6","LED_OTA_R",S,"(solder only)"); put("I5","LED_OTA_R","res","Rb 330R")
put("M5","LED_OTA","res","Rb 330R");     put("M4","LED_OTA",W,"OTA LED + (long leg)")
# --- gauges
put("N14","3V3",W,"Gauge I VCC"); put("M14","3V3",W,"Gauge II VCC")
put("V14","SCK",W,"Gauge I SCL"); put("W14","SCK",W,"Gauge II SCL")
put("V13","MOSI",W,"Gauge I SDA"); put("W13","MOSI",W,"Gauge II SDA")
put("V12","CS1",W,"Gauge I CS"); put("V11","DC1",W,"Gauge I DC"); put("V10","RST1",W,"Gauge I RST")
put("V9","CS2",W,"Gauge II CS"); put("V8","DC2",W,"Gauge II DC"); put("T6","RST2",W,"Gauge II RST")

# links: number, from, to, what, side, route as (column position, row) points; column position 0 = A, 1 = B ...
P="parts"; SS="solder"
LINKS = [
 (1,"D7","D16","+5 V up to the amp and 0x11",P,[(3,7),(3,16)]),
 (2,"G3","B15","ground up to the amp and 0x11",P,[(6,3),(6,4.0),(-1.0,4.0),(-1.0,13.5),(0.5,13.5),(0.5,14.6),(1,15)]),
 (3,"B16","P16","+5 V across to 0x10",P,[(1,16),(1,17.1),(15,17.1),(15,16)]),
 (4,"A15","P15","ground across to 0x10",P,[(0,15),(0,17.7),(16,17.7),(16,15.5),(15,15)]),
 (5,"F6","B12","sound data DIN (GP13)",P,[(5,6),(5,4.5),(-0.5,4.5),(-0.5,12),(1,12)]),
 (6,"H6","B11","sound clock BCLK (GP11)",P,[(7,6),(7,5.0),(0.0,5.0),(0.0,11),(1,11)]),
 (7,"G6","B10","sound L/R clock LRC (GP12)",P,[(6,6),(6,5.5),(0.5,5.5),(0.5,10),(1,10)]),
 (8,"M16","V16","I2C data SDA across to 0x10",SS,[(12,16),(12,16.8),(21,16.8),(21,16)]),
 (9,"M15","V15","I2C clock SCL across to 0x10",SS,[(12,15),(13,15.5),(13,17.35),(22,17.35),(22,15),(21,15)]),
]
RES = [("J6","N6","Ra"),("I5","M5","Rb")]

# ---------------- checks ----------------
def nb(h):
    c,r = parse(h); i = cx(c); out=[]
    for dc,dr in ((1,0),(-1,0),(0,1),(0,-1)):
        if 0<=i+dc<24 and 1<=r+dr<=NROW: out.append(f"{COLS[i+dc]}{r+dr}")
    return out
errs=[]; notes=[]
nets={}
for h,d in HOLES.items():
    if d["net"]!="NC": nets.setdefault(d["net"],[]).append(h)
link_adj={}
for n,a,b,*_ in LINKS:
    assert HOLES[a]["net"]==HOLES[b]["net"], (a,b)
    assert HOLES[a]["kind"]==L and HOLES[b]["kind"]==L, (a,b)
    link_adj.setdefault(a,[]).append(b); link_adj.setdefault(b,[]).append(a)
for n,hs in nets.items():                       # every net is one joined group (touching pads, a link, or the rail)
    seen={hs[0]}; todo=[hs[0]]
    while todo:
        h=todo.pop()
        for x in nb(h)+link_adj.get(h,[]):
            if x in HOLES and HOLES[x]["net"]==n and x not in seen: seen.add(x); todo.append(x)
    if len(seen)!=len(hs): errs.append(f"net {n} is not fully joined: {sorted(set(hs)-seen)} left out")
for h,d in HOLES.items():                       # touching pads on different nets
    for x in nb(h):
        if x in HOLES and x>h:
            a,b = d["net"],HOLES[x]["net"]
            if a!=b and "NC" not in (a,b):
                if "5V" in (a,b) and {a,b}!={"5V","GND"}: errs.append(f"+5 V pad beside a signal pad: {h}({a}) / {x}({b})")
                elif "5V" in (a,b) and not (d["kind"]=="pin" and HOLES[x]["kind"]=="pin"): notes.append(f"{h}({a}) beside {x}({b})")
for h,d in HOLES.items():                       # rows 1 and 18 sit on the shelf ledge (hole centre 3.4 mm from the edge)
    if parse(h)[1] in (1,18): errs.append(f"{h} is in row 1/18 (on the shelf ledge)")
for a,b,n in RES:
    if abs(cx(a[0])-cx(b[0]))*PITCH < 10: errs.append(f"{n} span too short")
# a link lying on the SOLDER side must not lie on a pad that gets soldered
def seg_pts(route):
    pts=[]
    for (x0,y0),(x1,y1) in zip(route,route[1:]):
        n=max(2,int(max(abs(x1-x0),abs(y1-y0))*20))
        pts += [(x0+(x1-x0)*t/n, y0+(y1-y0)*t/n) for t in range(n+1)]
    return pts
for n,a,b,what,side,route in LINKS:
    assert route[0]==(cx(a[0]),int(a[1:])) and route[-1]==(cx(b[0]),int(b[1:])), f"link {n} route ends"
    if side==SS:
        for h,d in HOLES.items():
            if h in (a,b): continue
            c,r=parse(h)
            if any(abs(x-cx(c))<0.3 and abs(y-r)<0.3 for x,y in seg_pts(route)): errs.append(f"solder-side link {n} lies on pad {h}")
# links on the same side that cross each other (added 2026-10-11: v2 was published saying "under the board
# nothing crosses", but links 8 and 9 cross once near N16-N17 and no check caught it)
ACCEPTED_CROSSINGS = {frozenset((5,6)), frozenset((5,7)),   # parts side, insulated, room above (built 2026-10-10)
                      frozenset((8,9))}                     # under the board; built 2026-10-11, measured 1.7 mm (limit 2 mm)
def _segs(route): return list(zip(route, route[1:]))
def _cross(p1,p2,q1,q2):
    def o(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    d1,d2,d3,d4 = o(q1,q2,p1),o(q1,q2,p2),o(p1,p2,q1),o(p1,p2,q2)
    return (d1*d2<0) and (d3*d4<0)
crossings=[]
for i,(n1,*_,s1,r1) in enumerate(LINKS):
    for (n2,*_,s2,r2) in LINKS[i+1:]:
        if s1!=s2: continue
        if any(_cross(a,b,c,d) for a,b in _segs(r1) for c,d in _segs(r2)):
            crossings.append((n1,n2,s1))
            if frozenset((n1,n2)) not in ACCEPTED_CROSSINGS: errs.append(f"links {n1} and {n2} cross ({s1} side)")
print("link crossings:", crossings)
print("holes used:", len(HOLES)); print("ERRORS:", errs or "none")
print("+5 V beside ground on wire pads (expected, check with a meter):", notes)
json.dump(HOLES, open("hub_holes.json","w"), indent=1)

# ---------------- drawing ----------------
def netcolor(n):
    if n in NETCOL: return NETCOL[n]
    if n in ("DIN","BCLK","LRC"): return NETCOL["I2S"]
    if n in ("SCK","MOSI","CS1","DC1","RST1","CS2","DC2","RST2"): return NETCOL["GAUGE"]
    if n.startswith("LED"): return NETCOL["LED"]
    return NETCOL["CTRL"]
MX = (BOARD_W-23*PITCH)/2/PITCH; MY = (BOARD_H-17*PITCH)/2/PITCH; LG = LEDGE/PITCH

def draw(ax, mirror, title):
    X = (lambda x: 23-x) if mirror else (lambda x: x)
    Y = lambda r: r
    ax.add_patch(Rectangle((-MX, 1-MY), 23+2*MX, 17+2*MY, fc="#f3ecd2", ec="#6b5d2e", lw=1.5, zorder=0))
    ax.add_patch(Rectangle((-MX+LG, 1-MY+LG), 23+2*MX-2*LG, 17+2*MY-2*LG, fc="#fbf8ea", ec="#b9ab78", lw=0.8, ls="--", zorder=0.1))
    if not mirror:
        for name, lc in (("0x11  (controls)", "E"), ("0x10  (gauges)", "O")):
            i = cx(lc)
            ax.add_patch(FancyBboxPatch((i-0.5, 6.45), 7.0, 10.35, boxstyle="round,pad=0.02,rounding_size=0.3", fc="#2f6fb5", ec="#12365e", alpha=0.16, lw=1.2, zorder=1))
            ax.add_patch(Rectangle((i+1.7, 16.1), 3.6, 1.25, fc="#999", ec="#444", alpha=0.45, zorder=1.1))
            ax.text(i+3.5, 16.72, "USB", ha="center", va="center", fontsize=6, zorder=5)
            ax.text(i+3, 11.3, name, ha="center", va="center", fontsize=9, color="#12365e", weight="bold", rotation=90, zorder=5, alpha=0.8)
        ax.add_patch(FancyBboxPatch((2.5-18.7/PITCH, 13-17.5/PITCH/2), 18.7/PITCH, 17.5/PITCH, boxstyle="round,pad=0.02,rounding_size=0.3", fc="#7b3fa0", ec="#3d1757", alpha=0.13, lw=1.2, zorder=1))
        ax.text(-3.6, 15.9, "AMP (above the wires)", ha="center", va="center", fontsize=6.5, color="#3d1757", zorder=5)
        ax.add_patch(Rectangle((-4.75, 11.55), 1.4, 2.9, fc="#3aa655", ec="#1c5a2c", alpha=0.5, zorder=1.2))
        ax.text(-5.0, 13, "speaker\nscrews", ha="right", va="center", fontsize=6)
    for i in range(24):
        for r in range(1, NROW+1):
            if f"{COLS[i]}{r}" not in HOLES: ax.add_patch(Circle((X(i), Y(r)), 0.13, fc="#c9bf99", ec="none", zorder=2))
    for h,d in HOLES.items():                   # solder bridges
        if d["net"]=="NC": continue
        c,r = parse(h); i=cx(c)
        for x in nb(h):
            if x in HOLES and HOLES[x]["net"]==d["net"] and x>h:
                c2,r2=parse(x); i2=cx(c2)
                if d["kind"]=="pin" and HOLES[x]["kind"]=="pin": continue
                ax.plot([X(i),X(i2)],[Y(r),Y(r2)], color=netcolor(d["net"]), lw=6 if mirror else 3.5, alpha=0.9 if mirror else 0.3, solid_capstyle="round", zorder=2.5)
    for n,a,b,what,side,route in LINKS:         # links, drawn along their real routes
        here = (side==SS)==mirror
        xs=[X(p[0]) for p in route]; ys=[Y(p[1]) for p in route]
        ax.plot(xs, ys, color=netcolor(HOLES[a]["net"]), lw=2.2 if here else 0.9, ls="-" if here else (0,(1,2.5)), zorder=6 if here else 3, alpha=0.95 if here else 0.5, solid_joinstyle="round")
        if here:
            k=len(route)//2; mxp=(xs[k-1]+xs[k])/2; myp=(ys[k-1]+ys[k])/2
            ax.text(mxp, myp, str(n), fontsize=6.5, ha="center", va="center", zorder=7, bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec=netcolor(HOLES[a]["net"]), lw=0.8))
    if not mirror:
        for a,b,n in RES:
            (ca,ra),(cb,rb)=parse(a),parse(b)
            ax.plot([cx(ca),cx(cb)],[ra,rb], color="#555", lw=1, zorder=3)
            ax.add_patch(Rectangle((cx(ca)+0.8, ra-0.32), cx(cb)-cx(ca)-1.6, 0.64, fc="#d9b98a", ec="#6b4a1e", zorder=3.5))
            ax.text((cx(ca)+cx(cb))/2, ra, n+" 330", fontsize=5.5, ha="center", va="center", zorder=4)
    for h,d in HOLES.items():
        c,r=parse(h); i=cx(c); col=netcolor(d["net"]); k=d["kind"]
        if k=="pin":   ax.add_patch(Rectangle((X(i)-0.36, Y(r)-0.36), 0.72, 0.72, fc=col if d["net"]!="NC" else "white", ec="#333", lw=0.7, zorder=4))
        elif k==B:     ax.add_patch(Circle((X(i), Y(r)), 0.36, fc="white", ec=col, lw=2.2, zorder=4)); ax.add_patch(Circle((X(i), Y(r)), 0.12, fc=col, ec="none", zorder=4.1))
        elif k in ("rail",S): ax.add_patch(Circle((X(i), Y(r)), 0.2, fc=col, ec="none", zorder=4))
        elif k=="res": ax.add_patch(Circle((X(i), Y(r)), 0.26, fc="#d9b98a", ec=col, lw=1.5, zorder=4))
        else:          ax.add_patch(Circle((X(i), Y(r)), 0.36, fc=col, ec="white", lw=0.8, zorder=4))
    for i in range(24):
        for yy in (19.9, 0.1): ax.text(X(i), yy, COLS[i], ha="center", va="center", fontsize=8, weight="bold")
    for r in range(1, NROW+1):
        ax.text(-3.2 if mirror else 26.2, Y(r), str(r), ha="center", va="center", fontsize=8, weight="bold")
    ax.set_xlim(-9.5, 27.5); ax.set_ylim(-1.0, 20.6); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=11, loc="left", weight="bold")

fig = plt.figure(figsize=(15.5, 18))
ax1 = fig.add_axes([0.02, 0.50, 0.66, 0.46]); ax2 = fig.add_axes([0.02, 0.03, 0.66, 0.46])
draw(ax1, False, "1. PARTS SIDE - your view: back of the panel facing you, cut tab at the bottom.  A at your left, row 18 at the panel top.")
draw(ax2, True,  "2. SOLDER SIDE (board flipped left-to-right: X is now at your left). Thick bars = pads joined with solder.")
ax1.text(27.3, 11, "to the GAUGES  ->", rotation=90, fontsize=9, va="center", color="#2ca02c", weight="bold")
ax1.text(-9.3, 8.6, "<- to the SPEAKER\n    and KNOB", fontsize=9, va="center", color="#7b3fa0", weight="bold")
ax1.text(11.5, -0.75, "POWER IN and the Presto lead arrive from this (bottom) edge", fontsize=8, ha="center", color="#d62728")
axl = fig.add_axes([0.69, 0.03, 0.30, 0.93]); axl.axis("off")
y=0.995
def line(t, **kw):
    global y; dy=kw.pop("dy",0.0125); axl.text(0, y, t, transform=axl.transAxes, va="top", **kw); y-=dy*0.84
line("ICCYC hub board - DRAFT v2, 2026-10-09", fontsize=11, weight="bold", dy=0.018)
line("Board 70 x 50 mm, 24 x 18 holes. Checked by script only\n(no hole used twice, every net joined, no +5 V pad beside\na signal pad, no under-board wire on a pad, link crossings listed).", fontsize=8, dy=0.042)
line("SYMBOLS", fontsize=9, weight="bold", dy=0.016)
for t in ["square  = a pin of a Zero or the amp (white = unused pin)","filled dot  = a wire soldered in from the parts side",
          "ring with dot  = a wire that comes up from underneath","tan dot  = resistor leg;  small dot = solder only / rail",
          "numbered line  = insulated link wire, drawn on its real route","faint dotted line  = a link on the other side of the board",
          "dashed box  = the shelf supports the board outside it"]:
    line("  "+t, fontsize=7.5)
y-=0.006
line("COLOURS", fontsize=9, weight="bold", dy=0.016)
for n,t in [("5V","+5 V"),("GND","ground"),("3V3","3.3 V (gauges only)"),("SDA","I2C data (blue wire)"),("SCL","I2C clock (yellow wire)"),
            ("I2S","sound to the amp"),("GAUGE","gauge display lines"),("CTRL","knob + toggles"),("LED","pilot lights")]:
    axl.add_patch(Rectangle((0.01, y-0.009), 0.05, 0.008, transform=axl.transAxes, fc=NETCOL[n], ec="none"))
    axl.text(0.08, y, t, transform=axl.transAxes, va="top", fontsize=7.5); y-=0.0125*0.84
y-=0.006
line("LINKS (insulated wire, hole to hole)", fontsize=9, weight="bold", dy=0.016)
for n,a,b,what,side,route in LINKS:
    line(f"  {n}  {a:<4}-> {b:<4} {what}" + ("  [UNDER]" if side==SS else ""), fontsize=7.0, family="monospace", dy=0.0118)
line("  Links 1-7 lie on the parts side. 8 and 9 lie under the board\n  and cross once near N16-N17 (built 2026-10-11: 1.7 mm, OK).", fontsize=7.3, dy=0.026)
y-=0.006
line("WIRES THAT LEAVE THE BOARD", fontsize=9, weight="bold", dy=0.016)
order = sorted([h for h,d in HOLES.items() if d["kind"] in (W,B)], key=lambda h:(cx(h[0]), -int(h[1:])))
for h in order:
    d=HOLES[h]; line(f"  {h:<4}{d['label']}" + ("   (from below)" if d["kind"]==B else ""), fontsize=7.2, family="monospace", dy=0.0116)
y-=0.006
line("PADS JOINED WITH SOLDER (the thick bars)", fontsize=9, weight="bold", dy=0.016)
for t in ["B16-C16-D16-E16 +5 V","A15-B15-C15-D15-E15 ground","B12-C12  B11-C11  B10-C10  amp signals","K16-L16-M16 SDA     K15-L15-M15 SCL",
          "K14-L14 ... K8-L8  knob + toggles","O16-P16 +5 V   O15-P15 ground   M14-N14-O14 3.3 V","U16-V16 ... U8-V8  gauges;  V14-W14, V13-W13",
          "F7-F6 G7-G6 H7-H6 I7-I6-I5 J7-J6","T7-T6   N6-O6   M5-M4","C7-D7-C6-D6  +5 V block","row 3, C to W: one bare wire = ground rail"]:
    line("  "+t, fontsize=7.2, family="monospace", dy=0.0116)
print("legend end y =", round(y,3))
fig.savefig("hub-board-layout.png", dpi=130, facecolor="white"); print("saved")
