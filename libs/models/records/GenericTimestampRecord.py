
from libs.tools import DexcomUtils
import datetime
from bitstring import Bits, BitArray

class GenericTimestampRecord:

    OFFSET_SYS_TIME = 0
    OFFSET_DISPLAY_TIME = 4
    systemTime = 0
    systemTimeSeconds = 0
    displayTime = 0

    def __init__(self, packet=None, displayTime=None, systemTime=None):
        if packet is not None:
            bits = BitArray(packet)
            self.systemTimeSeconds = bits[0:4 * 8].uintle
            self.systemTime = DexcomUtils.receiverTimeToDate(self.systemTimeSeconds)
            dt = bits[self.OFFSET_DISPLAY_TIME:self.OFFSET_DISPLAY_TIME + 4 * 8].uintle
            self.displayTime = DexcomUtils.receiverTimeToDate(dt)
        else:
            self.displayTime=displayTime
            self.systemTime=systemTime


    def getSystemTime(self):
        return self.systemTime


    def getSystemTimeSeconds(self):
        return self.systemTimeSeconds


    def getDisplayTime(self):
        return self.displayTime


    def getDisplayTimeSeconds(self):
        return self.displayTime / 1000
