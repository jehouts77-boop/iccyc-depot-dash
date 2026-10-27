> **Copy for the public repo, made 2026-10-14** from the builder's project folder (hub-board-build.md). It is a working log as much as a guide: dates, decisions and checks as they happened. "Roadmap" numbers refer to the builder's own plan, not a file here.

# ICCYC Depot Dashboard — Hub board: layout and build steps (draft v2)

> **2026-10-11 — Jason: the hub moves to an ordered PCB** (roadmap 4.1a). This perfboard is **shelved as is** (links 1–9 in, never powered). This file and `hub_layout.py` stay the reference for the PCB: the same nets, the same connections that leave the board, the same 70 × 50 outline for the P1 rev E1 pocket.

**Decided with Jason 2026-10-11 — the hub PCB (roadmap 4.1a):**
1. **Who solders:** Jason solders the through-hole parts himself on a bare PCB (no factory assembly) — "especially if it saves a bit of time or money".
2. **The Zeros and the amp sit in female header sockets** (to buy; none on hand). Same joint count as soldering them straight on, and a Zero can come out for flashing or swapping. The Zeros and amp already pinned for the perfboard go straight in.
3. **Connectors:** every wire that leaves the board plugs onto a pin header with ready-made jumper cables (no crimping), except power: **POWER IN is a JST-PH 2-pin socket the xiwai lead plugs straight into**, and the **Presto lead is a JST-PH socket + a PH-to-PH cable** (meter-check it against the Presto's + before the first plug-in). Qw/ST = a 4-pin header for the kit's JST-SH → female-socket cable (its red 3.3 V wire lands on a pin that goes nowhere). Gauges = a 7-pin header each in the module's order, straight across on a female-female ribbon. Knob + toggles + pilot lights = male pins with **a ground pin for every part (no ground bus)**; at the part end the jumper's plug is cut off and the wire soldered on (17 joints a unit).
4. **Fab: OSH Park, 6 boards** (3 units + 3 spares for some future project; about $54 with free US shipping, about 2–2½ weeks door to door, gold (ENIG) pads). Each Zero's unused pins come out to labelled spare holes so the spares can be reused.
5. **Tool:** one Python script, `hub_pcb.py`, writes the KiCad board file (KiCad runs in Claude's workspace); checked by the script, by KiCad's design-rule check with OSH Park's limits, by pictures of both sides for Jason, and by OSH Park's own preview on upload.

**Placement draft P1 (2026-10-11; now P3, see below) — built and checked by script only, not routed, not confirmed by Jason:** `hub_pcb.py` → `hub_pcb.kicad_pcb`, `hub_pcb_placement.png`, `hub_pcb_report.txt` (same folder). The Zeros and the amp stay in the perfboard's holes (amp column C, 0x11 E–K, 0x10 O–U); the gauge headers on the right edge, the knob header at the left, the 12-pin switch row along the bottom (WIFE MODE at the left … CHIME at the right, seen from the back), POWER IN bottom right; **new: a 5.5 × 12.5 mm cable slot between the Zeros** — the Qw/ST cable and the Presto lead come up through it from the Presto (VERIFY at the bench; the Presto lead may go over the bottom edge instead). Checks: the 53 Zero / amp pins carry the same nets as `hub_layout.py`; every perfboard wire has a connector pin; no pin within 4.5 mm of an edge (the ledge) or by the slot; KiCad DRC: no collisions (accepted: the spare holes' outlines, and each Zero's side sockets meeting its bottom socket corner to corner).  **Same day (Jason): placement draft P2 → P3** — the spare holes made the same 1.7 mm size as the socket pads, boxed and titled SPARE on the silkscreen, every hole named; for reuse, **4 × M3 mounting holes** in the corners (over the ledge, unused here), an **I2C add-on header** (GND 3V3 SDA SCL, Qwiic order, 3V3 from 0x10) bottom-left, and **the amp's GAIN and SD on spare holes beside the amp, with a GND hole** (a wire GAIN → GND = 12 dB instead of 9 dB, if the chime is too quiet); and **the nod to the original: `ICCYC CONTROL CONSOLE · MODEL 80 · TYPE 085` along the top edge, `HUB REV A · 2026` along the bottom** (silkscreen). **P3 additions agreed by Jason; the P3 picture is not yet seen by him. Next, after his look: the copper (routing)** **Copper draft C1 (2026-10-11) — built and checked by script + KiCad, not looked over by Jason yet:** `hub_router.py` (a small 2-layer router; Freerouting can't be downloaded into Claude's workspace) lays every trace; +5 V and the power ground (POWER IN, Presto, both Zeros, the amp) are 0.6 mm, 3.3 V to the gauges 0.4 mm, signals 0.25 mm; 17 vias; every other ground pin joins a ground fill on both faces through thermal-relief spokes (easier to solder). Silkscreen labels for every connector pin (WIFE/G/BKLT … on the switch row, A C B SW G on the knob, VCC … RST on the gauges, + / − on both JST-PH sockets), part names, USB arrows, and names on the underside. KiCad's check: 0 unconnected pads, no clearance errors (router keeps 0.25 mm, OSH Park allows 0.15); accepted: courtyard touches listed above, 8 ground pads with one thermal spoke on one face (still connected), labels touching part outlines (no label on another label). Pictures: `hub_pcb_copper.png` (both sides, colour-coded), `hub_pcb_kicad_view.png` (KiCad's own drawing). Fab files exported as a check: `hub_pcb_revA_gerbers_DRAFT.zip` — **not for ordering until Jason OKs the copper.** **C1 → C2 (after a design review):** the review found a real fault the checks had missed — **the ground fill ran right to the board edge and into the cable slot's edge (0 mm; OSH Park wants ≥ 0.38 mm)**: KiCad's filler did not apply the edge rule in a script run and KiCad's own check didn't flag it. Fixed: the fill stops 0.5 mm from the edge and the slot (now measured 0.47 mm at the closest corner of the fill, traces 0.46 mm, pads 1.4 mm), and `hub_pcb.py` now measures this itself. Added 26 ground stitching vias (small 0.3 mm vias tying the top and bottom fills together away from the lettering). Measured for the checklist: 0.6 mm 1 oz trace ≈ 1.65 A for a 10 °C rise (IPC-2221) vs ~0.7 A peak; +5 V drop ≈ 0.8 mΩ/mm; no SPI line runs beside I2C, I2S or the control lines; the longest side-by-side runs are DIN / ENC_B 4.6 mm and LRC / SDA 2.9 mm (slow or debounced lines, accepted). Still waiting for Jason's look. **Copper OK'd by Jason 2026-10-11. Then C3:** both JST-PH sockets changed to **pin 1 = ground, pin 2 = +5 V**, the usual battery order (Adafruit / SparkFun / Pololu's cables: black on pin 1, red on pin 2); C1/C2 had +5 V on pin 1, which would have put the xiwai lead's red wire on ground if the Presto follows the usual order — and the xiwai lead fits the Presto with red on +. Re-routed and re-checked (0 unconnected, no clearance errors, fill 0.47 mm from edges). **VERIFY before the first power-up:** unpowered, plug the xiwai lead into POWER IN and the Presto lead into both ends; the red wire / the Presto's + must meter through to the board's "+" pad. **Order files:** `hub_pcb_revA_gerbers.zip` (Gerbers + drill files, OSH Park's drill settings). **Parts to buy:** `hub-pcb-parts-list.md`. **Ordered from OSH Park: 6 boards (2 × 3);** uploaded `hub_pcb_revA_gerbers.zip`; Claude checked every layer on OSH Park's verify page first (outline + slot, drills incl. vias, both silkscreens, masks, both coppers — all as designed). Status at order: in production, awaiting panelization. Expected ~9–12 days to ship + mail. **Parts:** the five DigiKey lines listed (14 × S7007-ND, 4 × S7005-ND, 8 × S6103-ND, 10 × 455-1704-ND, 6 × S1011EC-40-ND) plus 4 × Pololu #5604 (DigiKey Marketplace 2183-5604-ND). — the Freerouting auto-router can't be downloaded into Claude's workspace, so the copper is laid by the script. Still open: the board flat in the P1 pocket (bench); gauge pins + room for a plug behind each gauge (bench); the parts list to buy (female header strips, JST-PH sockets, PH-to-PH cables, male pin strips, jumper ribbons).

Started 2026-10-09 (roadmap 4.1 → 4.2). Picture: `hub-board-layout.png` (same folder), drawn by
`hub_layout.py` — the script holds every hole, link and route and checks them, so change the layout
there and re-run it, never by hand in the picture.

**Status (2026-10-09): layout drawn and checked by script only** (no hole used twice, every
connection joined, no +5 V pad beside a signal pad, no under-board wire lying on a pad). **Jason
OK'd the placement; soldering started with the resistors, the ground rail and link 2.** **2026-10-10: the pins on the Zeros and amp (step 1) and links 1–7 are in. 2026-10-11: links 8 and 9 (under the board) are in — step 4 is complete; next is step 5 (sockets or straight on, still to decide)** (section 5 tracks what is done and where to pick up).
Nothing has been powered.

**v1 → v2 (2026-10-09):** the board is **70 × 50 mm** (Jason, calipers; the model had assumed
61 × 46 and the bare board did not fit the P1 pocket → P1 rev E1, section 3). No part moved. The
link wires were re-routed so that seven of the nine lie on the parts side, where there is room,
and only the two I2C links lie under the board; the amp's signal and power links now land on
columns A and B, under the amp. The ground rail hooks into C3 and W3.

**Orientation, everywhere in this file:** the parts side of the board facing you, as it sits on
the hub shelf (P1) seen from the back of the panel, cut tab at the bottom. **Column A is at your
left, row 18 is at the panel top, row 1 at the bottom** (how Jason's boards are printed — X meets
18 in the upper right). Board: 24 × 18 holes, A–X and 1–18.

---

## 1. What goes where

| Part | Holes | Notes |
|---|---|---|
| Amp (MAX98357A), 7 pins | **C16 → C10** | top to bottom: Vin, GND, SD, GAIN, DIN, BCLK, LRC — **order confirmed on the real amp 2026-10-09**. The amp's body points left, past the board's edge, toward the speaker; speaker screw terminal at the far end. |
| 0x11 (controls), left 9 pins | **E16 → E8** | 5V, GND, 3V3, GP29, GP28, GP27, GP26, GP15, GP14 |
| 0x11, right 9 pins | **K16 → K8** | GP0 … GP8 |
| 0x11, bottom 5 pins | **F7 → J7** | GP13, GP12, GP11, GP10, GP9 |
| 0x10 (gauges), left 9 pins | **O16 → O8** | 5V, GND, 3V3, then unused |
| 0x10, right 9 pins | **U16 → U8** | GP0 … GP8 |
| 0x10, bottom 5 pins | **P7 → T7** | only GP9 (T7) is used |
| Ra, 330 Ω (WiFi pilot light) | **J6 – N6** | lies flat along row 6 |
| Rb, 330 Ω (OTA pilot light) | **I5 – M5** | lies flat along row 5 |
| +5 V block | **C7, D7, C6, D6** | four pads joined |
| Ground rail | **row 3, C → W** | one bare wire along the row, on the solder side, hooked into C3 and W3 |

Both Zeros have their **USB socket toward row 18 (the panel top)**. Pin names confirmed against
the Zero's silkscreen, and **all 23 pins of a bare Zero drop into these holes** (Jason, 2026-10-09).

**Sockets or soldered straight on — not decided.** Jason has no female header strips (he first
thought he had). The layout works either way; soldered straight on, the Zeros and amp go on
**last**, after the board passes its meter checks, and each Zero is flashed and tested first.

**Keep clear:** nothing is soldered in rows 1 and 18 — those holes sit on the shelf's ledge.
Everything under the board must stay **under 2 mm tall** (the Presto's back is about 3 mm below
it): trim every pin and wire end close.

### Wires that leave the board

"From below" = the wire comes up from the Presto, goes in from the solder side and is soldered on
the parts side.

| Hole | Wire | Goes to |
|---|---|---|
| C7 | red | POWER IN + (the plug-in power lead, section 3) |
| D3 | black | POWER IN − |
| D6 | red, from below | Presto battery connector + |
| E3 | black, from below | Presto battery connector − |
| L16 | blue, from below | Qw/ST SDA |
| L15 | yellow, from below | Qw/ST SCL |
| K3 | black, from below | Qw/ST GND (the Qw/ST **red** wire is not connected — cut it short and cover the end) |
| L14 / L13 / L12 | | Encoder A / B / push switch |
| L11 / L10 / L9 / L8 | | CHIME / DAY·NIGHT / BACKLIGHT / WIFE MODE toggles |
| H3 | black | the ground bus along the switch row (encoder C, encoder switch, 4 toggles, both LED short legs) |
| O6 | | WiFi pilot LED, long leg (through Ra) |
| M4 | | OTA pilot LED, long leg (through Rb) |
| N14, U3, V14, V13, V11, V12, V10 | | **Gauge I**: VCC, GND, SCL, SDA, DC, CS, RST |
| M14, V3, W14, W13, V8, V9, T6 | | **Gauge II**: VCC, GND, SCL, SDA, DC, CS, RST |

The gauge lists are in the modules' own pin order (VCC GND SCL SDA **DC CS** RST), so a bundle can
be soldered in order at the gauge end.

### Links (insulated wire, hole to hole)

Links 1–7 lie on the **parts side**; 8 and 9 lie **under** the board. Cut lengths include about
10 mm spare; strip 3 mm at each end.

| # | From → to | Carries | Cut | Route |
|---|---|---|---|---|
| 1 | D7 → D16 | +5 V up to the amp and 0x11 | 35 mm | straight up column D |
| 2 | G3 → B15 | ground up to the amp and 0x11 | 65 mm | up one row to row 4, left along row 4 to just past the board's column A, up the left edge to row 13–14, in to B15 from below-left (not over A15) |
| 3 | B16 → P16 | +5 V across to 0x10 | 55 mm | up to just above row 17, right along the top, down into P16 |
| 4 | A15 → P15 | ground across to 0x10 | 70 mm | up column A to between rows 17 and 18, right along the top (outside link 3), down past Q16, into P15 from the right |
| 5 | F6 → B12 | sound data, DIN (GP13) | 55 mm | down to between rows 4 and 5, left, up the left edge, in to B12 |
| 6 | H6 → B11 | sound clock, BCLK (GP11) | 50 mm | down to row 5, left, up column A, in to B11 |
| 7 | G6 → B10 | sound left/right clock, LRC (GP12) | 40 mm | down half a row, left, up between columns A and B, in to B10 |
| 8 | M16 → V16 | I2C data (SDA) across to 0x10 — **under the board** | 40 mm | up to just past row 16, along, down into V16 |
| 9 | M15 → V15 | I2C clock (SCL) across to 0x10 — **under the board** | 50 mm | sideways past N15, up to between rows 17 and 18, along to column W, down column W to row 15, in to V15 |

Link 5 crosses links 6 and 7 near F5–G5, and that is fine (insulated, parts side). **Correction
2026-10-11:** v2 said "under the board nothing crosses" — wrong: **link 9 crosses link 8 once, near
N16–N17** (empty holes). The script had no crossing check (added 2026-10-11). Accepted as built:
link 8 lies flat, link 9 crosses over it at 90°; Jason measured **1.7 mm** at the crossing (limit 2 mm).

### Pads joined with solder

A wire sits in the hole next to a pin; its bare tip is bent over onto the pin's pad and the two are
soldered as one joint. Groups: B16-C16-D16-E16 (+5 V) · A15-B15-C15-D15-E15 (ground; D15 is solder
only) · B12-C12, B11-C11, B10-C10 (amp) · K16-L16-M16 (SDA) · K15-L15-M15 (SCL) · K14-L14 down to
K8-L8 (knob, toggles) · O16-P16 (+5 V) · O15-P15 (ground) · M14-N14-O14 (3.3 V) · U16-V16 down to
U8-V8 (I2C, gauges) · V14-W14, V13-W13 · F7-F6, G7-G6, H7-H6, J7-J6 · I7-I6-I5 · T7-T6 · N6-O6 ·
M5-M4 · C7-D7-C6-D6 (+5 V block; C6 is solder only).

**+5 V sits right beside ground at three places: B16/B15, D16/D15, P16/P15.** Those are the joints
to look at twice and to meter (section 4, step 7).

---

## 2. Checks before soldering (VERIFY)

- [x] **The Zero's five bottom pins land on row 7.** *(2026-10-09, Jason: "all 23 pins go through".)*
- [x] **Zero pin names** vs the silkscreen. *(2026-10-09, Jason: correct.)*
- [x] **Amp pin order** by its labels. *(2026-10-09, Jason: LRC, BCLK, DIN, GAIN, SD, GND, VIN left to
      right with the speaker end up — matches.)*
- [ ] **The bare board sits flat in the P1 pocket.** *(2026-10-09: it did **not fit** — the board is
      70 × 50, the pocket was modelled for 61 × 46. Fixed as P1 rev E1; recheck with the reprint.)*

## 3. Parts for one unit

On hand: perfboard, 330 Ω resistors, both Zeros, the amp, male pin strips, the Qw/ST cable (**the
kit's plain JST-SH cable fits the Presto's port — checked 2026-10-09**). **Not on hand: female
header strips** (corrected 2026-10-09).

**Hub shelf:** *(for the rev A PCB use `stl\p1_hub_shelf_revE2_print.stl`, see `hub-revA-rework.md`)* print **`stl\p1_hub_shelf_revE1_print.stl`** (2026-10-09; pocket 70.4 × 50.4, fits
the A1 Mini, top face down as before). Only the board frame changed — posts, fingers, deck height
and the board's centre are as in the confirmed rev D1. Sandbox-checked, not printed. The combined
`stl\parts_revD5_print.stl` still holds the old shelf — don't print P1 from it.

**Zeros:** the bottom five pins point **down**, like the side pins. Jason's first two Zeros (on the
breadboard, staying there for now as the working reference) have them pointing up; the hub board
gets new Zeros.

**The plug-in power lead** (decided: the lead from the back plate unplugs at
the hub; the Presto's plug is trapped under the P1 bracket, so it can't be the disconnect): XUGERIP
JST-PH 2.0 mm 2-pin pre-wired pairs, 20 + 20, 26 AWG, 150 mm (Amazon). One pair per unit: the
socket half on a short tail soldered at C7 / D3 takes the xiwai lead's plug; a plug half on a tail is
the Presto lead (D6 / E3). **On arrival:** does the socket half take the xiwai plug; and **check
red/black on every pair with a meter against the Presto's + mark.**

## 4. Solder order

1. **Pins onto the new Zeros and amp** — pin strips long-end down in the bare perfboard (E16–E8,
   K16–K8, F7–J7; amp C16–C10), board on top, solder the Zero / amp side only.
2. **Ra and Rb**, flat on the board; solder and trim.
3. **Ground rail**: bare wire on the solder side along row 3, hooks in C3 and W3, nudged toward
   row 2 so it lies beside the holes; tacked at F3, J3, N3, R3.
4. **Links 1–7** (parts side), then **8 and 9** (under the board) — table above. Put each end in
   its hole, solder it there, trim. No joining to the pins yet.
5. **Sockets, or the boards themselves** (not decided) — and with them every "pads joined" group.
6. Wires that leave the board — once their lengths are known from the fitted rev E enclosure.
7. **Meter checks before any power:** no connection between the +5 V block and the rail; +5 V
   block to C16, E16, O16; rail to C15, E15, O15; each link end to end; nothing between
   neighbouring pads that aren't in the same group.
8. First power-up (sockets: with nothing plugged in): 5 V between E16 and E15, and between O16
   and O15.

## 5. Build log — first unit

Perfboard prototype built 2026-10-09 to 2026-10-11 (resistors, ground rail, links 1–9); shelved 2026-10-11 in favour of the ordered PCB. Never powered.
