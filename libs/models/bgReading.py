"""

"""

from peewee import *
import math
import logging
from libs import Constants
import libs.app as app
from libs.tools import (ratelimits, TimeHelpers)
from libs.tools.BgSendQueue import BgSendQueue
import libs.models.Sensor as Sensor
import libs.models.Calibration as Calibration

log = logging.getLogger(__name__)

class BgReading(Model):

    _ID = IdentityField()

    PERSISTENT_HIGH_SINCE = "persistent_high_since"
    AGE_ADJUSTMENT_TIME = 86400000 * 1.9
    AGE_ADJUSTMENT_FACTOR = .45
    # TODO: Have these as adjustable settings!!
    BESTOFFSET = (60000 * 0) # Assume readings are about x minutes off from actual!

    sensor = BareField(index = True)

    calibration = BareField(index = True)

    timestamp = BigIntegerField(index = True)

    time_since_sensor_started = DoubleField()

    raw_data = DoubleField()

    filtered_data = DoubleField()

    age_adjusted_raw_value = DoubleField()

    calibration_flag = BooleanField()

    calculated_value = DoubleField()

    filtered_calculated_value = DoubleField()

    calculated_value_slope = DoubleField()

    a = DoubleField()

    b = DoubleField()

    c = DoubleField()

    ra = DoubleField()

    rb = DoubleField()

    rc = DoubleField()

    uuid = CharField(unique = True)

    calibration_uuid = CharField()

    sensor_uuid = CharField(index = True)

    # mapped to the no longer used "synced" to keep DB Scheme compatible
    ignoreForStats = BooleanField(column_name = "synced")

    raw_calculated = DoubleField()

    hide_slope = BooleanField()

    noise = CharField()

    dg_mgdl = DoubleField(default = 0.0)

    dg_slope = DoubleField(default = 0.0)

    dg_delta_name = TextField()


    def __init__(self, **kwargs):
        super.__init__(self, kwargs)


    def getDg_mgdl(self):
        if self.dg_mgdl != 0:
            return self.dg_mgdl
        return self.calculated_value


    def getDg_slope(self):
        if self.dg_mgdl != 0:
            return self.dg_slope
        return self.currentSlope()


    def getDg_deltaName(self):
        if self.dg_mgdl != 0 and self.dg_delta_name != None:
            return self.dg_delta_name
        return self.slopeName()


    def calculated_value_mmol(self):
        return self.mmolConvert(self.calculated_value)


    def injectDisplayGlucose(self, displayGlucose):
        # displayGlucose can be null. E.g. when out of order values come in
        if displayGlucose != None:
            if abs(displayGlucose.timestamp - self.timestamp) < Constants.MINUTE_IN_MS * 10:
                self.dg_mgdl = displayGlucose.mgdl
                self.dg_slope = displayGlucose.slope
                self.dg_delta_name = displayGlucose.delta_name
                # TODO we probably should reflect the display glucose delta here as well for completeness
                self.save()
            else:
                if ratelimits.ratelimit("cannotinjectdg", 30):
                    self.log.warn("Cannot inject display glucose value as time difference too great: " + TimeHelpers.dateTimeText(displayGlucose.timestamp) + " vs " + TimeHelpers.dateTimeText(self.timestamp))


    def mmolConvert(self, mgdl):
        return mgdl * Constants.MGDL_TO_MMOLL


    def displayValue(self, context):
        unit = self.prefs.getString("units", "mgdl")

        if self.calculated_value >= 400:
            return "HIGH"
        elif self.calculated_value >= 40:
            if unit == "mgdl":
                return self.calculated_value
            else:
                return self.calculated_value_mmol()
        else:
            return "LOW"
            # TODO doesn't understand special low values


    def activeSlope(self):
        bgReading = self.lastNoSenssor()
        if bgReading is not None:
            slope = (2 * bgReading.a * (TimeHelpers.tsl() + self.BESTOFFSET)) + bgReading.b
            log.info("ESTIMATE SLOPE" + slope)
            return slope
        return 0


    def activePrediction(self):
        bgReading = self.lastNoSenssor()
        if bgReading is not None:
            currentTime = TimeHelpers.tsl()
            if currentTime >= bgReading.timestamp + (60000 * 7):
                currentTime = bgReading.timestamp + (60000 * 7)

            time = currentTime + self.BESTOFFSET
            return (bgReading.a * time * time) + (bgReading.b * time) + bgReading.c

        return 0



    def calculateSlope(self, current, last):
        if current.timestamp == last.timestamp or current.calculated_value == last.calculated_value:
            return 0
        else:
            return (last.calculated_value - current.calculated_value) / (last.timestamp - current.timestamp)


    def currentSlope(self):
        last_2 = self.latest(2)
        if (last_2 is not None) and len(last_2) == 2:
            slope = self.calculateSlope(last_2[0], last_2[1])
            return slope
        else:
            return 0.0


    def create(self, egvRecords = None, sensorRecord = None, raw_data = None, filtered_data = None, timestamp = 0, quick = False, addativeOffset = 0):
        for egvRecord in egvRecords:
            bgReading = BgReading().getForTimestamp(egvRecord.getSystemTime().getTime() + addativeOffset)
            log.info("create: Looking for BG reading to tag this thing to: %f", egvRecord.getBGValue())
            if bgReading is not None:
                bgReading.calculated_value = egvRecord.getBGValue()
                if egvRecord.getBGValue() <= 13:
                    calibration = bgReading.calibration
                    firstAdjSlope = calibration.first_slope + (calibration.first_decay * (math.ceil(TimeHelpers.tsl() - calibration.timestamp) / (1000 * 60 * 10)))
                    calSlope = (calibration.first_scale / firstAdjSlope) * 1000
                    calIntercept = ((calibration.first_scale * calibration.first_intercept) / firstAdjSlope) * -1
                    bgReading.raw_calculated = (((calSlope * bgReading.raw_data) + calIntercept) - 5)

                log.info("create: NEW VALUE CALCULATED AT: %d", bgReading.calculated_value)
                bgReading.calculated_value_slope = bgReading.slopefromName(egvRecord.getTrend().friendlyTrendName())
                bgReading.noise = egvRecord.noiseValue()
                friendlyName = egvRecord.getTrend().friendlyTrendName()
                if friendlyName == "NONE" or friendlyName == "NOT_COMPUTABLE" or friendlyName == "NOT COMPUTABLE" or friendlyName == "OUT OF RANGE" or friendlyName == "OUT_OF_RANGE":
                    bgReading.hide_slope = True
                bgReading.save()
                bgReading.find_new_curve()
                bgReading.find_new_raw_curve()

                BgSendQueue.handleNewBgReading(bgReading = bgReading, operation_type = "create")
        if raw_data is not None:
            bgReading = self
            sensor = Sensor.currentSensor()
            if sensor is None:
                log.info("BG GSON: %s", bgReading.toS())

            if raw_data == 0:
                log.warning("Warning: raw_data is 0 in BgReading.create()")

            bgReading.sensor = sensor
            bgReading.sensor_uuid = sensor.uuid
            bgReading.raw_data = (raw_data / 1000)
            bgReading.filtered_data = (filtered_data / 1000)
            bgReading.timestamp = timestamp
            bgReading.uuid = uuid.uuid4()
            bgReading.time_since_sensor_started = bgReading.timestamp - sensor.started_at
            bgReading.calculateAgeAdjustedRawValue()

            calibration = Calibration.lastValid()

            if calibration is None:
                log.debug("create: No calibration yet")
                bgReading.calibration_flag = False
                bgReading.save()
                bgReading.perform_calculations()
            else:
                log.info("Calibrations, so doing everything: %s", calibration.uuid)

                bgReading.calibration = calibration
                bgReading.calibration_uuid = calibration.uuid

                if calibration.check_in:
                    firstAdjSlope = calibration.first_slope + (calibration.first_decay * (math.ceil(TimeHelpers.tsl() - calibration.timestamp) / (1000 * 60 * 10)))
                    calSlope = (calibration.first_scale / firstAdjSlope) * 1000
                    calIntercept = ((calibration.first_scale * calibration.first_intercept) / firstAdjSlope) * -1
                    bgReading.calculated_value = (((calSlope * bgReading.raw_data) + calIntercept) - 5)
                    bgReading.filtered_calculated_value = (((calSlope * bgReading.ageAdjustedFiltered()) + calIntercept) - 5)

                else:
                    lastBgReading = self.last()
                    if lastBgReading is not None and lastBgReading.calibration is not None:
                        log.info("Create calibration.uuid=%s bgReading.uuid: %s lastBgReading.calibration_uuid: %s lastBgReading.calibration.uuid: %s", calibration.uuid, bgReading.uuid, lastBgReading.calibration_uuid, lastBgReading.calibration.uuid)
                        log.info("Create lastBgReading.calibration_flag=%s  bgReading.timestamp: %s lastBgReading.timestamp: %s lastBgReading.calibration.timestamp: ", lastBgReading.calibration_flag, bgReading.timestamp, lastBgReading.timestamp, lastBgReading.calibration.timestamp)
                        log.info("Create lastBgReading.calibration_flag=" + lastBgReading.calibration_flag + " bgReading.timestamp: " + TimeHelpers.dateTimeText(bgReading.timestamp) + " lastBgReading.timestamp: " + TimeHelpers.dateTimeText(lastBgReading.timestamp) + " lastBgReading.calibration.timestamp: " + TimeHelpers.dateTimeText(lastBgReading.calibration.timestamp))

                        if lastBgReading.calibration_flag == True and ((lastBgReading.timestamp + (60000 * 20)) > bgReading.timestamp) and ((lastBgReading.calibration.timestamp + (60000 * 20)) > bgReading.timestamp):
                            lastBgReading.calibration.rawValueOverride(BgReading.weightedAverageRaw(lastBgReading.timestamp, bgReading.timestamp, lastBgReading.calibration.timestamp, lastBgReading.age_adjusted_raw_value, bgReading.age_adjusted_raw_value))
                            self.newCloseSensorData()

                    if (bgReading.raw_data != 0) and (bgReading.raw_data * 2 == bgReading.filtered_data):
                        self.log.warn("Filtered data is exactly double raw - this is completely wrong - dead transmitter? - blocking glucose calculation")
                        bgReading.calculated_value = 0
                        bgReading.filtered_calculated_value = 0
                        bgReading.hide_slope = True
                    elif not SensorSanity.isRawValueSane(bgReading.raw_data):
                        self.log.warn("Raw data fails sanity check! " + bgReading.raw_data)
                        bgReading.calculated_value = 0
                        bgReading.filtered_calculated_value = 0
                        bgReading.hide_slope = True
                    else:
                        # calculate glucose number from raw
                        
                        plugin = self.getCalibrationPluginFromPreferences()  # make sure do this only once
                        pcalibration = plugin.getCalibrationData()

                        if (plugin is not None) and (pcalibration is not None) and (self.pref.getValue("use_pluggable_alg_as_primary", False)):
                            log.info("USING CALIBRATION PLUGIN AS PRIMARY!!!")
                            bgReading.calculated_value = (pcalibration.slope * bgReading.age_adjusted_raw_value) + pcalibration.intercept
                            bgReading.filtered_calculated_value = (pcalibration.slope * bgReading.ageAdjustedFiltered()) + calibration.intercept
                        else:
                            bgReading.calculated_value = ((calibration.slope * bgReading.age_adjusted_raw_value) + calibration.intercept)
                            bgReading.filtered_calculated_value = ((calibration.slope * bgReading.ageAdjustedFiltered()) + calibration.intercept)

            if SensorSanity.isRawValueSane(bgReading.raw_data):
                self.updateCalculatedValueToWithinMinMax(bgReading)


            # LimiTTer can send 12 to indicate problem with NFC reading.
            if (not calibration.check_in) and (raw_data == 12) and (filtered_data == 12):
                # store the raw value for sending special codes, note updateCalculatedValue would try to nix it
                bgReading.calculated_value = raw_data
                bgReading.filtered_calculated_value = filtered_data

            bgReading.save()

            # used when we are not fast inserting data
            if not quick:
                bgReading.perform_calculations()

                if ratelimits.ratelimit("opportunistic-calibration", 60):
                    BloodTest.opportunisticCalibration()

            bgReading.injectNoise(True) # Add noise parameter for nightscout
            bgReading.injectDisplayGlucose(BestGlucose.getDisplayGlucose()) # Add display glucose for nightscout
            BgSendQueue.handleNewBgReading(bgReading, "create", context, Home.get_follower(), quick);

        self.log.i("BG GSON: ", bgReading.toS())

        return bgReading

        if sensorRecord is not None:
            log.info("create: gonna make some sensor records: " + sensorRecord.getUnfiltered())
            if BgReading().is_new(sensorRecord, addativeOffset):
                bgReading = BgReading()
                sensor = Sensor.currentSensor()
                calibration = Calibration.getForTimestamp(sensorRecord.getSystemTime().getTime() + addativeOffset)
                if sensor is not None and calibration is not None:
                    bgReading.sensor = sensor
                    bgReading.sensor_uuid = sensor.uuid
                    bgReading.calibration = calibration
                    bgReading.calibration_uuid = calibration.uuid
                    bgReading.raw_data = (sensorRecord.getUnfiltered() / 1000)
                    bgReading.filtered_data = (sensorRecord.getFiltered() / 1000)
                    bgReading.timestamp = sensorRecord.getSystemTime().getTime() + addativeOffset

                    if bgReading.timestamp > TimeHelper.tsl():
                        return

                    bgReading.uuid = uuid.uuid4()
                    bgReading.time_since_sensor_started = bgReading.timestamp - sensor.started_at
                    bgReading.calculateAgeAdjustedRawValue()
                    bgReading.save()


    def getForTimestamp(self, timestamp):
        sensor = Sensor.currentSensor()
        if sensor is not None:
            try:
                bgReading = self.get(BgReading.sensor == sensor.getId() & BgReading.timestamp <= (timestamp + (60 * 1000)) & BgReading.calculated_value == 0 & BgReading.raw_calculated == 0).order_by("timestamp desc")
            except DoesNotExist as err:
                self.log.debug("getForTimestamp: No luck finding a BG timestamp match", err)
                return None

            if abs(bgReading.timestamp - timestamp) < (3 * 60 * 1000): # cool, so was it actually within 4 minutes of that bg reading?
                log.info("getForTimestamp: Found a BG timestamp match")
                return bgReading
        
        return None


    def getForPreciseTimestamp(self, timestamp, precision, lock_to_sensor = True):
        sensor = Sensor.currentSensor()
        if sensor is not None or lock_to_sensor == False:
            try:
                if lock_to_sensor == False:
                    bgReading = self.get(BgReading.timestamp > 0 & BgReading.timestamp <= (timestamp + precision) & BgReading.timestamp >= (timestamp - precision)).order_by("abs(timestamp - " + timestamp + ") asc")
                else:
                    bgReading = self.get(BgRading.sensor==sensor.getId() & BgReading.timestamp <= (timestamp + precision) & BgReading.timestamp >= (timestamp - precision)).order_by("abs(timestamp - " + timestamp + ") asc")
                    
                if abs(bgReading.timestamp - timestamp) < precision: #cool, so was it actually within precision of that bg reading?
                    return bgReading;

            except DoesNotExist as err:
                self.log.debug("getForPreciseTimestamp: No luck finding a BG timestamp match: " + TimeHelpers.dateTimeText(timestamp) + " precision:" + precision + " Sensor: " + sensor.getId(), err)

        return None


    def is_new(self, sensorRecord, addativeOffset):
        timestamp = sensorRecord.getSystemTime().getTime() + addativeOffset
        sensor = Sensor.currentSensor()
        if sensor is not None:
            try:
                bgReading = self.get(BgReading.sensor == sensor.getId() & BgReading.timestamp <= (timestamp + (60 * 1000))).order_by("timestamp desc")
            except DoesNotExist as err:
                self.log.debug("error comparing values", err)
                return False

            if abs(bgReading.timestamp - timestamp) < (3 * 60 * 1000):
                log.info("isNew; Old Reading")
                return False
        log.info("isNew: New Reading")
        return True


    def updateCalculatedValueToWithinMinMax(self, bgReading):
        # TODO should this really be <10 other values also special??
        if bgReading.calculated_value < 10:
            bgReading.calculated_value = 38
            bgReading.hide_slope = True
        else:
            bgReading.calculated_value = min(400, max(39, bgReading.calculated_value))

        log.info("NEW VALUE CALCULATED AT: " + bgReading.calculated_value)


    # Used by xDripViewer
    def create(self, raw_data = None, age_adjusted_raw_value = None, filtered_data = None, timestamp = None, calculated_bg = None, calculated_current_slope = None, hide_slope = True):

        bgReading = BgReading(application = app)
        sensor = Sensor.currentSensor()
        if sensor is None:
            log.info("No sensor, ignoring this bg reading")
            return None


        calibration = Calibration.lastValid()

        if calibration is None:
            log.info("create: No calibration yet")
            bgReading.sensor = sensor
            bgReading.sensor_uuid = sensor.uuid
            bgReading.raw_data = (raw_data / 1000)
            bgReading.age_adjusted_raw_value = age_adjusted_raw_value
            bgReading.filtered_data = (filtered_data / 1000)
            bgReading.timestamp = timestamp
            bgReading.uuid = uuid.uuid4()
            bgReading.calculated_value = calculated_bg
            bgReading.calculated_value_slope = calculated_current_slope
            bgReading.hide_slope = hide_slope

            bgReading.save()
            bgReading.perform_calculations()
        else:
            log.info("Calibrations, so doing everything bgReading = " + bgReading)
            bgReading.sensor = sensor
            bgReading.sensor_uuid = sensor.uuid
            bgReading.calibration = calibration
            bgReading.calibration_uuid = calibration.uuid
            bgReading.raw_data = (raw_data / 1000)
            bgReading.age_adjusted_raw_value = age_adjusted_raw_value
            bgReading.filtered_data = (filtered_data / 1000)
            bgReading.timestamp = timestamp
            bgReading.uuid = uuid.uuid4()
            bgReading.calculated_value = calculated_bg
            bgReading.calculated_value_slope = calculated_current_slope
            bgReading.hide_slope = hide_slope

            bgReading.save()
        
        BgSendQueue.handleNewBgReading(bgReading, "create")

        log.info("BG GSON: ", bgReading.toS())


    def pushBgReadingSyncToWatch(bgReading = None, is_new = False):
        log.info("pushTreatmentSyncToWatch Add treatment to UploaderQueue.")
        if self.pref.getValue("wear_sync", False):
            if is_new:
                method = "insert"
            else:
                method = "update"
            if UploaderQueue.newEntryForWatch(method, bgReading) is not None:
                SyncService.startSyncService(3000) # sync in 3 seconds


    def activeSlopeArrow():
        slope = BgReading.activeSlope() * 60000
        return BgReading.slopeToArrowSymbol(slope)


    def slopeToArrowSymbol(slope):
        if slope <= (-3.5):
            return "\u21ca" # ⇊
        elif slope <= (-2):
            return "\u2193" # ↓
        elif slope <= (-1):
            return "\u2198" # ↘
        elif slope <= (1):
            return "\u2192" # →
        elif slope <= (2):
            return "\u2197" # ↗
        elif slope <= (3.5):
            return "\u2191" # ↑
        else:
            return "\u21c8" # ⇈

    def slopeArrow():
        return BgReading.slopeToArrowSymbol(this.calculated_value_slope * 60000)


    def slopeName(self, slope_by_minute=None):
        if slope_by_minute is None:
            slope_by_minute = calculated_value_slope * 60000
        arrow = "NONE"
        if slope_by_minute <= (-3.5):
            arrow = "DoubleDown"
        elif slope_by_minute <= (-2):
            arrow = "SingleDown"
        elif slope_by_minute <= (-1):
            arrow = "FortyFiveDown"
        elif slope_by_minute <= (1):
            arrow = "Flat"
        elif slope_by_minute <= (2):
            arrow = "FortyFiveUp"
        elif slope_by_minute <= (3.5):
            arrow = "SingleUp"
        elif slope_by_minute <= (40):
            arrow = "DoubleUp"

        if self.hide_slope:
            arrow = "NOT COMPUTABLE"
        return arrow



    def slopefromName(slope_name):
        slope_by_minute = 0
        if slope_name == DoubleDown:
            slope_by_minute = -3.5
        elif slope_name == "SingleDown":
            slope_by_minute = -2
        elif slope_name == "FortyFiveDown":
            slope_by_minute = -1
        elif slope_name == "Flat":
            slope_by_minute = 0
        elif slope_name == "FortyFiveUp":
            slope_by_minute = 2
        elif slope_name == "SingleUp":
            slope_by_minute = 3.5
        elif slope_name == "DoubleUp":
            slope_by_minute = 4
        elif BgReading.isSlopeNameInvalid(slope_name):
            slope_by_minute = 0

        return slope_by_minute / 60000


    def isSlopeNameInvalid(slope_name):
        if slope_name in ["NOT_COMPUTABLE", "NOT COMPUTABLE", "OUT_OF_RANGE", "OUT OF RANGE", "NONE"]:
            return True
        else:
            return False


    # Get a slope arrow based on pure guessed defaults so we can show it prior to calibration
    def getSlopeArrowSymbolBeforeCalibration():
        last = BgReading.latestUnCalculated(2)
        if last is None and (len(last)==2):
            guess_slope = 1 # This is the "Default" slope for Dex and LimiTTer
            time_delta = last[0].timestamp - last[1].timestamp
            if time_delta <= (BgGraphBuilder.DEXCOM_PERIOD * 2):
                estimated_delta = (last[0].age_adjusted_raw_value * guess_slope) - (last[1].age_adjusted_raw_value * guess_slope)
                estimated_delta2 = (last[0].raw_data * guess_slope) - (last[1].raw_data * guess_slope)
                # self.log.d(TAG, "SlopeArrowBeforeCalibration: guess delta: " + estimated_delta + " delta2: " + estimated_delta2 + " timedelta: " + time_delta)
                return BgReading.slopeToArrowSymbol(estimated_delta / (time_delta / 60000))
            else:
                return ""
        else:
            return ""


    def last_within_minutes(self,mins):
        return self.last_within_millis(mins * 60000)


    def last_within_millis(self,millis):
        reading = self.last()
        if reading is not None and (TimeUtils.tsl() - reading.timestamp) < millis:
            return True
        return False


    def last(self):
        sensor = Sensor.currentSensor()
        if sensor is not None:
            return self.get(BgReading.sensor == sensor.getId() and BgReading.calculated_value != 0 and BgReading.raw_data != 0).order_by("timestamp desc")


    def latest_by_size(self, number):
        sensor = Sensor.currentSensor()
        if sensor is not None:
            return self.get(BgReading.sensor == sensor.getId() and BgReading.raw_data != 0).order_by("timestamp desc").limit(number)


    def lastNoSenssor(self):
        return self.get(BgReading.calculated_value != 0 and BgReading.raw_data != 0).order_by("timestamp desc")


    def latest(self, number):
        sensor = Sensor.currentSensor()
        if sensor is not None:
            return self.get(BgReading.Sensor == sensor.getId() and BgReading.calculated_value != 0 and BgReading.raw_data != 0).order_by("timestamp desc").limit(number)
        return None


    def isDataStale(self):
        last = self.lastNoSenssor()
        if last is not None:
            return TimeHelpers.msSince(last.timestamp) > TimeHelpers.stale_data_millis()


    def latestUnCalculated(self, number):
        sensor = Sensor.currentSensor()
        if sensor is not None:
            return self.get(BgReading.sensor == sensor.getId() and BgReading.raw_data != 0).order_by("timestamp desc").limit(number)
        return None


    def latestForGraph(self, number, startTime, endTime = sys.maxsize):
        return self.get(BgReading.timestamp >= max(startTime, 0) and BgReading.timestamp <= endTime and BgReading.calculated_value != 0 and BgReading.raw_data != 0).order_by("timestamp desc").limit(number)


    def latestForGraphSensor(self, number, startTime, endTime):
        sensor = Sensor.currentSensor()
        if sensor is not None:
            return self.get(BgReading.sensor == sensor.getId() and BgReading.timestamp >= max(startTime, 0) and BgReading.timestamp <= endTime and BgReading.calculated_value != 0 and BgReading.raw_data != 0 and BgReading.calibration_uuid != "").order_by("timestamp desc").limit(number)
        return None


    def latestForGraphAsc(self, number, startTime, endTime):
        return self.get(BgReading.timestamp >= max(startTime, 0) and BgReading.timestamp <= endTime and BgReading.calculated_value != 0 and BgReading.raw_data != 0).order_by("timestamp asc").limit(number)


    def readingNearTimeStamp(self, startTime):
        margin = (4 * 60*1000)
        return self.get(BgReading.timestamp >= (startTime-margin) and BgReading.timestamp <= (startTime + margin) and BgReading.calculated_value != 0 and BgReading.raw_data != 0)


    def last30Minutes(self):
        timestamp = TimeHelpers.tsl() - (60000 * 30)
        return self.get(BgReading.timestamp >= timestamp and BgReading.calculated_value != 0 and BgReading.raw_data != 0).order_by("timestamp desc")


    def isDataSuitableForDoubleCalibration(self):
        uncalculated = self.latestUnCalculated(3)
        if len(uncalculated) < 3:
            return False
        if ProcessInitialDataQuality.getInitialDataQuality(uncalculated).check or self.pref.getValue("bypass_calibration_quality_check", False):
            return True
        return False


    def futureReadings(self):
        timestamp = TimeHelpers.tsl()
        return self.get(BgReading.timestamp > timestamp).order_by("timestamp desc")


    def estimated_bg(self, timestamp):
        timestamp = timestamp + BESTOFFSET
        latest = self.last()
        if latest is not None:
            return (latest.a * timestamp * timestamp) + (latest.b * timestamp) + latest.c
        return 0


    def estimated_raw_bg(self, timestamp):
        timestamp = timestamp + BESTOFFSET
        estimate = 0
        latest = self.last()
        if latest is None:
            log.info("No data yet, assume perfect!")
            estimate = 160
        else:
            estimate = (latest.ra * timestamp * timestamp) + (latest.rb * timestamp) + latest.rc
        log.info("ESTIMATE RAW BG" + estimate)
        return estimate


    def FixCalibration(self, bgr):
        if bgr.calibration_uuid == "":
            log.info("Bgr with no calibration, doing nothing")
            return

        calibration = Calibration.byuuid(bgr.calibration_uuid)
        if calibration is None:
            self.log.warn("recieved Unknown calibration," + bgr.calibration_uuid + " asking for sensor upate..." )
            GcmActivity.requestSensorCalibrationsUpdate()
        else:
            bgr.calibration = calibration


    def bgReadingInsertFromJson(self, json, do_notification = True, force_sensor = False):
        if json is None or len(json) == 0:
            self.log.warn("bgreadinginsertfromjson passed a null or zero length json")
            return

        bgr = self.fromJSON(json)
        if bgr is not None:
            try:
                if self.readingNearTimeStamp(bgr.timestamp) is None:
                    self.FixCalibration(bgr)
                    if force_sensor:
                        forced_sensor = Sensor.currentSensor()
                        if forced_sensor is not None:
                            bgr.sensor = forced_sensor
                            bgr.sensor_uuid = forced_sensor.uuid

                    bgr.save()
                    if do_notification:
                        BgSendQueue.handleNewBgReading(bgr, "create") # pebble and widget and follower

                else:
                    log.info("Ignoring duplicate bgr record due to timestamp: " + json)

            except AssertionError as e:
                self.log.debug("Could not save BGR: ", e)

        else:
            log.info("Got null bgr from json")


    # TODO this method shares some code with above.. merge
    def bgReadingInsertFromInt(self, value, timestamp, do_notification):
        # TODO sanity check data!

        if value <= 0 or timestamp <= 0 :
            log.info("Invalid data fed to InsertFromInt")
            return

        bgr = BgReading()

        if bgr is not None:
            bgr.uuid = uuid.uuid4()

            bgr.timestamp = timestamp
            bgr.calculated_value = value
            

            # rough code for testing!
            bgr.filtered_calculated_value = value
            bgr.raw_data = value
            bgr.age_adjusted_raw_value = value
            bgr.filtered_data = value
            
            forced_sensor = Sensor.currentSensor()
            if forced_sensor is not None:
                bgr.sensor = forced_sensor
                bgr.sensor_uuid = forced_sensor.uuid

            try:
                if self.readingNearTimeStamp(bgr.timestamp) is None:
                    bgr.save()
                    bgr.find_slope()
                    if do_notification:
                        BgSendQueue.handleNewBgReading(bgr, "create")
                else:
                    log.info("Ignoring duplicate bgr record due to timestamp: " + timestamp)

            except AssertionError as e:
                self.log.debug("Could not save BGR: ", e)

        else:
            log.info("Got null bgr from create")


    def byUUID(self, uuid):
        if uuid is None:
            return None
        return self.get(BgReading.uuid == uuid)


    def byid(self, id):
        return self.get(BgReading._ID == id)


    def fromJSON(self, json):
        if len(json) == 0:
            log.info("Empty json received in bgreading fromJson")
            return None

        try:
            log.info("Processing incoming json: " + json)
            return json_loads(json)
        except AssertionError as e:
            log.info("Got exception parsing BgReading json: ", e)
            
            return None


    CLOSEST_READING_MS = 290000


    def toJSON(self, sendCalibration = False):
        jsonObject = {}
        try:
            jsonObject["uuid"] = uuid
            jsonObject["a"] = a
            jsonObject["b"] = b
            jsonObject["c"] = c
            jsonObject["timestamp"] = timestamp
            jsonObject["age_adjusted_raw_value"] = age_adjusted_raw_value
            jsonObject["calculated_value"] = calculated_value
            jsonObject["filtered_calculated_value"] = filtered_calculated_value
            jsonObject["calibration_flag"] = calibration_flag
            jsonObject["filtered_data"] = filtered_data
            jsonObject["raw_calculated"] = raw_calculated
            jsonObject["raw_data"] = raw_data 
            jsonObject["calculated_value_slope"] = calculated_value_slope
            if sendCalibration:
                jsonObject["calibration_uuid"] = calibration_uuid

            jsonObject["sensor"] = sensor

            return json.dumps(jsonObject)
        except AssertionError as e:
            app.log.debug("error generating jsonObject: ", e)
            return ""


    def deleteALL(self):
        try:
            self.db.exececute_sql("delete from BgSendQueue")
            self.db.exececute_sql("delete from BgReadings")
            app.Log.info("Deleting all BGReadings")
        except AssertionError as e:
            app.log.debug("Got exception running deleteALL ", e)


    """*******INSTANCE METHODS***********"""
    def perform_calculations(self):
        self.find_new_curve()
        self.find_new_raw_curve()
        self.find_slope()


    def find_slope(self):
        last_2 = self.latest(2);

        assert last_2[0] == self , "Invariant condition not fulfilled: calculating slope and current reading wasn't saved before"

        if (last_2 is not None) and (len(last_2) == 2):
            calculated_value_slope = self.calculateSlope(this, last_2[1])
            self.save()
        elif (last_2 is not None) and (len(last_2) == 1):
            calculated_value_slope = 0
            self.save()
        else:
            if ratelimits.ratelimit("no-bg-couldnt-find-slope", 15):
                app.log.warn("NO BG? COULDNT FIND SLOPE!")


    def find_new_curve(self):
        
        last_3 = self.latest(3)
        if (last_3 is not None) and (len(last_3) == 3):
            latest = last_3[0]
            second_latest = last_3[1]
            third_latest = last_3[2]

            y3 = latest.calculated_value
            x3 = latest.timestamp
            y2 = second_latest.calculated_value
            x2 = second_latest.timestamp
            y1 = third_latest.calculated_value
            x1 = third_latest.timestamp

            a = y1/((x1-x2)*(x1-x3))+y2/((x2-x1)*(x2-x3))+y3/((x3-x1)*(x3-x2))
            b = (-y1*(x2+x3)/((x1-x2)*(x1-x3))-y2*(x1+x3)/((x2-x1)*(x2-x3))-y3*(x1+x2)/((x3-x1)*(x3-x2)))
            c = (y1*x2*x3/((x1-x2)*(x1-x3))+y2*x1*x3/((x2-x1)*(x2-x3))+y3*x1*x2/((x3-x1)*(x3-x2)))

            app.log.info("find_new_curve: BG PARABOLIC RATES: "+a+"x^2 + "+b+"x + "+c)

            self.save()
        elif (last_3 is not None) and (len(last_3) == 2):

            app.log.info("find_new_curve: Not enough data to calculate parabolic rates - assume Linear")
            latest = last_3[0]
            second_latest = last_3[1]
            y2 = latest.calculated_value
            x2 = latest.timestamp
            y1 = second_latest.calculated_value
            x1 = second_latest.timestamp

            if y1 == y2:
                b = 0
            else:
                b = (y2 - y1)/(x2 - x1)

            a = 0
            c = -1 * ((latest.b * x1) - y1)

            app.log.info( ""+latest.a+"x^2 + "+latest.b+"x + "+latest.c)
            self.save()
        else:
            app.log.info("find_new_curve: Not enough data to calculate parabolic rates - assume static data")
            a = 0
            b = 0
            c = calculated_value

            app.log.info(""+a+"x^2 + "+b+"x + "+c)
            self.save()


    def calculateAgeAdjustedRawValue(self):
        adjust_for = AGE_ADJUSTMENT_TIME - self.time_since_sensor_started

        if (adjust_for > 0) and (not DexCollectionType.hasLibre()):
            age_adjusted_raw_value = ((AGE_ADJUSTMENT_FACTOR * (adjust_for / AGE_ADJUSTMENT_TIME)) * self.raw_data) + self.raw_data
            app.log.info("calculateAgeAdjustedRawValue: RAW VALUE ADJUSTMENT FROM:" + self.raw_data + " TO: " + age_adjusted_raw_value)
        else:
            age_adjusted_raw_value = self.raw_data


    def find_new_raw_curve(self):

        last_3 = self.latest(3)
        if (last_3 is not None) and (len(last_3) == 3):

            latest = last_3[0]
            second_latest = last_3[1]
            third_latest = last_3[2]

            y3 = latest.age_adjusted_raw_value
            x3 = latest.timestamp
            y2 = second_latest.age_adjusted_raw_value
            x2 = second_latest.timestamp
            y1 = third_latest.age_adjusted_raw_value
            x1 = third_latest.timestamp

            ra = y1/((x1-x2)*(x1-x3))+y2/((x2-x1)*(x2-x3))+y3/((x3-x1)*(x3-x2))
            rb = (-y1*(x2+x3)/((x1-x2)*(x1-x3))-y2*(x1+x3)/((x2-x1)*(x2-x3))-y3*(x1+x2)/((x3-x1)*(x3-x2)))
            rc = (y1*x2*x3/((x1-x2)*(x1-x3))+y2*x1*x3/((x2-x1)*(x2-x3))+y3*x1*x2/((x3-x1)*(x3-x2)))

            app.log.info("find_new_raw_curve: RAW PARABOLIC RATES: "+ra+"x^2 + "+rb+"x + "+rc)
            self.save()
        elif (last_3 is not None) and (len(last_3) == 2):
            latest = last_3[0]
            second_latest = last_3[1]

            y2 = latest.age_adjusted_raw_value
            x2 = latest.timestamp
            y1 = second_latest.age_adjusted_raw_value
            x1 = second_latest.timestamp

            if y1 == y2:
                rb = 0
            else:
                rb = (y2 - y1)/(x2 - x1)

            ra = 0
            rc = -1 * ((latest.rb * x1) - y1)

            app.log.info("find_new_raw_curve: Not enough data to calculate parabolic rates - assume Linear data")

            app.log.info("RAW PARABOLIC RATES: "+ra+"x^2 + "+rb+"x + "+rc)
            self.save()
        else:
            log.info("find_new_raw_curve: Not enough data to calculate parabolic rates - assume static data")
            latest_entry = self.lastNoSenssor()
            ra = 0
            rb = 0
            if latest_entry is not None:
                rc = latest_entry.age_adjusted_raw_value
            else:
                rc = 105

            self.save()


    def weightedAverageRaw(self, timeA, timeB, calibrationTime, rawA, rawB):
        relativeSlope = (rawB -  rawA)/(timeB - timeA)
        relativeIntercept = rawA - (relativeSlope * timeA)
        return ((relativeSlope * calibrationTime) + relativeIntercept)


    def toS(self):
        try:
            return json.dumps(self)
        except AssertionError as e:
            app.log.debug("error erporting BgReading as json: ", e)


    def noiseValue(self):
        if (self.noise is None) or (self.noise == "") :
            return 1
        else:
            return int(self.noise)


    def injectNoise(self, save):
        
        if TimeHelpers.msSince(self.timestamp) > Constants.MINUTE_IN_MS * 20 :
            self.noise = "0"
        else:
            # ToDo: Drawing routines
            """
            BgGraphBuilder.refreshNoiseIfOlderThan(bgReading.timestamp);
            if (BgGraphBuilder.last_noise > BgGraphBuilder.NOISE_HIGH) {
                bgReading.noise = "4";
            } else if (BgGraphBuilder.last_noise > BgGraphBuilder.NOISE_TOO_HIGH_FOR_PREDICT) {
                bgReading.noise = "3";
            } else if (BgGraphBuilder.last_noise > BgGraphBuilder.NOISE_TRIGGER) {
                bgReading.noise = "2";
            }
            """
        if save:
            self.save();

        return self
    

    # list(0) is the most recent reading.
    def getXRecentPoints(self, NumReadings):
        latest = self.latest(NumReadings)
        if (latest is None) or len(size) != NumReadings:
            # for less than NumReadings readings, we can't tell what the situation
            #
            app.log.d("getXRecentPoints we don't have enough readings, returning null")
            return None

        # So, we have at least three values...
        for bgReading in latest:
            app.log.info("getXRecentPoints - reading: time = " + bgReading.timestamp + " calculated_value " + bgReading.calculated_value)


        # now let's check that they are relevant. the last reading should be from the last 5 minutes,
        # x-1 more readings should be from the last (x-1)*5 minutes. we will allow 5 minutes for the last
        # x to allow one packet to be missed.
        if TimeHelpers.tsl() - latest[NumReadings - 1].timestamp > (NumReadings * 5 + 6) * 60 * 1000:
            app.log.info("getXRecentPoints we don't have enough points from the last " + (NumReadings * 5 + 6) + " minutes, returning null")
            return None

        return latest


    def checkForPersistentHigh(self):

        # skip if not enabled
        if app.pref.getValue("persistent_high_alert_enabled", False):
            return False

        last = self.latest(1)
        if (last is not None) and (len(last) > 0):
            now = TimeHelpers.tsl()
            since = now - last[0].timestamp
            # only process if last reading <10 mins
            if since < 600000:
                # check if exceeding high
                if last[0].calculated_value > MathHelpers.convertToMgDlIfMmol(float(self.pref.getValue("highValue", "170"))):

                    this_slope = last[0].calculated_value_slope * 60000
                    # self.log.d(TAG, "CheckForPersistentHigh: Slope: " + JoH.qs(this_slope))

                    if this_slope > 0 :
                        high_since = app.pref.getValue(self.PERSISTENT_HIGH_SINCE, 0)
                        if high_since == 0:
                            # no previous persistent high so set start as now
                            app.pref.setValue(PERSISTENT_HIGH_SINCE, now)
                            app.log.info("Registering start of persistent high at time now")
                        else:
                            high_for_mins = (now - high_since) / (1000 * 60)
                            threshold_mins = 0
                            try:
                                threshold_mins = app.pref.getValue("persistent_high_threshold_mins", "60")
                            except AssertionError as e:
                                threshold_mins = 60
                                app.log.debug("Invalid persistent high for longer than minutes setting: using 60 mins instead", e)

                            if high_for_mins > threshold_mins :
                                # we have been high for longer than the threshold - raise alert

                                # except if alerts are disabled
                                if app.pref.getValue("alerts_disabled_until", 0) > TimeHelpers.tsl() :
                                    app.log.info("checkforPersistentHigh: Notifications are currently disabled cannot alert!!")
                                    return False

                                app.log.warn("Persistent high for: " + high_for_mins + " mins -> alerting")
                                userinteract.warning("Persistent high for " + high_for_mins + " minutes!")

                            else:
                                app.log.info("Persistent high below time threshold at: " + high_for_mins)
                else:
                    # not high - cancel any existing
                    if app.pref.getValue(PERSISTENT_HIGH_SINCE,0) != 0 :
                        app.log.info("Cancelling previous persistent high as we are no longer high")
                        app.pref.setValue(PERSISTENT_HIGH_SINCE, 0)
        return False; 


    def checkForRisingAllert(self) :
        
        rising_alert = app.ppref.getValue("rising_alert", False)
        if not rising_alert :
            return

        if app.pref.getValue("alerts_disabled_until", 0) > TimeHelpers.tsl() :
            app.log.info("NOTIFICATIONS", "checkForRisingAllert: Notifications are currently disabled!!")
            return


        riseRate = pprefs.getValue("rising_bg_val", "2")

        app.log.info("checkForRisingAllert will check for rate of " + riseRate)

        riseAlert = self.checkForDropRiseAllert(riseRate, False)
        userinteract.warning(riseAlert)


    def checkForDropAllert(self):
        
        falling_alert = app.pprefs.getValue("falling_alert", False)
        if not falling_alert:
            return

        if app.pref.getValue("alerts_disabled_until", 0) > TimeHelpers.tsl():
            app.log.info("NOTIFICATIONS", "checkForDropAllert: Notifications are currently disabled!!")
            return


        dropRate = app.ppref.getValue("falling_bg_val", "2")
        
        app.log.info("checkForDropAllert will check for rate of " + dropRate)

        dropAlert = self.checkForDropRiseAllert(fdropRate, True)
        userinteract.warning(dropAlert)


    # true say, alert is on.
    def checkForDropRiseAllert(self, MaxSpeed, drop):
        app.log.info("checkForDropRiseAllert called drop=" + drop)
        latest = self.getXRecentPoints(4)
        if latest is None:
            app.log.info("checkForDropRiseAllert we don't have enough points from the last 15 minutes, returning false")
            return False

        time3 = (latest[0].timestamp - latest[3].timestamp) / 60000
        bg_diff3 = latest[3].calculated_value - latest[0].calculated_value
        if not drop:
            bg_diff3 *= (-1)

        app.log.info( "bg_diff3=" + bg_diff3 + " time3 = " + time3)
        if bg_diff3 < time3 * MaxSpeed:
            app.log.info("checkForDropRiseAllert for latest 4 points not fast enough, returning false")
            return False

        # we should alert here, but if the last measurement was less than MaxSpeed / 2, I won't.

        time1 = (latest[0].timestamp - latest[1].timestamp) / 60000
        bg_diff1 = latest[1].calculated_value - latest[0].calculated_value
        if not drop:
            bg_diff1 *= (-1)


        if time1 > 7.0 :
            app.log.info("checkForDropRiseAllert the two points are not close enough, returning true")
            return True

        if bg_diff1 < time1 * MaxSpeed /2:
            app.log.info("checkForDropRiseAllert for latest 2 points not fast enough, returning false")
            return False

        app.log.info("checkForDropRiseAllert returning true speed is " + (bg_diff3 / time3))
        return True


    # Make sure that this function either sets the alert or removes it.
    def getAndRaiseUnclearReading(self):

        if app.ppref.getValue("alerts_disabled_until", 0) > TimeHelpers.tsl() :
            app.log.info("NOTIFICATIONS", "getAndRaiseUnclearReading Notifications are currently disabled!!")
            return False


        bg_unclear_readings_alerts = app.ppref.getValue("bg_unclear_readings_alerts", False)
        if not bg_unclear_readings_alerts or ( not DexCollectionType.hasFiltered() ):
            app.log.info("getUnclearReading returned false since feature is disabled")
            return False

        UnclearTimeSetting = app.ppref.getValue("bg_unclear_readings_minutes", "90") * 60000
        UnclearTime = self.getUnclearTime(UnclearTimeSetting)

        if UnclearTime >= UnclearTimeSetting :
            app.log.info("NOTIFICATIONS", "Readings have been unclear for too long!!")
            userinteract.warning("unclear reading!")
            return True
        
        if UnclearTime > 0 :
            app.log.info( "We are in an clear state, but not for too long. Alerts are disabled")
            return True
        
        return False

    """
      This function comes to check weather we are in a case that we have an allert but since things are
      getting better we should not do anything. (This is only in the case that the alert was snoozed before.)
      This means that if this is a low alert, and we have two readings in the last 15 minutes, and
      either we have gone in 10 in the last two readings, or we have gone in 3 in the last reading, we
      don't play the alert again, but rather wait for the alert to finish.
       I'll start with having the same values for the high alerts.
    """

    def trendingToAlertEnd(self, above):
        # TODO: check if we are not in an UnclerTime.
        app.log.info("trendingToAlertEnd called")

        latest = self.getXRecentPoints(3)
        if latest is None:
            app.log.info("trendingToAlertEnd we don't have enough points from the last 15 minutes, returning false")
            return False

        if not above:
            # This is a low alert, we should be going up
            if (latest[0].calculated_value - latest[1].calculated_value > 4) or (latest[0].calculated_value - latest[2].calculated_value > 10):
                app.log.info("trendingToAlertEnd returning true for low alert")
                return True
        else:
            # This is a high alert we should be heading down
            if (latest[1].calculated_value - latest[0].calculated_value > 4) or (latest[2].calculated_value - latest[0].calculated_value > 10):
                app.log.info("trendingToAlertEnd returning true for high alert")
                return True
        app.log.info("trendingToAlertEnd returning false, not in the right direction (or not fast enough)")
        return False


    # Should that be combined with noiseValue?
    def Unclear(self):
        app.log.info("Unclear filtered_data=" + self.filtered_data + " raw_data=" + self.raw_data)
        return ( self.raw_data > self.filtered_data * 1.3 or self.raw_data < self.filtered_data * 0.7 )


    """
     returns the time (in ms) that the state is not clear and no alerts should work
     The base of the algorithm is that any period can be bad or not. bgReading.Unclear() tells that.
     a non clear bgReading means MAX_INFLUANCE time after it we are in a bad position
     Since this code is based on heuristics, and since times are not accurate, boundary issues can be ignored.

     interstingTime is the period to check. That is if the last period is bad, we want to know how long does it go bad...
    """

    # The extra 120,000 is to allow the packet to be delayed for some time and still be counted in that group
    # Please don't use for MAX_INFLUANCE a number that is complete multiply of 5 minutes (300,000)
    MAX_INFLUANCE = 30 * 60000 - 120000  # A bad point means data is untrusted for 30 minutes.
    
    def getUnclearTimeHelper(self, latest, interstingTime, now):

        # The code ignores missing points (that is they some times are treated as good and some times as bad.
        # If this bothers someone, I believe that the list should be filled with the missing points as good and continue to run.

        LastGoodTime = 0 # 0 represents that we are not in a good part

        UnclearTime = 0

        for bgReading in latest:
            # going over the readings from latest to first

            if bgReading.timestamp < now - (interstingTime + self.MAX_INFLUANCE):
                # Some readings are missing, we can stop checking
                break

            if bgReading.timestamp <= now - self.MAX_INFLUANCE and UnclearTime == 0 :
                app.log.info("We did not have a problematic reading for MAX_INFLUANCE time, so now all is well")
                return 0

            if bgReading.Unclear():
                # here we assume that there are no missing points. Missing points might join the good and bad values as well...
                # we should have checked if we have a period, but it is hard to say how to react to them.
                app.log.info("We have a bad reading, so setting UnclearTime to " + bgReading.timestamp)
                UnclearTime = bgReading.timestamp
                LastGoodTime = 0
            else:
                if LastGoodTime == 0:
                    app.log.info("We are starting a good period at "+ bgReading.timestamp)
                    LastGoodTime = bgReading.timestamp
                else:
                    # we have some good period, is it good enough?
                    if LastGoodTime - bgReading.timestamp >= self.MAX_INFLUANCE :
                        # Here UnclearTime should be already set, otherwise we will return a toob big value
                        if UnclearTime ==0:
                            app.log.warn("ERROR - UnclearTime must not be 0 here !!!")

                        app.log.info("We have a good period from " + bgReading.timestamp + " to " + LastGoodTime + "returning " + (now - UnclearTime +5 *60000))
                        return now - UnclearTime + 5 *60000

        # if we are here, we have a problem... or not.
        if UnclearTime == 0:
            app.log.info("Since we did not find a good period, but we also did not find a single bad value, we assume things are good")
            return 0

        app.log.info("We scanned all over, but could not find a good period. we have a bad value, so assuming that the whole period is bad returning " + interstingTime)
        # Note that we might now have all the points, and in this case, since we don't have a good period I return a bad period.
        return interstingTime


    # This is to enable testing of the function, by passing different values
    def getUnclearTime(self, interstingTime):
        latest = self.latest((interstingTime.intValue() + MAX_INFLUANCE)/ 60000 /5 )
        if latest is None:
            return 0

        now = TimeHelpers.tsl()
        return self.getUnclearTimeHelper(latest, interstingTime, now)


    def getTimeSinceLastReading(self):
        bgReading = self.last()
        if bgReading is not None:
            return (TimeHelpers.tsl() - bgReading.timestamp)

        return 0


    def usedRaw(self):
        calibration = Calibration().lastValid()
        if calibration is None and calibration.check_in :
            return raw_data

        return age_adjusted_raw_value


    def ageAdjustedFiltered(self):
        usedRaw = self.usedRaw()
        if usedRaw == raw_data or raw_data == 0 :
            return self.filtered_data
        else:
            # adjust the filtered_data with the same factor as the age adjusted raw value
            return self.filtered_data * (usedRaw / self.raw_data)


    # ignores calibration checkins for speed
    def ageAdjustedFiltered_fast(self):
        # adjust the filtered_data with the same factor as the age adjusted raw value
        return self.filtered_data * (self.age_adjusted_raw_value / self.raw_data)


    # the input of this function is a string. each char can be g(=good) or b(=bad) or s(=skip, point unmissed).
    def createlatestTest(self, input, now):
        out = []
        
        for i in range( len(input) ):
            bg = BgReading()
            rand = random.randrange(20000) - 10000
            bg.timestamp = now - i * 5 * 60000 + rand
            bg.raw_data = 150
            if input[i] == 'g' :
                bg.filtered_data = 151
            elif input[i] == 'b' :
                bg.filtered_data = 110
            else:
                continue
            out.append(bg)

        return out


    def TestgetUnclearTime(self, input, interstingTime, expectedResult) :
        now = TimeHelpers.tsl()
        readings = self.createlatestTest(input, now)
        result = self.getUnclearTimeHelper(readings, interstingTime * 60000, now)
        if (result >= expectedResult * 60000 - 20000) and (result <= expectedResult * 60000+20000) :
            app.log.info("Test passed")
        else:
            app.log.info("Test failed expectedResult = " + expectedResult + " result = "+ result / 60000.0)


    def TestgetUnclearTimes(self):
        self.TestgetUnclearTime("gggggggggggggggggggggggg", 90, 0 * 5)
        self.TestgetUnclearTime("bggggggggggggggggggggggg", 90, 1 * 5)
        self.TestgetUnclearTime("bbgggggggggggggggggggggg", 90, 2 *5 )
        self.TestgetUnclearTime("gbgggggggggggggggggggggg", 90, 2 * 5)
        self.TestgetUnclearTime("gbgggbggbggbggbggbggbgbg", 90, 18 * 5)
        self.TestgetUnclearTime("bbbgggggggbbgggggggggggg", 90, 3 * 5)
        self.TestgetUnclearTime("ggggggbbbbbbgggggggggggg", 90, 0 * 5)
        self.TestgetUnclearTime("ggssgggggggggggggggggggg", 90, 0 * 5)
        self.TestgetUnclearTime("ggssbggssggggggggggggggg", 90, 5 * 5)
        self.TestgetUnclearTime("bb",                       90, 18 * 5)

        # intersting time is 2 minutes, we should always get 0 (in 5 minutes units
        self.TestgetUnclearTime("gggggggggggggggggggggggg", 2, 0  * 5)
        self.TestgetUnclearTime("bggggggggggggggggggggggg", 2, 2)
        self.TestgetUnclearTime("bbgggggggggggggggggggggg", 2, 2)
        self.TestgetUnclearTime("gbgggggggggggggggggggggg", 2, 2)
        self.TestgetUnclearTime("gbgggbggbggbggbggbggbgbg", 2, 2)

        # intersting time is 10 minutes, we should always get 0 (in 5 minutes units
        self.TestgetUnclearTime("gggggggggggggggggggggggg", 10, 0  * 5)
        self.TestgetUnclearTime("bggggggggggggggggggggggg", 10, 1 * 5)
        self.TestgetUnclearTime("bbgggggggggggggggggggggg", 10, 2 * 5)
        self.TestgetUnclearTime("gbgggggggggggggggggggggg", 10, 2 * 5)
        self.TestgetUnclearTime("gbgggbggbggbggbggbggbgbg", 10, 2 * 5)
        self.TestgetUnclearTime("bbbgggggggbbgggggggggggg", 10, 2 * 5)
        self.TestgetUnclearTime("ggggggbbbbbbgggggggggggg", 10, 0 * 5)
        self.TestgetUnclearTime("ggssgggggggggggggggggggg", 10, 0 * 5)
        self.TestgetUnclearTime("ggssbggssggggggggggggggg", 10, 2 * 5)
        self.TestgetUnclearTime("bb",                       10, 2 * 5)


    def getSlopeOrdinal(self):
        slope_by_minute = self.calculated_value_slope * 60000
        ordinal = 0
        if not hide_slope:
            if slope_by_minute <= (-3.5) :
                ordinal = 7
            elif slope_by_minute <= (-2) :
                ordinal = 6
            elif slope_by_minute <= (-1) :
                ordinal = 5
            elif slope_by_minute <= (1) :
                ordinal = 4
            elif slope_by_minute <= (2) :
                ordinal = 3
            elif slope_by_minute <= (3.5) :
                ordinal = 2
            else:
                ordinal = 1

        return ordinal


    def getMgdlValue(self) :
        return self.calculated_value


    def getEpochTimestamp(self):
        return self.timestamp
