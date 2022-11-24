from bluberry import app
from libs import Constants

def convertToMgDlIfMmol(value):
    if app.pref.getValue("units", "mgdl") == "mgdl" :
        return value * Constants.MMOLL_TO_MGDL
    else:
        return value
