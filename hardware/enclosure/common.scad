// ============================================================
// ICCYC Control Console — shared interface, constants & layout
// rev D (2026-10-01, roadmap 2.4; Presto back corrected 2026-10-02,
// rev D1; gauge pins changed 2026-10-07, rev D3; insert holes 4.2,
// rev D5; rev E 2026-10-09: tilt 8°, full-height panel, removable
// back plate): measured parts (plan doc,
// Measurements) + the 2.3 internal layout (canvas artboards 7–8).
// ============================================================
// Everything that has to stay IN SYNC between body.scad,
// panel.scad and parts.scad lives here: case size, tilt, screws,
// and every position a second part has to line up with.
//
// VERIFY = not measured / an estimate. Check before the gift print.
//
// ---- COORDINATES (read this first) -------------------------
// Panel-local frame: Y = 0 at the panel's bottom edge, Y up; Z = 0
// at the FRONT (visible) face, +Z going back into the case.
// The viewer looks at the front face along +Z, so in the raw
// panel frame +X is the viewer's LEFT. rev C got this wrong and
// came out mirrored (gauges on the viewer's right).
// From rev D every X in this project is written AS SEEN FROM THE
// FRONT (+X = viewer's right, like the canvas), and front_frame()
// converts it. Use front_frame() around anything placed by X.
// ============================================================

$fn = 64;

module front_frame() { mirror([1, 0, 0]) children(); }

// ---------------------------------------------------------------
// Outer case (body) — unchanged from rev C
// ---------------------------------------------------------------
case_w   = 230;   // outer width, mm — fits a 256x256 bed w/ brim room
case_h   = 210;   // outer height, mm
wall     = 3.2;   // body wall thickness
corner_r = 10;    // body corner radius
case_d   = 95;    // body depth. 2.3: ~27 mm spare behind the tallest part (at 12°; more at 8°)

// rev E (2026-10-09, Jason): the back is a separate, removable plate
// (black), set back_inset into the back of the (wood) body, held by
// 4 M3 screws into heat-set inserts in corner shelves. The USB-C
// power socket moved from the body's back wall onto this plate.
back_inset = 2;     // plate's outside face sits this far inside the body's back edge
back_t     = 3.2;   // plate thickness (= the old wall; the xiwai socket nut fits it)
back_clear = 0.3;   // per side, plate to body inside
back_shelf_leg = 22;    // corner shelf (a right triangle), measured from the inside corner along each wall
back_shelf_t   = 8;     // corner shelf thickness (front to back): 6 mm insert hole + 2
back_screw_in  = 7.5;   // screw centre, from each inside wall

// ---------------------------------------------------------------
// Panel tilt + plate
// ---------------------------------------------------------------
// rev E (2026-10-09, Jason): tilt 12 -> 8 ("12 might be a bit too
// much"), and the panel now fills the opening top to bottom (the D5
// panel left ~6 mm at the top and ~6.8 mm at the bottom — Jason
// measured 5-6 mm each). The layout keeps its own frame: Y = 0 is
// still where it was on the 195 mm panel, and the panel grows by
// panel_ext at each end, so every part keeps its place on the panel.
tilt_angle  = 8;
panel_thick = 3.5;
panel_clear = 0.3;                 // per side — the sides fit well at 0.3 (Jason, 2026-10-09)
panel_w = case_w - 2*wall - 2*panel_clear;   // 223.0
panel_h_layout = 195;              // the layout frame (rev D panel length)
panel_front_inset = 0;
// front-bottom edge of the panel, body frame; its back-bottom corner
// then clears the floor by panel_clear
panel_bottom_y = -(case_h/2 - wall) + panel_clear + panel_thick*sin(tilt_angle);
// full length ALONG the tilted plate; its front-top edge clears the
// top by panel_clear
panel_h = (case_h/2 - wall - panel_clear - panel_bottom_y) / cos(tilt_angle);   // ~204.5 at 8°
panel_ext = (panel_h - panel_h_layout) / 2;                                       // ~4.75 added at each end
panel_rise        = panel_h * cos(tilt_angle);  // informational
panel_top_setback = panel_h * sin(tilt_angle);  // informational (~28.5 at 8°: the hood)

// ---------------------------------------------------------------
// Corner screws — panel-to-body (symmetric, so mirror-proof)
// ---------------------------------------------------------------
screw_inset_x = 10;
screw_inset_y = 10;
screw_clear_d = 3.4;   // M3 clearance
screw_boss_d  = 8;
insert_d      = 4.2;   // M3 heat-set insert hole. Confirmed 2026-10-07 (Jason, test strip 4.0 / 4.2 / 4.4 / 4.6,
                       // inserts M3 x L4 x OD5, soldering iron): 4.2 was the best. Was 4.0.
