// ============================================================
// ICCYC Control Console — front panel (rev E, 2026-10-09; rev D7 2026-10-08; rev D 2026-10-01, roadmap 2.4)
// ============================================================
// Holds: Presto (cut-down aluminium plate, screen in a window),
// 2 x GC9A01 gauges (left column), EC11 knob (right column, moved
// up), speaker grille + printed speaker cage under the knob,
// 4 x MTS-101 toggles + 2 pilot lights, brass nameplate recess,
// 4 posts for the hub shelf (parts.scad), 2 bosses for the
// speaker strap (parts.scad).
//
// All layout numbers live in common.scad, written as seen from the
// FRONT. panel() mirrors once (front_frame) so the printed part
// matches the canvas. rev C was mirrored; this fixes it.
// rev C's screen window was only a 1.75 mm recess; now a through-cut.
//
// rev D3 (2026-10-07, C2 fit test): the gauge's springy snap hook
// broke on the first try (a 1 mm arm only ~5 mm tall can't bend
// 0.8 mm). It is now a RIGID lip: tuck the gauge's top edge under
// it at an angle, lower the tail onto the two pins, press the
// retainer on. Pins are 1.6 mm with a pointed tip above the
// retainer. Nothing else on the panel changed.
// rev D4 (2026-10-07, C3 fit test): the encoder's anti-rotation
// notch is 1 mm longer, away from the hole (the tab missed it by
// ~0.8 mm). Its direction (toward the panel top) was confirmed.
// rev D5 (2026-10-07, insert test strip): heat-set insert holes in
// the 4 shelf posts and 2 strap bosses are 4.2 mm (insert_d in
// common.scad; were 4.0). No other change.
// rev D6 (2026-10-08, roadmap 6.1a — Jason picked option B from
// renders\labels_mockup_2026-10-08.png): switch-row labels inlaid
// in the front face for a 2-colour AMS print. Each toggle and each
// pilot light has its own name under it (CHIME, DAY · NIGHT, WIFI,
// OTA, BACKLIGHT, WIFE MODE). The panel gets label-shaped pockets
// label_depth deep in the front face; PART = "labels" exports the
// matching cream inlay, in the same coordinates. Nothing else changed.
// rev D7 (2026-10-08, label test strip, labels_test.scad): the D6
// labels (Barlow Condensed, 3.5 mm caps) printed soft — gaps inside
// the letters were about one nozzle line. Jason picked row D: Barlow
// (regular width) SemiBold, 4.5 mm caps, spacing 1.05. Same centre
// line and depth. At 4.5 mm BACKLIGHT and WIFE MODE nearly ran
// together (3 mm gap). Jason's call: all labels stay 4.5 mm and
// WIFE MODE goes on two lines — WIFE on the label line, MODE under
// it (room there: the nameplate stops at x 51). Gap to BACKLIGHT
// is then ~16 mm.
// rev E (2026-10-09, Jason): no change in this file — the panel is
// longer (204.5 mm along the slope, was 195: it now fills the case
// opening top and bottom) and sits at 8° (was 12°); both come from
// common.scad. Every part keeps its place on the panel (the layout's
// Y = 0 is unchanged; the panel grows 4.75 mm at each end). The four
// corner screw holes moved with the corners. Labels unchanged.
//
// PRINT: face-down (front face on the bed, as modelled), 0.2 mm
// layers, SUPPORTS ON (build plate only). Corrected 2026-10-07 —
// this note said "no supports", which was wrong: the three front
// recesses (gauge, knob, screen) have a ring / frame roof around a
// through-hole, and that can't bridge. Only the nameplate recess is
// a plain bridge (26 mm). Everything on the back (posts, bosses,
// pins, gauge lips, cage) rises from the panel and needs none.
// Heat-set M3 inserts go into the 4 shelf posts and 2 strap bosses
// from the back.
// LABELS (rev D7): load panel_revD7_print.stl and
// panel_labels_revD7_print.stl together in Bambu Studio, say YES to
// "load as a single object with multiple parts", and give the labels
// part the cream filament. The labels are the first label_depth of
// the print (on the bed), so they come out flush with the front.
// ============================================================

include <common.scad>
use <fonts/Barlow-SemiBold.ttf>   // font file ships in fonts\ next to this file (rev D7)

PART = "panel";   // panel | labels  (export each one to its own STL)

eps = 0.01;
pb  = panel_thick;     // Z of the panel's back face

