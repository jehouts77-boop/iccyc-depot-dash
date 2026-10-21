# chime.py - when to chime, and the strike count
#
# Modes (config "chime" / "mode"):
#   off          never
#   hourly       the chime sound on the hour
#   hourly_count the chime sound on the hour, then one strike per hour (1-12)
#   half_hourly  the chime sound on the hour, one strike on the half hour
#
# Muted by: the CHIME switch, WIFE MODE, quiet hours, or mode "off".
# The Presto only decides; the Controls board plays the clip (protocol 0x30-0x33).

import time
import timeutil

FIRE_WINDOW_S = 20        # fire within the first 20 s of the minute (not on a late boot)
DONE_TIMEOUT_MS = 6000    # if a clip's "done" never arrives, carry on anyway


class Chime:
    def __init__(self):
        self.last_slot = None     # (day, hour, minute) already chimed
        self.queue = []           # clips still to play: [clip, ...]
        self.waiting = False      # a clip is playing; wait for its "done"
        self.wait_since = 0
        self.next_at = None       # ticks_ms when the next queued clip may start
        self.fired = 0            # diagnostics
        self.muted_reason = ""

    def muted(self, cfg, t, chime_switch_on, wife_mode):
        c = cfg["chime"]
        if c["mode"] == "off":
            return "MODE OFF"
        if not chime_switch_on:
            return "CHIME SWITCH"
        if wife_mode:
            return "WIFE MODE"
        if timeutil.in_window(t, c["quiet_start"], c["quiet_end"]):
            return "QUIET HOURS"
        return ""

    def plan(self, cfg, t):
        """Clips for local time t, or [] if this minute isn't a chime minute."""
        c = cfg["chime"]
        sounds = cfg["chime_sounds"]
        main = sounds.get(c["sound"], 0)
        strike = c.get("strike_clip", main)       # the single click-clack (config)
        minute = t[4]
        if minute == 0:
            clips = [main]
            if c["mode"] == "hourly_count":
                h = t[3] % 12 or 12
                clips += [strike] * h
            return clips
        if minute == 30 and c["mode"] == "half_hourly":
            return [strike]
        return []

    def tick(self, cfg, t, controls, chime_switch_on, wife_mode, done_events):
        """Call a few times a second with local time t. Plays through controls."""
        now = time.ticks_ms()
        c = cfg["chime"]
        vol = cfg["volume_steps"][max(0, min(c["volume_step"], len(cfg["volume_steps"]) - 1))]
        if done_events and self.waiting:
            self.waiting = False
            self.next_at = time.ticks_add(now, c.get("strike_gap_ms", 700))
        if self.waiting and time.ticks_diff(now, self.wait_since) > DONE_TIMEOUT_MS:
            self.waiting = False
            self.next_at = now
        slot = (t[2], t[3], t[4])
        if t[5] < FIRE_WINDOW_S and slot != self.last_slot:
            clips = self.plan(cfg, t)
            if clips:
                self.last_slot = slot
                self.muted_reason = self.muted(cfg, t, chime_switch_on, wife_mode)
                if not self.muted_reason:
                    self.queue = clips
                    self.next_at = now
                    self.fired += 1
        # a switch flipped mid-strike stops the rest
        if self.queue and self.muted(cfg, t, chime_switch_on, wife_mode) not in ("", "QUIET HOURS"):
            self.queue = []
            controls.stop()
        if self.queue and not self.waiting and self.next_at is not None \
                and time.ticks_diff(now, self.next_at) >= 0:
            clip = self.queue.pop(0)
            if controls.play(clip, vol):
                self.waiting = True
                self.wait_since = now
            else:
                self.queue = []           # board missing: give up this chime

    def test(self, cfg, controls):
        """Play the chime sound once now (Settings screen)."""
        c = cfg["chime"]
        vol = cfg["volume_steps"][c["volume_step"]]
        controls.play(cfg["chime_sounds"].get(c["sound"], 0), vol)
