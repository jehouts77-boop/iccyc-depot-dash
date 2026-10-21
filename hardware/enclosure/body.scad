// ============================================================
// ICCYC Control Console — body + back plate (rev E, 2026-10-09; rev D 2026-10-01, roadmap 2.4)
// rev E (Jason, 2026-10-09): tilt 8° (was 12°) and a full-height
// panel (both in common.scad); the closed back wall is gone — the
// back is now a removable BLACK plate (PART = "back"), set
// back_inset into the wood body and held by 4 M3 screws into
// heat-set inserts in four corner shelves. The USB-C power socket
// moved from the back wall onto the plate.
// rev D6: each side web now hulls the whole boss, so the bottom
// bosses no longer start in mid-air (Bambu "floating regions"
// warning on rev D5). Boss and insert-hole positions unchanged.
// rev D5: the 4 corner insert holes follow insert_d in common.scad,
// now 4.2 mm (was 4.0; insert test strip 2026-10-07). Nothing else changed.
// ============================================================
// rev D text, kept for the record: "Plain rectangular tub, closed back (no separate back plate/snap
// tabs — the panel is the only thing you ever open)." rev E: open at both ends. Holds four
// screw bosses for the panel's corner screws, angled to the same
// 12° tilt as the panel via panel_place() so the two parts can
// never drift out of sync — change tilt_angle or panel size in
// common.scad and both re-derive automatically.
//
// This file should NOT need to change when panel hardware changes.
// If you're editing dimensions here for anything other than case_w/
// case_h/case_d/wall/tilt_angle, that dimension probably belongs on
// the panel instead.
//
// PRINT: back face down on the bed — i.e. flipped from how it is
// modelled here (the STL export in stl\ is already flipped).
// 0.2 mm layers, brim recommended (rev E: only the 3.2 mm rim
// touches the bed now — use an inner + outer brim). The corner
// shelves' undersides are short bridges between two walls.
// BACK PLATE (rev E): print outside face down (smooth / textured
// side out), no supports. Insert M3 inserts in the 4 corner
// shelves from the back; M3 x 8 screws. rev D gives the
// boss webs sloped undersides so they print without support; check
// in the slicer.
// ============================================================

include <common.scad>

PART = "body";    // body | back  (export each one to its own STL)

// rev D: the old 30 x 12 rear cable slot is gone. The only thing
// through the back wall is the panel-mount USB-C power socket
// (xiwai "2Pin with Nut"), low and centred (roadmap 2.3). Every
// board rides on the panel; one power lead crosses to it.
// rev E: on the back plate now (same place as seen from behind)
sock_cx    = 0;
sock_cy    = -(case_h/2) + 40;  // ~40 mm above the desk
sock_d     = 10.8;    // thread 10.6, double-D
sock_flats = 9.2;     // 9.0 across the flats
sock_rot   = 0;       // 0 = flats top and bottom. Which way the USB-C slot sits vs the flats: VERIFY

inner_w = case_w - 2*wall;
inner_h = case_h - 2*wall;
inner_r = corner_r - wall;
back_face_z = case_d - back_inset;          // plate's outside face
back_in_z   = back_face_z - back_t;         // plate's inside face = shelves' back face

// screw / insert centres for the back plate (body frame, X/Y)
function back_screw_pts() = [for (sx = [-1, 1], sy = [-1, 1])
    [sx*(inner_w/2 - back_screw_in), sy*(inner_h/2 - back_screw_in)]];

module body_shell() {
    difference() {
        rounded_box(case_w, case_h, case_d, corner_r);
        // rev E: hollow all the way through (open front, open back)
        translate([0, 0, -1])
            rounded_box(inner_w, inner_h, case_d + 2, inner_r);
    }
    back_shelves();

    // Panel mounting bosses — angled to the panel's tilt, positioned
    // exactly under the panel's own corner screw holes via the
    // shared panel_place() transform, so they can't drift out of
    // alignment with panel.scad.
    panel_place()
        for (p = panel_screw_points())
            translate([p[0], p[1], panel_thick])
                cylinder(d = screw_boss_d, h = screw_insert_depth);

    // rev D: webs tie each boss to its side wall and to the top or
    // bottom wall (the copy of rev C on disk had the bosses floating
    // in mid-air — the bug the plan doc says was fixed on 09-24).
    boss_webs();
}

// panel-local point -> body frame (same maths as panel_place)
// rev E: layout-frame Y (Y = 0 is panel_ext up the slope)
function to_body(X, Y, Z) = [X, panel_bottom_y + (Y + panel_ext)*cos(tilt_angle) - Z*sin(tilt_angle),
                             panel_front_inset + (Y + panel_ext)*sin(tilt_angle) + Z*cos(tilt_angle)];