// ---- small knobs to tune after the fit coupons (roadmap 3.1) ----
window_clear   = 0.3;  // per side, around the Presto glass
gauge_lip_reach = 1.0;  // how far the rigid lip reaches in over the gauge PCB's top edge
gauge_lip_gap   = 0.2;  // lip underside above the PCB's back corner (PCB thickness is a VERIFY)
gauge_lip_wall_gap = 0.3;  // lip wall to the PCB's top edge
gauge_lip_w     = 8;    // lip width
gauge_lip_t     = 2.5;  // lip wall thickness (rigid: it must NOT bend)
enc_bore_d   = 7.2;
enc_notch_out = 1.5;   // notch reaches this far past enc_tab_r (rev D4: was 0.5; the real tab missed by ~0.8)
strap_preload = 0.3;   // strap bosses stop this far short of the speaker back

// ---- switch-row labels (rev D6; font / size / spacing rev D7) ----
label_font  = "Barlow SemiBold";   // D6: "Barlow Condensed SemiBold"
label_cap   = 4.5;    // capital-letter height, mm (D6: 3.5)
label_depth = 0.6;    // inlay depth = 3 layers at 0.2; thinner lets the black show through cream
label_y     = 39.5;   // centre line of the labels (switch row 49, nameplate recess top 33.8)
label_track = 1.05;   // letter spacing (1 = the font's own; D6: 1.08)
label_k     = 0.9722;   // OpenSCAD size -> cap height (measured; same for both Barlow cuts)
// one label per switch / light, in switch_xs order
label_texts = ["CHIME", "DAY · NIGHT", "WIFI", "OTA", "BACKLIGHT", "WIFE"];
label_line2 = ["", "", "", "", "", "MODE"];   // rev D7: second line under the first ("" = none)
label_line_pitch = 6.5;   // centre to centre of the two lines (4.5 caps + 2 mm gap)

gauge_pcb_back_z = pb + gauge_glass_to_pcb + gauge_pcb_t;   // 7.1

// ---------------------------------------------------------------
module flared_post(d, z1, flare = 2) {
    // post from the panel back to z1, with a small flare at the base
    translate([0, 0, pb - eps]) {
        cylinder(d1 = d + 2*flare, d2 = d, h = flare);
        cylinder(d = d, h = z1 - pb + eps);
    }
}

module stadium(cx, cy, w, h, z0, z1) {
    hull() for (s = [-1, 1])
        translate([cx + s*(w/2 - h/2), cy, z0]) cylinder(d = h, h = z1 - z0);
}

// ---- things that ADD material on the back ---------------------
module back_features() {
    // hub-shelf posts
    for (p = shelf_post_pts) translate([p[0], p[1], 0]) flared_post(shelf_post_d, shelf_z);
    // speaker-strap bosses
    // (the flare shrinks where a boss sits near the panel edge, so nothing sticks past it)
    for (p = strap_boss_pts) translate([p[0], p[1], 0])
        flared_post(strap_boss_d, spk_back_z - strap_preload,
                    flare = max(0, min(2, panel_w/2 - 0.3 - abs(p[0]) - strap_boss_d/2)));
    // speaker cage
    difference() {
        rrect(grille_cx - spk_flange_w/2 - spk_clear - cage_wall, grille_cx + spk_flange_w/2 + spk_clear + cage_wall,
              spk_cy - spk_flange_h/2 - spk_clear - cage_wall, spk_cy + spk_flange_h/2 + spk_clear + cage_wall,
              pb - eps, pb + cage_h, r = 2);
        rrect(grille_cx - spk_flange_w/2 - spk_clear, grille_cx + spk_flange_w/2 + spk_clear,
              spk_cy - spk_flange_h/2 - spk_clear, spk_cy + spk_flange_h/2 + spk_clear,
              pb - 1, pb + cage_h + 1, r = 1);
    }
    // gauges: 2 locating pins (tail) + 1 rigid lip (top) each — tilt-in, rev D3
    for (cy = [gauge1_cy, gauge2_cy]) {
        for (s = [-1, 1])
            translate([gauge_x + s*gauge_hole_dx/2, cy - gauge_hole_dy, pb - eps]) {
                cylinder(d1 = gauge_pin_d + 1.4, d2 = gauge_pin_d, h = 0.7);
                cylinder(d = gauge_pin_d, h = gauge_pcb_back_z + gauge_retainer_t - pb);
                translate([0, 0, gauge_pcb_back_z + gauge_retainer_t - pb - eps])
                    cylinder(d1 = gauge_pin_d, d2 = gauge_pin_tip_d, h = gauge_pin_taper);
            }
        r0 = gauge_pcb_d/2 + gauge_lip_wall_gap;     // wall inner face
        zl = gauge_pcb_back_z + gauge_lip_gap - gauge_lip_wall_gap;   // underside height at the wall
        translate([gauge_x, cy, 0]) {
            // wall, flared at the base
            rrect(-gauge_lip_w/2, gauge_lip_w/2, r0, r0 + gauge_lip_t, pb - eps, zl + gauge_lip_reach + 0.6);
            hull() {
                rrect(-gauge_lip_w/2 - 1, gauge_lip_w/2 + 1, r0, r0 + gauge_lip_t + 1.5, pb - eps, pb);
                rrect(-gauge_lip_w/2, gauge_lip_w/2, r0, r0 + gauge_lip_t, pb + 1.5, pb + 1.6);
            }
            // lip: 45-degree underside (prints without support), sits over the PCB's back corner
            hull() {
                rrect(-gauge_lip_w/2, gauge_lip_w/2, r0 - 0.01, r0 + 0.5, zl, zl + 0.01);
                rrect(-gauge_lip_w/2, gauge_lip_w/2, r0 - gauge_lip_reach, r0 + 0.5, zl + gauge_lip_reach, zl + gauge_lip_reach + 0.6);
            }
        }
    }
}

