from threading import lock
from libs.tools import TimeHelpers
from libs import Constants

"""
 
  The idea here is for a standard class format which you can
  extend to implement your own pluggable calibration algorithms
 
  See FixedSlopeExample or Datricsae for examples on doing this
 """

class CalibrationAbstract:

    memory_cache = {}

    # Overridable methods

    # boolean responses typically indicate if anything received and processed the call
    # None return values mean unsupported or invalid

    # get the calibration data (caching is handled internally)

    def getCalibrationData(self, until=None):
        if until is not None:
            return None
        
        return self.getCalibrationData(TimeHelpers.tsl() + Constants.HOUR_IN_MS)


    # get calibration data at specific timestamp (more advanced)

    def getCalibrationDataAtTime(self, timestamp):
        # default no implementation
        return None


    # indicate that the cache should be invalidated as BG sample data has changed
    # or time has passed in a way we want to invalidate any existing cache

    def invalidateCache(self):
        # default no implementation
        return True


    # called when any new sensor data is available such as on every reading
    # this could be used to invalidate the cache if this extra data is used;
    def newSensorData(self):
        return False


    # called when any new sensor data is available within 20 minutes of last calibration
    # this could be used to invalidate the cache if this extra data is used;
    def newCloseSensorData(self):
        return False


    # called when new blood glucose data is available or there is a change in existing data
    # by default this invalidates the caches
    def newFingerStickData(self):
        return PluggableCalibration.invalidateAllCaches()


    # the name of the alg - should be v.similar to its class name

    def getAlgorithmName(self):
        # default no implementation
        return None


    # a more detailed description of the basic idea behind the plugin

    def getAlgorithmDescription(self):
        # default no implementation
        return None


    # Common utility methods #

    def getNiceNameAndDescription(self):
        name = self.getAlgorithmName()
        description = ""
        if name is not None:
            description = getAlgorithmDescription()
        else:
            name = ""
        return name + " - " + description


    # slower method but for ease of use when calculating a single value

    def getGlucoseFromSensorValue(self, raw=None, data=None):
        if raw is None:
            return None
        if data is None:
            data = self.getCalibrationData()
        return raw * data.slope + data.intercept


    # faster method when CalibrationData is passed - could be overridden for non-linear algs

    def getGlucoseFromBgReading(self, bgReading = None, data = None):
        if data is None or bgReading is None:
            return -1
        # algorithm can override to decide whether or not to be using age_adjusted_raw
        return bgReading.age_adjusted_raw_value * data.slope + data.intercept


    def getBgReadingFromBgReading(self, bgReading = None, data = None):
        if data is None or bgReading is None:
            return None

        # do we need deep clone?
        new_bg = copy.deepcopy(bgReading)
        if new_bg is None:
            return None
        # algorithm can override to decide whether or not to be using age_adjusted_raw
        new_bg.calculated_value = self.getGlucoseFromBgReading(bgReading, data)
        new_bg.filtered_calculated_value = self.getGlucoseFromFilteredBgReading(bgReading, data)
        return new_bg


    def getGlucoseFromFilteredBgReading(self, bgReading = None, data = None):
        if data is None or bgReading is None:
            return None
        # algorithm can override to decide whether or not to be using age_adjusted_raw
        return bgReading.ageAdjustedFiltered_fast() * data.slope + data.intercept


    def jsonStringToData(json):
        try:
            return json.loads(json)
        except AssertionError as err:
            return None


    def dataToJsonString(data):
        try:
            return json.dumps(data)
        except AssertionError as err:
            return ""

    # persistent old style cache
    def saveDataToCache(self, tag, data):
        lookup_tag = "CalibrationDataCache-" + tag
        self.memory_cache[lookup_tag] = data
        app.ppref.setValue(lookup_tag, dataToJsonString(data))
        return True


    # memory only cache
    def clearMemoryCache(self):
        self.memory_cache.clear()
        return True


    # memory only cache - TODO possible room for improvement using timestamp as well
    def saveDataToCache(self, tag, data, timestamp, last_calibration):
        lookup_tag = tag + last_calibration
        self.memory_cache[lookup_tag] = data
        return True


    # memory only cache
    def loadDataFromCache(self, tag, timestamp):
        lookup_tag = tag + timestamp
        return self.memory_cache[lookup_tag]


    # persistent old style cache
    def loadDataFromCache(self, tag):
        lookup_tag = "CalibrationDataCache-" + tag
        if lookup_tag in self.memory_cache:
            self.memory_cache[lookup_tag] = json.loads(app.ppref.getValue(lookup_tag))

        return self.memory_cache[lookup_tag]


    # Data Exchange Class #

    # for returning data to xDrip

    class CalibrationData:
        
        slope = 0.0
        intercept = 0.0
        created = 0

        def __init__(self, slope, intercept):
            self.slope = slope
            self.intercept = intercept
            self.created = TimeHelpers.tsl()
