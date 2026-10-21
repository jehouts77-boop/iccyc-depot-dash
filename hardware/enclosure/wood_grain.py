"""wood_grain.py - ICCYC Control Console: cut a wood-grain texture into the
outside of the body's top and both sides (rev E, 2026-10-09).

The .scad files stay the parametric source. This script takes the plain body
STL that body.scad exports and cuts shallow grain grooves into three outside
faces, so the grain is part of the print (wood PLA; a gel stain wiped on and
off darkens the grooves).

    python wood_grain.py body_plain.stl body_grain.stl [--seed N]

Needs: numpy, trimesh, manifold3d   (pip install numpy trimesh manifold3d)

Grain direction (Jason, 2026-10-09): left to right on the top, front to back
on the sides, as if the box were made of boards joined at the corners.

Every number that matters is at the top. Coordinates are body.scad's: X left/
right, Y up, Z depth (front face Z = 0, back edge Z = case_d).
"""
import sys
import numpy as np
import trimesh
import manifold3d as m3d

# ---- case (must match common.scad) ----
CASE_W, CASE_H, CASE_D, CORNER_R = 230.0, 210.0, 95.0, 10.0

# ---- grain ----
# Printed back-down, the print's vertical is Z: on the TOP the grooves lie
# across the layers (their flanks are overhangs - keep "along v" under ~45
# deg); on the SIDES they run up the layers (no overhang).
DEPTH_MAX   = 0.50   # deepest groove, mm (wall is 3.2)
DEPTH_MIN   = 0.20   # shallowest groove that still counts as a line
SPACING     = 3.6    # average distance between grain lines, mm
HALF_W      = 1.10   # groove half-width, mm (sets the flank slope: kept under 45 deg)
WAVE        = 0.9    # how much the lines wander (in line spacings)
GRID        = 0.35   # mesh resolution of the textured skin, mm
EDGE_FADE   = 3.0    # grain fades out this far before a rounded edge / the front or back rim
LIFT        = 0.05   # cutter floats this far above the flat face (no coplanar faces)
SEED        = 7
MAX_SLOPE   = 40.0   # degrees from the face, any direction: groove flanks are clipped to this

FLAT_X = CASE_W / 2 - CORNER_R   # flat part of the top runs |x| <= 105
FLAT_Y = CASE_H / 2 - CORNER_R   # flat part of each side runs |y| <= 95


# ---------- noise ----------
def _grad_noise(rng, x, y):
    """2D gradient (Perlin-style) noise, vectorised. Returns ~[-0.7, 0.7]."""
    perm = rng.permutation(256)
    perm = np.concatenate([perm, perm])
    ang = rng.uniform(0, 2 * np.pi, 256)
    gx, gy = np.cos(ang), np.sin(ang)
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    xf, yf = x - xi, y - yi

    def dot(ix, iy, dx, dy):
        h = perm[(perm[ix & 255] + iy) & 255]
        return gx[h] * dx + gy[h] * dy

    def fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    n00 = dot(xi, yi, xf, yf)
    n10 = dot(xi + 1, yi, xf - 1, yf)
    n01 = dot(xi, yi + 1, xf, yf - 1)
    n11 = dot(xi + 1, yi + 1, xf - 1, yf - 1)
    u, v = fade(xf), fade(yf)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def fbm(rng_seed, x, y, octaves=4):
    out = np.zeros_like(x)
    amp, freq = 1.0, 1.0
    for o in range(octaves):
        out += amp * _grad_noise(np.random.default_rng(rng_seed + o), x * freq, y * freq)
        amp *= 0.5
        freq *= 2.0
    return out


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ---------- grain depth field ----------
def grain_depth(u, v, seed, u_len, u_mid, v_mid):
    """Groove depth (mm, >= 0) at along-grain u and across-grain v (mm).
    Lines run roughly along u, wander, bunch and spread like flat-sawn
    boards, with one long, low cathedral arch."""
    # slow wander of the lines, plus a low arch centred on the face
    # neighbouring lines move together (large v scale), with a little
    # independent wobble on top, so the lines stay roughly parallel
    wander = WAVE * fbm(seed, u / 80.0, v / 160.0, 3) + 0.22 * fbm(seed + 5, u / 35.0, v / 40.0, 2)
    uc = (u - u_mid) / u_len                            # -0.5..0.5 along the face
    arch = 1.4 * np.exp(-((v - v_mid) / 45.0) ** 2) * np.cos(np.pi * uc) ** 2
    # spacing varies across the board (tighter and looser growth rings)
    spacing = SPACING * (1.0 + 0.35 * fbm(seed + 11, v / 25.0, u / 200.0, 2))
    phase = v / spacing + wander + arch
    line = np.round(phase)
    t = phase - line                                   # -0.5..0.5, 0 on a line
    hw = HALF_W / spacing                              # half-width in phase units
    prof = np.where(np.abs(t) < hw, 0.5 * (1 + np.cos(np.pi * t / hw)), 0.0)
    # each line has its own depth; some lines fade in and out along their length
    rng = np.random.default_rng(seed + 23)
    table = rng.uniform(0, 1, 4096)
    per_line = table[(line.astype(int) % 4096)]
    along = 0.5 + 0.5 * fbm(seed + 31, u / 45.0, line * 0.37, 2) * 1.4
    strength = np.clip(per_line * 0.6 + along * 0.6, 0, 1)
    depth = DEPTH_MIN + (DEPTH_MAX - DEPTH_MIN) * strength
    depth = np.where(strength < 0.25, 0.0, depth)      # gaps: not every line runs full length
    return prof * depth


