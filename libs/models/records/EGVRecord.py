from bitstring import Bits, BitArray
from libs.tools import Dex_Constants
from libs.models.records.GenericTimestampRecord import GenericTimestampRecord
import json


class EGVRecord(GenericTimestampRecord):

    bGValue = 0
    noise = 0
    trend = None

    def __init__(self, packet = None, bGValue = None, trend = None, displayTime= None, systemTime = None):
        # system_time (UInt), display_time (UInt), glucose (UShort), trend_arrow (Byte), crc (UShort))
        super(self, packet=packet, displayTime=displayTime, systemTime=systemTime)
        if packet is not None:
            bits = BitArray(packet)
            self.bGValue = bits[8 * 2 * 8: 8 * 2 * 8 + 2 * 8].uintle & Dex_Constants.EGV_VALUE_MASK
            trendAndNoise = bits[10 * 8 : 10 * 8 + 8].uintle
            trendValue = trendAndNoise & Dex_Constants.EGV_TREND_ARROW_MASK
            noiseValue = ((trendAndNoise & Dex_Constants.EGV_NOISE_MASK) >> 4)
            self.trend = Dex_Constants.TREND_ARROW_VALUES[trendValue]
            self.noise = noiseValue
        else:
            self.bGValue=bGValue
            self.trend=trend


    def noiseValue(self):
        return str(self.noise)

    def getBGValue(self):
        return self.bGValue

    def getTrend(self):
        return self.trend

    def toJSON(self):
        obj = {"sgv": self.bGValue, "date": self.getDisplayTimeSeconds()}
        return json.dumps(obj)
