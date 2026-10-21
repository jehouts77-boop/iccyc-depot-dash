> **Copy for the public repo, made 2026-10-14** from the builder's project folder (hub-pcb-parts-list.md). It is a working log as much as a guide: dates, decisions and checks as they happened. "Roadmap" numbers refer to the builder's own plan, not a file here.

# ICCYC hub PCB rev A: parts to buy (2026-10-11)

**Parts:** the five DigiKey lines listed (14 × S7007-ND, 4 × S7005-ND, 8 × S6103-ND, 10 × 455-1704-ND, 6 × S1011EC-40-ND) plus 4 × Pololu #5604 (DigiKey Marketplace 2183-5604-ND).

For **three units**, plus a few spares. Prices were looked up 2026-10-11 (DigiKey through Octopart, Pololu's site); they're not quotes. The board itself is ordered separately from OSH Park (6 boards, about $54, free US shipping).

**Assumed on hand** (start-here says all project parts are in hand): six RP2040-Zeros and three MAX98357A amps for the three units, the 330 Ω resistors, the kit's JST-SH → female-socket cables for Qw/ST, and the xiwai USB-C leads.

## 1. DigiKey: one cart

| What | Part (maker) | DigiKey # | Per unit | Buy | Each | Line |
|---|---|---|---|---|---|---|
| Female socket, 9 pins (the Zeros' sides) | Sullins PPTC091LFBN-RC | S7007-ND | 4 | 14 | $0.59 (10+) | ~$8.23 |
| Female socket, 7 pins (the amp) | Sullins PPTC071LFBN-RC | S7005-ND | 1 | 4 | $0.58 | ~$2.32 |
| Female socket, 5 pins (the Zeros' bottom edge) | Sullins PPTC051LFBN-RC | S6103-ND | 2 | 8 | $0.44 | ~$3.52 |
| JST-PH 2-pin socket, upright, through-hole (POWER IN, PRESTO) | JST B2B-PH-K-S(LF)(SN) | 455-1704-ND | 2 | 10 | $0.10 (10+) | ~$1.00 |
| Male pin strip, 40 pins, breakable | Sullins PRPC040SAAN-RC | S1011EC-40-ND | (see below) | 6 | $1.04 (10+: $1.04; 1: $1.23) | ~$7.38 |

About $22 in parts, plus DigiKey shipping (roughly $7 by standard mail; check at checkout).

**Why these sockets:** they come cut to exact length, so there's no cutting strips (a cut female strip loses a pin and leaves a rough edge). Their tails fit the board's 1.0 mm holes.

**Male pins per unit:** Qw/ST 4, Gauge I + II 14, KNOB 5, switch row 12 = 35 pins on the board (the I2C add-on header stays empty for now). Units 2 and 3 also need pins on their new Zeros (23 each) and amp (7, often included with the amp). Six strips covers all of it with spare; break them with pliers at the notch.

## 2. Pololu: the Presto lead

| What | Pololu # | Buy | Each |
|---|---|---|---|
| JST PH-style cable, 2-pin, **female–female**, 16 cm | #5604 | 4 | $1.54 |

Plug-to-plug: one end into the hub's PRESTO socket, the other into the Presto's battery socket. Pololu wires **black to pin 1 and red to pin 2** on both ends, the same order as the board (pin 1 = ground, pin 2 = +5 V). On 2026-10-11 Pololu showed it **out of stock, backorders allowed**. If it hasn't shipped by the time the boards ship, a fallback is the eBay listing "JST-PH 2.0mm Pitch Female to Female Connector Cable Wires" (2-pin, 20 cm, about $5 each, ships from China, about 3–4 weeks; its wiring is not documented, so meter-check it).

**Either way, before the first power-up: with nothing powered, plug the lead in at both ends and check with the meter that the hub's "+" pad reaches the Presto's "+" mark.**

## 3. Cables: worked out from the model (2026-10-12)

~~Jumper wires (if not on hand): female-female Dupont jumpers, 20 cm, sold as 40-wire ribbons... three ribbons of 40 (not looked up).~~ *(Replaced 2026-10-12 by the run lengths below.)*

**Covered by parts on hand — nothing to buy (Jason, 2026-10-12).** He has **2 packs of the California JOS "120pcs Multicolored Dupont Wire" kit, 20 cm** (Amazon B0BRTJXND9), so **80 female–female, 80 male–female, 80 male–male**, 20 cm each. Gauges: 42 female–female for three units (80 on hand). Controls: 51 for three units, any wire with a female end for the hub pin (the 38 female–female left plus 80 male–female). Heat-shrink tubing: on hand (Jason).

~~Buy: 3 × Adafruit #793, 40 × 12" (300 mm) female–female ($7.95 each)~~ *(not needed: Claude's first answer, before Jason pointed out the packs on hand).*

**With 20 cm wires:**
- Gauges, knob, pilot lights, BACKLIGHT: ≤ ~16 cm, fine.
- DAY·NIGHT and WIFE MODE: ~18 cm along the edges. Fine with care: cutting the plug off and stripping uses 1–2 cm.
- **CHIME: ~21 cm along the edges, ~16 cm straight across the Presto's back. Route its two wires (signal + ground) straight across.** If still short: hub pin → a male–female wire → a female–female wire (cut at the toggle) = 40 cm, no extra solder joint; heat-shrink or tape over the plug-to-pin joint in the middle.
- **Before cutting anything at the bench:** lay one wire from the hub's CHIME pin to the CHIME toggle.

**Watch:** the listing says the wire is **copper-clad aluminium** — fine for plugged ends, a bit harder to solder. Try one joint first: flux, tin the wire, short iron contact.

**Per unit, 31 wires:**

| Run | Wires | Ends | Longest run (estimate) | Wire |
|---|---|---|---|---|
| Hub GAUGE I → Gauge I | 7 | plugged both ends, straight across | ~12 cm | 20 cm: ~8 cm spare |
| Hub GAUGE II → Gauge II | 7 | plugged both ends | ~12–16 cm | 20 cm: ~4–8 cm spare |
| Hub KNOB → encoder | 5 (A, C, B, SW, SW ground) | plug on the hub; cut and soldered at the encoder | ~13 cm | cut to fit |
| Hub switch row → 4 toggles | 8 (signal + ground each) | plug on the hub; cut and soldered at the toggle | WIFE MODE / DAY·NIGHT ~18 cm, **CHIME ~16–21 cm** | cut to fit; CHIME see above |
| Hub switch row → 2 pilot lights | 4 (long leg + short leg each) | plug on the hub; cut and soldered at the LED | ~13–15 cm | cut to fit |

**How the lengths were estimated:** each hub pin's position from `hub_pcb.py`, placed on the panel through the P1 pocket (`common.scad`: board centre X 7.5 / Y 138, top of a plugged Dupont housing about 42 mm behind the panel front); each part from `common.scad` (gauge header at the bottom of the tail, toggle lugs and LED legs about 15–18 mm behind the panel front). Run = across + down the panel along the edges (not diagonally) + the drop from the plug + 25 mm to bend and dress. The longest is **CHIME, about 21 cm** (switch row far left as seen from the front, about 85 mm across and 70 mm down from the hub). On the 20 cm wires on hand, CHIME needs the straight route (above).

**Not jumpers, already in hand or ordered:**
- **POWER IN:** the xiwai lead (17.5 cm) plugs straight into the hub. Back-plate socket to POWER IN is about 9 cm in a straight line, so about 8 cm is left to lift the back plate away before unplugging it at the hub.
- **Presto lead:** the Pololu #5604 PH–PH, 16 cm (ordered). It runs under the board through the slot to the Presto's battery socket (a few cm).
- **Qw/ST:** the kit's JST-SH cable (on hand). Same short run through the slot.
- **Speaker → amp:** as on the breadboard set (the amp's screw terminal).

**For the 17 joints per unit at the part end:** heat-shrink tubing (on hand), one piece over each joint — slide it on before soldering.

**Bench checks still open, from 2026-10-11:** room for a Dupont plug behind each gauge's header (the housing is about 14 mm long plus the wire's bend), and whether the gauge headers point straight back.

## Not needed any more

- The XUGERIP JST-PH pairs bought 2026-10-09: the xiwai lead now plugs straight into the board, and the Presto lead is the ready-made cable above. Keep them as spares.
