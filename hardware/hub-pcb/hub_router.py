# ICCYC hub PCB - a small 2-layer grid router used by hub_pcb.py (2026-10-11).
#
# Why this exists: the usual free auto-router (Freerouting) can't be downloaded into Claude's workspace, so
# hub_pcb.py lays its own copper with this. It is deterministic: the same placement always gives the same copper.
# KiCad's own design-rule check (run by hub_pcb.py afterwards) is the independent judge of the result.
#
# How it works, in plain words:
#   - The board is cut into a 0.1 mm grid, one grid per copper layer (top = F.Cu, bottom = B.Cu).
#   - Every pad is "painted" into both grids with its net's number (through-hole pads are copper on both faces).
#   - Each connection is found with A* (a shortest-path search) from the copper already belonging to that net to
#     the next pad, moving in 8 directions, never closer to other nets' copper than the clearance, never closer
#     to the board edge / slot / mounting holes than the edge clearance. Changing face costs a via.
#   - The found path is painted in, so later connections route around it. Nets that fail are moved to the front
#     and everything is routed again ("rip-up and retry").
import heapq, math
import numpy as np
from scipy import ndimage
import pcbnew

RES = 0.1                 # grid step, mm
CLR = 0.25                # trace-to-other-copper clearance used while routing (OSH Park minimum is 0.1524)
EDGE = 0.5                # copper to board edge / slot / mounting hole
VIA_D, VIA_DRILL = 0.8, 0.4
VIA_COST = 35.0           # a via costs as much as 3.5 mm of trace
TURN_COST = 0.6
DIRS = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