# ---------- height-field cutter ----------
def heightfield_solid(nu, nv, du, dv, h_top, depth, lift, to3d):
    """Closed solid whose bottom surface follows depth (nu x nv grid) and
    whose top is flat at h_top. Built in local (a, b, h) coordinates and
    mapped to 3D by to3d(a, b, h) -> (x, y, z). h grows OUTWARD."""
    a = np.arange(nu) * du
    b = np.arange(nv) * dv
    A, B = np.meshgrid(a, b, indexing="ij")
    H = lift - depth                                  # bottom surface (below the face where depth > lift)
    bot = np.stack([A, B, H], -1).reshape(-1, 3)
    top = np.stack([A, B, np.full_like(A, h_top)], -1).reshape(-1, 3)
    verts = np.vstack([bot, top])
    N = nu * nv
    idx = np.arange(N).reshape(nu, nv)
    i0, i1 = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel()
    i2, i3 = idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    # bottom faces outward = -h ; top faces +h
    tri_bot = np.concatenate([np.stack([i0, i2, i1], 1), np.stack([i0, i3, i2], 1)])
    tri_top = np.concatenate([np.stack([i0, i1, i2], 1), np.stack([i0, i2, i3], 1)]) + N
    # side walls around the border
    ring = np.concatenate([idx[:, 0], idx[-1, 1:], idx[-2::-1, -1], idx[0, -2:0:-1]])
    r0, r1 = ring, np.roll(ring, -1)
    walls = np.concatenate([np.stack([r0, r1, r1 + N], 1), np.stack([r0, r1 + N, r0 + N], 1)])
    tris = np.vstack([tri_bot, tri_top, walls])
    x, y, z = to3d(verts[:, 0], verts[:, 1], verts[:, 2])
    v3 = np.stack([x, y, z], 1).astype(np.float32)
    mesh = trimesh.Trimesh(v3, tris, process=False)
    if mesh.volume < 0:
        mesh.invert()
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                                 tri_verts=np.asarray(mesh.faces, np.uint32)))


def face_field(u0, u1, v0, v1, fade_u, fade_v, seed):
    nu = int(round((u1 - u0) / GRID)) + 1
    nv = int(round((v1 - v0) / GRID)) + 1
    du, dv = (u1 - u0) / (nu - 1), (v1 - v0) / (nv - 1)
    U, V = np.meshgrid(u0 + np.arange(nu) * du, v0 + np.arange(nv) * dv, indexing="ij")
    d = grain_depth(U, V, seed, (u1 - u0), (u0 + u1) / 2, (v0 + v1) / 2)
    w = 1.0
    if fade_u:
        w = w * smoothstep(u0, u0 + EDGE_FADE, U) * smoothstep(u1, u1 - EDGE_FADE, U)
    if fade_v:
        w = w * smoothstep(v0, v0 + EDGE_FADE, V) * smoothstep(v1, v1 - EDGE_FADE, V)
    return limit_slope(d * w, du, dv, MAX_SLOPE), nu, nv, du, dv


def limit_slope(d, du, dv, deg):
    """Clip groove flanks to `deg` from the face in both grid directions
    (two-pass running minimum: depth may only rise tan(deg) per mm)."""
    k = np.tan(np.radians(deg))
    for axis, step in ((0, du), (1, dv)):
        a = np.moveaxis(d, axis, 0).copy()
        for i in range(1, a.shape[0]):
            a[i] = np.minimum(a[i], a[i - 1] + k * step)
        for i in range(a.shape[0] - 2, -1, -1):
            a[i] = np.minimum(a[i], a[i + 1] + k * step)
        d = np.moveaxis(a, 0, axis)
    return d


def slope_check(d, du, dv, label):
    gu = np.abs(np.diff(d, axis=0)) / du
    gv = np.abs(np.diff(d, axis=1)) / dv
    print("%s: grid %s, deepest %.2f mm, steepest flank along u %.0f deg, along v %.0f deg (from the face)"
          % (label, d.shape, d.max(), np.degrees(np.arctan(gu.max())), np.degrees(np.arctan(gv.max()))))


def main():
    src, dst = sys.argv[1], sys.argv[2]
    seed = SEED
    if "--seed" in sys.argv:
        seed = int(sys.argv[sys.argv.index("--seed") + 1])
    body = trimesh.load(src)
    body.merge_vertices()
    man = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(body.vertices, np.float32),
                                tri_verts=np.asarray(body.faces, np.uint32)))
    cutters = []

    # TOP: y = +CASE_H/2, grain along x (u = x), across = z (v)
    d, nu, nv, du, dv = face_field(-FLAT_X, FLAT_X, 0.0, CASE_D, True, True, seed)
    slope_check(d, du, dv, "top")
    yt = CASE_H / 2
    cutters.append(heightfield_solid(nu, nv, du, dv, 2.0, d, LIFT,
                                     lambda a, b, h: (-FLAT_X + a, yt + h, b)))

    # SIDES: x = -/+CASE_W/2, grain along z (u = z), across = y (v)
    for sgn, sseed in ((+1, seed + 101), (-1, seed + 202)):
        d, nu, nv, du, dv = face_field(0.0, CASE_D, -FLAT_Y, FLAT_Y, True, True, sseed)
        slope_check(d, du, dv, "side %+d" % sgn)
        xs = sgn * CASE_W / 2
        cutters.append(heightfield_solid(nu, nv, du, dv, 2.0, d, LIFT,
                                         lambda a, b, h, xs=xs, sgn=sgn: (xs + sgn * h, -FLAT_Y + b, a)))

    for c in cutters:
        man = man - c
    out = man.to_mesh()
    res = trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts, process=True)
    print("result: watertight %s, volume %.0f mm3 (plain %.0f), %d triangles"
          % (res.is_watertight, res.volume, body.volume, len(res.faces)))
    res.export(dst)


if __name__ == "__main__":
    main()
