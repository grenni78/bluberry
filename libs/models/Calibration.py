"""

"""

import logging
from peewee import *
from bluberry import *
from libs.tools import TimeHelpers
from libs import Constants
from libs.models.Sensor import *
from libs.models.bgReading import *

log = logging.getLogger(__name__)

class SlopeParameters:
    LOW_SLOPE_1 = 0
    LOW_SLOPE_2 = 0
    HIGH_SLOPE_1 = 0
    HIGH_SLOPE_2 = 0
    DEFAULT_LOW_SLOPE_LOW = 0
    DEFAULT_LOW_SLOPE_HIGH = 0
    DEFAULT_SLOPE = 0
    DEFAULT_HIGH_SLOPE_HIGH = 0
    DEFAULT_HIGH_SLOPE_LOW = 0

    def getLowSlope1(self):
        return self.LOW_SLOPE_1

    def getLowSlope2(self):
        return self.LOW_SLOPE_2

    def getHighSlope1(self):
        return self.HIGH_SLOPE_1

    def getHighSlope2(self):
        return self.HIGH_SLOPE_2

    def getDefaultLowSlopeLow(self):
        return self.DEFAULT_LOW_SLOPE_LOW

    def getDefaultLowSlopeHigh(self):
        return self.DEFAULT_LOW_SLOPE_HIGH

    def getDefaultSlope(self):
        return self.DEFAULT_SLOPE

    def getDefaultHighSlopeHigh(self):
        return self.DEFAULT_HIGH_SLOPE_HIGH

    def getDefaulHighSlopeLow(self):
        return self.DEFAULT_HIGH_SLOPE_LOW


class DexParameters(SlopeParameters):
    def __init__(self):
        self.LOW_SLOPE_1 = 0.75
        self.LOW_SLOPE_2 = 0.70
        self.HIGH_SLOPE_1 = 1.5
        self.HIGH_SLOPE_2 = 1.6
        self.DEFAULT_LOW_SLOPE_LOW = 0.7
        self.DEFAULT_LOW_SLOPE_HIGH = 0.70
        self.DEFAULT_SLOPE = 1
        self.DEFAULT_HIGH_SLOPE_HIGH = 1.5
        self.DEFAULT_HIGH_SLOPE_LOW = 1.4


class DexOldSchoolParameters(SlopeParameters):
    # Previous defaults up until 20th March 2017
    def __init__(self):
        self.LOW_SLOPE_1 = 0.95
        self.LOW_SLOPE_2 = 0.85
        self.HIGH_SLOPE_1 = 1.3
        self.HIGH_SLOPE_2 = 1.4
        self.DEFAULT_LOW_SLOPE_LOW = 1.08
        self.DEFAULT_LOW_SLOPE_HIGH = 1.15
        self.DEFAULT_SLOPE = 1
        self.DEFAULT_HIGH_SLOPE_HIGH = 1.3
        self.DEFAULT_HIGH_SLOPE_LOW = 1.2


class DexParametersAdrian(SlopeParameters):
    """
    Other default vlaues and thresholds that can be only activated in settings, when in engineering mode.
    promoted to be the regular defaults 20th March 2017
    """
    def __init__(self):
        self.LOW_SLOPE_1 = 0.75
        self.LOW_SLOPE_2 = 0.70
        self.HIGH_SLOPE_1 = 1.3
        self.HIGH_SLOPE_2 = 1.4
        self.DEFAULT_LOW_SLOPE_LOW = 0.75
        self.DEFAULT_LOW_SLOPE_HIGH = 0.70
        self.DEFAULT_SLOPE = 1
        self.DEFAULT_HIGH_SLOPE_HIGH = 1.3
        self.DEFAULT_HIGH_SLOPE_LOW = 1.2


class LiParameters(SlopeParameters):
    def __init__(self):
        self.LOW_SLOPE_1 = 1
        self.LOW_SLOPE_2 = 1
        self.HIGH_SLOPE_1 = 1
        self.HIGH_SLOPE_2 = 1
        self.DEFAULT_LOW_SLOPE_LOW = 1
        self.DEFAULT_LOW_SLOPE_HIGH = 1
        self.DEFAULT_SLOPE = 1
        self.DEFAULT_HIGH_SLOPE_HIGH = 1
        self.DEFAULT_HIGH_SLOPE_LOW = 1

# Alternate Li Parameters which don't use a fixed slope #
class LiParametersNonFixed(SlopeParameters):
    def __init__(self):
        self.LOW_SLOPE_1 = 0.55
        self.LOW_SLOPE_2 = 0.50
        self.HIGH_SLOPE_1 = 1.5
        self.HIGH_SLOPE_2 = 1.6
        self.DEFAULT_LOW_SLOPE_LOW = 0.55
        self.DEFAULT_LOW_SLOPE_HIGH = 0.50
        self.DEFAULT_SLOPE = 1
        self.DEFAULT_HIGH_SLOPE_HIGH = 1.5
        self.DEFAULT_HIGH_SLOPE_LOW = 1.4