class Router:
    def __init__(self, board, W, H, kc, jv, outside_fn):
        self.b, self.W, self.H, self.kc, self.jv = board, W, H, kc, jv
        self.nx, self.ny = int(round(W/RES)) + 1, int(round(H/RES)) + 1
        self.owner = [np.full((self.ny, self.nx), -1, np.int32) for _ in (0, 1)]
        ys, xs = np.mgrid[0:self.ny, 0:self.nx]
        self.X, self.Y = xs*RES, ys*RES
        out = outside_fn(self.X, self.Y)                       # True where there is no board (edge, slot, holes)
        self.d_out = ndimage.distance_transform_edt(~out)*RES
        self.netid, self.netname = {}, []
        self.padcells = {}                                     # (ref, num) -> list of (iy, ix)
        self.segs = {}                                         # net -> list of (layer, (x0,y0), (x1,y1), w)
        self.vias = {}                                         # net -> list of (x, y)
        self.padinfo = {}
        self.last_cells = []

    def nid(self, net):
        if net not in self.netid: self.netid[net] = len(self.netname); self.netname.append(net)
        return self.netid[net]

    def add_pad(self, ref, num, pad, net):
        n = self.nid(net)
        bb = pad.GetBoundingBox()
        (x0, y1), (x1, y0) = self.jv(bb.GetOrigin()), self.jv(bb.GetEnd())
        cells = []
        for iy in range(max(0, int(y0/RES) - 1), min(self.ny, int(y1/RES) + 2)):
            for ix in range(max(0, int(x0/RES) - 1), min(self.nx, int(x1/RES) + 2)):
                if pad.HitTest(self.kc(ix*RES, iy*RES), 0):
                    cells.append((iy, ix))
                    for L in (0, 1): self.owner[L][iy, ix] = n
        self.padcells[(ref, num)] = cells
        cx, cy = self.jv(pad.GetPosition())
        self.padinfo[(ref, num)] = (cx, cy, net)

    def paint_seg(self, L, a, b, w, n):
        (x0, y0), (x1, y1) = a, b
        r = w/2
        ix0, ix1 = max(0, int((min(x0, x1) - r)/RES) - 1), min(self.nx, int((max(x0, x1) + r)/RES) + 2)
        iy0, iy1 = max(0, int((min(y0, y1) - r)/RES) - 1), min(self.ny, int((max(y0, y1) + r)/RES) + 2)
        X, Y = self.X[iy0:iy1, ix0:ix1], self.Y[iy0:iy1, ix0:ix1]
        dx, dy = x1 - x0, y1 - y0; l2 = dx*dx + dy*dy
        t = np.clip(((X - x0)*dx + (Y - y0)*dy)/l2, 0, 1) if l2 > 0 else 0
        d = np.hypot(X - (x0 + t*dx), Y - (y0 + t*dy))
        o = self.owner[L][iy0:iy1, ix0:ix1]
        o[(d <= r) & (o == -1)] = n
        ys, xs = np.nonzero(d <= r)
        self.last_cells.extend((L, int(a) + iy0, int(b) + ix0) for a, b in zip(ys, xs))

    def paint_via(self, x, y, n):
        for L in (0, 1): self.paint_seg(L, (x, y), (x, y), VIA_D, n)

    def route_conn(self, net, w, tree_cells, target_key, bot_cost):
        n = self.netid[net]
        free, dist = [], []
        for L in (0, 1):
            other = (self.owner[L] >= 0) & (self.owner[L] != n)
            d = ndimage.distance_transform_edt(~other)*RES
            dist.append(d)
            free.append((d > w/2 + CLR + RES*0.71) & (self.d_out > w/2 + EDGE))
        via_ok = (dist[0] > VIA_D/2 + CLR + RES*0.71) & (dist[1] > VIA_D/2 + CLR + RES*0.71) & (self.d_out > VIA_D/2 + EDGE)
        tgt = set(self.padcells[target_key])
        tx, ty, _ = self.padinfo[target_key]
        tix, tiy = tx/RES, ty/RES
        def h(iy, ix):
            dx, dy = abs(ix - tix), abs(iy - tiy)
            return (max(dx, dy) + (math.sqrt(2) - 1)*min(dx, dy))
        INF = 1e18
        g = np.full((2, self.ny, self.nx), INF)
        par = {}
        heap = []
        for (L, iy, ix) in tree_cells:
            if free[L][iy, ix] or (iy, ix) in self.padcells_all_of(n):
                g[L, iy, ix] = 0; heapq.heappush(heap, (h(iy, ix), 0.0, L, iy, ix, -1)); par[(L, iy, ix)] = None
        cost_layer = (1.0, bot_cost)
        found = None
        while heap:
            f, gc, L, iy, ix, din = heapq.heappop(heap)
            if gc > g[L, iy, ix]: continue
            if (iy, ix) in tgt: found = (L, iy, ix); break
            for k, (dx, dy) in enumerate(DIRS):
                jx, jy = ix + dx, iy + dy
                if not (0 <= jx < self.nx and 0 <= jy < self.ny): continue
                if not (free[L][jy, jx] or (jy, jx) in tgt): continue
                if dx and dy and not (free[L][iy, jx] or free[L][jy, ix]): continue
                step = (1.41421356 if dx and dy else 1.0)*cost_layer[L]
                if din >= 0 and din != k: step += TURN_COST
                ng = gc + step
                if ng < g[L, jy, jx]:
                    g[L, jy, jx] = ng; par[(L, jy, jx)] = (L, iy, ix)
                    heapq.heappush(heap, (ng + h(jy, jx), ng, L, jy, jx, k))
            if via_ok[iy, ix]:
                M = 1 - L; ng = gc + VIA_COST
                if ng < g[M, iy, ix] and free[M][iy, ix]:
                    g[M, iy, ix] = ng; par[(M, iy, ix)] = (L, iy, ix)
                    heapq.heappush(heap, (ng + h(iy, ix), ng, M, iy, ix, -1))
        if not found: return None
        path = [found]
        while par[path[-1]] is not None: path.append(par[path[-1]])
        return path[::-1]

    _pc_cache = None
    def padcells_all_of(self, n):
        return self._own_pad_cells.get(n, set())

    def route_net(self, net, keys, w, bot_cost):
        """Connect all pads `keys` of `net` (Prim order). Returns list of failed pad keys."""
        n = self.nid(net)
        self.segs.setdefault(net, []); self.vias.setdefault(net, [])
        rem = list(keys)
        start = rem.pop(0)
        tree = {(L, iy, ix) for (iy, ix) in self.padcells[start] for L in (0, 1)}
        done = [start]; failed = []
        while rem:
            # next pad: the one nearest to anything already connected
            def dmin(k):
                x, y, _ = self.padinfo[k]
                return min(math.hypot(x - self.padinfo[d][0], y - self.padinfo[d][1]) for d in done)
            rem.sort(key=dmin)
            k = rem.pop(0)
            path = self.route_conn(net, w, tree, k, bot_cost)
            if path is None: failed.append(k); continue
            self.last_cells = []
            self._emit(net, n, w, path, start_tree=tree, target=k)
            tree.update(self.last_cells)                       # the new trace / vias join the tree
            for (iy, ix) in self.padcells[k]:
                for L in (0, 1): tree.add((L, iy, ix))
            done.append(k)
        return failed

    def _emit(self, net, n, w, path, start_tree, target):
        # split into runs on one layer; layer changes are vias
        pts = [(L, ix*RES, iy*RES) for (L, iy, ix) in path]
        # snap the start onto existing copper's centre (a pad centre, or the nearest point on a trace)
        L0, x0, y0 = pts[0]
        snap = self._snap(net, L0, x0, y0)
        if snap: pts.insert(0, (L0, snap[0], snap[1]))
        tx, ty, _ = self.padinfo[target]
        pts.append((pts[-1][0], tx, ty))
        runs, cur = [], [pts[0]]
        for p in pts[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur); self.vias[net].append((p[1], p[2])); self.paint_via(p[1], p[2], n); cur = [p]
            else: cur.append(p)
        runs.append(cur)
        for run in runs:
            L = run[0][0]
            simp = [run[0]]
            for i in range(1, len(run) - 1):
                a, b, c = simp[-1], run[i], run[i+1]
                if abs((b[1]-a[1])*(c[2]-a[2]) - (b[2]-a[2])*(c[1]-a[1])) > 1e-9: simp.append(b)
            if len(run) > 1: simp.append(run[-1])
            for a, b in zip(simp, simp[1:]):
                if math.hypot(b[1]-a[1], b[2]-a[2]) < 1e-6: continue
                self.segs[net].append((L, (a[1], a[2]), (b[1], b[2]), w))
                self.paint_seg(L, (a[1], a[2]), (b[1], b[2]), w, n)

    def _snap(self, net, L, x, y):
        best, bd = None, 0.6
        for (ref, num), (px, py, pn) in self.padinfo.items():
            if pn == net and math.hypot(px - x, py - y) < 1.2 and (int(round(y/RES)), int(round(x/RES))) in set(self.padcells[(ref, num)]):
                return (px, py)
        for (SL, a, b, w) in self.segs.get(net, []):
            if SL != L: continue
            dx, dy = b[0]-a[0], b[1]-a[1]; l2 = dx*dx + dy*dy
            t = 0 if l2 == 0 else max(0, min(1, ((x-a[0])*dx + (y-a[1])*dy)/l2))
            qx, qy = a[0] + t*dx, a[1] + t*dy
            d = math.hypot(qx - x, qy - y)
            if d < bd: bd, best = d, (qx, qy)
        for (vx, vy) in self.vias.get(net, []):
            d = math.hypot(vx - x, vy - y)
            if d < bd: bd, best = d, (vx, vy)
        return best

    def write(self, board, netcode):
        L_ID = (pcbnew.F_Cu, pcbnew.B_Cu)
        for net, segs in self.segs.items():
            for (L, a, b, w) in segs:
                t = pcbnew.PCB_TRACK(board); t.SetStart(self.kc(*a)); t.SetEnd(self.kc(*b))
                t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(L_ID[L]); t.SetNet(netcode(net)); board.Add(t)
            for (x, y) in self.vias[net]:
                v = pcbnew.PCB_VIA(board); v.SetPosition(self.kc(x, y)); v.SetWidth(pcbnew.FromMM(VIA_D))
                v.SetDrill(pcbnew.FromMM(VIA_DRILL)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(netcode(net)); board.Add(v)


def route_all(board, W, H, kc, jv, outside_fn, pad_objs, widths, order, bot_cost=1.6, tries=6, log=print, only=None):
    """pad_objs: {(ref, num): (pad, net)}. widths: net -> mm. order: list of nets (first routed first)."""
    order = list(order)
    for attempt in range(tries):
        r = Router(board, W, H, kc, jv, outside_fn)
        for (ref, num), (pad, net) in pad_objs.items(): r.add_pad(ref, num, pad, net)
        r._own_pad_cells = {}
        for (ref, num), cells in r.padcells.items():
            r._own_pad_cells.setdefault(r.netid[r.padinfo[(ref, num)][2]], set()).update(cells)
        failed = {}
        for net in order:
            keys = [k for k, (p, n) in pad_objs.items() if n == net and (only is None or only(net, k))]
            if len(keys) < 2: continue
            f = r.route_net(net, keys, widths(net), 1.0 if net == "GND" else bot_cost)
            if f: failed[net] = f
        log(f"routing attempt {attempt+1}: {len(failed)} nets with unrouted pads" + (f" {failed}" if failed else ""))
        if not failed: return r, {}
        order = [n for n in order if n in failed] + [n for n in order if n not in failed]
    return r, failed
