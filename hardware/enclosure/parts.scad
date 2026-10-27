// ============================================================
// ICCYC Control Console — small printed parts (rev D5, 2026-10-07; hub shelf rev E1, 2026-10-09)
// ============================================================
// hub_shelf()      deck over the Presto's back on the 4 panel posts.
//                  Carries the perfboard hub; its 4 fingers hold the
//                  Presto's aluminium plate against the panel.
// speaker_strap()  bar across the speaker's back, 2 x M3 into the
//                  panel's strap bosses.
// gauge_retainer() bar over each gauge's 2 locating pins (x2).
// knob_cap()       printed knob for the EC11 (rev D2: black fluted, skirted,
//                  with a recessed line + dot to fill with cream paint).
//
// The *_assembled() modules sit in the panel-local frame (same as
// panel()), for checking. The bottom of this file lays everything
// out flat for printing.
//
// rev D1 (2026-10-02, C1/P1 fit test): the hub shelf's two border
// fingers were re-placed from real measurements. The old top-left
// corner finger fell off the plate's rounded corner; it now sits on
// the connector-side strip, above the microSD. The plain-side finger
// is wider and longer. Tab fingers unchanged (confirmed flush).
// Set PART to export one part on its own.
//
// rev D2 (2026-10-02, evening): knob restyled from the agreed mockup
// (renders\knob_mockup_2026-10-02.png). Bore, nut pocket, height and
// lift are unchanged from rev D; only the outside changed. The old
// plain knob is kept as knob_cap_plain(). Nothing else changed.
//
// rev D3 (2026-10-07, C2 fit test): the gauge retainer's holes were
// too small for the pins (1.9 modelled on 1.7 pins; small upright
// holes print undersize). Pins are now 1.6 (common.scad) and the
// hole size is a named variable. The print layout makes one retainer
// of each trial size: A = plain bar, B = bar with a corner notch.
// Nothing else changed.
//
// rev D4 (2026-10-07, C3 / P4 fit test): the knob's nut pocket now
// has a 45-degree cone roof up to the shaft bore, so the knob prints
// skirt down with NO support inside (the flat roof was a ring around
// a hole; support material left in the bore blocked the shaft).
// Bore size 5.9 confirmed snug on the real shaft (first P4 print).
// Outside shape unchanged.
//
// rev D5 (2026-10-07, C2 reprint fitted): retainer A (2.0 mm holes)
// presses onto the 1.6 mm pins and stays — confirmed by Jason. The
// looser trial B (2.2 mm, notched) is dropped; both retainers are A.
//
// rev E2 (2026-10-25, hub shelf only): the hub PCB (70 x 50, edges sanded
// flush) caught at the corners of the printed pocket. The model gave
// 0.2 mm a side and the print came out 70.2 x 50.2 (Jason, calipers).
// Now hub_pocket_clear = 0.5 mm a side (pocket 71.0 x 51.0) plus a
// round relief at each corner for the board's square corners. Nothing
// else changed: frame, ledge opening, zip-tie slots, posts, fingers.
//
// rev E1 (2026-10-09, hub shelf only): the perfboard pocket was
// modelled at 61 x 46 and the real board is 70 x 50 (Jason,
// calipers) - it did not fit. perf_w / perf_h corrected in
// common.scad; the frame, pocket, opening and zip-tie slots follow.
// Board centre, posts, fingers and deck height are unchanged.
//
// Screws: shelf 4 x M3 x 8-10, strap 2 x M3 x 8, into heat-set
// inserts in the panel (VERIFY lengths against what's on hand).
// ============================================================

include <common.scad>

eps = 0.01;
hub_pocket_clear    = 0.5;   // rev E2: room around the hub board, each side (was 0.2; printed 0.1)
hub_corner_relief_r = 1.0;   // rev E2: round relief centred on each board corner (square PCB corners)
pb  = panel_thick;
plate_face_z = plate_z0 + plate_t;   // 5.4: back face of the aluminium plate
PART = "all";          // all | shelf | strap | retainers | knob
retainer_hole_d   = 2.0;   // press fit on the 1.6 mm pins — confirmed 2026-10-07 (was trial "A"; trial B = 2.2 dropped)

