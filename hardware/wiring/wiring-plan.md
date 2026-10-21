> **Copy for the public repo, made 2026-10-14** from the builder's project folder (wiring-plan.md). It is a working log as much as a guide: dates, decisions and checks as they happened. "Roadmap" numbers refer to the builder's own plan, not a file here.

# ICCYC Depot Dashboard — Wiring & power plan (draft v0)

Started 2026-09-30 (roadmap 0.1 cable plan + first draft of 4.1 harness drawing). Updated the same evening: power input = Jason's xiwai panel-mount USB-C sockets.
**Status: draft — nothing here is built yet. Measured 2026-10-08: current, the socket, polarity (section 1). Hub board layout drawn 2026-10-09 (section 5; `hub-board-build.md`, `hub-board-layout.png`).** **2026-10-11 (Jason): the hub becomes an ordered PCB (roadmap 4.1a); the perfboard is shelved.** The wire lists here still hold — they become the PCB's connectors. **2026-10-11, evening (Jason): PCB decisions made — see `hub-board-build.md` (top): sockets for the Zeros and amp, pin headers + ready-made jumper cables for every wire that leaves the board, JST-PH sockets for power in and the Presto lead, a ground pin per control part (the ground bus of section 4 is dropped on the PCB), OSH Park × 6. Placement draft: `hub_pcb_placement.png`.** Wire lengths come
from the fitted enclosure (M3); items marked **VERIFY** need a check before
anything is soldered. Picture: `wiring-diagram.svg` (same folder).

Pin assignments are the ones already proven on the breadboard in M1 (plan doc,
Co-processor GPIO map). Nothing here changes them.

---

## 1. Power — decided 2026-10-08: option A

Today every board runs from its own USB cable. A finished unit should have
**one cable going into the box**. What needs power:

| Load | Rail | Estimated current | Source of estimate |
|---|---|---|---|
| Presto (screen backlight, RP2350, WiFi) | 5 V in | ~0.3–0.5 A, WiFi bursts higher | estimate — **VERIFY** with a USB power meter |
| RP2040-Zero 0x10 at 200 MHz | 5 V pin | ~0.04 A | estimate |
| 2 × GC9A01 gauge modules (always lit) | 3.3 V from 0x10 | ~0.02–0.04 A each | estimate — **VERIFY** |
| RP2040-Zero 0x11 | 5 V pin | ~0.03 A | estimate |
| 2 pilot LEDs | from 0x11 GPIO | ~0.004 A each | 330 Ω, measured design value |
| MAX98357A amp + 4 Ω speaker | 5 V | idle ~few mA; **up to ~0.7 A peaks at full volume** (3 W ÷ ~90 % ÷ 5 V) | datasheet-level estimate |
| **Total** | | **~0.5 A typical, ~1.4 A worst-case peak** | → use a **5 V, 3 A** USB-C supply |

**Measured 2026-10-08 (desk, Jason, USB power meter):** Presto 0.20 A; 0x10 with both gauges lit 0.05 A; 0x11 0.00 A with a brief 0.01 A (the meter reads in 0.01 A steps; a chime peak was not caught) — **about 0.25 A at idle**. The amp's peak at full volume is still unmeasured.

### The choices

