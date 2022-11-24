"""
Batteriemanagement der Bluetooth bridge
"""

from libs.base import Base
from libs.tools import ratelimits
from libs.tools import TimeHelpers
from libs import userinteract
import bluberry


PREFS_ITEM = "devices.bluetooth.bridge_battery"
PARAKEET_PREFS_ITEM = "devices.bluetooth.parakeet_battery"
LAST_PARAKEET_PREFS_ITEM = "devices.bluetooth.last-parakeet-battery"
NOTIFICATION_ITEM = 541
PARAKEET_NOTIFICATION_ITEM = 542
repeat_seconds = 1200
last_level = -1
last_parakeet_level = -1
threshold = 20


def checkBridgeBattery():
    global last_level

    lowbattery = False

    if not bluberry.app.pref.getValue("devices.bluetooth.bridge_battery_alerts", False):
        return False

    try:
        threshold = int( bluberry.app.pref.getValue("devices.bluetooth.bridge_battery_alert_level", "30") )
    except AssertionError as err:
        bluberry.app.log.debug("Got error parsing alert level", err)

    this_level = bluberry.app.pref.getValue(PREFS_ITEM, -1)

    bluberry.app.log.info("checkBridgeBattery threshold:" + threshold + " this_level:" + this_level + " last_level:" + last_level)

    if (this_level > 0) and (threshold > 0):
        if (this_level < threshold) and ((this_level < last_level) or (last_level == -1)):
            if ratelimits.ratelimit("bridge-battery-warning", repeat_seconds):
                lowbattery = True

                userinteract.warning("Low bridge battery", "Bridge battery dropped to: " + this_level + "%")
        last_level = this_level
    return lowbattery


def checkForceWearBridgeBattery():

    lowbattery = False

    if not bluberry.app.pref.getValue("devices.bluetooth.bridge_battery_alerts", False):
        return False
    if not bluberry.app.pref.getValue("devices.bluetooth.disable_wearG5_on_lowbattery", False):
        return False

    try:
        threshold = int(bluberry.app.pref.getValue("devices.bluetooth.bridge_battery_alert_level", "30"))
        if threshold > 5: #give user 5% leeway to begin charging wear device
            threshold = threshold - 5
    except AssertionError as err:
        bluberry.app.log.info("Got error parsing alert level", err)

    this_level = bluberry.app.pref.getValue("devices.bluetooth.bridge_battery", -1)
    bluberry.app.log.info("checkForceWearBridgeBattery threshold:" + threshold + " this_level:" + this_level)
    if (this_level > 0) and (threshold > 0):
        if this_level < threshold:
            lowbattery = True

    return lowbattery


def checkParakeetBattery():
    global last_parakeet_level

    if not bluberry.app.pref.getValue("devices.bluetooth.bridge_battery_alerts", False):
        return

    threshold = int(bluberry.app.pref.getValue("bridge_battery_alert_level", 30))

    this_level = int(bluberry.app.pref.getValue(PARAKEET_PREFS_ITEM, -1))
    if last_parakeet_level == -1:
        last_parakeet_level = int(bluberry.app.pref.getValue(LAST_PARAKEET_PREFS_ITEM))

    bluberry.app.log.info("checkParakeetBattery threshold:" + threshold + " this_level:" + this_level + " last:" + last_parakeet_level)

    if (this_level > 0) and (threshold > 0):
        if (this_level < threshold) and (this_level < last_parakeet_level):
            if ratelimits.ratelimit("parakeet-battery-warning", repeat_seconds):
                userinteract.warning("low battery on parakeet", "Parakeet battery dropped to: " + this_level + "%")

                bluberry.app.log.info("checkParakeetBattery RAISED ALERT threshold:" + threshold + " this_level:" + this_level + " last:" + last_parakeet_level)

        last_parakeet_level = this_level
        bluberry.app.pref.setValue(LAST_PARAKEET_PREFS_ITEM, this_level)



def testHarness():
    if bluberry.app.pref.getValue(PREFS_ITEM, -1) < 1:
        bluberry.app.pref.setValue(PREFS_ITEM, 60)
    bluberry.app.pref.setValue(PREFS_ITEM, bluberry.app.pref.getValue(PREFS_ITEM, 0) - int(datetime.tsl() % 15))

    bluberry.app.log.info("Bridge battery: " + bluberry.app.pref.getValue(PREFS_ITEM, 0))
    checkBridgeBattery()


