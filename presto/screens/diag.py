# screens/diag.py - diagnostics (long-press the knob to open or close)
# Plain counters for when something misbehaves (Model 100 lesson: a line like
# "RAW 11 HIDDEN 11 USABLE 0" is what cracks a bug).

import gc
import time
import net
import timeutil
import ui as U
from screens.base import Screen

LINE_H = 17                  # was 18; 17 makes room for the ISS RADIO line (2026-10-14):
                             # with both boards and a slow GET the screen held exactly 20
MAX_W = U.W - 14             # a line wider than this is drawn smaller, not cut off


class Diag(Screen):
    key = "diag"
    title = "DIAGNOSTICS"
    short = "DIAG"

    def __init__(self):
        self.last = 0

    def lines(self, app):
        out = []
        for b in (app.gauges, app.controls):
            if b.present:
                out.append(("%s 0x%02X  fw %s  boot %d  restarts %d" %
                            (b.name.upper(), b.addr, b.fw, b.boot_id, b.restarts), "text"))
                out.append(("   beat %d loop %dms free %dKB fault %d err %d" %
                            (b.heartbeat(), b.loop_ms(), b.free_kb(), b.fault(), b.bus_errors),
                            "dim"))
            else:
                out.append(("%s 0x%02X  MISSING  (bus err %d)" % (b.name.upper(), b.addr,
                                                                   b.bus_errors), "red"))
        c = app.controls
        out.append(("KNOB %d  PRESS %d  LONG %d  SWITCHES %s" %
                    (c.knob_total, c.presses, c.long_presses, app.switch_text()), "text"))
        out.append(("AUDIO %s  CLIPS %d  DONE %d  CHIMES %d %s" %
                    (("idle", "PLAYING", "ERROR")[min(c.audio_state, 2)], c.clip_count,
                     c.done_count, app.chime.fired, app.chime.muted_reason), "text"))
        ssid, ip, rssi = net.info()
        out.append(("WIFI %s  %s" % (app.wifi_state.upper(), ssid or "(no network set)"),
                    "text"))
        out.append(("   IP %s  RSSI %s  DNS %s%s" % (     # DNS: see net.PUBLIC_DNS (2026-10-17)
            ip or "-", rssi if rssi is not None else "-", net.dns_server(),
            " (switched %d)" % net.dns_switches if net.dns_switches else ""), "dim"))
        out.append(("NTP %s  tries %d  fails %d" % (
            "OK" if timeutil.last_sync else "NOT YET", timeutil.sync_tries, timeutil.sync_fails),
            "text"))
        w = app.weather
        out.append(("WEATHER ok %d  fail %d  last %dms  %s" %
                    (w.ok, w.fails, w.last_ms, "OLD" if w.stale() else "fresh"),
                    "red" if w.last_error and w.fails and not w.ok else "text"))
        if w.last_error:
            out.append(("   " + w.last_error[:42], "dim"))
        t = app.local()
        out.append(("LOCAL %s %s  UTC OFFSET %+d" % (timeutil.date_line(t), timeutil.hhmmss(t),
                                                     timeutil.offset_s(time.time(),
                                                                       app.cfg["tz"]) // 3600),
                    "dim"))
        gc.collect()
        out.append(("PRESTO free %dKB  loop %dms  draw %dms" %
                    (gc.mem_free() // 1024, app.loop_ms, app.draw_ms), "text"))
        out.append(("   slowest loop %dms  %s  at %ds" %
                    (app.loop_max_ms, app.loop_max_what, app.loop_max_at), "dim"))
        tr = app.trains
        out.append(("TRAINS ok %d  fail %d  last %dms  on list %s" %
                    (tr.ok, tr.fails, tr.last_ms, "-" if tr.ids is None else len(tr.ids)),
                    "text"))
        pl = app.planes
        out.append(("PLANES ok %d  fail %d  last %dms  seen %s  via %s" %   # via: planes.FEEDS
                    (pl.ok, pl.fails, pl.last_ms, "-" if pl.list is None else len(pl.list),
                     pl.last_feed), "text"))
        li = app.listener
        out.append(("ISS RADIO " + li.status(), "text"))   # one line: the screen was full
        g = net.slow                              # where the slowest web request spent its time
        if g:
            out.append(("   slowest GET %dms  ...%s" % (g[0], g[8]), "dim"))
            out.append(("   dns %d con %d tls %d wait %d body %d  redir %d  %dB" % g[1:8], "dim"))
        al = app.almanac
        if al.day is not None:
            out.append(("SUN az %d el %d  %s  %s-%s  calc %dms" % (
                al.az, al.el, al.phase.upper(), al.hm(al.t["rise"]), al.hm(al.t["set"]),
                al.calc_ms), "dim"))
        ck = app.ring[0]
        out.append(("CLOCK sec %dms  max %dms" % (getattr(ck, "sec_ms", 0),
                                                 getattr(ck, "sec_max_ms", 0)), "dim"))
        out.append(("UPTIME %ds  UNIT %s  APP %s" %
                    (time.ticks_diff(time.ticks_ms(), app.started) // 1000,
                     app.cfg["unit"]["serial"], app.VERSION), "dim"))
        # trouble goes first, so it can never fall off the bottom of the list
        if app.ui.font_error:                  # smooth fonts not loaded: built-in font in use
            out.insert(0, (app.ui.font_error[:44], "red"))
        if app.cfg_error:
            out.insert(0, (app.cfg_error[:44], "red"))
        return out

    def draw(self, app):
        u = app.ui
        u.clear()
        u.header(self.title, app.clock_text(), plain=True)   # built-in font: see ui.py
        y = U.BODY_Y
        for s, colour in self.lines(app):
            if u.btext_w(s, 2) <= MAX_W:
                u.btext(s, 10, y, 2, colour)
            else:                              # too wide: smaller, so nothing is lost
                u.btext(s, 10, y + 4, 1, colour)
            y += LINE_H
        u.hint("LONG-PRESS THE KNOB TO GO BACK", plain=True)

    def tick(self, app, now):
        if time.ticks_diff(now, self.last) >= 1000:
            self.last = now
            return "full"
        return None

    def on_knob(self, app, n):
        return True           # knob does nothing here (keeps the counters on screen)

    def on_press(self, app):
        return True

    def on_touch(self, app, x, y):
        return True
