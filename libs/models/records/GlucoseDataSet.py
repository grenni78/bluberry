

class GlucoseDataSet:

    systemTime = 0
    displayTime = 0
    bGValue = 0
    trend = None
    unfiltered = 0.0
    filtered = 0.0
    rssi = 0

    def __init(self,egvRecord,sensorRecord):
        # TODO check times match between record
        self.systemTime = egvRecord.getSystemTime()
        self.displayTime = egvRecord.getDisplayTime()
        self.bGValue = egvRecord.getBGValue()
        self.trend = egvRecord.getTrend()
        self.unfiltered = sensorRecord.getUnfiltered()
        self.filtered = sensorRecord.getFiltered()
        self.rssi = sensorRecord.getRSSI()


    def getSystemTime(self):
        return self.systemTime


    def getDisplayTime(self):
        return self.displayTime


    def getBGValue(self):
        return self.bGValue


    def getTrend(self):
        return self.trend


    def getTrendSymbol(self):
        return self.trend.Symbol()


    def getUnfiltered(self):
        return self.unfiltered


    def getFiltered(self):
        return self.filtered


    def getRssi(self):
        return self.rssi