web_t = 4;     // web thickness
gusset = 14;   // how much further back each web runs along the wall (sloped underside)
module boss_webs() {
    inner_x = case_w/2 - wall;
    inner_y = case_h/2 - wall;
    for (p = panel_screw_points()) {
        sx = sign(p[0]);
        // side web, in the panel frame (rotation is about X, so the side wall is still X = +-inner_x)
        // rev D6: the boss end of this hull is the whole boss (was a
        // 4 mm sliver ending 0.2 short of the boss's back face). The
        // boss's back face is tilted 12°, so its edge toward the panel
        // centre hung below every web — a floating island two layers
        // thick on the two bottom bosses (slicer warning 2026-10-08).
        // Now the boss's underside is part of the sloped gusset.
        panel_place() hull() {
            translate([p[0], p[1], panel_thick + 0.2]) cylinder(d = screw_boss_d + 0.02, h = screw_insert_depth - 0.2);  // +0.02: not coincident with the boss (keeps the mesh manifold)
            // the wall end runs further back than the boss -> sloped (gusset)
            // underside, so the web prints without support, back face down
            translate([sx > 0 ? inner_x - 0.5 : -inner_x - 1, p[1] - web_t/2, panel_thick + 0.2])
                cube([1.5, web_t, screw_insert_depth - 0.4 + gusset]);
        }
        // top / bottom web, in the body frame, kept behind the panel's back face
        sy = p[1] > panel_h_layout/2 ? 1 : -1;
        c  = to_body(p[0], p[1], panel_thick + screw_insert_depth/2);
        zr = sy > 0 ? [c[2] + 2, c[2] + 6 + gusset] : [c[2] - 1, c[2] + 3 + gusset];
        hull() {
            panel_place() translate([p[0] - web_t/2 - 0.13, p[1] - 0.5, panel_thick + 1.37]) cube([web_t + 0.26, 1, screw_insert_depth - 1.91]);
            translate([p[0] - web_t/2 - 0.13, sy > 0 ? inner_y - 0.5 : -inner_y - 1, zr[0]]) cube([web_t + 0.26, 1.5, zr[1] - zr[0]]);
        }
    }
}
eps2 = 0.01;

// rev E: corner shelves for the back plate's screws. Each is a plain
// right TRIANGLE in an inside corner, back_shelf_leg along each wall.
// Printed back-down, its underside (the face the plate sits on) is a
// bridge: every line across it runs from one wall to the other.
// (rev E first draft had square-ish shelves with free edges square to
// the walls; Bambu Studio flagged them as a "floating cantilever",
// 2026-10-09.)
module back_shelves() {
    for (sx = [-1, 1], sy = [-1, 1])
        intersection() {
            translate([0, 0, back_in_z - back_shelf_t])
                rounded_box(inner_w + 0.02, inner_h + 0.02, back_shelf_t, inner_r);   // stay inside the walls' rounded corners
            translate([sx*inner_w/2, sy*inner_h/2, back_in_z - back_shelf_t])
                linear_extrude(height = back_shelf_t)
                    polygon([[0, 0], [-sx*back_shelf_leg, 0], [0, -sy*back_shelf_leg]]);
        }
}

module body() {
    difference() {
        body_shell();
        panel_place()
            for (p = panel_screw_points())
                translate([p[0], p[1], panel_thick])
                    cylinder(d = screw_insert_d, h = screw_insert_depth + 0.5);
        // rev E: back-plate insert holes, from the back
        for (p = back_screw_pts())
            translate([p[0], p[1], back_in_z - insert_depth])
                cylinder(d = insert_d, h = insert_depth + 0.5);
    }
}

// rev E: the removable back plate, modelled in place (body frame)
module back_plate() {
    difference() {
        translate([0, 0, back_in_z])
            rounded_box(inner_w - 2*back_clear, inner_h - 2*back_clear, back_t, inner_r - back_clear);
        for (p = back_screw_pts())
            translate([p[0], p[1], back_in_z - 1]) cylinder(d = screw_clear_d, h = back_t + 2);
        // USB-C power socket (double-D), moved here from the old back wall
        translate([sock_cx, sock_cy, back_in_z - 1])
            rotate([0, 0, sock_rot])
                intersection() {
                    cylinder(d = sock_d, h = back_t + 2);
                    translate([-sock_d/2, -sock_flats/2, 0]) cube([sock_d, sock_flats, back_t + 2]);
                }
    }
}

if (PART == "body") body();
if (PART == "back") back_plate();

// ---- Uncomment to sanity-check panel fit against the body ----
// use <panel.scad>
// %panel_place() panel();
