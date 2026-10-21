// ============================================================
// ICCYC Control Console — brass bezels / frames (rev D, 2026-10-02)
// ============================================================
// Option C from the 2026-10-02 mockup (plan doc, Open items #10):
// separate frames that drop into the panel's front recesses and
// stand `proud` above the panel face, bevelled on the inside.
//
// P5 screen_frame()  square frame around the Presto window (x1)
// P6 gauge_ring()    ring around a gauge window (x2)
// P7 knob_ring()     ring around the knob (x1)
//
// The panel does not change. Each part is only as big as its
// recess, so a wrong fit costs one small reprint.
//
// PRINT: visible face DOWN on the bed (as exported), no supports —
// every slope is 45 degrees. 0.12-0.16 mm layers look best on the
// bevels. Fix with a few dots of glue or thin double-sided tape.
// TEST FIRST: one P6 on coupon C2 (PART = "gauge").
// Set PART to export one part on its own.
// ============================================================

include <common.scad>

PART = "all";      // all | screen | gauge | knob

// ---- the look (agreed from the mockup) ----
proud    = 1.5;    // frame top above the panel face
edge_ch  = 1.0;    // 45-degree chamfer on the outer top edge
land     = 0.6;    // straight wall at the bottom of the inner edge, before the bevel starts
// ---- the fit (VERIFY on the coupons) ----
fit      = 0.2;    // gap per side between a frame and its recess wall
rec_d    = 1.2;    // recess depth — as cut by panel.scad (all three recesses)
// ---- recess sizes: copied from panel.scad / common.scad ----
scr_rec_w   = 104;   // screen recess, square (panel.scad: screen_cx +- 52)
scr_rec_r   = 3;     // its corner radius
gauge_rec_d = gauge_bezel_d;   // 50
knob_rec_d  = knob_bezel_d;    // 46
// ---- openings ----
scr_lip     = 1.0;   // screen frame reaches this far in over the glass edge (hides the window gap). VERIFY: must stay off the lit area
scr_open    = min(glass_w, glass_h) - 2*scr_lip;   // 82.1, square, so the frame fits any way round
scr_open_r  = 1;
gauge_open_d = gauge_window_d;   // 34 = the panel window, no lip
knob_open_d  = 32.5;             // printed knob P4 is 30.4 over its ribs and dips 1 mm into the ring

H   = rec_d + proud;      // 2.7 total height
bev = H - land;           // 2.1: inner bevel, 45 degrees, opens toward the viewer

// Parts are modelled seat-down: Z = 0 is the recess floor, Z = H the visible top.
module rsq(w, r) { offset(r = r) offset(delta = -r) square([w, w], center = true); }
module slab(w, r, z0, z1) { translate([0, 0, z0]) linear_extrude(height = z1 - z0) rsq(w, r); }

module screen_frame() {
    ow = scr_rec_w - 2*fit;   or = scr_rec_r - fit;
    difference() {
        hull() { slab(ow, or, 0, H - edge_ch); slab(ow - 2*edge_ch, or, H - 0.01, H); }
        translate([0, 0, -1]) linear_extrude(height = land + 1) rsq(scr_open, scr_open_r);
        hull() { slab(scr_open, scr_open_r, land - 0.01, land);
                 slab(scr_open + 2*bev + 0.02, scr_open_r + 1, H, H + 0.01); }
    }
}

module ring(rec_dia, open_dia) {
    ro = rec_dia/2 - fit;  ri = open_dia/2;
    rotate_extrude($fn = 128) polygon([
        [ri, 0], [ro, 0], [ro, H - edge_ch], [ro - edge_ch, H], [ri + bev, H], [ri, land]]);
}
module gauge_ring() { ring(gauge_rec_d, gauge_open_d); }
module knob_ring()  { ring(knob_rec_d, knob_open_d); }

// ---- in place on the panel (panel-local frame, same as panel()) ----
module seat(x, y) { front_frame() translate([x, y, rec_d]) mirror([0, 0, 1]) children(); }
module bezels_assembled() {
    seat(screen_cx, screen_cy) screen_frame();
    for (cy = [gauge1_cy, gauge2_cy]) seat(gauge_x, cy) gauge_ring();
    seat(knob_x, knob_y) knob_ring();
}

// ---- print layout: visible face down ----
module face_down() { translate([0, 0, H]) mirror([0, 0, 1]) children(); }
if (PART == "screen") face_down() screen_frame();
if (PART == "gauge")  face_down() gauge_ring();
if (PART == "knob")   face_down() knob_ring();
if (PART == "all") {
    face_down() screen_frame();
    translate([0, 0, 0]) face_down() gauge_ring();          // one gauge ring fits inside the screen frame
    translate([82, 27, 0]) face_down() gauge_ring();
    translate([80, -25, 0]) face_down() knob_ring();
}
