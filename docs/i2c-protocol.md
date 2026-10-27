> Copy of the builder's working protocol doc, refreshed 2026-10-14. "Roadmap" numbers refer to the builder's own plan, not a file here.

# ICCYC Depot Dashboard — I2C Protocol v0.3

Created 2026-09-28 (roadmap step 1.2). This defines how the Presto talks to the two RP2040-Zero co-processors. Background is in `iccyc-depot-dashboard-plan.md`, and the proven link test is in the roadmap, 1.6 and 1.7.

**Status: v0.3 (2026-10-26): adds 0x23 LED_OTA_BRIGHT (Controls fw 0.5).** Before that v0.2 (2026-09-30). v0 approved 2026-09-28; v0.1 adds a BOOT_ID copy to the Controls input block; v0.2 adds READOUT_TEXT to each gauge block (see Change log). `controls_test.py` / `controls_presto_test.py` (roadmap 1.10) implement the Controls part. **2026-09-30: Gauges firmware v1.0 (`iccyc-depot-dash\coproc\gauges\main.py`) and the Presto driver (`iccyc-depot-dash\presto\coproc.py`) implement the full map — simulator-verified only, not yet run on hardware.** **2026-10-07: Gauges fw 1.1 and the Presto driver ran on hardware (M5 foundation desk test, passed): setup blocks, dial and compass, READOUT_TEXT, BACKLIGHT 0 / dimming, missing-board handling — confirmed by Jason, 0 bus errors.**

## The big idea, in plain words

Each co-processor is a **row of numbered mailbox slots** called *registers*. The Presto **writes** slots to give orders and **reads** slots to get news. The co-processors can't speak first. The Presto checks in about 50 times a second. This is the same "memory mode" `I2CTarget` setup that passed the 10-minute soak on 2026-09-28.