// --- hub-shelf fingers (front-view X; all on bare aluminium) ---
finger_edge_gap = 0.25;   // fingers start this far inside the plate edge
// connector-side finger (front-view left), above the microSD slot
conn_finger_w  = 2.5;     // strip there is 4.0 (strip_conn)
conn_finger_y0 = 154;     // card slot ends at <= 150 (usd_top_y)
conn_finger_y1 = 162;     // corner round-over starts at ~165.25
// plain-side finger (front-view right)
plain_finger_w  = 3.0;    // strip there is 4.5 (strip_plain)
plain_finger_y0 = 127;
plain_finger_y1 = 139;
finger_press = 0.2;    // fingers reach this far past the plate face -> light clamp
deck_top_z   = shelf_z + deck_t;

// ---------------- hub shelf (front-view coordinates) -----------
module hub_deck_2d() {
    difference() {
        union() {
            translate([-49.5, 72.5]) square([114, 8]);          // bottom bar (BL, BR posts)
            translate([-49.5, 72.5]) square([8, 95]);           // left bar (BL, TL posts)
            translate([-41.5, conn_finger_y0 - 0.5])
                square([plate_x0 + finger_edge_gap + conn_finger_w + 0.5 + 41.5, 157.5 - conn_finger_y0 + 0.5]);   // tab over the connector-side finger
            translate([plate_x1 - plain_finger_w - 1, plain_finger_y0 - 0.5])
                square([plain_finger_w + 2, plain_finger_y1 - plain_finger_y0 + 1]);   // pad over the plain-side finger
            translate([perf_cx - perf_w/2 - 4, perf_cy - perf_h/2 - 4])
                square([perf_w + 8, perf_h + 8]);              // perfboard frame
            translate([-45.5, 157]) square([20, 8]);            // TL link
            translate([perf_cx + perf_w/2, 129]) square([64.5 - (perf_cx + perf_w/2), 8]);   // TR arm
            for (x = [-10, 17]) translate([x, 76.5]) square([8, 36]);          // links to the bottom bar
        }
        // opening under the perfboard: wires (Qw/ST, battery lead) come up through here
        translate([perf_cx - perf_w/2 + 3.5, perf_cy - perf_h/2 + 3.5]) square([perf_w - 7, perf_h - 7]);
        // zip-tie slots, 2 each side of the board
        for (sx = [-1, 1]) for (dy = [-12, 12])
            translate([perf_cx + sx*(perf_w/2 + 2.2) - 0.8, perf_cy + dy - 2]) square([1.6, 4]);
    }
}

module hub_shelf_front() {
    difference() {
        union() {
            translate([0, 0, shelf_z]) linear_extrude(height = deck_t) hub_deck_2d();
            // fingers down onto the Presto plate (front-view X)
            for (f = [
                [plate_x0 + finger_edge_gap, plate_x0 + finger_edge_gap + conn_finger_w, conn_finger_y0, conn_finger_y1],   // connector side, above the microSD
                [plate_x1 - finger_edge_gap - plain_finger_w, plate_x1 - finger_edge_gap, plain_finger_y0, plain_finger_y1],  // plain side
                [-38.5, -28.5, 71.0, 76.0],                 // tab, left
                [ 42.5,  52.5, 71.0, 76.0],                 // tab, right (battery lead runs between)
            ])
                rrect(f[0], f[1], f[2], f[3], plate_face_z - finger_press, shelf_z + eps);
        }
        // perfboard locating pocket, 1 mm deep in the top face
        rrect(perf_cx - perf_w/2 - hub_pocket_clear, perf_cx + perf_w/2 + hub_pocket_clear,
              perf_cy - perf_h/2 - hub_pocket_clear, perf_cy + perf_h/2 + hub_pocket_clear, deck_top_z - 1, deck_top_z + 1);
        for (sx = [-1, 1]) for (sy = [-1, 1])
            translate([perf_cx + sx*perf_w/2, perf_cy + sy*perf_h/2, deck_top_z - 1])
                cylinder(r = hub_corner_relief_r, h = 2, $fn = 32);
        // screw clearance at the posts
        for (p = shelf_post_pts) translate([p[0], p[1], shelf_z - 1]) cylinder(d = screw_clear_d, h = deck_t + 2);
    }
}
module hub_shelf_assembled() { front_frame() hub_shelf_front(); }