insert_depth  = 6;
screw_insert_d     = insert_d;      // old names, kept for body.scad
screw_insert_depth = insert_depth;

// layout-frame Y of the panel's real bottom and top edges
panel_y_bot = -panel_ext;
panel_y_top = panel_h_layout + panel_ext;

// rev E: the screws stay screw_inset from the panel's real corners
function panel_screw_points() = [
    [-(panel_w/2 - screw_inset_x), panel_y_bot + screw_inset_y],
    [ (panel_w/2 - screw_inset_x), panel_y_bot + screw_inset_y],
    [-(panel_w/2 - screw_inset_x), panel_y_top - screw_inset_y],
    [ (panel_w/2 - screw_inset_x), panel_y_top - screw_inset_y],
];

// layout frame -> body frame. rev E: the layout's Y = 0 sits
// panel_ext up the slope from the panel's front-bottom edge.
module panel_place() {
    translate([0, panel_bottom_y, panel_front_inset])
        rotate([tilt_angle, 0, 0])
            translate([0, panel_ext, 0])
                children();
}

// ---------------------------------------------------------------
// LAYOUT — front-view X (+X = viewer's right), Y up from the
// panel's bottom edge. Matches canvas artboard 5 (front, look
// agreed 2026-09-30) and artboards 7–8 (inside, 2026-10-01).
// ---------------------------------------------------------------
// Presto: cut-down aluminium plate (screen glued in) behind a window
screen_cx   = 7;      // screen centre
screen_cy   = 122.5;
glass_w     = 84.3;   // measured
glass_h     = 84.1;   // measured
glass_proud = 1.1;    // glass stands this far in front of the plate
plate_t     = 1.9;    // aluminium
plate_border = 3.7;   // plate edge -> glass edge (sides + top)
plate_tab    = 10.1;  // glass bottom edge -> cut edge (first cut unit)
plate_w   = glass_w + 2*plate_border;            // 91.7
plate_x0  = screen_cx - plate_w/2;               // -38.85
plate_x1  = screen_cx + plate_w/2;               //  52.85
plate_y1  = screen_cy + glass_h/2 + plate_border; // 168.25 (top)
plate_y0  = screen_cy - glass_h/2 - plate_tab;    //  70.35 (cut edge)
presto_depth = 7.9;   // behind the plate, battery plug included
plate_z0 = panel_thick;                    // plate lies on the panel back
presto_back_z = plate_z0 + plate_t + presto_depth;   // 13.3
// Presto back, corrected 2026-10-02 from the C1 fit coupon (Jason:
// calipers + photo). The PCB is NOT centred on the plate. Bare
// aluminium strip between the plate edge and the PCB edge:
strip_conn  = 4.0;    // connector side = front-view LEFT (gauge side)
strip_plain = 4.5;    // plain side     = front-view RIGHT (knob side)
strip_top   = 2.9;    // top edge (opposite the cut tab)
plate_corner_r = 3;   // plate corners are rounded (~3, from the photo: VERIFY)
pcb_x0 = plate_x0 + strip_conn;    // -34.85
pcb_x1 = plate_x1 - strip_plain;   //  48.35
pcb_y1 = plate_y1 - strip_top;     // 165.35
pcb_h  = 85;                       // from the photo, VERIFY
pcb_y0 = pcb_y1 - pcb_h;           //  80.35 (tab-end edge)
// Connectors are on the front-view LEFT edge, facing the gauges
// (rev D had them on the right, and measured from the wrong end):
usbc_cy = pcb_y0 + 15.5;   // ~95.9  USB-C, low, about level with Gauge II
usd_cy  = pcb_y0 + 54.4;   // ~134.8 microSD, between the two gauges
usd_top_y = 150;           // upper end of the card slot, upper bound (Jason ~16 below the old corner finger; photo says ~146)
// Service = panel out + a right-angle USB-C plug toward the gauges
// (~22 mm from the plate edge to the Gauge II PCB: VERIFY with a plug).

// Gauges (GC9A01, DORHEA), stacked in the left column, tail DOWN
gauge_x   = -80;
gauge1_cy = 153.5;    // Gauge I (top)
gauge2_cy = 91.5;     // Gauge II
gauge_window_d = 34;   // visible display is ~32.4
gauge_bezel_d  = 50;   // decorative front counterbore
gauge_pcb_d    = 37.5;
gauge_glass_d  = 35.3;
gauge_glass_to_pcb = 2.0;  // glass face -> PCB front (measured)
gauge_pcb_t    = 1.6;      // VERIFY (4.6 overall at the thickest point)
gauge_tail_w   = 22.8;
gauge_overall  = 45.4;     // circle top -> tail bottom
gauge_hole_dx  = 19.0;     // two ~1.8 mm holes, centre to centre
gauge_hole_dy  = 39.6 - gauge_pcb_d/2;  // 20.85 below the centre
gauge_pin_d    = 1.6;      // printed pins (rev D3: was 1.7; thinner so the board can tilt on)
gauge_pin_tip_d = 0.9;     // rev D3: pointed tip, finds the hole as the tail comes down
gauge_pin_taper = 1.5;     // rev D3: length of the pointed tip, above the retainer
gauge_retainer_t = 2.0;    // retainer bar (parts.scad) on top of the gauge PCB

