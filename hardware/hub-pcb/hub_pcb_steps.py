# hub_pcb_steps.py - draws the pictures for hub-pcb-solder-guide.md from hub_pcb.kicad_pcb (2026-10-24).
# Run from the project folder:  python3 hub_pcb_steps.py   (needs matplotlib; no KiCad needed)
# Writes hub-pcb-solder-guide/pcb_step*.png and pcb_check_*.png. Change the board in hub_pcb.py, re-run that, then this.
import re
def parse(s):
    toks = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', s)
    st=[[]]
    for t in toks:
        if t=='(':
            st.append([])
        elif t==')':
            x=st.pop(); st[-1].append(x)
        else:
            st[-1].append(t[1:-1] if t.startswith('"') else t)
    return st[0][0]
def find(node, key):
    return [c for c in node if isinstance(c,list) and c and c[0]==key]
def one(node,key):
    r=find(node,key); return r[0] if r else None
# Draw the hub PCB (rev A) step pictures from hub_pcb.kicad_pcb: top (parts side, Jason's view) and
# bottom (solder side, as seen when the board is flipped over left-to-right).
import sys, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Polygon
from matplotlib import patheffects as pe

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hub_pcb.kicad_pcb')
OX, OY, W, H = 100.0, 100.0, 70.0, 50.0
B = parse(open(SRC).read())

def J(x, y): return (float(x) - OX, OY + H - float(y))      # KiCad -> Jason coords (y up)
def rot(x, y, a):                                            # KiCad: angle CCW on screen, y down
    r = math.radians(a); return (x*math.cos(r) + y*math.sin(r), -x*math.sin(r) + y*math.cos(r))

FP = {}
for f in find(B, 'footprint'):
    ref = [c for c in find(f, 'fp_text') if c[1] == 'reference'][0][2]
    at = one(f, 'at'); fx, fy = float(at[1]), float(at[2]); fa = float(at[3]) if len(at) > 3 else 0.0
    pads = []
    for p in find(f, 'pad'):
        pa = one(p, 'at'); px, py = rot(float(pa[1]), float(pa[2]), fa)
        sz = one(p, 'size'); dr = one(p, 'drill')
        pads.append(dict(num=p[1], kind=p[2], shape=p[3], xy=J(fx + px, fy + py),
                         w=float(sz[1]), h=float(sz[2]), drill=float(dr[1]) if dr else 0, rot=fa))
    silk = []
    for l in find(f, 'fp_line'):
        if one(l, 'layer')[1] != 'F.SilkS': continue
        s, e = one(l, 'start'), one(l, 'end')
        a = rot(float(s[1]), float(s[2]), fa); b = rot(float(e[1]), float(e[2]), fa)
        silk.append((J(fx + a[0], fy + a[1]), J(fx + b[0], fy + b[1])))
    FP[ref] = dict(name=f[1], pads=pads, silk=silk)

TEXTS = []
for t in find(B, 'gr_text'):
    at = one(t, 'at'); lay = one(t, 'layer')[1]
    eff = one(t, 'effects'); fnt = one(eff, 'font'); size = float(one(fnt, 'size')[1])
    just = one(eff, 'justify'); js = [x for x in (just[1:] if just else []) if x in ('left', 'right')]
    TEXTS.append(dict(s=t[1], xy=J(at[1], at[2]), a=float(at[3]) if len(at) > 3 else 0, layer=lay, size=size,
                      bold='bold' in fnt, just=js[0] if js else 'center'))
GLINES = []
for l in find(B, 'gr_line'):
    lay = one(l, 'layer')[1]; s, e = one(l, 'start'), one(l, 'end')
    GLINES.append((lay, J(s[1], s[2]), J(e[1], e[2])))

# colours: OSH Park purple board, gold (ENIG) pads, white silkscreen
BOARD = '#4b2a6b'; GOLD = '#d9b44a'; SILK = '#f2f2f2'; HOLE = '#141414'
HL = '#00e5ff'; DONE = '#9aa3ad'; WARN = '#ff5a5a'