**A. One panel-mount USB-C socket on the case — DECIDED 2026-10-08 (Jason), after the checks below.**
*Updated 2026-09-30:* Jason already has **xiwai panel-mount USB-C female
sockets with 2-pin leads** ("2Pin with Nut", 17.5 cm red/black lead, 2.0 mm
JST-PH-style plug; Amazon B0D5B82V6K). The socket bolts through the case's back
wall with its nut; its lead feeds a 5 V rail on the hub. From that rail:
- **Presto** via its **battery connector** (2-pin JST-PH, rated **3–5.5 V**,
  no charger on board, per Pimoroni's product page) — so 5 V is within spec.
- **0x10 and 0x11** via their **5V pins** (each board's own regulator makes its 3.3 V).
- **Amp Vin** directly (it's already on 5 V today).
- The Presto's and the Zeros' own USB-C ports stay free for reprogramming.

  **VERIFY 1 (Presto schematic) — still open 2026-10-08:** nothing found online; Pimoroni staff confirm 5 V into the battery connector is fine ([forum](https://forums.pimoroni.com/t/pimoroni-presto/26815)). Covered by the rule under VERIFY 2.
  *Original:* that the battery input and USB are combined
  through diodes (so plugging a laptop into the Presto's USB while the 5 V
  rail is on is safe). The schematic link is on Pimoroni's Presto page;
  the sandbox couldn't download it.
  **VERIFY 3 — passed 2026-10-08:** 5.16 V on the leads from a USB-C charger on a C-to-C cable. The lead's warmth in a full-volume chime is still to check once wired (M4).
  *Original:* **VERIFY 3 (xiwai socket, with the USB power meter):** does a USB-C charger
  with a **C-to-C** cable put 5 V on the leads? 2-pin sockets often lack the
  two CC resistors, and then only a USB-A → C cable works. If so: either ship
  the units with an A-to-C cable + USB-A charger, or use a socket with the
  resistors. Also check the lead doesn't get warm in a full-volume chime test
  (no current rating listed).
  **VERIFY 4 — passed 2026-10-08:** the xiwai plug's red wire lands on the Presto's **+** marking.
  *Original:* **VERIFY 4 (polarity):** *(2026-10-01: the xiwai lead **fits** the Presto's
  battery connector, tested unpowered; polarity still unchecked.)* The xiwai plug looks like the same 2-pin JST-PH as
  the Presto's battery connector — check red/black against the Presto's + / −
  marks (or with a meter) **before plugging in**; reversed polarity could
  damage the Presto. A second xiwai lead's plug can serve as the hub → Presto
  battery cable.
  **Case:** needs a mounting hole for the socket in the back wall (roadmap
  2.4; position decided 2026-10-01 in 2.3: low and centred, ~40 mm up); socket measured 2026-10-01 (double-D thread Ø10.6, 9.0 across the flats; nut 13.8 AF — plan doc, Measurements).
  **VERIFY 2 — answered second-hand 2026-10-08:** a forum reading of Waveshare's schematic says the 5V pin is wired straight to USB 5 V, no diode ([Core Electronics forum](https://forum.core-electronics.com.au/t/rp2040-zero-battery-connection/14877)). **Rule (proposed, covers VERIFY 1 too): unplug the case's power before plugging any USB cable into the Presto or a Zero.**
  *Original:* **VERIFY 2 (RP2040-Zero):** whether the 5V pin is wired straight to the USB
  5 V (no diode). If it is, **unplug the case's power before plugging a
  Zero into the computer** (otherwise two 5 V sources fight). A rule on a
  label inside the lid is enough; no part needed.

**B. Presto on its own USB-C cable; a second cable for the co-processors.**
Simplest electrically, but two cables into the box (or a Y-cable) — looks less
finished and is easy to half-plug.

**C. Everything from the Presto's Qw/ST 3.3 V.** One cable, but the amp would
run at 3.3 V (quieter) and the whole load (~0.2 A + amp peaks) would hang off a
regulator whose limit isn't published. **Not recommended.**

---

## 2. The I2C link (Qw/ST) — roadmap 0.1

- **One** JST-SH 4-pin cable per unit from the Presto's Qw/ST port, split to
  both co-processors (they share the bus; the Presto tells them apart by
  address).
- Colours stay as on the breadboard: **blue = SDA → GP0, yellow = SCL → GP1,
  black = GND**. **Red (Qw/ST 3.3 V): leave unconnected** — each Zero makes its
  own 3.3 V (option A), and joining two 3.3 V supplies is asking for trouble.
- **The split:** cut one kit cable (female-jumper type) and solder the Y on the
  hub board (section 5), not in mid-air. Keep the I2C run short (< ~30 cm total).
- **VERIFY — passed 2026-10-09 (Jason):** the kit's plain JST-SH cable plugs into the
  Presto's Qw/ST port (roadmap 0.1). No second kit is needed.

---

## 3. Gauges board 0x10 — wire list

| From 0x10 | To | Wire | Note |
|---|---|---|---|
| GP0 | Qw/ST blue (SDA) | via hub | I2C |
| GP1 | Qw/ST yellow (SCL) | via hub | I2C |
| GND | Qw/ST black, hub GND | via hub | |
| 5V | hub 5 V rail | | option A power |
| 3V3 | Gauge I **VCC** + Gauge II **VCC** | split at the hub or a 2-way header | gauges' supply |
| GND | Gauge I **GND** + Gauge II **GND** | | |
| GP2 (SPI SCK) | Gauge I **SCL** + Gauge II **SCL** | split | shared clock — the modules' "SCL/SDA" are SPI, not I2C |
| GP3 (SPI MOSI) | Gauge I **SDA** + Gauge II **SDA** | split | shared data |
| GP4 | Gauge I **CS** | | |
| GP5 | Gauge I **DC** | | |
| GP6 | Gauge I **RST** | | |
| GP7 | Gauge II **CS** | | |
| GP8 | Gauge II **DC** | | GP8/GP9 share a corner of the Zero — easy to swap |
| GP9 | Gauge II **RST** | | |

Module pin order on the gauge board: **VCC GND SCL SDA DC CS RST** — DC comes
*before* CS (reverse of the GPIO order). Wire by label.

**SPI at 60 MHz:** fine on breadboard jumpers in M1. Keep the SCK/MOSI runs
**short (< ~15 cm) and equal-ish**, and route them away from the speaker
wires. If noise ever shows up, dropping `SPI_BAUD` to 30 MHz costs little
(partial redraw sends few pixels).

---

## 4. Controls board 0x11 — wire list

| From 0x11 | To | Note |
|---|---|---|
| GP0 / GP1 / GND | Qw/ST blue / yellow / black (via hub) | I2C |
| 5V | hub 5 V rail | option A power |
| GP2 | Encoder **A** | encoder 3-pin side: A – C – B |
| GP3 | Encoder **B** | |
| GND | Encoder **C** (middle pin) | |
| GP4 | Encoder push-switch, one pin | other pin → GND |
| GP5 | CHIME toggle | other leg → GND |
| GP6 | DAY·NIGHT toggle | other leg → GND |
| GP7 | BACKLIGHT toggle | other leg → GND |
| GP8 | WIFE MODE toggle | other leg → GND |
| GP9 | 330 Ω → WiFi pilot LED + (long leg) | LED − → GND |
| GP10 | 330 Ω → OTA pilot LED + | LED − → GND |
| GP11 | Amp **BCLK** | |
| GP12 | Amp **LRC** | must stay BCLK + 1 |
| GP13 | Amp **DIN** | |
| — | Amp **Vin** ← hub 5 V rail; Amp **GND** ← hub GND | today Vin comes from 0x11's 5V pin; on the rail instead so amp peaks don't pass through the Zero |
| — | Amp **+ / −** screw terminal → speaker | twist the pair; keep away from the SPI wires |

All the switches, the encoder and the push-button share one **GND return** —
run it as a single "ground bus" wire along the switch row, each part tapping it.
That's one ground wire to the hub instead of seven. *(2026-10-11: on the PCB each part gets its own ground pin instead — one wire per lug, no daisy-chained joints.)*

Which way is "on" for each toggle doesn't matter now: `switch_invert` in the
config flips any switch after assembly.

---

## 5. Suggested build: a small hub board

Use one piece of the **double-sided perfboard** on hand as a **hub**:
- the **5 V input** (USB-C input board) and the 5 V / GND rails,
- the **Qw/ST split** (one cable in, two short runs out),
- the **ground bus** start,
- optionally pin headers so 0x10 and 0x11 **plug in** (lets either board come
  out for USB flashing without desoldering).

**Where it goes (decided 2026-10-01, roadmap 2.3):** on a printed **hub shelf** over the
Presto's back, with both Zeros plugged into female headers (USB ports facing the panel
top) and the amp on the same board. Everything is on the panel; the only lead from
the body is the 5 V input from the USB-C socket (low-centre on the back wall, ~100 mm
path for the 175 mm lead). SPI to the gauges runs on the gauge side (~7–9 cm), the
speaker leads on the other side. Picture: canvas artboards 7–8. ~~Still open (4.1):
whether the power lead plugs into the hub (unplug to lift the panel off) or is
soldered with slack.~~ **Decided 2026-10-09 (Jason): it plugs in at the hub.** The
Presto's battery plug is trapped under the P1 bracket, so that end can't be the
disconnect; and since rev E the socket is on the removable back plate (not the back
wall). Part: a pre-wired JST-PH 2-pin pair on a short tail — **to buy** (none on hand).

**Hole-by-hole layout: draft v2, 2026-10-09** — `hub-board-build.md` (tables, checks,
solder order) and `hub-board-layout.png`, drawn and checked by `hub_layout.py`. Jason
OK'd the placement and started soldering the same afternoon. **Corrections the same day:
the board is 70 × 50 mm, not 61 × 46 (it did not fit P1 → `stl\p1_hub_shelf_revE1_print.stl`);
Jason has no female header strips, so "plugged into female headers" above is open —
sockets or soldered straight on; seven of the nine links lie on the parts side and only
the two I2C links under the board (v1 had all nine underneath); the rail runs C3–W3.** Seen from the back of the panel, A at the left and row 18 at the
top (the boards are 18 × 24 holes, labelled 1–18 and A–X — counted 2026-10-09): the
**amp** in column C, hanging off the left edge toward the speaker; **0x11** in columns
E–K; **0x10** in columns O–U, its gauge wires leaving from column V; a +5 V block
bottom-left; a **ground rail** along row 3; both 330 Ω LED resistors on the board
(not in the wiring); nine insulated links. Unlike the first sketch
there is no 5 V "rail" — just a four-pad block with two links. Not built; the open
check (the board flat in the reprinted P1 pocket) is in `hub-board-build.md` section 2;
pin names and the amp's pin order were confirmed 2026-10-09. **The Zero's bottom five pins land on the grid — confirmed
2026-10-09 (Jason: all 23 pins of a bare Zero go through).**

Why: almost every solder joint then happens on a board clamped flat in a vise
or helping hands, instead of wire-to-wire in mid-air, and the harness for the
two gift units is a copy of a board rather than a tangle. Fewer, bigger,
easier joints.

---

## 6. Before any soldering (checklist)

- [x] Decide power option (A / B / C). *(A, 2026-10-08.)*
- [ ] VERIFY 1: Presto battery input + USB are diode-combined (schematic). *(Not found 2026-10-08; covered by the unplug-before-USB rule.)*
- [x] VERIFY 2: RP2040-Zero 5V pin vs USB 5 V (diode or not). *(No diode, per a forum reading, 2026-10-08 → the unplug-before-USB rule.)*
- [x] VERIFY: kit JST-SH cable fits the Presto Qw/ST port (0.1). *(Fits, 2026-10-09.)*
- [x] Measure real current with a USB power meter (Presto + both Zeros + gauges,
      then a chime at full volume) → confirm a 5 V 3 A supply is enough. *(2026-10-08: ~0.25 A idle; the chime peak not caught — recheck on the single rail.)*
- [x] ~~Pick the USB-C input board~~ — use the xiwai panel-mount USB-C 2-pin sockets already on hand (2026-09-30), pending VERIFY 3 and 4. *(Both passed 2026-10-08.)*
- [x] Find the USB power meter (Jason has one somewhere). *(Found, used 2026-10-08.)*
- [ ] Wire lengths from the fitted enclosure (M3).
- [x] Hub board layout drawn. *(Draft v1, 2026-10-09: `hub-board-build.md`.)*
- [x] The Zero's bottom five pins land on the perfboard grid. *(All 23 pins go through, 2026-10-09.)*
- [x] Zero pin names and the amp's pin order. *(Both match, 2026-10-09.)*
- [ ] Print P1 rev E1 (`stl\p1_hub_shelf_revE1_print.stl`) and check the 70 × 50 board sits flat in it. *(The board did not fit the rev D1 pocket, 2026-10-09.)*
- [x] Decide: female header sockets (none on hand) or Zeros and amp soldered straight to the hub. *(Sockets, 2026-10-11 — on the PCB; strips to buy.)*
- [x] Buy pre-wired JST-PH 2-pin pairs for the plug-in power lead (one pair per unit). *(XUGERIP 20 + 20; check fit and polarity.)*
- [ ] ~~Re-solder the bottom five pins on the two soldered Zeros so they point down.~~ *(Not needed for now, 2026-10-09: the breadboard set stays as the working reference; the first hub board gets new Zeros with all pins down.)*