// ---------------- speaker strap ---------------------------------
strap_y = strap_boss_pts[0][1];
strap_x0 = strap_boss_pts[0][0] - strap_boss_d/2;
strap_x1 = strap_boss_pts[1][0] + strap_boss_d/2 - 0.5;   // stays inside the panel edge
module speaker_strap_front() {
    z0 = spk_back_z;      // rests on the speaker; the bosses stop 0.3 short -> preload
    difference() {
        rrect(strap_x0, strap_x1, strap_y - strap_w/2, strap_y + strap_w/2, z0, z0 + strap_t, r = 2);
        for (p = strap_boss_pts) translate([p[0], p[1], z0 - 1]) cylinder(d = screw_clear_d, h = strap_t + 2);
    }
}
module speaker_strap_assembled() { front_frame() speaker_strap_front(); }

// ---------------- gauge retainer --------------------------------
gauge_pcb_back_z = pb + gauge_glass_to_pcb + gauge_pcb_t;
module gauge_retainer_front(cy, hole_d = retainer_hole_d, notch = false) {
    y = cy - gauge_hole_dy;
    difference() {
        rrect(gauge_x - 12, gauge_x + 12, y - 2, y + 2, gauge_pcb_back_z, gauge_pcb_back_z + gauge_retainer_t, r = 1);
        for (s = [-1, 1]) translate([gauge_x + s*gauge_hole_dx/2, y, gauge_pcb_back_z - 1])
            cylinder(d = hole_d, h = 4);
        if (notch) translate([gauge_x + 10.5, y + 0.5, gauge_pcb_back_z - 1]) cube([3, 3, 4]);
    }
}
module gauge_retainers_assembled() { front_frame() for (cy = [gauge1_cy, gauge2_cy]) gauge_retainer_front(cy); }

// ---------------- knob cap ---------------------------------------
// Fits the EC11 (unchanged from rev D):
knob_h        = 20;
knob_lift     = 0.5;    // gap between knob and panel face
shaft_bore_d  = 5.9;    // knurled split shaft 5.7 — friction fit (confirmed snug 2026-10-07, first P4 print)
shaft_bore_h  = 12.5;   // bore depth above the nut pocket
nut_pocket_d  = 12.6;   // front nut 11.3 across corners
nut_pocket_h  = 4.0;    // collar sticks out 3.5 past the panel face
nut_cone_h    = (nut_pocket_d - shaft_bore_d)/2;   // rev D4: 45-degree roof, pocket -> bore (3.35)
// The look (rev D2, fluted + skirted):
knob_d        = 30;     // skirt diameter (the P7 ring's opening is 32.5)
knob_rim_h    = 1.2;    // straight rim at the bottom of the skirt
knob_skirt_h  = 5.5;    // top of the skirt cone, from the knob's bottom
knob_body_d0  = 23;     // body diameter where it meets the skirt
knob_body_d1  = 20.5;   // body diameter at the top
knob_top_ch   = 1.2;    // height of the rounded-off top edge
knob_flutes   = 8;
knob_flute_r  = 4.2;    // radius of each scallop
knob_flute_depth = 1.6; // how deep a scallop cuts into the body
// Marks to fill with paint (recessed):
mark_depth    = 0.4;
line_w        = 1.6;    // pointer line on the top, over a flute crest
line_r0       = 1.5;    // line start / end, from the centre
line_r1       = 7.6;
dot_d         = 2.4;    // dot on the skirt cone, in line with the pointer