def draw(ax, bottom, hl=(), done=(), hl_color=HL, notes=(), dim_text=False, tag_pads=None, hl_map=None):
    hl_map = dict(hl_map or {}); hl_map.update({r: hl_color for r in hl}); hl = tuple(hl_map)
    mx = (lambda x: W - x) if bottom else (lambda x: x)
    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle='round,pad=0,rounding_size=0.6', fc=BOARD, ec='#222', lw=1.2))
    # slot
    x0, y0, x1, y1 = 33.6, 19.5, 39.1, 32.0; r = (x1 - x0)/2
    sx0, sx1 = sorted((mx(x0), mx(x1)))
    ax.add_patch(FancyBboxPatch((sx0, y0), sx1 - sx0, y1 - y0, boxstyle=f'round,pad=0,rounding_size={r}', fc='white', ec='#888', lw=0.6))
    # silkscreen text of this side
    want = 'B.SilkS' if bottom else 'F.SilkS'
    for t in TEXTS:
        if t['layer'] != want: continue
        x, y = t['xy']; ha = t['just']
        if bottom and ha in ('left', 'right'): ha = 'right' if ha == 'left' else 'left'
        ax.text(mx(x), y, t['s'], rotation=t['a'], ha=ha if ha != 'center' else 'center', va='center',
                fontsize=t['size']*5.2, color=SILK, alpha=0.45 if dim_text else 0.9,
                fontweight='bold' if t['bold'] else 'normal', family='DejaVu Sans', rotation_mode='anchor')
    if not bottom:
        for lay, a, b in GLINES:
            if lay == 'F.SilkS': ax.plot([a[0], b[0]], [a[1], b[1]], color=SILK, lw=0.6, alpha=0.6)
    # footprints
    for ref, f in FP.items():
        state = 'hl' if ref in hl else 'done' if ref in done else 'none'
        if not bottom and f['silk']:
            col = hl_map[ref] if state == 'hl' else SILK
            for a, b in f['silk']:
                ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=1.6 if state == 'hl' else 0.5,
                        alpha=1 if state == 'hl' else 0.55, solid_capstyle='round')
        for p in f['pads']:
            x, y = p['xy']; x = mx(x)
            if p['kind'] == 'np_thru_hole':
                ax.add_patch(Circle((x, y), p['drill']/2, fc='white', ec='#888', lw=0.5)); continue
            rad = max(p['w'], p['h'])/2
            if p['shape'] in ('rect', 'roundrect') and p['w'] == p['h']:
                patch = Rectangle((x - p['w']/2, y - p['h']/2), p['w'], p['h'])
            elif p['shape'] in ('rect', 'roundrect', 'oval') and p['w'] != p['h']:
                w_, h_ = (p['w'], p['h']) if p['rot'] % 180 == 0 else (p['h'], p['w'])
                patch = FancyBboxPatch((x - w_/2, y - h_/2), w_, h_, boxstyle=f'round,pad=0,rounding_size={min(w_,h_)/2*0.95}')
            else:
                patch = Circle((x, y), rad)
            if state == 'hl':
                patch.set(fc=GOLD, ec=hl_map[ref], lw=2.2)
            elif state == 'done':
                patch.set(fc=DONE, ec='#555', lw=0.6)
            else:
                patch.set(fc=GOLD, ec='none', alpha=0.55)
            ax.add_patch(patch)
            hole_fc = '#6d747c' if state == 'done' else HOLE
            ax.add_patch(Circle((x, y), p['drill']/2, fc=hole_fc, ec='none'))
            if tag_pads and (ref, p['num']) in tag_pads:
                lab, c, dx, dy = tag_pads[(ref, p['num'])]
                ax.add_patch(Circle((x, y), rad + 0.6, fc='none', ec=c, lw=2.6))
                if lab:
                    ax.annotate(lab, (x, y), xytext=(x + dx, y + dy), color=c, fontsize=8, fontweight='bold',
                                ha='center', va='center', arrowprops=dict(arrowstyle='-', color=c, lw=1.2),
                                path_effects=[pe.withStroke(linewidth=2.5, foreground='black')])
    for (x, y, s, c) in notes:
        ax.text(mx(x), y, s, color=c, fontsize=8.5, fontweight='bold', ha='center', va='center',
                path_effects=[pe.withStroke(linewidth=2.8, foreground='black')])
    ax.set_xlim(-1.5, W + 1.5); ax.set_ylim(-1.5, H + 1.5); ax.set_aspect('equal'); ax.axis('off')

