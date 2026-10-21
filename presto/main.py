# main.py - starts the ICCYC Depot Dashboard app on the Presto
#
# Kept tiny on purpose: if the app crashes, this shows the error on the
# screen, writes it to /error.log, waits 30 s and restarts the Presto - so a
# unit in a closed case never just sits frozen. Pressing Stop in Thonny still
# stops it normally (KeyboardInterrupt is let through).
#
# Before the app starts, otaguard.check() undoes an over-the-air update that
# was cut short or that keeps crashing (roadmap 5.13). main.py and otaguard.py
# are the two files an update never replaces.

import sys
import time

try:
    import otaguard
    _undone = otaguard.check()
    if _undone:
        print(_undone)
except Exception as e:                # the safety net must never stop the unit starting
    sys.print_exception(e)

presto = None
try:
    from presto import Presto
    presto = Presto(full_res=True, ambient_light=False)
    import app
    app.App(presto).run()
except KeyboardInterrupt:
    raise
except Exception as e:
    try:
        with open("/error.log", "w") as f:
            sys.print_exception(e, f)
    except Exception:
        pass
    sys.print_exception(e)
    if presto is not None:
        try:
            d = presto.display
            d.set_pen(d.create_pen(10, 7, 5))
            d.clear()
            d.set_pen(d.create_pen(225, 60, 40))
            d.text("SOMETHING WENT WRONG", 20, 40, 440, 3)
            d.set_pen(d.create_pen(240, 225, 190))
            d.text("%s: %s" % (type(e).__name__, e), 20, 100, 440, 2)
            d.text("Details in /error.log. Restarting in 30 s.", 20, 400, 440, 2)
            presto.set_backlight(1.0)
            presto.update()
        except Exception:
            pass
    time.sleep(30)
    import machine
    machine.reset()