class TestParameters(SlopeParameters):
    def __init__(self):
        self.LOW_SLOPE_1 = 0.85 #0.95
        self.LOW_SLOPE_2 = 0.80 #0.85
        self.HIGH_SLOPE_1 = 1.3
        self.HIGH_SLOPE_2 = 1.4
        self.DEFAULT_LOW_SLOPE_LOW = 0.9 #1.08
        self.DEFAULT_LOW_SLOPE_HIGH = 0.95 #1.15
        self.DEFAULT_SLOPE = 1
        self.DEFAULT_HIGH_SLOPE_HIGH = 1.3
        self.DEFAULT_HIGH_SLOPE_LOW = 1.2


class Calibration(Model):
    _note_only_marker = 0.000001

    _ID = IdentityField(name="_ID")

    timestamp = BigIntegerField(index = True)

    sensor_age_at_time_of_estimation = DoubleField()

    sensor = BareField(index = True)

    bg = DoubleField()

    raw_value = DoubleField()

    adjusted_raw_value = DoubleField()

    sensor_confidence = DoubleField()

    slope_confidence = DoubleField()

    raw_timestamp = BigIntegerField()

    slope = DoubleField()

    intercept = DoubleField()

    distance_from_estimate = DoubleField()

    estimate_raw_at_time_of_calibration = DoubleField()

    estimate_bg_at_time_of_calibration = DoubleField()

    uuid = CharField(index = True)

    sensor_uuid = CharField(index = True)

    possible_bad = BooleanField(default=False)

    check_in = BooleanField()

    first_decay = DoubleField()

    second_decay = DoubleField()

    first_slope = DoubleField()

    second_slope = DoubleField()

    first_intercept = DoubleField()

    second_intercept = DoubleField()

    first_scale = DoubleField()

    second_scale = DoubleField()


    def initialCalibration(self, bg1, bg2, context):
        unit = self.prefs.getValue("units", "mgdl")
        
        if not unit == "mgdl":
            bg1 = bg1 * Constants.MMOLL_TO_MGDL
            bg2 = bg2 * Constants.MMOLL_TO_MGDL

        self.clear_all_existing_calibrations()

        higherCalibration = Calibration.create()
        lowerCalibration = Calibration.create()
        sensor = Sensor.currentSensor()
        bgReadings = BgReading.latest_by_size(number = 3)

        # don't allow initial calibration if data would be stale
        if (bgReadings is None) or (not bgReadings.size() == 3) or not self.isDataSuitableForDoubleCalibration():
            log.warn("Did not find 3 readings for initial calibration - aborting")
            return

        bgReading1 = bgReadings.get(0)
        bgReading2 = bgReadings.get(1)

        if  not SensorSanity.isRawValueSane(bgReading1.raw_data) or not SensorSanity.isRawValueSane(bgReading2.raw_data):
            log.warn("Sensor raw data is outside sane range! Cannot calibrate: %s %s", bgReading1.raw_data, bgReading2.raw_data)
            return

        highBgReading = None
        lowBgReading = None
        higher_bg = max(bg1, bg2)
        lower_bg = min(bg1, bg2)

        # TODO This should be reworked in the future as it doesn't really make sense
        if bgReading1.raw_data > bgReading2.raw_data:
            highBgReading = bgReading1
            lowBgReading = bgReading2
        else:
            highBgReading = bgReading2
            lowBgReading = bgReading1

        higherCalibration.bg = higher_bg
        higherCalibration.slope = 1
        higherCalibration.intercept = higher_bg
        higherCalibration.sensor = sensor
        higherCalibration.estimate_raw_at_time_of_calibration = highBgReading.age_adjusted_raw_value
        higherCalibration.adjusted_raw_value = highBgReading.age_adjusted_raw_value
        higherCalibration.raw_value = highBgReading.raw_data
        higherCalibration.raw_timestamp = highBgReading.timestamp
        higherCalibration.save()

        highBgReading.calculated_value = higher_bg
        highBgReading.calibration_flag = true
        highBgReading.calibration = higherCalibration
        highBgReading.save()
        higherCalibration.save()

        lowerCalibration.bg = lower_bg
        lowerCalibration.slope = 1
        lowerCalibration.intercept = lower_bg
        lowerCalibration.sensor = sensor
        lowerCalibration.estimate_raw_at_time_of_calibration = lowBgReading.age_adjusted_raw_value
        lowerCalibration.adjusted_raw_value = lowBgReading.age_adjusted_raw_value
        lowerCalibration.raw_value = lowBgReading.raw_data
        lowerCalibration.raw_timestamp = lowBgReading.timestamp
        lowerCalibration.save()

        lowBgReading.calculated_value = lower_bg
        lowBgReading.calibration_flag = true
        lowBgReading.calibration = lowerCalibration
        lowBgReading.save()
        lowerCalibration.save()

        highBgReading.find_new_curve()
        highBgReading.find_new_raw_curve()
        lowBgReading.find_new_curve()
        lowBgReading.find_new_raw_curve()

        calibrations = []
        calibrations.append(lowerCalibration)
        calibrations.append(higherCalibration)

        for calibration in calibrations:
            calibration.timestamp = TimeHelpers.tsl()
            calibration.sensor_uuid = sensor.uuid
            calibration.slope_confidence = .5
            calibration.distance_from_estimate = 0
            calibration.check_in = False
            calibration.sensor_confidence = ((-0.0018 * calibration.bg * calibration.bg) + (0.6657 * calibration.bg) + 36.7505) / 100

            calibration.sensor_age_at_time_of_estimation = calibration.timestamp - sensor.started_at
            calibration.uuid = uuid.uuid4()
            calibration.save()

            self.calculate_w_l_s()
            self.newFingerStickData()
            CalibrationSendQueue.addToQueue(calibration)

        self.adjustRecentBgReadings(5)
        CalibrationRequest().createOffset(lowerCalibration.bg, 35)

        """ context.startService(new Intent("Notifications"))"""


    # Create Calibration Checkin Dexcom Bluetooth Share
    @staticmethod
    def create(calRecords, override=False, addativeOffset=0, bg=None, timeoffset=None, note_only=None, estimatedInterstitialLagSeconds=None):
        if bg is None:
            #TODO: Change calibration.last and other queries to order calibrations by timestamp rather than ID
            log.info("Creating Calibration Record")
            sensor = Sensor.currentSensor()
            firstCalRecord = calRecords[0]
            secondCalRecord = calRecords[0]

            #TODO: Figgure out how the ratio between the two is determined
            calSlope = ((secondCalRecord.getScale() / secondCalRecord.getSlope()) + (3 * firstCalRecord.getScale() / firstCalRecord.getSlope())) * 250

            calIntercept = (((secondCalRecord.getScale() * secondCalRecord.getIntercept()) / secondCalRecord.getSlope()) + ((3 * firstCalRecord.getScale() * firstCalRecord.getIntercept()) / firstCalRecord.getSlope())) / -4
            if sensor is not None:
                for csr in firstCalRecord.getCalSubrecords():
                    if (csr is not None) and Calibration.is_new(csr, addativeOffset) or (i == 0 and override):
                        calSubrecord = csr

                        calibration = Calibration()
                        calibration.bg = calSubrecord.getCalBGL()
                        calibration.timestamp = calSubrecord.getDateEntered().getTime() + addativeOffset
                        calibration.raw_timestamp = calibration.timestamp
                        if calibration.timestamp > TimeHelpers.tsl():
                            log.info("ERROR - Calibration timestamp is from the future, wont save!")
                            return

                        calibration.raw_value = calSubrecord.getCalRaw() / 1000
                        calibration.slope = calSlope
                        calibration.intercept = calIntercept

                        calibration.sensor_confidence = ((-0.0018 * calibration.bg * calibration.bg) + (0.6657 * calibration.bg) + 36.7505) / 100
                        if calibration.sensor_confidence <= 0 :
                            calibration.sensor_confidence = 0

                        calibration.slope_confidence = 0.8  #TODO: query backwards to find this value near the timestamp
                        calibration.estimate_raw_at_time_of_calibration = calSubrecord.getCalRaw() / 1000
                        calibration.sensor = sensor
                        calibration.sensor_age_at_time_of_estimation = calibration.timestamp - sensor.started_at
                        calibration.uuid = uuid.uuid4()
                        calibration.sensor_uuid = sensor.uuid
                        calibration.check_in = True

                        calibration.first_decay = firstCalRecord.getDecay()
                        calibration.second_decay = secondCalRecord.getDecay()
                        calibration.first_slope = firstCalRecord.getSlope()
                        calibration.second_slope = secondCalRecord.getSlope()
                        calibration.first_scale = firstCalRecord.getScale()
                        calibration.second_scale = secondCalRecord.getScale()
                        calibration.first_intercept = firstCalRecord.getIntercept()
                        calibration.second_intercept = secondCalRecord.getIntercept()

                        calibration.save()
                        CalibrationSendQueue.addToQueue(calibration)
                        Calibration.requestCalibrationIfRangeTooNarrow()
                        self.newFingerStickData()

                if (firstCalRecord.getCalSubrecords()[0] is not None) and (firstCalRecord.getCalSubrecords()[2] is None) :
                    if Calibration.latest(2).size() == 1 :
                        Calibration.create(calRecords, True, 0)
            else:
                unit = prefs.getString("units", "mgdl")
                adjustPast = app.pprefs.getValue("rewrite_history", True)

                if unit.compareTo("mgdl") != 0:
                    bg = bg * Constants.MMOLL_TO_MGDL

                if (bg < 40) or (bg > 400) :
                    log.warn("Invalid out of range calibration glucose mg/dl value of: " + bg)
                    return None


                if not note_only:
                    CalibrationRequest.clearAll()

                calibration = Calibration()


                if sensor is None:
                    Sensor.create(math.round(TimeHelpers.ts())) # no sensor? no problem, create virtual one for follower
                    sensor = Sensor.currentSensor()


                if sensor is not None:
                    bgReading = None
                    if timeoffset == 0:
                        bgReading = BgReading.last()
                    else:
                        # get closest bg reading we can find with a cut off at 15 minutes max time
                        bgReading = BgReading.getForPreciseTimestamp(TimeHelpers.tsl() - ((timeoffset - estimatedInterstitialLagSeconds) * 1000 ), (15 * 60 * 1000))

                    if bgReading is not None:
                        if SensorSanity.isRawValueSane(bgReading.raw_data, DexCollectionType.getDexCollectionType()):
                            calibration.sensor = sensor
                            calibration.bg = bg
                            calibration.check_in = False
                            calibration.timestamp = TimeHelpers.tsl() - (timeoffset * 1000) #  potential historical bg readings
                            calibration.raw_value = bgReading.raw_data
                            calibration.adjusted_raw_value = bgReading.age_adjusted_raw_value
                            calibration.sensor_uuid = sensor.uuid
                            calibration.slope_confidence = math.min(math.max(((4 - Math.abs((bgReading.calculated_value_slope) * 60000)) / 4), 0), 1)

                            estimated_raw_bg = BgReading.estimated_raw_bg(TimeHelpers.tsl())
                            calibration.raw_timestamp = bgReading.timestamp
                            if math.abs(estimated_raw_bg - bgReading.age_adjusted_raw_value) > 20:
                                calibration.estimate_raw_at_time_of_calibration = bgReading.age_adjusted_raw_value
                            else:
                                calibration.estimate_raw_at_time_of_calibration = estimated_raw_bg

                            calibration.distance_from_estimate = math.abs(calibration.bg - bgReading.calculated_value)
                            if not note_only:
                                calibration.sensor_confidence = math.max(((-0.0018 * bg * bg) + (0.6657 * bg) + 36.7505) / 100, 0)
                            else:
                                calibration.sensor_confidence = 0 # exclude from calibrations but show on graph
                                calibration.slope_confidence = note_only_marker # this is a bit ugly
                                calibration.slope = 0
                                calibration.intercept = 0

                            calibration.sensor_age_at_time_of_estimation = calibration.timestamp - sensor.started_at
                            calibration.uuid = uuid.uuid4()
                            calibration.save()

                            if not note_only:
                                bgReading.calibration = calibration
                                bgReading.calibration_flag = True
                                bgReading.save()

                            if not note_only:
                                BgSendQueue.handleNewBgReading(bgReading, "update")
                                # TODO probably should add a more fine grained prefs option in future
                                self.calculate_w_l_s(app.pprefs.getValue("infrequent_calibration", False))
                                CalibrationSendQueue.addToQueue(calibration)
                                BgReading.pushBgReadingSyncToWatch(bgReading, False)
                                if adjustPast:
                                    adjustRecentBgReadings(30)
                                else:
                                    adjustRecentBgReadings(2)
                                
                                Calibration.requestCalibrationIfRangeTooNarrow()
                                self.newFingerStickData()
                            else:
                                log.info("Follower mode or note so not processing calibration deeply")
                        else:
                            
                            log.info("Sensor data fails sanity test - Cannot Calibrate! raw:" + bgReading.raw_data)
                else:
                    log.warn("CALIBRATION", "No sensor, cant save!")

                return Calibration.last()


    def is_new(self, calSubrecord, addativeOffset):
        sensor = Sensor.currentSensor()
        calibration = this.get(Calibration.sensor == sensor.getId() and Calibration.timestamp <= calSubrecord.getDateEntered().getTime() + addativeOffset + (1000 * 60 * 2)).order_by("timestamp desc").limit(1)

        if (calibration is not None) and math.abs(calibration.timestamp - (calSubrecord.getDateEntered().getTime() + addativeOffset)) < (4 * 60 * 1000):
            log.d("Already have that calibration!")
            return False
        else:
            log.info("Looks like a new calibration!")
            return True


    def getForTimestamp(self, timestamp):
        sensor = Sensor.currentSensor()
        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.timestamp < timestamp).order_by("timestamp desc").limit(1)


    def getByTimestamp(self, timestamp):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return self.get(Calibration.sensor == sensor.getId() and Calibration.timestamp == timestamp).limit(1)


    # regular calibration

    def allForSensorInLastFiveDays(self):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.timestamp > TimeHelpers.tsl() - (60000 * 60 * 24 * 5)).order_by("timestamp desc")


    def calculate_w_l_s(self, extended = False):
        if Sensor().isActive():
            l = 0
            m = 0
            n = 0
            p = 0
            q = 0
            w = 0

            sParams = self.getSlopeParameters()

            calibrations = self.allForSensorInLastFourDays() # 5 days was a bit much, dropped this to 4

            if calibrations is None:
                log.info("Somehow ended up with null calibration list!")
                return

            # less than 5 calibrations in last 4 days? cast the net wider if in extended mode
            ccount = calibrations.size()
            if (ccount < 5) and extended:
                calibrations = self.allForSensorLimited(5)
                if len(calibrations) > ccount :
                    userinteract.info("Calibration", "Calibrated using data beyond last 4 days")

            if len(calibrations) <= 1 :
                calibration = Calibration.last()

                calibration.slope = 1
                calibration.intercept = calibration.bg - (calibration.raw_value * calibration.slope)
                calibration.save()
                CalibrationRequest.createOffset(calibration.bg, 25)
                self.newFingerStickData()
            else:
                for calibration in calibrations:
                    w = calibration.calculateWeight()
                    l += (w)
                    m += (w * calibration.estimate_raw_at_time_of_calibration)
                    n += (w * calibration.estimate_raw_at_time_of_calibration * calibration.estimate_raw_at_time_of_calibration)
                    p += (w * calibration.bg)
                    q += (w * calibration.estimate_raw_at_time_of_calibration * calibration.bg)

                last_calibration = Calibration.last()
                if last_calibration is not None:

                    w = (last_calibration.calculateWeight() * (calibrations.size() * 0.14))
                    l += (w)
                    m += (w * last_calibration.estimate_raw_at_time_of_calibration)
                    n += (w * last_calibration.estimate_raw_at_time_of_calibration * last_calibration.estimate_raw_at_time_of_calibration)
                    p += (w * last_calibration.bg)
                    q += (w * last_calibration.estimate_raw_at_time_of_calibration * last_calibration.bg)

                d = (l * n) - (m * m)
                calibration = Calibration.last()

                calibration.intercept = ((n * p) - (m * q)) / d
                calibration.slope = ((l * q) - (m * p)) / d
                log.info("Calibration slope debug: slope:" + calibration.slope + " q:" + q + " m:" + m + " p:" + p + " d:" + d)
                if len(calibrations) == 2 and (calibration.slope < sParams.getLowSlope1()) or (calibration.slope < sParams.getLowSlope2()): # I have not seen a case where a value below 7.5 proved to be accurate but we should keep an eye on this
                    log.info("calibration.slope 1 : " + calibration.slope)
                    calibration.slope = calibration.slopeOOBHandler(0)
                    log.info("calibration.slope 2 : " + calibration.slope)
                    if calibrations.size() > 2:
                        calibration.possible_bad = true

                    calibration.intercept = calibration.bg - (calibration.estimate_raw_at_time_of_calibration * calibration.slope)
                    CalibrationRequest.createOffset(calibration.bg, 25)

                if len(calibrations) == 2 and (calibration.slope > sParams.getHighSlope1()) or (calibration.slope > sParams.getHighSlope2()):
                    log.info("calibration.slope 3 : " + calibration.slope)
                    calibration.slope = calibration.slopeOOBHandler(1)
                    log.info("calibration.slope 4 : " + calibration.slope)
                    if len(calibrations) > 2 :
                        calibration.possible_bad = True

                    calibration.intercept = calibration.bg - (calibration.estimate_raw_at_time_of_calibration * calibration.slope)
                    CalibrationRequest.createOffset(calibration.bg, 25)

                log.info("Calculated Calibration Slope: " + calibration.slope)
                log.info("Calculated Calibration intercept: " + calibration.intercept)

                # sanity check result
                if calibration.slope == float("inf") or calibration.slope == float('nan') or calibration.intercept == float("inf") or calibration == float('nan'):
                    calibration.sensor_confidence = 0
                    calibration.slope_confidence = 0
                    userinteract.warn("Calibrate","Got invalid impossible slope calibration!")
                    calibration.save()  # Save nulled record, lastValid should protect from bad calibrations
                    self.newFingerStickData()


                if (calibration.slope == 0) and (calibration.intercept == 0):
                    calibration.sensor_confidence = 0
                    calibration.slope_confidence = 0
                    userinteract.warn("Calibrate","Got invalid zero slope calibration!")
                    calibration.save() # Save nulled record, lastValid should protect from bad calibrations
                    self.newFingerStickData()
                else:
                    calibration.save()
                    self.newFingerStickData()
        else:
            log.info("NO Current active sensor found!!")


    def getSlopeParameters(self):

        if CollectionServiceStarter.isLimitter():
            if app.ppref.getValue("use_non_fixed_li_parameters", False):
                return LiParametersNonFixed()
            else:
                return LiParameters()

        # open question about parameters used with LibreAlarm

        if app.ppref.getValue("engineering_mode",False) and app.ppref.getValue("old_school_calibration_mode",False):
            userinteract.info("getSlopeParameters","Using old pre-2017 calibration mode!")
            return DexOldSchoolParameters()

        return DexParameters()


    # here be dragons.. at time of writing estimate_bg_at_time_of_calibration is never written to and the possible_bad logic below looks backwards but
    # will never fire because the bg_at_time_of_calibration is not set.
    def slopeOOBHandler(self, status):

        sParams = self.getSlopeParameters()

        # If the last slope was reasonable and reasonably close, use that, otherwise use a slope that may be a little steep, but its best to play it safe when uncertain
        calibrations = self.latest(3)
        thisCalibration = calibrations[0]
        if status == 0:
            if len(calibrations) == 3 :
                if (math.abs(thisCalibration.bg - thisCalibration.estimate_bg_at_time_of_calibration) < 30) and (calibrations[1].slope != 0) and (calibrations[1].possible_bad is not None) and calibrations[1].possible_bad:
                    return calibrations[1].slope
                else:
                    return math.max(((-0.048) * (thisCalibration.sensor_age_at_time_of_estimation / (60000 * 60 * 24))) + 1.1, sParams.getDefaultLowSlopeLow())
            elif len(calibrations) == 2:
                return math.max(((-0.048) * (thisCalibration.sensor_age_at_time_of_estimation / (60000 * 60 * 24))) + 1.1, sParams.getDefaultLowSlopeHigh())

            return sParams.getDefaultSlope()
        else:
            if len(calibrations) == 3:
                if (math.abs(thisCalibration.bg - thisCalibration.estimate_bg_at_time_of_calibration) < 30) and (calibrations[1].slope != 0) and (calibrations[1].possible_bad is not None and calibrations[1].possible_bad == True):
                    return calibrations[1].slope
                else:
                    return sParams.getDefaultHighSlopeHigh()
            elif len(calibrations) == 2 :
                return sParams.getDefaulHighSlopeLow()

        return sParams.getDefaultSlope()


    def calibrations_for_sensor(self, sensor):
        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0).order_by("timestamp desc")


    def calculateWeight(self):
        firstTimeStarted = self.first().sensor_age_at_time_of_estimation
        lastTimeStarted = self.last().sensor_age_at_time_of_estimation
        time_percentage = math.min(((sensor_age_at_time_of_estimation - firstTimeStarted) / (lastTimeStarted - firstTimeStarted)) / (.85), 1)
        time_percentage = (time_percentage + .01)
        log.info("CALIBRATIONS TIME PERCENTAGE WEIGHT: " + time_percentage)
        return math.max((((((slope_confidence + sensor_confidence) * (time_percentage))) / 2) * 100), 1)


    def adjustRecentBgReadings(self, adjustCount):
        #TODO: add some handling around calibration overrides as they come out looking a bit funky
        calibrations = self.latest(3)
        if calibrations is None:
            log.warn("Calibrations is null in adjustRecentBgReadings")
            return

        bgReadings = BgReading().latestUnCalculated(adjustCount)
        if bgReadings is None:
            log.wtf(TAG, "bgReadings is null in adjustRecentBgReadings")
            return

        # ongoing calibration
        if len(calibrations) >= 3:
            denom = len(bgReadings)
            
            try:
                latestCalibration = self.lastValid()
                i = 0
                for bgReading in bgReadings:
                    oldYValue = bgReading.calculated_value
                    newYvalue = (bgReading.age_adjusted_raw_value * latestCalibration.slope) + latestCalibration.intercept
                    new_calculated_value = ((newYvalue * (denom - i)) + (oldYValue * (i))) / denom
                    
                    if bgReading.filtered_calculated_value == bgReading.calculated_value:
                        bgReading.filtered_calculated_value = new_calculated_value

                    bgReading.calculated_value = new_calculated_value

                    bgReading.save()
                    BgReading.pushBgReadingSyncToWatch(bgReading, False)
                    i += 1
            except AssertionError as e:
                log.warn("Null pointer in AdjustRecentReadings >=3: ", e)

        elif len(calibrations) == 2:
            
            try:
                latestCalibration = self.lastValid()
                for bgReading in bgReadings:
                    newYvalue = (bgReading.age_adjusted_raw_value * latestCalibration.slope) + latestCalibration.intercept
                    if bgReading.filtered_calculated_value == bgReading.calculated_value:
                        bgReading.filtered_calculated_value = newYvalue

                    bgReading.calculated_value = newYvalue
                    BgReading.updateCalculatedValueToWithinMinMax(bgReading)
                    bgReading.save()
                    BgReading.pushBgReadingSyncToWatch(bgReading, False)

            except AssertionError as e:
                log.debug("Null pointer in AdjustRecentReadings ==2: ", e)

        try:
            # TODO this method call is probably only needed when we are called for initial calibration, it should probably be moved
            bgReadings[0].find_new_raw_curve()
            bgReadings[0].find_new_curve()
            BgReading.pushBgReadingSyncToWatch(bgReadings[0], False)
        except AssertionError as e:
            log.debug("Got null pointer exception in adjustRecentBgReadings",e)


    def rawValueOverride(self, rawValue):
        estimate_raw_at_time_of_calibration = rawValue
        self.save()
        self.calculate_w_l_s()
        CalibrationSendQueue.addToQueue(this, context)


    def requestCalibrationIfRangeTooNarrow(self):
        max = self.max_recent()
        min = self.min_recent()
        if max - min < 55:
            avg = ((min + max) / 2)
            dist = max - avg
            CalibrationRequest().createOffset(avg, dist + 20)


    def clear_all_existing_calibrations(self):
        CalibrationRequest.clearAll()
        pastCalibrations = self.allForSensor()
        if pastCalibrations is not None:
            for calibration in pastCalibrations:
                calibration.slope_confidence = 0
                calibration.sensor_confidence = 0
                calibration.save()
                self.newFingerStickData()


    def msSinceLastCalibration(self):
        calibration = self.lastValid()
        if calibration is None:
            return 86400000000
        return TimeHelpers.msSince(calibration.timestamp)


    def clearLastCalibration(self):
        CalibrationRequest.clearAll()
        log.info("Trying to clear last calibration")
        calibration = self.last()
        if calibration is not None:
            calibration.invalidate()
            CalibrationSendQueue.addToQueue(calibration)
            self.newFingerStickData()


    def clearCalibrationByUUID(self, uuid):
        calibration = self.byuuid(uuid)
        if calibration is not None:
            CalibrationRequest.clearAll()
            apop.log.info("Trying to clear last calibration: " + uuid)
            calibration.invalidate()
            CalibrationSendQueue.addToQueue(calibration)
            self.newFingerStickData()
        else:
            log.info("Could not find calibration to clear: "+uuid)


    def toS(self):
        return json.dumps(self)


    def byid(self, id):
        return self.get(Calibration._ID == id)


    def byuuid(self, uuid):
        if uuid is None:
            return None
        return self.get(Calibration.uuid == uuid).order_by("_ID desc").limit(1)


    def clear_byuuid(self, uuid, from_interactive):
        if uuid is None:
            return
        calibration = self.byuuid(uuid)
        if calibration is not None:
            calibration.invalidate()
            CalibrationSendQueue.addToQueue(calibration)
            self.newFingerStickData()
            if from_interactive:
                GcmActivity.clearLastCalibration(uuid)


    def upsertFromMaster(self, jsonCalibration):
        if jsonCalibration is None:
            log.warn("Got null calibration from json")
            return
        try:
            sensor = Sensor.getByUuid(jsonCalibration.sensor_uuid)
            if sensor is None:
                log.warn("No sensor found, ignoring cailbration " + jsonCalibration.sensor_uuid)
                return

            existingCalibration = self.byuuid(jsonCalibration.uuid)
            if existingCalibration is None:
                log.info("saving new calibration record. sensor uuid =" + jsonCalibration.sensor_uuid + " calibration uuid = " + jsonCalibration.uuid)
                jsonCalibration.sensor = sensor
                jsonCalibration.save()
            else:
                log.info("updating existing calibration record: " + jsonCalibration.uuid)
                existingCalibration.sensor = sensor
                existingCalibration.timestamp = jsonCalibration.timestamp
                existingCalibration.sensor_age_at_time_of_estimation = jsonCalibration.sensor_age_at_time_of_estimation
                existingCalibration.bg = jsonCalibration.bg
                existingCalibration.raw_value = jsonCalibration.raw_value
                existingCalibration.adjusted_raw_value = jsonCalibration.adjusted_raw_value
                existingCalibration.sensor_confidence = jsonCalibration.sensor_confidence
                existingCalibration.slope_confidence = jsonCalibration.slope_confidence
                existingCalibration.raw_timestamp = jsonCalibration.raw_timestamp
                existingCalibration.slope = jsonCalibration.slope
                existingCalibration.intercept = jsonCalibration.intercept
                existingCalibration.distance_from_estimate = jsonCalibration.distance_from_estimate
                existingCalibration.estimate_raw_at_time_of_calibration = jsonCalibration.estimate_raw_at_time_of_calibration
                existingCalibration.estimate_bg_at_time_of_calibration = jsonCalibration.estimate_bg_at_time_of_calibration
                existingCalibration.uuid = jsonCalibration.uuid
                existingCalibration.sensor_uuid = jsonCalibration.sensor_uuid
                existingCalibration.possible_bad = jsonCalibration.possible_bad
                existingCalibration.check_in = jsonCalibration.check_in
                existingCalibration.first_decay = jsonCalibration.first_decay
                existingCalibration.second_decay = jsonCalibration.second_decay
                existingCalibration.first_slope = jsonCalibration.first_slope
                existingCalibration.second_slope = jsonCalibration.second_slope
                existingCalibration.first_intercept = jsonCalibration.first_intercept
                existingCalibration.second_intercept = jsonCalibration.second_intercept
                existingCalibration.first_scale = jsonCalibration.first_scale
                existingCalibration.second_scale = jsonCalibration.second_scale
                
                existingCalibration.save()

        except AssertionError as e:
            log.debug("Could not save Calibration: ", e)


    # COMMON SCOPES!
    @staticmethod
    def last(self):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return Calibration.get(Calibration.sensor == sensor.getId()).order_by("timestamp desc").limit(1)

    @staticmethod
    def lastValid():
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return Calibration.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.slope != 0).order_by("timestamp desc").limit(1)

    @staticmethod
    def first():
        sensor = Sensor.currentSensor()
        return Calibration.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0).order_by("timestamp asc").limit(1)

    @staticmethod
    def max_recent():
        sensor = Sensor.currentSensor()
        calibration = Calibration.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.timestamp > (TimeHelpers.tsl() - (60000 * 60 * 24 * 4))).order_by("bg desc").limit(1)

        if calibration is not None:
            return calibration.bg
        else:
            return 120

    @staticmethod
    def min_recent():
        sensor = Sensor.currentSensor()
        calibration = Calibration.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.timestamp > (TimeHelpers.tsl() - (60000 * 60 * 24 * 4))).order_by("bg asc").limit(1)

        if calibration is not None:
            return calibration.bg
        else:
            return 100


    def latest(self, number):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return self.get(Calibration.sensor == sensor.getId()).order_by("timestamp desc").limit(number)


    def latestValid(self,number, until = None):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        if until is None:
            until = TimeHelpers.tsl() + Constants.HOUR_IN_MS

        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.slope != 0 and Calibration.timestamp <= until).order_by("timestamp desc").limit(number)


    def latestForGraph(self, number, startTime):
        return self.latestForGraph(number, startTime, TimeHelpers.tsl())


    def latestForGraph(self, number, startTime, endTime):
        return self.get(Calibration.timestamp >= math.max(startTime, 0) and Calibration.timestamp <= endTime and (Calibration.slope != 0 or Calibration.slope_confidence == Calibration.note_only_marker)).order_by("timestamp desc").limit(number)


    def latestForGraphSensor(self, number, startTime, endTime):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return self.get(Calibration.sensor == sensor.getId() and Calibration.timestamp >= math.max(startTime, 0) and Calibration.timestamp <= endTime and (Calibration.slope != 0 or Calibration.slope_confidence == Calibration.note_only_marker)).order_by("timestamp desc").limit(number)


    def allForSensor(self):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0).order_by("timestamp desc")


    def allForSensorInLastFourDays(self):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None
        
        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0 and Calibration.timestamp > (TimeHelpers.tsl() - (60000 * 60 * 24 * 4))).order_by("timestamp desc")


    def allForSensorLimited(self, limit):
        sensor = Sensor.currentSensor()
        if sensor is None:
            return None

        return self.get(Calibration.sensor == sensor.getId() and Calibration.slope_confidence != 0 and Calibration.sensor_confidence != 0).order_by("timestamp desc").limit(limit)


    def getCalibrationsForSensor(self, sensor, limit):
        return self.get(Calibration.sensor_uuid == sensor.uuid).order_by("timestamp desc").limit(limit)


    def futureCalibrations(self):
        timestamp = TimeHelpers.tsl()
        return self.get(Calibration.timestamp > timestamp).order_by("timestamp desc")


    def isNote(self):
        calibration = self
        if calibration.slope == 0 and (calibration.slope_confidence == self.note_only_marker) and (calibration.sensor_confidence == 0) and (calibration.intercept == 0):
            return True
        else:
            return False


    def isValid(self):
        calibration = self
        if (calibration.slope_confidence != 0) and (calibration.sensor_confidence != 0) and (calibration.slope != 0) and (calibration.intercept != 0):
            return True
        else:
            return False


    def invalidate(self):
        self.slope_confidence = 0
        self.sensor_confidence = 0
        self.slope = 0
        self.intercept = 0
        self.save()
        PluggableCalibration.invalidateAllCaches()


    def invalidateAllForSensor(self):
        cals = self.allForSensorLimited(9999999)
        if cals is not None:
            for cal in cals:
                cal.invalidate()

        log.info("Deleted all calibrations for sensor")
        userinteract.info("Deleted all calibrations for sensor")
