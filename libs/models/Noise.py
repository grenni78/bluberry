

from bluberry import *

# TODO future move noise trigger constants here

def getNoiseBlockLevel():
    value = 200
    try:
        value = int(app.pref.getValue("noise_block_level", "200"))
    except:
        app.log.warn("Cannot process noise block level.")

    return value