def lab_off(x, bottom): return 0

def figure(path, title, hl=(), done=(), notes_top=(), notes_bot=(), both=True, tag_pads=None, sub=None):
    n = 2 if both else 1
    fig, axs = plt.subplots(1, n, figsize=(7.2*n, 5.6), dpi=150)
    axs = axs if n == 2 else [axs]
    draw(axs[0], False, hl, done, notes=notes_top, tag_pads=tag_pads)
    axs[0].set_title('PARTS SIDE (your view: cut tab down, panel top up)', fontsize=10, loc='left')
    if both:
        draw(axs[1], True, hl, done, notes=notes_bot, tag_pads=tag_pads)
        axs[1].set_title('SOLDER SIDE (board flipped left-to-right)', fontsize=10, loc='left')
    fig.suptitle(title, fontsize=13, fontweight='bold', x=0.01, ha='left')
    if sub: fig.text(0.01, 0.905, sub, fontsize=9.5, ha='left', color='#333')
    fig.tight_layout(rect=(0, 0, 1, 0.9 if sub else 0.94))
    fig.savefig(path, facecolor='white'); plt.close(fig)

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hub-pcb-solder-guide') + os.sep
import os; os.makedirs(OUT, exist_ok=True)

S1 = ('RA', 'RB'); S2 = ('JCTRL', 'JKNOB', 'JQW', 'JG1', 'JG2'); S3 = ('JPWR', 'JPRESTO')
S4 = ('J11L', 'J11R', 'J11B', 'JAMP'); S5 = ('J10L', 'J10R', 'J10B')
EMPTY = tuple(r for r in FP if r.startswith(('S1', 'SP_', 'H')) ) + ('JI2C',)

# 0: overview - what goes in, what stays empty
fig, ax = plt.subplots(figsize=(9.5, 7.2), dpi=150)
cols = {}
for grp, c in ((S1, '#ffd166'), (S2, '#06d6a0'), (S3, '#ff7b54'), (S4, '#4cc9f0'), (S5, '#c77dff')):
    for r in grp: cols[r] = c
draw(ax, False, hl_map=cols)
ax.set_title('Hub PCB rev A: what goes where (parts side, your view)', fontsize=12, fontweight='bold', loc='left')
from matplotlib.lines import Line2D
leg = [Line2D([0], [0], marker='o', color='w', markerfacecolor='#d9b44a', markeredgecolor=c, markeredgewidth=2.5, markersize=11, label=t)
       for c, t in (('#ffd166', 'Step 1  resistors Ra, Rb (330 Ω)'), ('#06d6a0', 'Step 2  male pin headers (35 pins)'),
                    ('#ff7b54', 'Step 3  JST-PH sockets: POWER IN, PRESTO'), ('#4cc9f0', 'Step 4  sockets: 0x11 (9, 9, 5) + amp (7)'),
                    ('#c77dff', 'Step 5  sockets: 0x10 (9, 9, 5)'))]
leg.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='#d9b44a', markeredgecolor='none', alpha=0.55, markersize=11,
                  label='Leave empty: SPARE holes, AMP spares, I2C header, 4 corner holes'))
ax.legend(handles=leg, loc='upper center', bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=8.5, frameon=False)
fig.tight_layout(); fig.savefig(OUT + 'pcb_step0_overview.png', facecolor='white'); plt.close(fig)