// ---- things that REMOVE material ------------------------------
module cuts() {
    // Presto screen window (through) — the glass sits in it, which
    // also locates the plate side to side
    rrect(screen_cx - glass_w/2 - window_clear, screen_cx + glass_w/2 + window_clear,
          screen_cy - glass_h/2 - window_clear, screen_cy + glass_h/2 + window_clear,
          -1, pb + 1, r = 1);
    // decorative screen-frame counterbore on the front (brass frame look)
    rrect(screen_cx - 52, screen_cx + 52, screen_cy - 52, screen_cy + 52, -1, 1.2, r = 3);

    // gauge windows + bezel counterbores + ribbon-clamp relief (back)
    for (cy = [gauge1_cy, gauge2_cy]) {
        translate([gauge_x, cy, -1]) cylinder(d = gauge_window_d, h = pb + 2);
        translate([gauge_x, cy, -1]) cylinder(d = gauge_bezel_d, h = 2.2);
        rrect(gauge_x - 8.5, gauge_x + 8.5, cy - 19.5, cy - 15.5, pb - 0.6, pb + 1);   // VERIFY position
    }

    // knob: collar bore, front bezel counterbore, anti-rotation notch (back)
    translate([knob_x, knob_y, -1]) cylinder(d = enc_bore_d, h = pb + 2);
    translate([knob_x, knob_y, -1]) cylinder(d = knob_bezel_d, h = 2.2);
    translate([knob_x, knob_y, 0]) rotate([0, 0, enc_tab_angle])
        rrect(3.2, enc_tab_r + enc_notch_out, -1.0, 1.0, pb - 0.8, pb + 1);

    // speaker grille: horizontal slots, centred on the speaker cone
    for (i = [0 : grille_slots - 1])
        stadium(grille_cx, grille_cy + (i - (grille_slots - 1)/2) * grille_pitch,
                grille_w, grille_slot_h, -1, pb + 1);

    // toggles + pilot lights
    for (i = [0 : len(switch_xs) - 1])
        translate([switch_xs[i], switch_row_y, -1])
            cylinder(d = (switch_kind[i] == "toggle") ? toggle_hole_d : pilot_hole_d, h = pb + 2);

    // brass nameplate recess (front)
    rrect(plate_rec_cx - plate_rec_w/2, plate_rec_cx + plate_rec_w/2,
          plate_rec_cy - plate_rec_h/2, plate_rec_cy + plate_rec_h/2, -1, plate_rec_d, r = 0.5);

    // corner screws
    for (p = panel_screw_points())
        translate([p[0], p[1], -1]) cylinder(d = screw_clear_d, h = pb + 2);

    // heat-set insert holes: shelf posts and strap bosses
    for (p = shelf_post_pts)
        translate([p[0], p[1], shelf_z - insert_depth]) cylinder(d = insert_d, h = insert_depth + 1);
    for (p = strap_boss_pts)
        translate([p[0], p[1], spk_back_z - strap_preload - insert_depth]) cylinder(d = insert_d, h = insert_depth + 1);
}

// labels as seen from the FRONT, from Z = z0 to Z = label_depth
module labels_front_view(z0 = 0) {
    for (i = [0 : len(switch_xs) - 1])
        translate([switch_xs[i], label_y, z0])
            linear_extrude(height = label_depth - z0) {
                // front-view coordinates, so the text is written normally
                text(label_texts[i], size = label_cap / label_k, font = label_font,
                     halign = "center", valign = "center", spacing = label_track);
                if (label_line2[i] != "")
                    translate([0, -label_line_pitch])
                        text(label_line2[i], size = label_cap / label_k, font = label_font,
                             halign = "center", valign = "center", spacing = label_track);
            }
}

module panel_front_view() {
    difference() {
        union() { panel_blank(); back_features(); }
        cuts();
        labels_front_view(z0 = -1);   // label pockets in the front face
    }
}

// THE panel, in the panel-local frame (mirrored once — see common.scad)
module panel() { front_frame() panel_front_view(); }
// the cream inlay that fills the pockets exactly
module panel_labels() { front_frame() labels_front_view(); }

if (PART == "panel")  panel();
if (PART == "labels") panel_labels();