// Knob (EC11 with push switch), right column, moved up for the grille
knob_x = 86;
knob_y = 150;
knob_bezel_d = 46;     // 86 + 23 = 109 < 111.5 -> no longer overruns the edge
enc_collar_d = 6.7;    // M7 threaded collar
enc_body_w = 11.7;  enc_body_h = 12.7;  enc_body_t = 4.8;  enc_pin_len = 5.1;
enc_tab_r = 5.55;      // anti-rotation tab, from the shaft centre
enc_tab_angle = 90;    // which way the tab points, degrees from +X — VERIFY

// Speaker grille + speaker (CQRobot 70 x 31), wire end DOWN
grille_cx = knob_x;
grille_cy = 94.25;     // = speaker cone centre
grille_slots = 10;
grille_slot_h = 3;
grille_pitch  = 5.5;
grille_w      = 38;
spk_flange_w = 31.3;  spk_flange_h = 69.5;  spk_flange_t = 2.4;
spk_box_w = 30.7;     spk_box_h = 66.6;     spk_depth = 15.9;
spk_cone_offset = 3.45;   // cone sits this far toward the wire end
spk_cy = grille_cy + spk_cone_offset;   // flange centre (wire end is at the bottom)
spk_clear = 0.3;
cage_wall = 3.5;          // covers the grille slot ends (slots 38, flange 31.3)
cage_h    = 6;            // above the panel back
spk_back_z = panel_thick + spk_depth;   // 19.4

// Speaker strap: printed bar across the speaker's back, 2 bosses
strap_boss_pts = [[60, 95], [107.5, 95]];
strap_boss_d = 7;
strap_w = 8;
strap_t = 3;

// Switch row: CHIME, DAY·NIGHT, [WiFi], [OTA], BACKLIGHT, WIFE MODE
switch_row_y = 49;
switch_xs    = [-80, -44, -12, 12, 50, 86];
switch_kind  = ["toggle", "toggle", "pilot", "pilot", "toggle", "toggle"];
toggle_hole_d = 6.3;   // MTS-101 bushing 5.6 (M6)
pilot_hole_d  = 8.2;   // LED holder thread 7.7 (M8)

// Brass nameplate recess, 4" x 1" x 0.04" plate
plate_rec_w = 102.6;  plate_rec_h = 26.0;  plate_rec_d = 1.2;   // VERIFY vs the real plate
plate_rec_cx = 0;     plate_rec_cy = 20.8;

// Hub shelf: printed deck on 4 panel posts, over the Presto's back.
// Carries the perfboard hub (0x10, 0x11, amp, rails, Qw/ST split).
// Its fingers also hold the Presto plate against the panel.
shelf_post_pts = [[-45.5, 163.5], [60.5, 133], [-45.5, 76.5], [60.5, 76.5]];
shelf_post_d = 8;
shelf_z = 15;          // underside of the deck (Presto back is 13.3)
deck_t  = 2.5;
perf_w = 70;  perf_h = 50;  perf_t = 1.6;   // full perfboard, 24 x 18 holes. MEASURED 2026-10-09 (Jason, calipers): 70 x 50.
                                            // Was 61 x 46 (never measured - the hole span plus a guess); the real board did not fit the pocket.
perf_cx = 7.5;  perf_cy = 138;              // board centre unchanged, so every hole stays where the layout drawing has it

// ---------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------
module rounded_box(w, h, d, r) {
    linear_extrude(height = d)
        offset(r = r)
            offset(delta = -r)
                square([w, h], center = true);
}

// The panel blank, in the layout frame (rev E: runs from -panel_ext
// to 195 + panel_ext; was Y = 0 at its bottom edge, see rev C bug 1)
module panel_blank() {
    translate([0, (panel_y_bot + panel_y_top)/2, 0])
        rounded_box(panel_w, panel_h, panel_thick, corner_r - wall);
}

// rounded rectangle by corners, extruded from z0 to z1
module rrect(x0, x1, y0, y1, z0, z1, r = 0.01) {
    translate([0, 0, z0]) linear_extrude(height = z1 - z0)
        offset(r = r) offset(delta = -r)
            translate([x0, y0]) square([x1 - x0, y1 - y0]);
}
