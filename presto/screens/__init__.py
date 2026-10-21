# screens - one module per screen. The ring order (knob turn / PREV / NEXT)
# and the Home menu both come from RING below: to add a screen, write its
# module and add one line here (the Model 100 menus used the same
# table-driven pattern).

from screens.clock import Clock
from screens.settings import Settings
from screens.home import Home
from screens.diag import Diag
from screens.weather import WeatherScreen
from screens.onthisday import OnThisDayScreen
from screens.lantern import LanternTime
from screens.fitz import Fitz
from screens.train import NearestTrain
from screens.wifi import WifiSetup
from screens.overhead import Overhead
from screens.update import Update
from screens.setpages import ChimePage, BrightPage, GaugesPage


def build():
    ring = [
        Clock(),
        WeatherScreen(),
        LanternTime(),
        OnThisDayScreen(),
        NearestTrain(),
        Overhead(),
        Settings(),
    ]
    return ring, Home(), Diag()
