
from bluberry import *
from libs import userinteract
from libs.tools import DexcomCollectionType



DEXCOM_MIN_RAW = 5 # raw values below this will be treated as error
DEXCOM_MAX_RAW = 1000 # raw values above this will be treated as error

LIBRE_MIN_RAW = 5 # raw values below this will be treated as error

def isRawValueSane(raw_value, t = DexcomCollectionType.getDexCollectionType()):
    # passes by default!
    state = True

    # checks for each type of data source

    if DexCollectionType.hasDexcomRaw(t):
        if raw_value < DEXCOM_MIN_RAW:
            state = False
        elif raw_value > DEXCOM_MAX_RAW:
            state = False

    elif DexCollectionType.hasLibre(t):
        if raw_value < LIBRE_MIN_RAW:
            state = False

    if not state:
        if ratelimits.ratelimit("sanity-failure", 20):
            msg = "Sensor Raw Data Sanity Failure: " + raw_value
            app.log.info(msg)
            userinteract.info("SensorSanity",msg)

    return state
