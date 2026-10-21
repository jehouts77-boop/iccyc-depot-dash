// ============================================================
// ICCYC Control Console — fit coupons (roadmap 3.1), rev D (cut from the current panel: rev D7)
// ============================================================
// Each coupon is cut straight out of the real panel / body
// geometry, so it fits exactly like the full print would.
// Print like the panel: FRONT FACE DOWN. Supports ON for presto,
// gauge and knob (their front recesses have a ring / frame roof
// around a through-hole, which can't bridge). switches, speaker and
// socket need none. (Corrected 2026-10-07; this said "no supports".)
// Set COUPON to one name to export it on its own.
// C7 labels (2026-10-08, rev D6): the middle of the switch row with
// its inlaid labels — DAY · NIGHT, WIFI, OTA, BACKLIGHT. Export
// COUPON = "labels" (black) and "labels_inlay" (cream) and load them
// together as one object with two parts. No supports. It checks the
// 2-colour print (letters sharp, cream opaque, flush) and the switches
// and lights next to their labels. Not part of "all".
// ============================================================
use <panel.scad>
use <body.scad>
use <fonts/Barlow-SemiBold.ttf>
include <common.scad>

COUPON = "all";   // presto | gauge | knob | switches | speaker | socket | labels | labels_inlay | all

// a piece of the panel, picked by a box in FRONT-VIEW coordinates,
// mirrored like the real panel, then moved so its corner is at the origin
module piece(x0, x1, y0, y1) {
    // after the mirror, front x in [x0,x1] lands at raw x in [-x1,-x0]
    translate([x1, -y0, 0])
        front_frame() intersection() {
            panel_front_view();
            translate([x0, y0, -1]) cube([x1 - x0, y1 - y0, 40]);
        }
}

// 1. Presto window + the 4 hub-shelf posts (test with the cut Presto + the printed hub shelf)
module c_presto()   piece(-51, 66, 69, 169);
// 2. Gauge II: window, 2 pins, rigid lip (rev D3, tilt-in), ribbon pocket (test with a gauge + a retainer)
module c_gauge()    piece(-107, -53, 63, 115);
// 3. Knob: collar bore, anti-rotation notch, bezel ring (test with an EC11 + the printed knob)
module c_knob()     piece(60, 111.5, 124, 175);
// 4. Switch strip: WiFi + OTA pilot lights and the BACKLIGHT toggle
module c_switches() piece(-24, 62, 37, 61);
// 5. Speaker: grille, cage, strap bosses (test with a speaker + the printed strap)
module c_speaker()  piece(55, 111.5, 55, 140);
// 7. Labels (rev D6): DAY · NIGHT to BACKLIGHT, with the inlay that fills its label pockets
module piece_labels(x0, x1, y0, y1) {
    translate([x1, -y0, 0])
        front_frame() intersection() {
            labels_front_view();
            translate([x0, y0, -1]) cube([x1 - x0, y1 - y0, 40]);
        }
}
module c_labels()       piece(-64, 70, 34, 58);        // rev D7: widened for the 4.5 mm labels (was -58..62)
module c_labels_inlay() piece_labels(-64, 70, 34, 58);
// 6. Back-wall socket hole: a 30 x 30 piece of the body's back wall
module c_socket() {
    translate([15, -50, case_d]) rotate([180, 0, 0])   // outside face down
        intersection() {
            body();
            translate([-15, -(case_h/2) + 25, case_d - wall - 0.5]) cube([30, 30, wall + 1]);
        }
}

if (COUPON == "presto")   c_presto();
if (COUPON == "gauge")    c_gauge();
if (COUPON == "knob")     c_knob();
if (COUPON == "switches") c_switches();
if (COUPON == "speaker")  c_speaker();
if (COUPON == "socket")   c_socket();
if (COUPON == "labels")       c_labels();
if (COUPON == "labels_inlay") c_labels_inlay();
if (COUPON == "all") {    // one bed, ~200 x 230
    c_presto();
    translate([0, 108, 0]) c_speaker();
    translate([65, 108, 0]) c_gauge();
    translate([125, 108, 0]) c_knob();
    translate([125, 0, 0]) c_switches();
    translate([125, 32, 0]) c_socket();
}
