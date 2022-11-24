
import tzlocal
import datetime

from bitstring import Bits
from libs.tools import TimeHelpers
from libs.models.records import *
from libs.models.records.GlucoseDataSet import GlucoseDataSet

def receiverTimeToDate(delta):
    local_tz = tzlocal.get_localzone()
    currentTZOffset = int(datetime.date.astimezone(local_tz).utcoffset().total_seconds()/60)
    epochMS = 1230768000000  # Jan 01, 2009 00:00 in UTC
    milliseconds = epochMS - currentTZOffset
    timeAdd = milliseconds + (1000 * delta)
    return timeAdd

def getTimeString(timeDeltaMS):
    return TimeHelpers.niceTimeSince(timeDeltaMS)

def mergeGlucoseDataRecords(egvRecords, sensorRecords):
    egvLength = len(egvRecords)
    sensorLength = len(sensorRecords)
    if egvLength < sensorLength:
        smallerLength = egvLength
    else:
        smallerLength = sensorLength

    glucoseDataSets = []
    for i in range(smallerLength):
        glucoseDataSets.append(GlucoseDataSet(egvRecords[egvLength - i], sensorRecords[sensorLength - i]))

    return glucoseDataSets


def bytesToHex(bytes):
    return Bits(bytes).hex