figure(OUT + 'pcb_step1_resistors.png', 'Step 1 — Ra and Rb, 330 Ω, lying flat', hl=S1,
       sub='Not polarised: either way round. Solder the 4 highlighted pads on the solder side, then clip the leads.')
figure(OUT + 'pcb_step2_headers.png', 'Step 2 — male pin headers: switch row 12, KNOB 5, Qw/ST 4, GAUGE I 7, GAUGE II 7', hl=S2, done=S1,
       sub='Short ends down through the board, long pins up. Leave the 4-hole I2C header (left edge) empty.')
figure(OUT + 'pcb_step3_jst.png', 'Step 3 — the two JST-PH sockets: POWER IN and PRESTO', hl=S3, done=S1 + S2,
       sub='Match the printed outline: the pins sit nearer the TOP of the outline, the deeper part of the housing toward the bottom edge.')
figure(OUT + 'pcb_step4_0x11_amp.png', 'Step 4 — sockets for 0x11 (left Zero) and the amp', hl=S4, done=S1 + S2 + S3,
       sub='9 + 9 + 5 for the Zero, 7 for the amp. Line them up with the Zero / amp sitting in them (see the guide).')
figure(OUT + 'pcb_step5_0x10.png', 'Step 5 — sockets for 0x10 (right Zero)', hl=S5, done=S1 + S2 + S3 + S4,
       sub='Same as step 4. The 5-pin row along the bottom; only its right-hand pin carries a signal, but solder all 5.')

# Step 6 meter checks (solder side, where the joints are bare)
ALL = S1 + S2 + S3 + S4 + S5
R, G, Y = '#ff4d4d', '#7CFC00', '#ffd400'
t5 = {('JPWR', '2'): ('POWER IN +', R, 9, -3.2), ('JPRESTO', '2'): ('PRESTO +', R, -1, -4.2),
      ('J11L', '1'): ('0x11 5V', R, 4, 3.4), ('J10L', '1'): ('0x10 5V', R, 0, 3.6), ('JAMP', '1'): ('amp VIN', R, -5, 3.4),
      ('SP_5V', '1'): ('5V spare', R, 5, 0)}
figure(OUT + 'pcb_check_a_plus5.png', 'Check A — every "+5 V" point beeps to POWER IN +', done=ALL, both=False,
       tag_pads=t5, sub='Meter on beep, nothing plugged in. Parts side shown so the labels read; probe the same joints on the solder side.')
tg = {('JPWR', '1'): ('POWER IN −', G, -6, -4), ('JPRESTO', '1'): ('PRESTO −', G, -6, -3.5),
      ('J11L', '2'): ('0x11 GND', G, 5, 5.5), ('J10L', '2'): ('0x10 GND', G, 5, 5.5), ('JAMP', '2'): ('amp GND', G, -5, 5.5),
      ('JG1', '2'): ('', G, 0, 0), ('JG2', '2'): ('', G, 0, 0), ('JQW', '1'): ('', G, 0, 0),
      ('JKNOB', '2'): ('', G, 0, 0), ('JKNOB', '5'): ('', G, 0, 0),
      **{('JCTRL', str(n)): ('', G, 0, 0) for n in (2, 4, 6, 8, 10, 12)}}
figure(OUT + 'pcb_check_b_ground.png', 'Check B — every ground point beeps to POWER IN −', done=ALL, both=False, tag_pads=tg,
       sub='Ringed in green: 5 power grounds, the 6 G pins on the switch row, KNOB C and G, both gauges\' GND, Qw/ST GND.')
tn = {('SP_5V', '1'): ('5V', Y, 7, 0), ('SP_GND', '1'): ('GND', Y, 7, 0), ('SP_3V3', '1'): ('3V3', Y, 7, 0)}
figure(OUT + 'pcb_check_c_noshort.png', 'Check C — must NOT beep: 5V–GND, 3V3–GND, 5V–3V3', done=ALL, both=False, tag_pads=tn,
       sub='Test points: the three SPARE holes beside POWER IN. A beep = a solder bridge; find it before any power.')
print(sorted(os.listdir(OUT)))
