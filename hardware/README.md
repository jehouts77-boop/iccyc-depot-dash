# Hardware: the case, the hub board and the wiring

Everything needed to build the physical console, as it stood on 2026-10-14.
The software is in the rest of the repo (see the main `README.md`).

These files were copied from the builder's working folder; the `.md` files in
here are working logs as much as guides, with dates and decisions as they
happened. Where a file says "roadmap 4.1a" or similar, that is the builder's
own plan, which isn't in this repo.

## `enclosure/` - the 3D-printed case (OpenSCAD)

| File | What it makes |
|---|---|
| `common.scad` | every shared measurement: the Presto, gauges, knob, switches, speaker, the tilt (8°) - change sizes here |
| `body.scad` | the case body (rev E): box with a sloped front, removable back plate, corner screw bosses for M3 heat-set inserts |
| `panel.scad` | the front panel (rev E): screen window, two gauge holes, knob, the switch row and pilot lights, the inlaid labels |
| `parts.scad` | the small parts: P1 hub shelf, P2 speaker strap, P3 gauge retainers, P4 knob |
| `bezels.scad` | P5 screen frame, P6 gauge rings, P7 knob ring |
| `coupons.scad` | small test pieces for checking fits before a full print |
| `wood_grain.py` | adds the carved wood-grain texture to the body: `python wood_grain.py body_plain.stl body_grain.stl` (needs numpy, trimesh, manifold3d) |
| `fonts/` | the label font (Barlow SemiBold, SIL Open Font License - `Barlow-OFL.txt`); OpenSCAD finds it through the `use <fonts/...>` line |
| `revE_mockup_2026-10-09.png` | what rev E looks like |

To make an STL: open the `.scad` in OpenSCAD, render (F6), export. The
`.scad` files are written as seen from the FRONT, so left and right swap when
you look at the back of the panel.

### `enclosure/stl/` - ready to print (current revisions)

| File | Notes |
|---|---|
| `body_revE_wood_print.3mf` | the body with the wood grain (printed in wood PLA). Back face down, brim, no supports |
| `body_revE_plain_print.stl` | the same body without the grain |
| `back_plate_revE_print.stl` | removable back plate (printed black); sits 2 mm into the body, 4 × M3 × 8 screws, holds the USB-C power socket |
| `panel_revE_print.stl` + `panel_labels_revE_print.stl` | the front panel and its inlaid labels: load both together in Bambu Studio as one object with two parts (labels part = cream filament, panel = black); supports on the build plate under the three front recesses |
| `p1_hub_shelf_revE2_print.stl` | the shelf the hub board sits on, behind the Presto (rev E2: a roomier pocket for the rev A board) |
| `parts_revD5_print.stl` | all the small parts on one plate |
| `p3_gauge_retainers_revD5_print.stl`, `p4_knob_fluted_revD4_print.stl` | the gauge retainers and the knob on their own |
| `bezels_revD_print.stl`, `p5_screen_frame_revD_print.stl`, `p6_gauge_ring_revD_print.stl`, `p7_knob_ring_revD_print.stl` | the bezels, all together or one by one |

Printed on Bambu Lab printers at 0.2 mm layers. Hardware: M3 heat-set inserts
(8 in the body) and M3 × 8 screws.

## `hub-pcb/` - the hub board

A small 70 × 50 mm two-layer board that sits behind the Presto. It carries the
two RP2040-Zeros (0x10 gauges, 0x11 controls) and the MAX98357A amp in female
header sockets, the two 330 Ω resistors for the pilot lights, one +5 V rail and
ground, and a pin header (or JST-PH socket) for every wire that leaves the
board.

| File | What it is |
|---|---|
| `hub_pcb_revA_gerbers.zip` | **the order files** - upload this to a board maker (rev A was made by OSH Park) |
| `hub-pcb-parts-list.md` | what to buy to populate it, with part numbers |
| `hub-board-build.md` | what goes where, every off-board wire, and the build log |
| `hub-revA-rework.md` | **read first: three corrections rev A needs** (6 wires for the Zeros' bottom row, the PRESTO socket turned round, sand the edge nubs), with `hub_revA_rework_wires.png` |
| `hub-pcb-solder-guide.md` | **how to solder and check the board**, step by step, with pictures (in `hub-pcb-solder-guide/`) |
| `hub_pcb_steps.py` | draws those pictures from `hub_pcb.kicad_pcb` (needs matplotlib only, not KiCad): `python hub_pcb_steps.py` |
| `hub_pcb_copper.png`, `hub_pcb_kicad_view.png`, `hub_pcb_placement.png` | pictures of the board |
| `hub_layout.py` | the netlist in practice: every connection and hole, with checks; writes `hub_holes.json` and `hub-board-layout.png` |
| `hub_pcb.py` | builds the KiCad board from `hub_layout.py`'s output, routes it (`hub_router.py`), runs KiCad's design-rule check, draws the pictures and writes the Gerbers. Needs KiCad 7's Python module (`pcbnew`). Run `python hub_layout.py` first, then `python hub_pcb.py` |
| `hub_pcb.kicad_pcb`, `hub_pcb.kicad_pro` | the board itself, openable in KiCad |
| `hub_pcb_report.txt` | the checks from the last build |

**Check the power socket polarity with a meter before the first power-up.**
JST-PH sockets on this board are pin 1 = ground, pin 2 = +5 V.

## `wiring/`

`wiring-plan.md` - power (one panel-mount USB-C socket feeding a single 5 V
rail) and the full wire lists for both co-processors; `wiring-diagram.svg` -
the picture.

## The rule that matters most

**Unplug the case's power before plugging a USB cable into anything inside.**
The USB-C socket feeds the 5 V rail directly, and so does a computer's USB.