**The shaping rule:** co-processor firmware can only be updated with the panel off and a USB cable plugged in, so the co-processors stay **generic instruments**. Anything that might change later (what a gauge shows, how a light blinks, which chime plays, and whether it's muted) is sent from the Presto, which *can* update over the air. The test for each feature: *could this be changed with an OTA update?* If yes, it's a message, not something built into the co-processor.

## Five rules every register follows

1. **State, not commands.** The Presto writes *what it wants* ("Gauge I needle at 72"), not *what to do* ("move needle up 3"). If a write is ever lost, the next one fixes it, and writing the same state twice is harmless.
2. **Counters, not events.** Things that *happen* (a knob click, a button press, a chime request) are **8-bit counters** that go up by one each time. They wrap from 255 back to 0. The reader compares against the last value it saw, so nothing is missed if a poll comes late, and nothing is double-counted. The difference is computed as `(new - old) & 0xFF`.
3. **One group per transaction.** Anything that belongs together (a 2-byte value, a gauge's whole setup block, a clip number plus its "play" counter) is written in **one** `writeto_mem` call. The co-processor copies what it received only when the transaction ends (the `IRQ_END_WRITE` handler), so it never acts on a half-written group.
4. **The co-processors hold their last state.** If the Presto goes quiet (a crash, or a reboot after an update), needles, lights and switches reading stay as they were. Nothing times out on its own.
5. **After a co-processor restarts, the Presto re-sends everything.** Each co-processor picks a random `BOOT_ID` at power-up. When the Presto sees it change, it knows that board restarted and re-sends all its setup and state. **A restart also resets every counter to 0, so the Presto must check BOOT_ID before comparing counters** — otherwise the jump back to 0 looks like presses, clicks or switch changes (v0.1; see Controls 0x19).

## Bus basics

| Item | Value |
|---|---|
| Bus | Presto Qw/ST port = I2C0, SDA GP40 / SCL GP41. Nothing else on this bus (confirmed 2026-09-28). |
| Co-processor pins | I2C0 target on SDA GP0 / SCL GP1 (both boards) |
| Addresses | **0x10** = Gauges (Co-processor A), **0x11** = Controls (Co-processor B) |
| Speed | 100 kHz (proven). 400 kHz is optional, only if a future test shows it's needed. |
| Register addressing | 1-byte register address (`mem_addrsize=8`), up to 256 registers per board |
| Multi-byte numbers | little-endian (low byte first), signed 16-bit unless noted |
| Text | plain ASCII, padded with zero bytes. Byte **0xB0** is drawn as a degree sign (°). |

## Common header, both boards: 0x00–0x0F (read-only for the Presto)

| Reg | Name | Meaning |
|---|---|---|
| 0x00 | MAGIC | always 0xC5, so the Presto knows it's talking to our firmware |
| 0x01 | BOARD | the board's own address (0x10 or 0x11) |
| 0x02 | PROTO | protocol version, **0** for v0, v0.1 and v0.2 (both only add registers in reserved slots) |
| 0x03 | FW_MAJOR | co-processor firmware version, major |
| 0x04 | FW_MINOR | co-processor firmware version, minor |
| 0x05 | HEARTBEAT | counter, goes up about every 10 ms. If it stops changing, the board is frozen. |
| 0x06 | FLAGS | bit 0 = READY (setup finished); bit 1 = FAULT |
| 0x07 | FAULT | fault code (0 = none; codes listed per board below) |
| 0x08 | LOOP_MS | how long its last main loop / screen frame took, in ms (capped at 255) |
| 0x09 | FREE_KB | free memory in KB (capped at 255) |
| 0x0A | WRITES | counter of write transactions received (diagnostics) |
| 0x0B | BOOT_ID | random byte chosen at power-up (see rule 5) |
| 0x0C–0x0F | — | reserved, read as 0 |

---

## Gauges board (0x10)

### Board-wide: 0x10–0x1F (Presto writes)

| Reg | Name | Meaning |
|---|---|---|
| 0x10 | BACKLIGHT | 0–255, shared by both round screens. 0 = dark (used by the BACKLIGHT switch; DAY·NIGHT picks the level). |
| 0x11 | SWEEP | counter. Each time it changes, both needles do the full-scale "self-test" sweep. This also happens automatically at power-up. |
| 0x12–0x1F | — | reserved |

### Per-gauge blocks: Gauge I at **0x20**, Gauge II at **0x60** (64 bytes each)

Offsets below are from the block start. For example, Gauge II's LABEL is at 0x60 + 0x10 = 0x70.

**Setup** (written as one transaction whenever what the gauge shows changes):

| Offset | Size | Name | Meaning |
|---|---|---|---|
| +0x00 | 1 | STYLE | 0 = **dial** (270° sweep, min at lower-left, max at lower-right); 1 = **compass** (360°, N at top, letters N/E/S/W on the face; MIN/MAX ignored) |
| +0x01 | 1 | DECIMALS | how many decimal places the numbers carry (0–2). Example: 29.92 inHg is sent as 2992 with DECIMALS = 2. |
| +0x02 | 2 | MIN | dial minimum, scaled by DECIMALS |
| +0x04 | 2 | MAX | dial maximum, scaled by DECIMALS |
| +0x06 | 1 | MAJOR_TICKS | number of long tick marks, including both ends (for example 11 gives 0, 10, 20 … 100) |
| +0x07 | 1 | MINOR_TICKS | short ticks between each pair of long ones (0 = none) |
| +0x08 | 1 | SHOW | bit 0 = show the numeric readout; bit 1 = number the long ticks |
| +0x09 | 1 | GLIDE | needle damping. 0 = jump straight to the value; higher = slower, smoother glide. Default 40, to be tuned by eye in step 1.8. |
| +0x0A–0x0F | — | — | reserved |
| +0x10 | 16 | LABEL | text on the dial face, for example `OUTSIDE TEMP` (up to 16 characters) |
| +0x20 | 8 | UNITS | text after the readout, for example `°F` (sent as 0xB0 then `F`) |

**Readout text** *(v0.2, 2026-09-30)* (written whenever it changes, as its own 8-byte transaction):

| Offset | Size | Name | Meaning |
|---|---|---|---|
| +0x28 | 8 | READOUT_TEXT | if not empty, shown in the big readout **instead of** the number — e.g. a compass pointing where the wind comes from with `12 MPH` under it. Zero-padded; first byte 0 = show the number as usual. 0xB0 = degree sign. Needs SHOW bit 0. |

**Live value** (written whenever it changes, as its own transaction):

| Offset | Size | Name | Meaning |
|---|---|---|---|
| +0x30 | 2 | VALUE | where the needle should go, scaled by DECIMALS. For compass: degrees 0–359. The needle takes the short way round, so 350 → 10 passes through N. |

**Read-back** (co-processor writes; diagnostics):

| Offset | Size | Name | Meaning |
|---|---|---|---|
| +0x38 | 2 | SHOWN | where the needle actually is right now, mid-glide |

**Power-up defaults**, before the Presto sends anything:
- Dial style, 0–100, 11 long ticks, labels `GAUGE I` and `GAUGE II`, value 0.
- The startup sweep runs, then the needles rest at 0 until the Presto sends setup.

**Fault codes (0x07):** 1 = a screen failed to start, 2 = out of memory, 3 = bad setup values (for example MIN = MAX; the last good setup is kept).

---

## Controls board (0x11)

### Inputs: 0x10–0x1F (co-processor writes, Presto reads 0x10–0x19, 10 bytes, in one go about 50 times a second)

| Reg | Name | Meaning |
|---|---|---|
| 0x10 | ENC_COUNT | knob counter: +1 per click clockwise, −1 anticlockwise (wraps 0–255; difference computed as `(new-old)` as a signed byte) |
| 0x11 | BTN_DOWN_COUNT | +1 each time the knob button is pressed |
| 0x12 | BTN_UP_COUNT | +1 each time it's released |
| 0x13 | BTN_STATE | 1 while held down right now, 0 otherwise. The Presto times long presses itself. |
| 0x14 | SWITCHES | bit 0 CHIME, bit 1 DAY·NIGHT, bit 2 BACKLIGHT, bit 3 WIFE MODE (1 = the switch's "on" position; which way is up is VERIFY at assembly) |
| 0x15 | SWITCH_COUNT | +1 whenever any switch changes |
| 0x16 | AUDIO_STATE | 0 = idle, 1 = playing, 2 = error (clip missing or unreadable) |
| 0x17 | AUDIO_DONE | +1 each time a clip finishes (or is stopped) |
| 0x18 | CLIP_COUNT | how many clips are stored on the board |
| 0x19 | BOOT_ID_COPY | *(v0.1)* same value as header 0x0B. Read with every input poll: if it changed, the board restarted — take the new counter values as the starting point (don't count the jump), then re-send everything (rule 5). |
| 0x1A–0x1F | — | reserved |

Switches are debounced on the co-processor: a change only counts after it has held steady for 20 ms. The knob and button are debounced there too.

**The co-processor only reports switch positions; it doesn't act on them.** The Presto reads CHIME, WIFE MODE and the others and decides what to do: skip the chime, dim the screen, and so on. That keeps every behavior OTA-updatable.

### Pilot lights: 0x20–0x2F (Presto writes)

| Reg | Name | Meaning |
|---|---|---|
| 0x20 | LED_WIFI | 0 = off, 1 = on, 2 = slow blink (1 per second), 3 = fast blink (4 per second), 4 = slow pulse (gentle fade in and out) |
| 0x21 | LED_OTA | same choices as LED_WIFI |
| 0x22 | LED_BRIGHT | 0–255, the WiFi light (for example lower at night / WIFE MODE). Before v0.3: both lights |
| 0x23 | LED_OTA_BRIGHT | v0.3: 0–255, the OTA light (starts at 255). A fw 0.4-or-older board ignores it and uses 0x22 for both |
| 0x23–0x2F | — | reserved |

The blinking and fading run on the co-processor, so they stay steady even while the Presto is busy, for example downloading an update.

### Chime: 0x30–0x3F (Presto writes)

| Reg | Name | Meaning |
|---|---|---|
| 0x30 | CLIP | which stored clip to play (0 = first) |
| 0x31 | VOLUME | 0–255 (0 = silent). The Settings screen offers a few steps and maps them to this. |
| 0x32 | PLAY | counter. Each time it changes, play CLIP at VOLUME. **Write 0x30–0x32 as one transaction.** If a clip is already playing, it's replaced. |
| 0x33 | STOP | counter. Each time it changes, stop playing. |
| 0x34–0x3F | — | reserved |

**Fault codes (0x07):** 1 = audio amp / I2S failed to start, 2 = no clips found in flash, 3 = out of memory.

---

**Implementation notes (from 1.9 Part 2, 2026-09-30 — fw 0.3 `controls_test.py` implements the whole Controls map):**
- VOLUME is applied per chunk, so a write to 0x31 alone changes the volume of a clip **already playing**.
- AUDIO_DONE counts every clip that ends — finished, replaced by a new PLAY, or stopped — so the Presto can match it against the plays it sent.
- Clips are numbered in **alphabetical order** of the `.wav` names in `/clips`. A CLIP number ≥ CLIP_COUNT sets AUDIO_STATE = 2.
- The firmware must pad the end of each clip with a full I2S buffer of silence before stopping the sound chip, or the last ~¼ s is cut off.
- Test-only diagnostics use reserved chime registers 0x3C–0x3F (refills, worst refill gap ms, buffer ms, starved count). Not part of the protocol; drop or formalize in the real firmware.

**Implementation notes (Gauges fw 1.0 / 1.1, 2026-09-30 — simulator-verified; fw 1.1 confirmed on hardware 2026-10-07):**
- **GLIDE units:** glide time = GLIDE × 7.5 ms, so the default 40 = the 300 ms glide picked in 1.8a. 0 = jump.
- **BACKLIGHT:** 0 = both screens off (display-off command 28h); 1–255 = on, with the dial colours scaled to that brightness. Turning back on (29h) re-sends both whole screens, since needles kept moving while dark.
- **Readout** shows the VALUE the Presto sent (the number doesn't count up through the glide); the needle glides to it. Compass readout = degrees. Up to 8 characters, drawn at double size. SHOW bit 0 off hides it — the Presto uses that while a reading isn't available yet.
- **Setup checks:** STYLE ≤ 1, DECIMALS ≤ 2, MAJOR_TICKS ≤ 37, MINOR_TICKS ≤ 9; a dial also needs MIN < MAX and MAJOR_TICKS ≥ 2. A bad setup sets FAULT 3 and keeps the last good one; the next good setup clears FAULT 3.
- **Power-up defaults** as listed above, plus MINOR_TICKS 1 and SHOW 1 (readout on).
- Rule 3 is done by copying 0x10–0x9F when a write transaction ends; the drawing loop only reads that copy.
- ~~**Limit found:** a gauge has one VALUE, so a compass can't also show a second number (e.g. wind direction *and* speed).~~ **Solved in v0.2 / fw 1.1 (Jason picked this, 2026-09-30):** READOUT_TEXT at +0x28 puts any short text in the big readout; changing it re-sends only the readout box (~5,000 px in the simulator).

## How the Presto uses this (normal running)

- **Every ~20 ms:** read Controls 0x10–0x19 (10 bytes). **First** check byte 0x19 (BOOT_ID copy): if it changed, re-baseline and re-send, and skip counting this poll. Otherwise act on any counter that changed.
- **Every ~1 s:** read both boards' headers (0x00–0x0B). Watch the heartbeat and FAULT, and the Gauges board's BOOT_ID: if it changed, re-send everything to that board (rule 5). (The Gauges board has no input counters, so the 1 s check is enough there; Controls restarts are caught on every poll via 0x19.)
- **When a screen's gauges change** (for example switching to the Weather screen): write each gauge's setup block, then its VALUE.
- **When a reading changes:** write that gauge's VALUE only.
- **Switches:** decide brightness, mute and the rest from SWITCHES, then write BACKLIGHT, LED_BRIGHT and so on.

## Decisions behind this version (Jason, 2026-09-28)

- Gauges support **dial + compass** styles, fully set up from the Presto (no reflash to change what a gauge shows).
- Needles **glide smoothly**, and do a **full-scale sweep at power-up**, like a car dashboard.
- Pilot lights support **blink and dim**, run by the co-processor.
- Chime **volume is adjustable** in Settings (software volume). CHIME and WIFE MODE mute it, decided by the Presto.
- Co-processors **hold their last state** if the Presto goes quiet (proposed default, not objected to).

## Open / VERIFY

- Which physical direction is "on" for each toggle switch: settle at assembly (M4).
- Clip storage format, size limits and how many clips fit: **format settled 2026-09-30 (1.9 Part 1): 16 kHz mono WAV in `/clips` on the Controls board, 16-bit by default, 8-bit acceptable if flash is tight.** VOLUME can map onto a sample shift (all steps usable, no distortion at full scale). How many clips fit: once the real clips exist (5.10); rough guide ~32 KB per second at 16-bit.
- GLIDE default (40) and the startup sweep speed: tune by eye in step 1.8. **2026-09-30 (1.8a):** Jason picked a **300 ms glide** (`GLIDE_MS = 300` in `gauge_partial_test.py`, judged with a new value every 2 s). Map the GLIDE register's units to that when the Gauges firmware is written. Sweep speed still open.
- **A board that stops answering (found 2026-09-30, 1.10 restart re-check):** while 0x11 was unplugged the Presto logged ~50 `EIO` bus errors per second. Real firmware should show that board as **missing** (and keep polling quietly) rather than count errors; errors should mean a board that is present but misbehaving. **Built 2026-09-30 in the Presto's `coproc.py` (simulator-verified):** 3 failed transfers in a row = MISSING (shown on Diagnostics); a missing board is re-checked once a second and re-sent everything when it answers.
- Whether 400 kHz is ever needed: probably not, since the traffic is tiny.
- **0x10 BACKLIGHT (Gauges) has no hardware to drive (found 2026-09-29):** the GC9A01 modules on hand have no backlight pin, so the backlight is always on. ~~Decided 2026-09-29: power switch on GP10 + software dimming.~~ **Revised 2026-09-30 (roadmap 1.8c): software only, no power switch** — the chip's brightness commands (51h/53h) do nothing on these modules, but display off (28h) is dark enough. Planned meaning for a later version (not yet changed): **0 = display off (28h; any non-zero value sends 29h to turn it back on); 1–255 = software brightness** (the dial colours are scaled). Settle the exact mapping when the Gauges firmware is written.
- ~~**Needle glide vs. frame rate (found 2026-09-29):** full-screen redraws of both gauges run at only ~6–7 fps, which looks steppy. GLIDE tuning waits on partial redraw (roadmap 1.8a).~~ **Resolved 2026-09-30:** partial redraw runs ~25–32 fps over I2C and looks smooth (roadmap 1.8a).

## Change log

- 2026-10-26 — **v0.3:** 0x23 LED_OTA_BRIGHT, so the two pilot lights can be set separately (the green OTA LED looked far brighter than the amber WiFi one at the same level on the first assembled unit). Controls fw 0.5 and the Presto driver implement it; the Presto writes 0x20–0x23 in one transfer.
- 2026-09-28 — v0 drafted (roadmap 1.2). Not yet implemented.
- 2026-09-29 — Open items added from the 1.8 gauge desk run: BACKLIGHT has no hardware pin; glide depends on partial redraw. No register changes.
- 2026-09-29 — **v0.1 (approved by Jason):** Controls 0x19 = BOOT_ID copy; the Presto polls 10 bytes and checks it before the counters. Found in the 1.10 desk test: unplugging and replugging the Controls board made the Presto count a fake 0 ms button press and "switch changes 256" (8 real + 248 from the counter reset), because the restart was only noticed by the 1 s header check. Fix tested against a mocked bus: the same sequence now counts 4 presses (3 + 1 after the restart) and 8 switch changes.
- 2026-09-30 — Open item for 0x10 BACKLIGHT revised after the 1.8c test: 0 = display off (28h), not power off; no power switch. No register changes.
- 2026-09-30 — v0.1 restart fix confirmed on hardware (1.10 re-check, two replugs, no fake counts). Open items: glide pick (300 ms), glide-vs-frame-rate resolved by partial redraw, and handling a board that stops answering. No register changes.
- 2026-09-30 — Clip format settled by 1.9 Part 1 (16 kHz mono WAV, 16-bit default). No register changes.
- 2026-09-30 — Chime registers (0x16–0x18, 0x30–0x33) implemented and confirmed on hardware in the fw 0.3 test script (roadmap 1.9 Part 2). Implementation notes added. No register changes.
- 2026-09-30 — Gauges map implemented in Gauges fw 1.0 and the Presto driver (M5 foundation, simulator-verified). GLIDE units fixed at 7.5 ms, BACKLIGHT 0 = display off / 1–255 = scaled colours, readout = sent VALUE. Missing-board handling built. No register changes.
- 2026-09-30 — **v0.2 (Jason picked "option 2"):** READOUT_TEXT (8 bytes) at gauge block +0x28, in the reserved space between the setup and VALUE. Gauges fw 1.1 and the Presto driver implement it (simulator-verified). PROTO stays 0: the new register sits in a formerly reserved slot, and a board without it just shows the number.
- 2026-10-07 — Gauges fw 1.1 + the Presto driver confirmed on hardware (M5 foundation desk test). No register changes.
