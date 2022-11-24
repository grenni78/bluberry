from peewee import *

from libs.base import Base
from libs.models.bgReading import BgReading
from libs import DexcomCollectionType


class CalibrationRequest(Model, Base):
    max = 250
    min = 70

    _ID = IdentityField(name = "_ID")

    requestIfAbove = DoubleField()

    requestIfBelow = DoubleField()

    def createRange(self, low, high):
        calibrationRequest = CalibrationRequest(app = self.app)
        calibrationRequest.requestIfAbove = low
        calibrationRequest.requestIfBelow = high
        calibrationRequest.save()

    def createOffset(self, center, distance):
        calibrationRequest = CalibrationRequest(app = self.app)
        calibrationRequest.requestIfAbove = center + distance
        calibrationRequest.requestIfBelow = max
        calibrationRequest.save()

        calibrationRequest = CalibrationRequest(app = self.app)
        calibrationRequest.requestIfAbove = min
        calibrationRequest.requestIfBelow = center - distance
        calibrationRequest.save()

    def clearAll(self):
        calibrationRequests = self.get()
        if len(calibrationRequests) >= 1:
            for calibrationRequest in calibrationRequests:
                calibrationRequest.delete()

    def shouldRequestCalibration(self, bgReading):
        try:
            calibrationRequest = self.get(CalibrationRequest.requestIfAbove < bgReading.calculated_value, CalibrationRequest.requestIfBelow > bgReading.calculated_value).limit(1)
            return calibrationRequest.isSlopeFlatEnough(bgReading, 1)
        except:
            return False

    def isSlopeFlatEnough(self, bgReading=None, limit = None):
        if bgReading is None:
            bgReading = BgReading(app = self.app).last(True)

        if limit is None:
            stale_millis = (60000 * 11)
            if DexCollectionType.getDexCollectionType() == DexCollectionType.LibreAlarm:
                stale_millis(60000 * 13)
            
            if datetime.msSince(bgReading.timestamp) > stale_millis:
                self.log.info("Slope cannot be flat enough as data is stale")
                return False

            # TODO check if stale, check previous slope also, check that reading parameters also
            return self.isSlopeFlatEnough(bgReading)
        else:
            # TODO use BestGlucose
            return abs(bgReading.calculated_value_slope * 60000) < limit