module knob_flute_2d(d) {
    difference() {
        circle(d = d, $fn = 96);
        for (a = [0 : 360/knob_flutes : 359]) rotate(a + 180/knob_flutes)
            translate([d/2 + knob_flute_r - knob_flute_depth, 0]) circle(r = knob_flute_r, $fn = 48);
    }
}
module knob_cap() {
    cone_top_r = (knob_body_d0 - 1)/2;
    cone_ang = atan2(knob_skirt_h - knob_rim_h, knob_d/2 - cone_top_r);   // cone slope above horizontal
    dot_r = (knob_d/2 + cone_top_r)/2;                                     // halfway up the cone
    dot_z = (knob_rim_h + knob_skirt_h)/2;
    difference() {
        union() {
            cylinder(d = knob_d, h = knob_rim_h, $fn = 96);
            translate([0, 0, knob_rim_h]) cylinder(d1 = knob_d, d2 = knob_body_d0 - 1, h = knob_skirt_h - knob_rim_h, $fn = 96);
            translate([0, 0, knob_rim_h]) linear_extrude(height = knob_h - knob_rim_h - knob_top_ch, scale = knob_body_d1/knob_body_d0)
                knob_flute_2d(knob_body_d0);
            translate([0, 0, knob_h - knob_top_ch - eps]) linear_extrude(height = knob_top_ch + eps, scale = 0.9)
                scale(knob_body_d1/knob_body_d0) knob_flute_2d(knob_body_d0);
        }
        translate([0, 0, -1]) cylinder(d = nut_pocket_d, h = nut_pocket_h + 1);
        translate([0, 0, nut_pocket_h - eps]) cylinder(d1 = nut_pocket_d, d2 = shaft_bore_d, h = nut_cone_h);
        translate([0, 0, nut_pocket_h - eps]) cylinder(d = shaft_bore_d, h = shaft_bore_h);
        // pointer line, recessed in the top
        translate([0, 0, knob_h - mark_depth]) hull() for (r = [line_r0, line_r1])
            translate([r, 0, 0]) cylinder(d = line_w, h = mark_depth + 1, $fn = 24);
        // dot, recessed square-on into the skirt cone
        translate([dot_r, 0, dot_z]) rotate([0, 90 - cone_ang, 0])
            translate([0, 0, -mark_depth]) cylinder(d = dot_d, h = 3, $fn = 24);
    }
}
// rev D plain knob, kept for reference (not exported)
module knob_cap_plain() {
    difference() {
        union() {
            cylinder(d = knob_d, h = knob_h - 4);
            translate([0, 0, knob_h - 4]) cylinder(d1 = knob_d, d2 = knob_d - 4, h = 4);
            for (a = [0 : 15 : 345]) rotate([0, 0, a])
                translate([knob_d/2 - 0.6, 0, (knob_h - 4)/2]) cube([1.6, 1.5, knob_h - 4], center = true);
        }
        translate([0, 0, -1]) cylinder(d = nut_pocket_d, h = nut_pocket_h + 1);
        translate([0, 0, nut_pocket_h - eps]) cylinder(d = shaft_bore_d, h = 12.5);
    }
}

// ---------------- print layout ----------------------------------
// hub shelf: top face down (fingers up); strap and retainers flat
module shelf_print() {
    // top face on the bed (fingers up), centred near the origin
    translate([0, 0, deck_top_z]) rotate([180, 0, 0]) translate([-7.5, -120, 0]) hub_shelf_assembled();
}
module strap_print() {
    translate([-strap_x0 - 60, 70 - strap_y, -spk_back_z]) speaker_strap_front();
}
module retainers_print() {
    for (i = [0, 1]) translate([10 - gauge_x, 66 + i*10 - (gauge1_cy - gauge_hole_dy), -gauge_pcb_back_z])
        gauge_retainer_front(gauge1_cy);
}
module knob_print() { translate([75, 80, 0]) knob_cap(); }

if (PART == "all" || PART == "shelf")     shelf_print();
if (PART == "all" || PART == "strap")     strap_print();
if (PART == "all" || PART == "retainers") retainers_print();
if (PART == "all" || PART == "knob")      knob_print();
