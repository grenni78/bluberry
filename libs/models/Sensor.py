
"""
 Verwaltung der Sensoren
"""
import json
import logging
from peewee import *
from playhouse import shortcuts
import libs.tools.TimeHelpers as TimeHelpers
from libs.models.SensorSendQueue import SensorSendQueue

log = logging.getLogger(__name__)

class Sensor(Model):
    _ID = IdentityField(column_name="_ID")

    started_at = BigIntegerField(index=True, default=0)

    stopped_at = BigIntegerField(default=0)

    latest_minimal_battery_level = IntegerField(default=0)

    latest_battery_level = IntegerField(default=0)

    uuid_str = CharField(index=True, name="uuid")

    sensor_location = CharField()

    class Meta:
        legacy_table_names = False

    @staticmethod
    def create(started_at, uuid_str=None, stopped_at=None, latest_battery_level=None):
        sensor = None

        if latest_battery_level is not None:
            try:
                sensor = Sensor.get(Sensor.started_at == started_at)
                log.info("updatinga an existing sensor")
            except DoesNotExist:
                log.info("Sensor started at {} not found!".format(started_at))

        if sensor is None:
            log.info("creating a new sensor")
            sensor = Sensor()

        sensor.started_at = started_at
        if stopped_at is not None:
            sensor.stopped_at = stopped_at

        if uuid_str is None:
            sensor.uuid_str = uuid.uuid4()
        else:
            sensor.uuid_str = uuid_str

        sensor.save()
        SensorSendQueue.addToQueue(sensor)
        log.info("SENSOR MODEL: {}".format(sensor))
        return sensor

    @staticmethod
    def createUpdate(started_at, stopped_at, latest_battery_level, uuid_str):

        sensor = Sensor.getByTimestamp(started_at)
        if sensor is not None:
            log.info("updatinga an existing sensor")
        else:
            log.info("creating a new sensor")
            sensor = Sensor()

        sensor.started_at = started_at
        sensor.stopped_at = stopped_at
        sensor.latest_battery_level = latest_battery_level
        sensor.uuid_str = uuid_str
        sensor.save()

    @staticmethod
    def stopSensor():
        sensor = Sensor.currentSensor()
        if sensor is None:
            return

        sensor.stopped_at = TimeHelpers.tsl()
        log.info("Sensor stopped at {}".format(sensor.stopped_at))
        sensor.save()
        SensorSendQueue.addToQueue(sensor)


    def toS(self):
        model_dict = shortcuts.model_to_dict(self, backrefs=True)
        log.info( "Sensor toS uuid=" + self.uuid_str + " started_at=" + self.started_at + " active=" + self.isActive() + " battery=" + self.latest_battery_level + " location=" + self.sensor_location + " stopped_at=" + self.stopped_at)
        return json.dumps(model_dict)

    @staticmethod
    def currentSensor():
        try:
            sensor = Sensor.get(Sensor.started_at != 0, Sensor.stopped_at == 0).orderBy("_ID desc")
            return sensor
        except DoesNotExist:
            return None


    @staticmethod
    def isActive():
        sensor = Sensor.currentSensor()
        if sensor is None:
            return False
        return True

    @staticmethod
    def getByTimestamp(started_at):
        try:
            return Sensor.get(Sensor.started_at == started_at)
        except DoesNotExist:
            return None

    @staticmethod
    def getByUuid(uuid_str=None):
        if uuid_str is None:
            log.info("uuid is null")
            return None

        log.info("uuid is {}".format(uuid_str))

        try:
            return Sensor.get(Sensor.uuid == uuid_str).limit(1)
        except DoesNotExist:
            log.warn("Given sensor with uuid = {} not found!".format(uuid_str))
            return None


    @staticmethod
    def updateBatteryLevel(sensorBatteryLevel, sensor = None):
        if sensor is None:
            sensor = Sensor.currentSensor()

        if sensor is None:
            log.info("Cant sync battery level from master as sensor data is None")
            return

        if sensorBatteryLevel < 120:
            # This must be a wrong battery level. Some transmitter send those every couple of readings
            # even if the battery is ok.
            return

        startBatteryLevel = sensor.latest_battery_level

        sensor.latest_battery_level = sensorBatteryLevel

        if startBatteryLevel == sensor.latest_battery_level:
            # no need to update anything if nothing has changed.
            return

        sensor.save()
        SensorSendQueue.addToQueue(sensor)




    @staticmethod
    def updateSensorLocation(sensor_location):
        sensor = Sensor.currentSensor()
        if sensor is None:
            log.info("updateSensorLocation called but sensor is None")
            return

        sensor.sensor_location = sensor_location
        sensor.save()


    @staticmethod
    def upsertFromMaster(jsonSensor = None):
        if jsonSensor is None:
            log.warn("Got null sensor from json")
            return

        try:
            existingSensor = Sensor.getByUuid(jsonSensor.uuid)
            if existingSensor is None:
                log.info("saving new sensor record.")
                jsonSensor.save()
            else:
                log.info("updating existing sensor record.")
                existingSensor.started_at = jsonSensor.started_at
                existingSensor.stopped_at = jsonSensor.stopped_at
                existingSensor.latest_battery_level = jsonSensor.latest_battery_level
                existingSensor.sensor_location = jsonSensor.sensor_location
                existingSensor.save()
        except AssertionError as err:
            log.debug("Could not save Sensor: {}".format(err))


    def toJSON(self):
        return self.toS()

    @staticmethod
    def fromJSON(jsn):
        if not jsn:
            log.info("Empty json received in Sensor fromJson")
            return None
        try:
            log.d("Processing incoming json: " + jsn)
            dc = json.loads(jsn)
            return shortcuts.dict_to_model(Sensor, dc)
        except AssertionError as err:
            log.debug("Got exception parsing Sensor json: {}".format(err))
            return None
